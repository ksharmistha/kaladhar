import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.fidelity.safecut import analyse
R = pathlib.Path("runs/run_m2_real/scores")
names = ["BASELINE-courtyard","MANDAP-dusk","MANSION-marble","ROOFTOP-night"]
print("%-20s %s" % ("clip", "  ".join("thr=%d" % t for t in (55,60,65,70,72))))
for n in names:
    s = json.load(open(R/(n+".json")))
    row=[]
    for t in (55,60,65,70,72):
        a = analyse(s, t)
        if a.get("applicable"):
            row.append("%.2fs" % a["kept_s"])
        else:
            w = a.get("longest_window_s")
            row.append("-" if w is None else "(%.2f)" % w)
    print("%-20s %s" % (n, "  ".join("%-7s" % x for x in row)))
print()
print("  value = kept window if Safe Cut applies; (x) = longest window found but under 3.0s; - = nothing to cut")
