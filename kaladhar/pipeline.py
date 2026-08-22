"""End-to-end orchestration.

One runnable flow from a product image to exported 1080x1920 ads, with the
manual Ekly generation step modelled explicitly as a pause rather than hidden.

    plan()          A  ingest  ->  B  briefs   ->  state AWAITING_CLIPS
                                                   [ human generates in Ekly ]
    resume()        clips in   ->  D  fidelity ->  E  diversity -> F review
    export()        G  convert to 9:16 / 1080x1920

This is deliberately not a single uninterrupted function. Ekly exposes no API
to us, so the honest shape of the workflow is two automated halves either side
of one clearly marked manual step. Pretending otherwise would mean writing code
that claims to do something it cannot.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PIL import Image

from kaladhar.config import EXPORT_H, EXPORT_W
from kaladhar.diversity.select import clip_embedding, select
from kaladhar.fidelity.lock import score_clip
from kaladhar.fidelity.report import drift_plot, weave_guard
from kaladhar.input.ingest import ingest
from kaladhar.planner.brief import (DEFAULT_PRODUCT, as_operator_sheet,
                                    build_briefs)
from kaladhar.planner.sampler import sample
from kaladhar.storage.run import Run, Stopwatch
from kaladhar.video.io import probe, to_9_16

VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


# --------------------------------------------------------------------- plan
def plan(source, n=6, seed=0, run_id=None, product_noun=DEFAULT_PRODUCT):
    """Stages A and B. Ends at AWAITING_CLIPS with an operator sheet on disk."""
    run = ingest(source, run_id=run_id)

    with Stopwatch(run, "plan_briefs"):
        points, report = sample(n=n, seed=seed)
        briefs = build_briefs(points, product_noun=product_noun)

    run.write_json("briefs/briefs.json", briefs)
    run.write_json("briefs/sampling_report.json", report)

    sheet = as_operator_sheet(briefs, run.run_id, str(run.path("input/reference.png")))
    run.path("briefs/EKLY_SHEET.txt").write_text(sheet, encoding="utf-8")

    run.meta["plan"] = {
        "n_briefs": len(briefs),
        "min_axis_diff_achieved": report["min_axis_diff_achieved"],
        "expected_credits": round(sum(
            b["ekly_settings"]["expected_credits"] for b in briefs), 2),
    }
    run.set_state("AWAITING_CLIPS", "%d briefs ready for manual Ekly generation" % len(briefs))
    return run, briefs


# ------------------------------------------------------------------- import
def import_clips(run, folder):
    """Bring downloaded Ekly clips into the run and probe each one.

    Association with the brief that produced it is by filename (V01.mp4 ->
    brief V01), which is what the operator sheet instructs. Anything that does
    not match a brief is still imported and flagged rather than dropped.
    """
    folder = Path(folder)
    files = sorted(p for p in folder.iterdir()
                   if p.suffix.lower() in VIDEO_EXT and p.is_file())
    if not files:
        raise FileNotFoundError("No video files found in %s" % folder)

    briefs = run.read_json("briefs/briefs.json") if run.has("briefs/briefs.json") else []
    by_id = {b["id"]: b for b in briefs}

    imported = []
    for f in files:
        cid = f.stem.upper().split("_")[0]
        dst = run.ingest(f, "clips/%s%s" % (f.stem, f.suffix.lower()))
        info = probe(dst)
        rec = {
            "id": f.stem,
            "path": str(dst),
            "brief_id": cid if cid in by_id else None,
            "matched_brief": cid in by_id,
            "probe": info,
            "format_ok": info["is_9_16"],
        }
        if not info["is_9_16"]:
            rec["format_note"] = (
                "Delivered at %dx%d (aspect %.3f), not 9:16. Conversion to "
                "%dx%d happens at export." % (info["width"], info["height"],
                                              info["aspect"], EXPORT_W, EXPORT_H))
        imported.append(rec)

    run.write_json("clips/imported.json", imported)
    run.set_state("CLIPS_IMPORTED", "%d clips imported" % len(imported))
    return imported


# -------------------------------------------------------------------- score
def score_all(run, stride=5, progress=True):
    """Stage D: Fidelity Lock over every imported clip, plus evidence."""
    sig = run.read_json("input/signature.json")
    patch_path = run.path("input/border_patch.png")
    patch = np.asarray(Image.open(patch_path).convert("RGB")) if patch_path.exists() else None

    imported = run.read_json("clips/imported.json")
    # If this run has already been calibrated, draw the pass line on the plots.
    thr = None
    if run.has("scores/calibration.json"):
        thr = run.read_json("scores/calibration.json").get("proposed_threshold")

    scores = []
    t0 = time.perf_counter()
    for rec in imported:
        if progress:
            print("  scoring %s ..." % rec["id"], flush=True)
        s = score_clip(rec["path"], sig, patch, stride=stride)
        s["id"] = rec["id"]
        s["brief_id"] = rec.get("brief_id")
        run.write_json("scores/%s.json" % rec["id"], s)

        try:
            drift_plot(s, run.path("evidence/drift_%s.png" % rec["id"]),
                       threshold=thr, title=rec["id"])
            if patch is not None:
                weave_guard(patch, s, rec["path"],
                            run.path("evidence/weave_%s.png" % rec["id"]))
        except Exception as exc:                      # evidence is not worth failing a run
            s["evidence_error"] = str(exc)
        scores.append(s)

    run.record_timing("score_all", time.perf_counter() - t0)
    run.write_json("scores/summary.json", [
        {k: s.get(k) for k in ("id", "brief_id", "fidelity_mean", "fidelity_min",
                               "fidelity_std", "worst_frame", "means", "motion")}
        for s in scores])
    run.set_state("SCORED", "%d clips scored" % len(scores))
    return scores


# ------------------------------------------------------------------- select
def select_best(run, k=6, threshold=None, motion_min=0.002, motion_max=0.25):
    """Gate 1 (fidelity) then Gate 2 (diversity).

    A clip must pass BOTH to be exported: Gate 1 rejects it for drifting off
    the product, Gate 2 rejects it for looking too much like another clip.
    """
    # summary/selection/calibration live alongside the per-clip score files, so
    # they are excluded by name rather than by assuming every json here is a clip.
    aux = {"summary.json", "selection.json", "calibration.json", "safecut.json",
           "diversity_full.json"}
    scores = {}
    for p in sorted(run.path("scores").glob("*.json")):
        # Safe Cut outputs are derivatives of a parent clip, not independent
        # candidates -- gating them again would double-count the same footage.
        if p.name in aux or p.stem.endswith("__safecut"):
            continue
        s = run.read_json("scores/%s" % p.name)
        if "fidelity_mean" not in s:
            continue
        scores[s.get("id", p.stem)] = s

    passing, rejected = [], []
    for cid, s in scores.items():
        reasons = []
        if threshold is not None and s.get("fidelity_mean", 0) < threshold:
            reasons.append("fidelity_mean %.1f below threshold %.1f"
                           % (s["fidelity_mean"], threshold))
        m = s.get("motion", {})
        if m.get("mean", 0) < motion_min:
            reasons.append("effectively static (motion %.4f) -- generator ignored "
                           "the camera direction" % m.get("mean", 0))
        if m.get("max", 0) > motion_max:
            reasons.append("motion spike %.3f -- likely flicker or a cut" % m.get("max", 0))
        (rejected if reasons else passing).append(
            {"id": cid, "fidelity_mean": s.get("fidelity_mean"),
             "fidelity_min": s.get("fidelity_min"), "reasons": reasons,
             "clip": s["clip"]})

    result = {"gate1_passing": passing, "gate1_rejected": rejected,
              "threshold_used": threshold}

    if len(passing) >= 2:
        with Stopwatch(run, "diversity_embed"):
            cands = [{"id": p["id"], "clip": p["clip"],
                      "embedding": clip_embedding(p["clip"])} for p in passing]
        result["diversity"] = select(cands, k=k)
    elif passing:
        result["diversity"] = {"selected_ids": [passing[0]["id"]],
                               "note": "Only one clip passed Gate 1; "
                                       "diversity selection needs at least two."}
    else:
        result["diversity"] = {"selected_ids": [],
                               "note": "No clip passed Gate 1."}

    run.write_json("scores/selection.json", result)
    run.set_state("SELECTED", "%d selected" % len(result["diversity"].get("selected_ids", [])))
    return result


# ------------------------------------------------------------------- export
def export(run, ids=None, mode="auto"):
    """Stage G: convert selected clips to the delivery format.

    mode="auto" decides crop vs pad per clip by measuring how much of the
    garment a crop would actually destroy -- see exporter/decide.py.
    """
    from kaladhar.exporter.decide import choose_mode

    sel = run.read_json("scores/selection.json")
    ids = ids or sel["diversity"].get("selected_ids", [])
    imported = {r["id"]: r for r in run.read_json("clips/imported.json")}

    out = []
    t0 = time.perf_counter()
    for cid in ids:
        rec = imported.get(cid)
        if not rec:
            continue
        if mode == "auto":
            chosen, rationale = choose_mode(rec["path"])
        else:
            chosen, rationale = mode, {"rationale": "mode forced to %s by the caller" % mode}
        dst = run.path("exports/%s_1080x1920.mp4" % cid)
        info = to_9_16(rec["path"], dst, mode=chosen)
        out.append({"id": cid, "export": str(dst), "mode": chosen,
                    "mode_decision": rationale, "probe": info,
                    "conforms": info["is_1080x1920"] and info["is_9_16"]})
    run.record_timing("export", time.perf_counter() - t0)
    run.write_json("exports/exports.json", out)
    run.set_state("EXPORTED", "%d exported" % len(out))
    return out
