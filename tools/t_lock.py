import sys, pathlib, json, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from PIL import Image
from kaladhar.storage.run import Run
from kaladhar.fidelity.lock import score_clip

run = Run.load("run_demo")
sig = run.read_json("input/signature.json")
patch = np.asarray(Image.open(run.path("input/border_patch.png")).convert("RGB"))

t = time.perf_counter()
res = score_clip("assets/clips/proto_01.mp4", sig, patch, stride=5)
print("TOTAL %.1fs  (scoring_seconds=%s)" % (time.perf_counter()-t, res["scoring_seconds"]))
print()
print("FIDELITY  mean=%.2f  min=%.2f  std=%.2f" % (
    res["fidelity_mean"], res["fidelity_min"], res["fidelity_std"]))
print("WORST FRAME", res["worst_frame"])
print("MEANS", json.dumps(res["means"]))
print("MOTION", json.dumps(res["motion"]))
print()
print("PER-FRAME SERIES")
print(" idx    t     dE2000  weave   clipcos  ssim   conf   FIDELITY")
for f in res["per_frame"]:
    if not f.get("found"):
        print(" %3d  skipped" % f["frame"]); continue
    print(" %3d  %5.2f  %6.2f  %6.4f  %6.4f  %5.3f  %5.3f   %6.2f" % (
        f["frame"], f["t"], f["delta_e2000"], f["weave_distance"],
        f["clip_cosine"], f["ssim"], f["ssim_confidence"], f["fidelity"]))
run.write_json("scores/proto_01.json", res)
print()
print("saved scores/proto_01.json")
