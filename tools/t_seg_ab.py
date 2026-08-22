"""Rigorous warm A/B of segmentation cost by input resolution."""
import sys, pathlib, time, statistics
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from PIL import Image
from kaladhar.input.segment import segment
from kaladhar.video.io import sample_frames
from kaladhar.fidelity.lock import SEG_LONG_EDGE

frame = sample_frames("runs/run_m2_real/clips/BASELINE-courtyard.mp4", stride=1, max_frames=1)[0][1]
fw, fh = frame.size
small = frame.resize((round(fw*SEG_LONG_EDGE/max(fw,fh)), round(fh*SEG_LONG_EDGE/max(fw,fh))))

segment(frame); segment(small)          # warm up both paths first
full, red = [], []
for i in range(5):
    t=time.perf_counter(); segment(frame); full.append(time.perf_counter()-t)
    t=time.perf_counter(); segment(small); red.append(time.perf_counter()-t)

print("WARM A/B, 5 alternating reps, model already loaded")
print("  full  %s  median %.3fs" % (str(frame.size), statistics.median(full)))
print("  small %s  median %.3fs" % (str(small.size), statistics.median(red)))
print("  speed-up: %.2fx" % (statistics.median(full)/statistics.median(red)))
print()
print("  full  raw:", [round(x,3) for x in full])
print("  small raw:", [round(x,3) for x in red])
print()
print("NOTE: rembg internally resizes every input to 320x320 for U2-Net, so the")
print("model inference cost is nearly constant regardless of input size. The")
print("saving is only in decode/resize/post-processing, not inference.")
