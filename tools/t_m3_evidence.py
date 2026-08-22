"""Milestone 3.1 / 3.2 evidence generator.

Read-only with respect to every run: it probes files and re-times operations on
copies held in memory. It never writes into runs/, never re-scores a clip and
never alters a measured result.

Produces:
  evidence/m3_performance.json      stage timings, hot-spot analysis, warm-cache repeat timings
  evidence/m3_stage_timings.png     stage breakdown chart
  evidence/m3_delivery_manifest.json  per-export delivery spec read from the finished files
"""
import json
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import imageio_ffmpeg  # noqa: E402
from kaladhar.storage.run import Run  # noqa: E402
from kaladhar.video.io import probe  # noqa: E402

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "run_m2_real"
EV = pathlib.Path("evidence")
EV.mkdir(exist_ok=True)

run = Run.load(RUN_ID)
timings = dict(run.meta.get("timings", {}))
n_clips = len(run.read_json("clips/imported.json")) if run.has("clips/imported.json") else 0
n_exports = len(run.read_json("exports/exports.json")) if run.has("exports/exports.json") else 0

# ---------------------------------------------------------------- 3.1 timings
# ingest_total is a roll-up of validate+preprocess+segment+signature, so it is
# excluded from the sum to avoid double counting.
ROLLUPS = {"ingest_total"}
stages = {k: v for k, v in timings.items() if k not in ROLLUPS}
total = sum(stages.values())
ranked = sorted(stages.items(), key=lambda kv: -kv[1])

print("=" * 72)
print("3.1  END-TO-END PIPELINE TIMING  —  run %s" % RUN_ID)
print("=" * 72)
print("  %-20s %10s %8s" % ("stage", "seconds", "share"))
for k, v in ranked:
    print("  %-20s %10.3f %7.1f%%" % (k, v, 100 * v / total))
print("  %-20s %10.3f %7s" % ("TOTAL AUTOMATED", total, "100%"))
print()
print("  Clips processed              : %d" % n_clips)
if n_clips:
    print("  Scoring throughput           : %.1f s per clip" % (stages.get("score_all", 0) / n_clips))
if n_exports:
    print("  Export throughput            : %.1f s per exported ad" % (stages.get("export", 0) / n_exports))
print("  Dominant stage               : %s (%.1f%% of total)" % (ranked[0][0], 100 * ranked[0][1] / total))
print("  Ekly generation time         : NOT INCLUDED — manual web step, no API, never measured")
print()

# --------------------------------------------------- 3.1 warm-cache repeat run
# Demonstrates that repeating work is cheap: the ONNX sessions for segmentation
# and CLIP are loaded once per process and reused. Measured on the run's own
# working image, in memory, writing nothing.
print("=" * 72)
print("3.1  REPEATABILITY — warm-cache cost of repeating the same work")
print("=" * 72)
from kaladhar.diversity.embed import embed  # noqa: E402
from kaladhar.input.segment import segment  # noqa: E402

img = Image.open(run.path("input/working.png")).convert("RGB")
seg_times, emb_times = [], []
for i in range(3):
    t = time.perf_counter(); segment(img); seg_times.append(time.perf_counter() - t)
for i in range(3):
    t = time.perf_counter(); embed([img]); emb_times.append(time.perf_counter() - t)

print("  segmentation  call 1 %.3fs | call 2 %.3fs | call 3 %.3fs" % tuple(seg_times))
print("  CLIP embed    call 1 %.3fs | call 2 %.3fs | call 3 %.3fs" % tuple(emb_times))
print("  -> model sessions are loaded once per process and reused across calls,")
print("     so repeated processing pays the inference cost only, not model load.")
print()

# ----------------------------------------- 3.1 measured effect of frame stride
# The single largest lever. Re-times mask extraction at full resolution vs the
# 512px working resolution the Fidelity Lock actually uses.
from kaladhar.fidelity.lock import SEG_LONG_EDGE  # noqa: E402
from kaladhar.config import FRAME_STRIDE  # noqa: E402

