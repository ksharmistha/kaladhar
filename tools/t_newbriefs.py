import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.planner.sampler import sample
from kaladhar.planner.matrix import difference_matrix, min_axis_difference, AXIS_ORDER, is_coherent
from kaladhar.planner.brief import build_briefs

pts, rep = sample(6, seed=7)
print("min axis diff achieved:", rep["min_axis_diff_achieved"], "(required", rep["min_axis_diff_required"], ")")
print("all coherent:", all(is_coherent(p) for p in pts))
print()
print("     " + "".join("V%02d " % (j+1) for j in range(6)))
for i, row in enumerate(difference_matrix(pts)):
    print("V%02d  " % (i+1) + "".join("%3d " % v for v in row))
print()
for prod in ["saree", "kurti", "dress"]:
    bs = build_briefs(pts, product_noun=prod)
    print("=== %s ===" % prod.upper())
    for b in bs:
        print("  %s  %s" % (b["id"], " | ".join(b["axis_labels"][k] for k in AXIS_ORDER)))
    print()
print("SAMPLE PROMPT (kurti, V01):")
print(build_briefs(pts, "kurti")[0]["prompt"])
