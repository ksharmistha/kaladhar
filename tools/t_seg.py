import sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.input.preprocess import normalise
from kaladhar.input.segment import segment, overlay

t = time.perf_counter()
im = normalise("assets/source/saree_source.jpg")
print("working size", im.size)
m = segment(im)
print("segment took %.1fs" % (time.perf_counter() - t))
print("subject frac %.3f  garment frac %.3f" % (m.subject_fraction, m.garment_fraction))
for n in m.notes:
    print(" -", n)
overlay(im, m.garment).save("evidence/mask_garment.png")
overlay(im, m.subject, colour=(0, 128, 255)).save("evidence/mask_subject.png")
print("saved overlays")
