import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
R = pathlib.Path("runs/run_m2_real/scores")
for name in ["BASELINE-courtyard","MANDAP-dusk","MANSION-marble","ROOFTOP-night"]:
    s = json.load(open(R/(name+".json")))
    m = s["means"]
    print("%-20s mean=%6.2f min=%6.2f | dE=%5.2f weave=%.4f clip=%.4f ssim=%.4f | motion mean=%.4f max=%.4f" % (
        name, s["fidelity_mean"], s["fidelity_min"], m["delta_e2000"], m["weave_distance"],
        m["clip_cosine"], m["ssim"], s["motion"]["mean"], s["motion"]["max"]))
print()
print("MANSION-marble per-frame detail:")
s = json.load(open(R/"MANSION-marble.json"))
print("  idx    t    dE2000  weave  clipcos  ssim   conf  maskfrac  FID")
for f in s["per_frame"]:
    if not f.get("found"):
        print("  %3d  SKIPPED %s" % (f["frame"], f.get("reason",""))); continue
    print("  %3d %5.2f  %6.2f %6.4f %7.4f %6.3f %6.3f %7.4f %6.2f" % (
        f["frame"], f["t"], f["delta_e2000"], f["weave_distance"], f["clip_cosine"],
        f["ssim"], f["ssim_confidence"], f["mask_fraction"], f["fidelity"]))
