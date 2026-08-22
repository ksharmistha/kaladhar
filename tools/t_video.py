import sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.video.io import probe, sample_frames, motion_profile
from kaladhar.input.segment import segment
from PIL import Image

info = probe("assets/clips/proto_01.mp4")
for k, v in info.items():
    print("  %-14s %s" % (k, v))

t = time.perf_counter()
frames = sample_frames("assets/clips/proto_01.mp4", stride=5)
print("sampled %d frames in %.2fs" % (len(frames), time.perf_counter() - t))

# segmentation cost at full res vs downscaled
f = frames[len(frames)//2][1]
for le in (None, 512, 384):
    im = f if le is None else f.resize((int(f.width*le/f.height), le), Image.BILINEAR)
    t = time.perf_counter()
    m = segment(im)
    print("  seg at %-9s %.2fs  garment=%.3f" % (str(im.size), time.perf_counter()-t, m.garment_fraction))

t = time.perf_counter()
mp = motion_profile("assets/clips/proto_01.mp4")
print("motion mean=%.4f max=%.4f std=%.4f  (%.2fs)" % (mp["mean"], mp["max"], mp["std"], time.perf_counter()-t))