# Measured on a real VIDEO FRAME, because that is the workload this
# optimisation targets -- the Fidelity Lock segments frames, not the source
# photograph. Frames are larger than the source here (768x1152 vs 500x724).
from kaladhar.video.io import sample_frames  # noqa: E402

first_clip = (run.read_json("clips/imported.json")[0]["path"]
              if run.has("clips/imported.json") else None)
frame = sample_frames(first_clip, stride=1, max_frames=1)[0][1] if first_clip else img
fw, fh = frame.size
fsmall = frame.resize((max(1, round(fw * SEG_LONG_EDGE / max(fw, fh))),
                       max(1, round(fh * SEG_LONG_EDGE / max(fw, fh)))))
t = time.perf_counter(); m_full = segment(frame); t_full = time.perf_counter() - t
t = time.perf_counter(); m_small = segment(fsmall); t_small = time.perf_counter() - t
frames_per_clip = None
sc = [k for k in run.path("scores").glob("*.json")] if run.path("scores").exists() else []
for f in sc:
    d = json.loads(f.read_text(encoding="utf-8"))
    if "frames_scored" in d:
        frames_per_clip = d["frames_scored"]; total_frames = d["info"]["frame_count"]; break

print("=" * 72)
print("3.1  OPTIMISATIONS IN EFFECT — measured, on a real video frame")
print("=" * 72)
print("  A. segmentation resolution (the per-frame cost)")
print("     full frame %-12s %.3fs   garment fraction %.4f" % (str(frame.size), t_full, m_full.garment_fraction))
print("     %dpx long edge %-9s %.3fs   garment fraction %.4f" % (SEG_LONG_EDGE, str(fsmall.size), t_small, m_small.garment_fraction))
print("     speed-up %.1fx for a %.4f change in the measured mask" % (
    t_full / max(t_small, 1e-6), abs(m_full.garment_fraction - m_small.garment_fraction)))
if frames_per_clip:
    print("  B. frame stride: %d of %d frames scored per clip (every %dth)"
          % (frames_per_clip, total_frames, FRAME_STRIDE))
    print("     without it, scoring would touch %.1fx more frames" % (total_frames / frames_per_clip))
print("  C. model sessions cached per process (see repeatability above)")
print("  D. CLIP embeddings batched 16 at a time")
print()

perf = {
    "run_id": RUN_ID,
    "stage_seconds": stages,
    "rollups_excluded": sorted(ROLLUPS),
    "total_automated_seconds": round(total, 3),
    "ranked_stages": [{"stage": k, "seconds": round(v, 3), "share_pct": round(100 * v / total, 1)}
                      for k, v in ranked],
    "dominant_stage": ranked[0][0],
    "clips_processed": n_clips,
    "exports_produced": n_exports,
    "seconds_per_clip_scoring": round(stages.get("score_all", 0) / n_clips, 2) if n_clips else None,
    "seconds_per_export": round(stages.get("export", 0) / n_exports, 2) if n_exports else None,
    "warm_cache_repeat": {
        "segment_calls_seconds": [round(x, 3) for x in seg_times],
        "clip_embed_calls_seconds": [round(x, 3) for x in emb_times],
    },
    "segmentation_resolution_optimisation": {
        "measured_on": "real video frame from the first imported clip",
        "full_res_size": list(frame.size), "full_res_seconds": round(t_full, 3),
        "reduced_size": list(fsmall.size), "reduced_seconds": round(t_small, 3),
        "speedup_x": round(t_full / max(t_small, 1e-6), 2),
        "garment_fraction_full": round(m_full.garment_fraction, 4),
        "garment_fraction_reduced": round(m_small.garment_fraction, 4),
    },
    "frame_stride": FRAME_STRIDE,
    "frames_scored_per_clip": frames_per_clip,
    "excluded": "Ekly generation time is a manual web-interface step with no API and was never measured.",
}
(EV / "m3_performance.json").write_text(json.dumps(perf, indent=2), encoding="utf-8")

