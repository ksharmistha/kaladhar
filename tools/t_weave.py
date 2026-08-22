import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cv2, numpy as np
from PIL import Image
from kaladhar.fidelity.metrics import weave_descriptor, weave_distance, weave_hf_ratio

img = np.asarray(Image.open("runs/run_m2_real/input/working.png").convert("RGB"))
mask = np.asarray(Image.open("runs/run_m2_real/input/mask_garment.png").convert("L"))

base = weave_descriptor(img, mask)
print("SANITY CHECK - weave metric response to known degradation")
print("  reference hf_ratio = %.4f" % weave_hf_ratio(base))
print()
print("  %-28s %-10s %-10s" % ("variant", "distance", "hf_ratio"))
print("  " + "-"*50)
print("  %-28s %-10.4f %-10.4f" % ("identical", weave_distance(base, base), weave_hf_ratio(base)))

for k in (3, 5, 9, 15):
    d = weave_descriptor(cv2.GaussianBlur(img, (k, k), 0), mask)
    print("  %-28s %-10.4f %-10.4f" % ("gaussian blur k=%d" % k, weave_distance(base, d), weave_hf_ratio(d)))

# scale invariance: same fabric, different sampling resolution
for s in (0.6, 1.5):
    im2 = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC)
    m2 = cv2.resize(mask, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    d = weave_descriptor(im2, m2)
    print("  %-28s %-10.4f %-10.4f" % ("rescaled x%.1f (should be low)" % s, weave_distance(base, d), weave_hf_ratio(d)))

# a genuinely different fabric region: flat colour patch
flat = np.full_like(img, 0); flat[:,:] = img[mask>0].mean(axis=0).astype(np.uint8)
d = weave_descriptor(flat, mask)
print("  %-28s %-10.4f %-10.4f" % ("flat colour (no weave)", weave_distance(base, d), weave_hf_ratio(d)))
