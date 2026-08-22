import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import cv2, numpy as np
from PIL import Image
from kaladhar.video.io import sample_frames
from kaladhar.input.segment import segment, overlay

frames = dict(sample_frames("runs/run_m2_real/clips/MANSION-marble.mp4", stride=1))
picks = [0, 5, 30, 75, 150]
tiles = []
for i in picks:
    f = frames[i]
    w, h = f.size
    small = f.resize((int(w*512/h), 512), Image.BILINEAR)
    m = segment(small)
    ov = overlay(small, m.garment)
    lab = Image.new("RGB", (ov.width, ov.height+22), (255,255,255))
    lab.paste(ov, (0,22))
    from PIL import ImageDraw
    ImageDraw.Draw(lab).text((4,5), "frame %d  mask=%.3f" % (i, m.garment_fraction), fill=(0,0,0))
    tiles.append(lab)
W = sum(t.width for t in tiles) + 10*len(tiles)
canvas = Image.new("RGB", (W, tiles[0].height), (255,255,255))
x=0
for t in tiles:
    canvas.paste(t,(x,0)); x += t.width+10
canvas.save("evidence/mansion_mask_diagnosis.png")
print("saved evidence/mansion_mask_diagnosis.png", canvas.size)
