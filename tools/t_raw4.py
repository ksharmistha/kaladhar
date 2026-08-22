import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from PIL import Image, ImageDraw
from kaladhar.video.io import sample_frames

src = Image.open("runs/run_m2_real/input/working.png").convert("RGB")
clips = ["BASELINE-courtyard","MANDAP-dusk","MANSION-marble","ROOFTOP-night"]
H = 430
tiles = [src.resize((int(src.width*H/src.height), H))]
names = ["SOURCE"]
for c in clips:
    fr = dict(sample_frames("runs/run_m2_real/clips/%s.mp4" % c, stride=1))
    f = fr[75]
    tiles.append(f.resize((int(f.width*H/f.height), H)))
    names.append(c)
W = sum(t.width for t in tiles) + 8*len(tiles)
canvas = Image.new("RGB",(W,H+24),(255,255,255))
d = ImageDraw.Draw(canvas); x=0
for t,n in zip(tiles,names):
    canvas.paste(t,(x,24)); d.text((x+3,6), n, fill=(0,0,0)); x+=t.width+8
canvas.save("evidence/raw_frame_comparison.png")
print("saved", canvas.size)
