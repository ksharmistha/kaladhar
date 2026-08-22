"""HTTP layer for the Kaladhar demo UI.

This is a THIN WRAPPER. Every endpoint calls the existing pipeline functions
unchanged -- no algorithm, threshold, metric or selection logic lives here. If
a number appears in the UI, it came out of the same code the CLI runs.

Nothing here calls Ekly. There is no Ekly API available to us, so step 4 of the
flow serves the operator sheet for a human to work from and the run sits in
AWAITING_CLIPS until real MP4s are uploaded.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kaladhar.config import RUNS                                    # noqa: E402
from kaladhar.fidelity.calibrate import calibrate                   # noqa: E402
from kaladhar.fidelity.safecut import MIN_KEEP_SECONDS, run_safe_cut  # noqa: E402
from kaladhar.input.ingest import IngestError, ingest               # noqa: E402
from kaladhar.input.validate import validate_image                  # noqa: E402
from kaladhar.pipeline import (export as pipe_export, import_clips,  # noqa: E402
                               score_all, select_best)
from kaladhar.planner.brief import (DEFAULT_PRODUCT, PRODUCT_DETAILS,  # noqa: E402
                                    as_operator_sheet, build_briefs)
from kaladhar.planner.matrix import AXIS_ORDER, difference_matrix   # noqa: E402
from kaladhar.planner.sampler import sample                         # noqa: E402
from kaladhar.storage.run import Run, Stopwatch                     # noqa: E402
from server.jobs import REGISTRY                                    # noqa: E402

app = FastAPI(title="Kaladhar Product Fidelity Studio")

DEMO_RUN = "run_m2_real"          # the real, fully-processed reference run
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


# --------------------------------------------------------------------- utils
def _run(run_id):
    try:
        return Run.load(run_id)
    except FileNotFoundError:
        raise HTTPException(404, "No such run: %s" % run_id)


def _safe_json(rel, run):
    return run.read_json(rel) if run.has(rel) else None


def _run_state(run):
    """Everything the UI needs to render any step of the flow."""
    meta = run.meta
    scores = {}
    sdir = run.path("scores")
    aux = {"summary.json", "selection.json", "calibration.json",
           "safecut.json", "diversity_full.json"}
    if sdir.exists():
        for p in sorted(sdir.glob("*.json")):
            if p.name in aux or p.stem.endswith("__safecut"):
                continue
            s = json.loads(p.read_text(encoding="utf-8"))
            if "fidelity_mean" not in s:
                continue
            scores[s.get("id", p.stem)] = {
                "id": s.get("id", p.stem),
                "fidelity_mean": s["fidelity_mean"],
                "fidelity_min": s["fidelity_min"],
                "fidelity_std": s["fidelity_std"],
                "worst_frame": s.get("worst_frame"),
                "means": s.get("means"),
                "motion": s.get("motion"),
                "frames_scored": s.get("frames_scored"),
                "stride": s.get("stride"),
                "info": s.get("info"),
                "per_frame": [
                    {"t": f.get("t"), "frame": f.get("frame"),
                     "fidelity": f.get("fidelity"),
                     "delta_e2000": f.get("delta_e2000"),
                     "weave_distance": f.get("weave_distance"),
                     "clip_cosine": f.get("clip_cosine"),
                     "mask_fraction": f.get("mask_fraction")}
                    for f in s.get("per_frame", []) if f.get("found")
                ],
            }

    briefs = _safe_json("briefs/briefs.json", run) or []
    return {
        "run_id": run.run_id,
        "state": meta.get("state"),
        "created": meta.get("created"),
        "history": meta.get("history", []),
        "timings": meta.get("timings", {}),
        "source": meta.get("source"),
        "plan": meta.get("plan"),
        "briefs": briefs,
        "axis_order": AXIS_ORDER,
        "sampling_report": _safe_json("briefs/sampling_report.json", run),
        "difference_matrix": (difference_matrix([b["axes"] for b in briefs])
                              if briefs else None),
        "imported": _safe_json("clips/imported.json", run) or [],
        "scores": scores,
        "selection": _safe_json("scores/selection.json", run),
        "calibration": _safe_json("scores/calibration.json", run),
        "diversity_full": _safe_json("scores/diversity_full.json", run),
        "safecut": _safe_json("scores/safecut.json", run),
        "exports": _safe_json("exports/exports.json", run) or [],
        "is_demo_run": run.run_id == DEMO_RUN,
        "safecut_min_keep_s": MIN_KEEP_SECONDS,
        "product": meta.get("product") or (briefs[0].get("product") if briefs else None),
        "known_products": sorted(PRODUCT_DETAILS.keys()),
    }


# ---------------------------------------------------------------------- runs
@app.get("/api/runs")
def list_runs():
    out = []
    for rid in Run.list_all():
        try:
            m = Run.load(rid).meta
            out.append({"run_id": rid, "state": m.get("state"),
                        "created": m.get("created"),
                        "is_demo_run": rid == DEMO_RUN})
        except Exception:
            continue
    out.sort(key=lambda r: (not r["is_demo_run"], r["created"]), reverse=False)
    return {"runs": out, "demo_run": DEMO_RUN}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    return _run_state(_run(run_id))


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str):
    if run_id == DEMO_RUN:
        raise HTTPException(400, "The reference run cannot be deleted.")
    shutil.rmtree(RUNS / run_id, ignore_errors=True)
    return {"deleted": run_id}


# ------------------------------------------------- step 1: upload + validate
@app.post("/api/runs")
async def create_run(file: UploadFile = File(...)):
    run = Run.create()
    suffix = Path(file.filename or "upload.jpg").suffix.lower() or ".jpg"
    dst = run.path("input/upload" + suffix)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "wb") as fh:
        shutil.copyfileobj(file.file, fh)

    report = validate_image(dst)
    run.meta["upload"] = {"filename": file.filename, "path": str(dst),
                          "validation": report.as_dict()}
    run.save()
    return {"run_id": run.run_id, "validation": report.as_dict(),
            "preview": "/api/runs/%s/file/input/upload%s" % (run.run_id, suffix),
            "ok": report.ok}


# ------------------------------------------------------- step 2: analyse
@app.post("/api/runs/{run_id}/analyze")
def analyze(run_id: str):
    run = _run(run_id)
    up = run.meta.get("upload")
    if not up:
        raise HTTPException(400, "No image uploaded for this run.")
    try:
        ingest(up["path"], run=run)
    except IngestError as exc:
        raise HTTPException(422, str(exc))
    return _run_state(Run.load(run_id))


# ------------------------------------------------------- step 3: briefs
@app.post("/api/runs/{run_id}/briefs")
def make_briefs(run_id: str, n: int = Form(6), seed: int = Form(7),
                product: str = Form(DEFAULT_PRODUCT)):
    run = _run(run_id)
    if not run.has("input/reference.png"):
        raise HTTPException(400, "Analyse the product image first.")
    # The product type is DECLARED by the operator, not detected. We have no
    # garment classifier, and guessing one would be inventing a capability.
    product = (product or DEFAULT_PRODUCT).strip().lower()
    with Stopwatch(run, "plan_briefs"):
        points, report = sample(n=n, seed=seed)
        briefs = build_briefs(points, product_noun=product)
    run.write_json("briefs/briefs.json", briefs)
    run.write_json("briefs/sampling_report.json", report)
    run.path("briefs/EKLY_SHEET.txt").write_text(
        as_operator_sheet(briefs, run.run_id, str(run.path("input/reference.png"))),
        encoding="utf-8")
    run.meta["product"] = product
    run.meta["plan"] = {
        "n_briefs": len(briefs),
        "product": product,
        "min_axis_diff_achieved": report["min_axis_diff_achieved"],
        "expected_credits": round(sum(
            b["ekly_settings"]["expected_credits"] for b in briefs), 2)}
    run.set_state("AWAITING_CLIPS",
                  "%d briefs ready for manual Ekly generation" % len(briefs))
    return _run_state(Run.load(run_id))


@app.get("/api/runs/{run_id}/sheet")
def get_sheet(run_id: str):
    run = _run(run_id)
    p = run.path("briefs/EKLY_SHEET.txt")
    if not p.exists():
        raise HTTPException(404, "No operator sheet yet.")
    return PlainTextResponse(p.read_text(encoding="utf-8"))


# ------------------------------------------------------- step 5: import
@app.post("/api/runs/{run_id}/clips")
async def upload_clips(run_id: str, files: list[UploadFile] = File(...)):
    run = _run(run_id)
    inbox = run.path("inbox")
    inbox.mkdir(parents=True, exist_ok=True)
    saved = 0
    for f in files:
        name = Path(f.filename or "clip.mp4").name
        if Path(name).suffix.lower() not in VIDEO_EXT:
            continue
        with open(inbox / name, "wb") as fh:
            shutil.copyfileobj(f.file, fh)
        saved += 1
    if not saved:
        raise HTTPException(400, "No usable video files were uploaded.")
    import_clips(run, inbox)
    return _run_state(Run.load(run_id))


# ------------------------------------------------------- step 6: score
@app.post("/api/runs/{run_id}/score")
def start_score(run_id: str, stride: int = Form(5)):
    run = _run(run_id)
    imported = _safe_json("clips/imported.json", run) or []
    if not imported:
        raise HTTPException(400, "Import clips first.")

    total = len(imported)
    job = REGISTRY.create("score", total=total,
                          label="Fidelity Lock over %d clip(s)" % total)
    aux = {"summary.json", "selection.json", "calibration.json",
           "safecut.json", "diversity_full.json"}

    def _watch(j):
        # Progress is read from score files actually landing on disk, so it
        # reflects completed work rather than an estimate.
        d = run.path("scores")
        if not d.exists():
            return
        n = len([p for p in d.glob("*.json")
                 if p.name not in aux and not p.stem.endswith("__safecut")])
        j.done = min(n, total)

    def _work(j):
        j.note("scoring %d clip(s) at stride %d" % (total, stride))
        scores = score_all(run, stride=stride, progress=False)
        j.note("scored %d clip(s)" % len(scores))
        return {"scored": len(scores)}

    REGISTRY.run(job, _work, watcher=_watch)
    return {"job": job.as_dict()}


# ------------------------------------------------------- calibrate
@app.post("/api/runs/{run_id}/calibrate")
def do_calibrate(run_id: str):
    run = _run(run_id)
    job = REGISTRY.create("calibrate", total=1, label="Calibrating threshold")

    def _work(j):
        rep = calibrate(run)
        return {"proposed_threshold": rep["proposed_threshold"]}

    REGISTRY.run(job, _work)
    return {"job": job.as_dict()}


# ------------------------------------------------------- step 7: select
@app.post("/api/runs/{run_id}/select")
def do_select(run_id: str, k: int = Form(6), threshold: float = Form(None)):
    run = _run(run_id)
    job = REGISTRY.create("select", total=1, label="Gate 1 + Gate 2")

    def _work(j):
        j.note("embedding clips and running both gates")
        res = select_best(run, k=k, threshold=threshold)
        return {"selected": res.get("diversity", {}).get("selected_ids", [])}

    REGISTRY.run(job, _work)
    return {"job": job.as_dict()}


# ------------------------------------------------------- step 8: safecut
@app.post("/api/runs/{run_id}/safecut")
def do_safecut(run_id: str, threshold: float = Form(...)):
    run = _run(run_id)
    job = REGISTRY.create("safecut", total=1, label="Safe Cut analysis")

    def _work(j):
        recs = run_safe_cut(run, threshold=threshold)
        applied = len([r for r in recs if r.get("applied")])
        return {"considered": len(recs), "applied": applied}

    REGISTRY.run(job, _work)
    return {"job": job.as_dict()}


# ------------------------------------------------------- step 8: export
@app.post("/api/runs/{run_id}/export")
def do_export(run_id: str, mode: str = Form("auto")):
    run = _run(run_id)
    if not run.has("scores/selection.json"):
        raise HTTPException(400, "Run selection first.")
    sel = run.read_json("scores/selection.json")
    ids = sel.get("diversity", {}).get("selected_ids", [])
    job = REGISTRY.create("export", total=max(len(ids), 1),
                          label="Exporting %d clip(s) to 1080x1920" % len(ids))

    def _watch(j):
        d = run.path("exports")
        if d.exists():
            j.done = min(len(list(d.glob("*.mp4"))), j.total)

    def _work(j):
        out = pipe_export(run, mode=mode)
        return {"exported": len(out)}

    REGISTRY.run(job, _work, watcher=_watch)
    return {"job": job.as_dict()}


# ------------------------------------------------------------------- jobs
@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = REGISTRY.get(job_id)
    if not job:
        raise HTTPException(404, "No such job")
    return job.as_dict()


# ------------------------------------------------------------------- files
@app.get("/api/runs/{run_id}/file/{path:path}")
def get_file(run_id: str, path: str):
    run = _run(run_id)
    target = (run.root / path).resolve()
    if not str(target).startswith(str(run.root.resolve())):
        raise HTTPException(403, "Path outside the run directory.")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "No such file: %s" % path)
    return FileResponse(target)


@app.get("/api/health")
def health():
    return {"ok": True, "runs": len(Run.list_all()), "demo_run": DEMO_RUN,
            "ts": time.strftime("%H:%M:%S")}


# ------------------------------------------------------------------ static
STATIC = ROOT / "static"
app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
