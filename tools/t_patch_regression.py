"""Check the new patch selector on the saree WITHOUT touching run_m2_real files."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np, cv2
from PIL import Image
from kaladhar.fidelity.metrics import find_border_patch

for name, R in [("saree", "runs/run_m2_real"), ("kurti", "runs/run_20260822_181833")]:
    rgb = np.asarray(Image.open(R + "/input/working.png").convert("RGB"))
    m = np.asarray(Image.open(R + "/input/mask_garment.png").convert("L"))
    box = find_border_patch(rgb, m, 128)
    x, y, w, h = box
    patch = rgb[y:y+h, x:x+w]
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    mag = cv2.magnitude(cv2.Sobel(g,cv2.CV_32F,1,0,3), cv2.Sobel(g,cv2.CV_32F,0,1,3))
    pg = cv2.cvtColor(patch, cv2.COLOR_RGB2GRAY).astype(np.float32)
    pmag = cv2.magnitude(cv2.Sobel(pg,cv2.CV_32F,1,0,3), cv2.Sobel(pg,cv2.CV_32F,0,1,3))
    inside = m > 0
    thr = np.percentile(mag[inside], 60)
    print("%-6s box=%-22s detail-coverage %5.1f%%   %.2fx garment-average gradient"
          % (name, str(box), 100*(pmag>=thr).mean(), pmag.mean()/mag[inside].mean()))
    Image.fromarray(patch).resize((384,384), Image.NEAREST).save("evidence/patch_%s_NEW.png" % name)
