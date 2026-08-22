"""Regenerate ONLY the briefs of run_m2_real with the new environment set.

Briefs are a plan, not a measurement. The four real videos were never generated
from them (no filename matched a brief ID, and the run already records that), so
refreshing them changes no evidence. Scores, calibration, diversity, safecut and
exports are not touched.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.planner.sampler import sample
from kaladhar.planner.brief import as_operator_sheet, build_briefs
from kaladhar.storage.run import Run

run = Run.load("run_m2_real")
state_before = run.meta["state"]
points, report = sample(n=6, seed=7)
briefs = build_briefs(points, product_noun="saree")
run.write_json("briefs/briefs.json", briefs)
run.write_json("briefs/sampling_report.json", report)
run.path("briefs/EKLY_SHEET.txt").write_text(
    as_operator_sheet(briefs, run.run_id, str(run.path("input/reference.png"))), encoding="utf-8")
run.meta["product"] = "saree"
run.meta["plan"] = {"n_briefs": len(briefs), "product": "saree",
                    "min_axis_diff_achieved": report["min_axis_diff_achieved"],
                    "expected_credits": round(sum(b["ekly_settings"]["expected_credits"] for b in briefs), 2)}
run.meta["state"] = state_before          # do not rewind the run
run.save()
print("regenerated briefs for run_m2_real; state preserved:", run.meta["state"])
for b in briefs:
    print("  %s  %s" % (b["id"], b["axis_labels"]["environment"]))
