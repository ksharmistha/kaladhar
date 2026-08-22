import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cv2, numpy as np
from PIL import Image
from kaladhar.input.segment import _skin_mask

R = "runs/run_20260822_181833"
rgb = np.asarray(Image.open(R + "/input/working.png").convert("RGB"))
subj = np.asarray(Image.open(R + "/input/mask_subject.png").convert("L")) > 0
garm = np.asarray(Image.open(R + "/input/mask_garment.png").convert("L")) > 0
skin = _skin_mask(rgb) > 0

removed = subj & ~garm            # what the skin filter + head cut took out
g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, 3)
mag = np.sqrt(gx*gx + gy*gy)

print("subject %.3f  garment %.3f  removed %.3f of frame" % (subj.mean(), garm.mean(), removed.mean()))
print("skin-classified inside subject: %.1f%% of subject" % (100*(skin & subj).sum()/subj.sum()))
print()
print("mean gradient magnitude (texture) by region:")
print("  kept as garment      : %6.2f" % mag[garm].mean())
print("  removed by skin/head : %6.2f" % mag[removed].mean())
print()
print("=> the REMOVED region is %.1fx more textured than the kept region."
      % (mag[removed].mean()/max(mag[garm].mean(),1e-6)))
print("   The printed panels are warm-toned, so they fall inside the skin")
print("   chrominance range and are being deleted from the product mask.")
