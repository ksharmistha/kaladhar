import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np, cv2
from PIL import Image
from kaladhar.video.io import to_9_16, sample_frames
from kaladhar.storage.run import Run
from kaladhar.input.segment import segment

src = "runs/run_m2/clips/V01.mp4"
out = {}
for mode in ("pad", "crop"):
    dst = "evidence/export_%s.mp4" % mode
    info = to_9_16(src, dst, mode=mode)
    out[mode] = (dst, info)
    print("%-5s -> %dx%d  %.2f MB  conforms=%s" % (
        mode, info["width"], info["height"], info["file_mb"],
        info["is_1080x1920"] and info["is_9_16"]))

# How much of the GARMENT does crop actually remove? That is the real question.
f0 = sample_frames(src, stride=1, max_frames=1)[0][1]
m = segment(f0.resize((341, 512)))
mask = cv2.resize(m.garment, f0.size, interpolation=cv2.INTER_NEAREST)
total = float((mask > 0).sum())

w, h = f0.size                       # 768x1152
keep_w = int(round(h * 1080 / 1920))  # width kept when filling 9:16
x0 = (w - keep_w) // 2
kept = float((mask[:, x0:x0 + keep_w] > 0).sum())
print()
print("source frame %dx%d ; crop keeps centre %dpx of %dpx width (%.1f%%)"
      % (w, h, keep_w, w, 100.0 * keep_w / w))
print("garment pixels retained by crop: %.2f%%  -> %.2f%% of the saree is cut"
      % (100.0 * kept / total, 100.0 * (1 - kept / total)))

# side-by-side still for the report
frames = {mode: sample_frames(p, stride=1, max_frames=1)[0][1] for mode,(p,_) in out.items()}
canvas = Image.new("RGB", (1080//2*2 + 30, 1920//2 + 60), (255,255,255))
for i, mode in enumerate(("pad","crop")):
    canvas.paste(frames[mode].resize((1080//2, 1920//2)), (10 + i*(1080//2+10), 45))
from PIL import ImageDraw
d = ImageDraw.Draw(canvas)
d.text((12,12), "EXPORT 1080x1920: pad (left, nothing lost) vs crop (right, sides removed)", fill=(0,0,0))
canvas.save("evidence/export_pad_vs_crop.png")
print("wrote evidence/export_pad_vs_crop.png")
