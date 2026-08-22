import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from PIL import Image
from kaladhar.input.segment import segment

for name, path in [("saree", "runs/run_m2_real/input/working.png"),
                   ("kurti", "runs/run_20260822_181833/input/working.png")]:
    im = Image.open(path).convert("RGB")
    m = segment(im)
    print("%-6s subject %.3f  garment %.3f" % (name, m.subject_fraction, m.garment_fraction))
