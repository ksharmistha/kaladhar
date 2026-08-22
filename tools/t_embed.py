import sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from PIL import Image
from kaladhar.diversity.embed import embed, cosine

t = time.perf_counter()
im = Image.open("assets/source/saree_source.jpg")
v = embed([im, im.rotate(180), im.convert("L").convert("RGB")])
print("shapes", v.shape, "norms", [round(float((x**2).sum()),4) for x in v])
print("self-sim (same img vs greyscale) %.4f" % cosine(v[0], v[2]))
print("vs rotated %.4f" % cosine(v[0], v[1]))
print("took %.1fs" % (time.perf_counter()-t))
