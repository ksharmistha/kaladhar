import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.planner.sampler import sample
from kaladhar.planner.matrix import difference_matrix, AXIS_ORDER
from kaladhar.planner.brief import build_briefs

pts, rep = sample(6, seed=7)
print("min axis diff achieved:", rep["min_axis_diff_achieved"], "(required 3)")
print("total spread:", rep["total_pairwise_spread"], " value reuse:", rep["axis_value_reuse"])
print()
print("PAIRWISE AXIS-DIFFERENCE MATRIX")
print("     " + "".join("V%02d " % (j+1) for j in range(len(pts))))
for i, row in enumerate(difference_matrix(pts)):
    print("V%02d  " % (i+1) + "".join("%3d " % v for v in row))
print()
briefs = build_briefs(pts)
for b in briefs:
    print(b["id"], " | ".join(b["axis_labels"][k] for k in AXIS_ORDER))
print()
print("SAMPLE PROMPT", briefs[0]["id"])
print(briefs[0]["prompt"])