# ------------------------------------------------------------- timing chart
fig, ax = plt.subplots(figsize=(9, 4.2))
names = [k for k, _ in ranked][::-1]
vals = [v for _, v in ranked][::-1]
cols = ["#a8342a" if v == max(vals) else "#0e7d8c" for v in vals]
bars = ax.barh(names, vals, color=cols, height=.62)
for b, v in zip(bars, vals):
    ax.text(v + total * .012, b.get_y() + b.get_height() / 2,
            "%.2fs  (%.1f%%)" % (v, 100 * v / total), va="center", fontsize=9)
ax.set_xlim(0, max(vals) * 1.28)
ax.set_xlabel("seconds")
ax.set_title("Automated pipeline stage timings — run %s\n"
             "total %.1fs for %d clips · %s dominates at %.1f%%"
             % (RUN_ID, total, n_clips, ranked[0][0], 100 * ranked[0][1] / total), fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", alpha=.25)
fig.tight_layout()
fig.savefig(EV / "m3_stage_timings.png", dpi=150)
plt.close(fig)

# --------------------------------------------------- 3.2 delivery manifest
print("=" * 72)
print("3.2  DELIVERY MANIFEST — read from the finished export files")
print("=" * 72)
ff = imageio_ffmpeg.get_ffmpeg_exe()
manifest = []
for e in (run.read_json("exports/exports.json") if run.has("exports/exports.json") else []):
    path = run.path("exports/%s_1080x1920.mp4" % e["id"])
    info = probe(path)
    err = subprocess.run([ff, "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    vline = next((l.strip() for l in err.split("\n") if "Video:" in l), "")
    codec = vline.split("Video:")[1].split(",")[0].strip() if "Video:" in vline else "?"
    pixfmt = next((p for p in ("yuv420p", "yuv422p", "yuv444p") if p in vline), "?")
    brand = next((l.split(":")[1].strip() for l in err.split("\n") if "major_brand" in l), "?")
    rec = {
        "id": e["id"],
        "file": os.path.basename(str(path)),
        "width": info["width"], "height": info["height"],
        "aspect": info["aspect"], "is_9_16": info["is_9_16"],
        "is_1080x1920": info["is_1080x1920"],
        "duration_s": info["duration_s"], "fps": info["fps"],
        "frame_count": info["frame_count"], "file_mb": info["file_mb"],
        "codec": codec, "pix_fmt": pixfmt, "container_brand": brand,
        "fit_mode": e["mode"],
        "fit_rationale": e.get("mode_decision", {}).get("rationale", ""),
        "conforms": bool(info["is_9_16"] and info["is_1080x1920"]),
    }
    manifest.append(rec)
    print("  %-20s %dx%d  %.4f  %.2fs @ %.0ffps  %s / %s  %.2f MB  %s"
          % (rec["id"], rec["width"], rec["height"], rec["aspect"], rec["duration_s"],
             rec["fps"], rec["codec"], rec["pix_fmt"], rec["file_mb"],
             "CONFORMS" if rec["conforms"] else "DOES NOT CONFORM"))

allc = manifest and all(r["conforms"] for r in manifest)
print()
print("  %d/%d exports conform to 1080x1920 / 9:16" % (sum(r["conforms"] for r in manifest), len(manifest)))
print("  Target placements: Instagram Reels & Stories, Facebook Reels, Meta feed vertical, YouTube Shorts")
print("  Conformance is read from the written files, not from encoder settings.")

(EV / "m3_delivery_manifest.json").write_text(json.dumps({
    "run_id": RUN_ID,
    "exports": manifest,
    "all_conform": bool(allc),
    "delivery_target": {"width": 1080, "height": 1920, "aspect": 0.5625,
                        "placements": ["Instagram Reels", "Instagram Stories",
                                       "Facebook Reels", "Meta vertical feed",
                                       "YouTube Shorts"]},
    "verification": "Resolution, aspect, duration, fps and frame count read back from the written files with probe(); codec, pixel format and container brand read with ffmpeg.",
}, indent=2), encoding="utf-8")

print()
print("wrote evidence/m3_performance.json, evidence/m3_stage_timings.png, evidence/m3_delivery_manifest.json")
