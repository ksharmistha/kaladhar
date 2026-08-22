import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
R = pathlib.Path("runs/run_m2_real/scores")
print("%-20s %8s %8s %8s | %9s %9s" % ("clip","mask_mean","mask_min","mask_max","motion_max","note"))
for n in ["BASELINE-courtyard","MANDAP-dusk","MANSION-marble","ROOFTOP-night"]:
    s = json.load(open(R/(n+".json")))
    mf = [f["mask_fraction"] for f in s["per_frame"] if f.get("found")]
    a = np.array(mf)
    note = "product tiny in frame" if a.mean() < 0.12 else ""
    spike = s["motion"]["max"]
    print("%-20s %8.4f %8.4f %8.4f | %9.4f %9s" % (n, a.mean(), a.min(), a.max(), spike, note))
print()
print("Source garment fraction for reference: 0.3570")
print()
print("MANSION-marble motion series (first 12, stride 2 frames):")
s = json.load(open(R/"MANSION-marble.json"))
print(" ", [round(x,4) for x in s["motion_series"][:12]])
print("  -> a spike this large in the first fractions of a second is a hard scene cut")
