import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from PIL import Image
from kaladhar.storage.run import Run
from kaladhar.fidelity.safecut import safe_cut

run = Run.load("run_m2_real")
sig = run.read_json("input/signature.json")
patch = np.asarray(Image.open(run.path("input/border_patch.png")).convert("RGB"))
score = run.read_json("scores/ROOFTOP-night.json")
print("FUNCTIONAL VERIFICATION of the Safe Cut trim + re-score path.")
print("Threshold 72.0 with min_keep lowered to 2.0s. This is a CODE-PATH CHECK,")
print("not a shipping decision -- the production minimum stays 3.0s.")
print()
r = safe_cut(run, "ROOFTOP-night", score, 72.0, sig, patch, min_keep=2.0)
print(json.dumps({k: v for k, v in r.items() if k != "output_probe"}, indent=2, default=str))
if r.get("applied"):
    p = r["output_probe"]
    print("trimmed file: %dx%d  %.2fs  %.2f MB" % (p["width"], p["height"], p["duration_s"], p["file_mb"]))
