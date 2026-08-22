"""Extract one representative frame from each FINAL exported 1080x1920 file.

Frames come straight out of the delivered MP4s, so what appears in the PDF is
the actual shipped output at delivery resolution -- not a re-render.
"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cv2
from PIL import Image

OUT = pathlib.Path("evidence/m3_export_frames"); OUT.mkdir(parents=True, exist_ok=True)
man = json.load(open("evidence/m3_delivery_manifest.json"))
for e in man["exports"]:
    src = "runs/run_m2_real/exports/%s" % e["file"]
    cap = cv2.VideoCapture(src)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * 0.40))     # representative, mid-clip
    ok, fr = cap.read(); cap.release()
    if not ok:
        print("  FAILED", e["id"]); continue
    img = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    print("  %-20s frame %d of %d  %dx%d" % (e["id"], int(n*0.40), n, img.width, img.height))
    img.save(OUT / ("%s.png" % e["id"]))
print("wrote", OUT)
