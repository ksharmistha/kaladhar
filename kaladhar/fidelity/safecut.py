"""Safe Cut -- recovering a usable ad from a clip that dips below threshold.

Motivation comes straight from what the per-frame scoring showed: product drift
in these clips is LOCAL AND TRANSIENT, not global. A clip can be perfectly
faithful for four seconds and fall apart for one. Rejecting the whole clip
throws away good footage, and at 45.50 credits per generation that is expensive
waste.

Safe Cut finds the longest CONTIGUOUS window in which every scored frame clears
the fidelity threshold, and trims the clip to that window -- but only when the
result is still long enough to work as an ad.

Deliberate limits, so this cannot be used to launder a bad clip into a good one:

  * It only trims. It never re-generates, re-colours or repairs anything.
  * The kept window must be a single contiguous run. Stitching together
    scattered good frames would change the motion and produce a jump cut.
  * The window must be at least MIN_KEEP_SECONDS long, otherwise the clip is
    left rejected rather than cut down to something unusable.
  * The trimmed clip is RE-SCORED from the trimmed file. The reported score is
    measured on the actual output, never inherited from the parent.
"""
from __future__ import annotations

import time

from kaladhar.video.io import probe, trim

# A vertical social ad shorter than this stops reading as an ad. Below it we
# would rather reject the clip than ship a fragment.
MIN_KEEP_SECONDS = 3.0

# Safety margin around the cut, in seconds. The scored frames are sampled every
# Nth frame, so the true boundary of the bad region can sit slightly outside the
# last frame we measured.
EDGE_MARGIN_S = 0.10


def _passing_runs(per_frame, threshold):
    """Contiguous runs of scored frames at or above the threshold.

    Frames that failed to score at all (no garment found) break a run -- we
    cannot claim a window is clean across a frame we never measured.
    """
    runs, cur = [], []
    for f in per_frame:
        ok = f.get("found") and f.get("fidelity", 0) >= threshold
        if ok:
            cur.append(f)
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def analyse(score, threshold, min_keep=MIN_KEEP_SECONDS):
    """Decide whether a clip is a Safe Cut candidate, without touching files."""
    per_frame = score.get("per_frame", [])
    scored = [f for f in per_frame if f.get("found")]
    if not scored:
        return {"applicable": False, "reason": "no scorable frames"}

    failing = [f for f in scored if f["fidelity"] < threshold]
    duration = score.get("info", {}).get("duration_s") or 0.0

    if not failing:
        return {"applicable": False,
                "reason": "every scored frame already clears the threshold; "
                          "nothing to cut"}

    runs = _passing_runs(per_frame, threshold)
    if not runs:
        return {"applicable": False,
                "reason": "no contiguous passing window exists -- the clip fails "
                          "throughout, so trimming cannot recover it"}

    best = max(runs, key=lambda r: r[-1]["t"] - r[0]["t"])
    start = max(0.0, best[0]["t"] + EDGE_MARGIN_S)
    end = min(duration, best[-1]["t"] - EDGE_MARGIN_S)
    kept = end - start

    if kept < min_keep:
        return {"applicable": False,
                "reason": "longest passing window is %.2fs, under the %.1fs minimum "
                          "for a usable ad" % (max(kept, 0.0), min_keep),
                "longest_window_s": round(max(kept, 0.0), 3)}

    return {
        "applicable": True,
        "start_s": round(start, 3),
        "end_s": round(end, 3),
        "kept_s": round(kept, 3),
        "removed_s": round(duration - kept, 3),
        "frames_below_threshold": len(failing),
        "frames_scored": len(scored),
        "threshold": threshold,
        "reason": "trimming to the longest contiguous passing window",
    }


def safe_cut(run, clip_id, score, threshold, sig, src_patch, stride=5,
              min_keep=MIN_KEEP_SECONDS):
    """Apply Safe Cut and re-score the trimmed file.

    Returns a record describing what was done and what the trimmed clip actually
    measures. If the clip is not a candidate, returns the analysis unchanged.
    """
    from kaladhar.fidelity.lock import score_clip

    plan = analyse(score, threshold, min_keep=min_keep)
    if not plan.get("applicable"):
        plan["clip_id"] = clip_id
        plan["applied"] = False
        return plan

    t0 = time.perf_counter()
    src = score["clip"]
    dst = run.path("clips/%s__safecut.mp4" % clip_id)
    trim(src, dst, plan["start_s"], plan["end_s"])

    new_score = score_clip(dst, sig, src_patch, stride=stride)
    new_score["id"] = "%s__safecut" % clip_id
    new_score["safecut_parent"] = clip_id
    run.write_json("scores/%s__safecut.json" % clip_id, new_score)

    plan.update({
        "clip_id": clip_id,
        "applied": True,
        "output": str(dst),
        "output_probe": probe(dst),
        "before": {"mean": score["fidelity_mean"], "min": score["fidelity_min"],
                   "duration_s": score["info"]["duration_s"]},
        "after": {"mean": new_score["fidelity_mean"], "min": new_score["fidelity_min"],
                  "duration_s": new_score["info"]["duration_s"]},
        "now_passes": new_score["fidelity_mean"] >= threshold
                      and new_score["fidelity_min"] >= threshold,
        "seconds": round(time.perf_counter() - t0, 2),
    })
    return plan


def run_safe_cut(run, threshold, stride=5, min_keep=MIN_KEEP_SECONDS):
    """Consider every scored clip in the run. Returns a list of records."""
    import numpy as np
    from PIL import Image

    sig = run.read_json("input/signature.json")
    pp = run.path("input/border_patch.png")
    patch = np.asarray(Image.open(pp).convert("RGB")) if pp.exists() else None

    aux = {"summary.json", "selection.json", "calibration.json", "safecut.json"}
    out = []
    for p in sorted(run.path("scores").glob("*.json")):
        if p.name in aux or p.stem.endswith("__safecut"):
            continue
        s = run.read_json("scores/%s" % p.name)
        if "fidelity_mean" not in s:
            continue
        out.append(safe_cut(run, s.get("id", p.stem), s, threshold, sig, patch,
                            stride=stride, min_keep=min_keep))

    run.write_json("scores/safecut.json", out)
    return out
