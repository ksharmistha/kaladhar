"""Kaladhar ad-variation pipeline -- command line entry point.

    python cli.py plan         --image <path> [--n 6] [--seed 0]
    python cli.py import-clips --run <id> --dir <folder>
    python cli.py score        --run <id> [--stride 5]
    python cli.py calibrate    --run <id>
    python cli.py select       --run <id> [--k 6] [--threshold 65]
    python cli.py export       --run <id> [--mode auto|pad|crop]
    python cli.py safe-cut     --run <id> --threshold <t>
    python cli.py review       --run <id>
    python cli.py status       [--run <id>]
    python cli.py runs

The workflow deliberately stops after `plan`. Ekly.ai exposes no API to us, so
generation is performed by hand from the sheet written at
runs/<id>/briefs/EKLY_SHEET.txt, and the run resumes at `import-clips`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kaladhar.input.ingest import IngestError, summary  # noqa: E402
from kaladhar.planner.brief import DEFAULT_PRODUCT  # noqa: E402
from kaladhar.pipeline import (export, import_clips, plan, score_all,  # noqa: E402
                               select_best)
from kaladhar.storage.run import Run  # noqa: E402

BAR = "=" * 72


def _resolve(run_id):
    return Run.load(run_id) if run_id else Run.latest()


def cmd_plan(a):
    try:
        if not a.product:
            print("No --product given; using the neutral term 'garment'.")
        run, briefs = plan(a.image, n=a.n, seed=a.seed, run_id=a.run,
                           product_noun=a.product or DEFAULT_PRODUCT)
    except IngestError as exc:
        print(exc)
        return 1
    print(BAR)
    print(summary(run))
    print(BAR)
    rep = run.read_json("briefs/sampling_report.json")
    print("Briefs           %d" % len(briefs))
    print("Min axis diff    %d  (rule: at least %d of 5 axes differ between any two)"
          % (rep["min_axis_diff_achieved"], rep["min_axis_diff_required"]))
    print("Expected credits %.2f  (45.50 each, measured on our real run)"
          % run.meta["plan"]["expected_credits"])
    print()
    for b in briefs:
        print("  %s  %s" % (b["id"], " | ".join(
            b["axis_labels"][k] for k in
            ("environment", "lighting", "camera", "concept", "grade"))))
    print()
    print("NEXT -- MANUAL STEP (Ekly has no API available to us):")
    print("  1. Open %s" % run.path("briefs/EKLY_SHEET.txt"))
    print("  2. Generate each brief in Ekly, attaching %s"
          % run.path("input/reference.png"))
    print("  3. Save clips as V01.mp4, V02.mp4, ... then run:")
    print("     python cli.py import-clips --run %s --dir <folder>" % run.run_id)
    return 0


def cmd_import(a):
    run = _resolve(a.run)
    recs = import_clips(run, a.dir)
    print("Imported %d clip(s) into run %s" % (len(recs), run.run_id))
    for r in recs:
        p = r["probe"]
        flag = "OK " if r["format_ok"] else "!! "
        print("  %s%-14s %dx%d  aspect %.3f  %.2fs  %s" % (
            flag, r["id"], p["width"], p["height"], p["aspect"],
            p["duration_s"] or 0, "9:16" if r["format_ok"] else "NOT 9:16"))
        if not r["matched_brief"]:
            print("       note: filename does not match any brief id")
    if any(not r["format_ok"] for r in recs):
        print("\n  Clips not in 9:16 are converted to 1080x1920 at export.")
    return 0


def cmd_score(a):
    run = _resolve(a.run)
    scores = score_all(run, stride=a.stride)
    print(BAR)
    print("%-12s %8s %8s %8s  %s" % ("clip", "mean", "min", "std", "worst frame"))
    print(BAR)
    for s in scores:
        w = s.get("worst_frame", {})
        print("%-12s %8.2f %8.2f %8.2f  frame %s (t=%ss)" % (
            s["id"], s["fidelity_mean"], s["fidelity_min"], s["fidelity_std"],
            w.get("frame"), w.get("t")))
    print()
    print("Evidence written to %s" % run.path("evidence"))
    print("Timings: %s" % run.meta.get("timings"))
    return 0


def cmd_calibrate(a):
    from kaladhar.fidelity.calibrate import calibrate
    run = _resolve(a.run)
    rep = calibrate(run)
    print(rep["render"])
    return 0


def cmd_select(a):
    run = _resolve(a.run)
    res = select_best(run, k=a.k, threshold=a.threshold)
    print(BAR)
    print("GATE 1 - Fidelity Lock")
    print(BAR)
    for p in res["gate1_passing"]:
        print("  PASS   %-12s mean %.2f  min %.2f" % (
            p["id"], p["fidelity_mean"] or 0, p["fidelity_min"] or 0))
    for p in res["gate1_rejected"]:
        print("  REJECT %-12s %s" % (p["id"], "; ".join(p["reasons"])))
    d = res.get("diversity", {})
    print()
    print(BAR)
    print("GATE 2 - Diversity Engine")
    print(BAR)
    if "diversity_score_selected" in d:
        print("  Pool size            %d" % d["pool_size"])
        print("  Selected             %s" % ", ".join(d["selected_ids"]))
        print("  Rejected             %s" % (", ".join(d["rejected_ids"]) or "-"))
        print("  Diversity (selected) %.2f" % d["diversity_score_selected"])
        print("  Diversity (pool)     %.2f" % d["diversity_score_pool"])
        print("  Gain from selection  %+.2f" % d["diversity_gain"])
    else:
        print("  %s" % d.get("note", "n/a"))
    return 0


def cmd_export(a):
    run = _resolve(a.run)
    out = export(run, mode=a.mode)
    if not out:
        print("Nothing selected to export. Run `select` first.")
        return 1
    print(BAR)
    for o in out:
        p = o["probe"]
        print("  %-12s -> %dx%d  mode=%s  %.2f MB  %s" % (
            o["id"], p["width"], p["height"], o["mode"], p["file_mb"],
            "CONFORMS 9:16 1080x1920" if o["conforms"] else "DOES NOT CONFORM"))
        print("       %s" % o.get("mode_decision", {}).get("rationale", ""))
    print(BAR)
    print("Exports in %s" % run.path("exports"))
    return 0


def cmd_safecut(a):
    from kaladhar.fidelity.safecut import MIN_KEEP_SECONDS, run_safe_cut
    run = _resolve(a.run)
    recs = run_safe_cut(run, threshold=a.threshold, stride=a.stride)
    print(BAR)
    print("SAFE CUT  (threshold %.1f, minimum kept length %.1fs)"
          % (a.threshold, MIN_KEEP_SECONDS))
    print(BAR)
    for r in recs:
        if not r.get("applied"):
            print("  SKIP   %-20s %s" % (r["clip_id"], r.get("reason", "")))
            continue
        b, af = r["before"], r["after"]
        print("  CUT    %-20s keep %.2f-%.2fs  (%.2fs kept, %.2fs removed)"
              % (r["clip_id"], r["start_s"], r["end_s"], r["kept_s"], r["removed_s"]))
        print("         before  mean %.2f  min %.2f  %.2fs"
              % (b["mean"], b["min"], b["duration_s"]))
        print("         after   mean %.2f  min %.2f  %.2fs   %s"
              % (af["mean"], af["min"], af["duration_s"],
                 "now passes" if r["now_passes"] else "still below threshold"))
        print("         re-scored from the trimmed file, not inherited")
    return 0


def cmd_review(a):
    from kaladhar.review.build import build
    run = _resolve(a.run)
    out = build(run)
    print("Review page written to %s" % out)
    return 0


def cmd_status(a):
    run = _resolve(a.run)
    print(BAR)
    print(summary(run))
    print(BAR)
    print("State    %s" % run.meta["state"])
    for h in run.meta.get("history", []):
        print("   %s  %-16s %s" % (h["at"], h["state"], h.get("note", "")))
    if run.meta["state"] == "AWAITING_CLIPS":
        print()
        print("PAUSED at the manual Ekly step. Sheet: %s"
              % run.path("briefs/EKLY_SHEET.txt"))
    return 0


def cmd_runs(a):
    for r in Run.list_all():
        try:
            m = Run.load(r).meta
            print("  %-22s %-16s %s" % (r, m.get("state"), m.get("created")))
        except Exception:
            print("  %-22s <unreadable>" % r)
    return 0


def main():
    p = argparse.ArgumentParser(prog="cli.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("plan", help="ingest an image and generate Ekly briefs")
    s.add_argument("--image", required=True)
    s.add_argument("--n", type=int, default=6)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--run", default=None)
    s.add_argument("--product", default=None,
                   help="Product type, e.g. saree, kurti, lehenga, dress, shirt. "
                        "If omitted the neutral term 'garment' is used -- an "
                        "unspecified product is never assumed to be a saree.")
    s.set_defaults(fn=cmd_plan)

    s = sub.add_parser("import-clips", help="import clips generated in Ekly")
    s.add_argument("--run", default=None)
    s.add_argument("--dir", required=True)
    s.set_defaults(fn=cmd_import)

    s = sub.add_parser("score", help="run the Fidelity Lock over imported clips")
    s.add_argument("--run", default=None)
    s.add_argument("--stride", type=int, default=5)
    s.set_defaults(fn=cmd_score)

    s = sub.add_parser("calibrate", help="derive a pass threshold from scored clips")
    s.add_argument("--run", default=None)
    s.set_defaults(fn=cmd_calibrate)

    s = sub.add_parser("select", help="apply both quality gates")
    s.add_argument("--run", default=None)
    s.add_argument("--k", type=int, default=6)
    s.add_argument("--threshold", type=float, default=None)
    s.set_defaults(fn=cmd_select)

    s = sub.add_parser("export", help="convert selected clips to 1080x1920")
    s.add_argument("--run", default=None)
    s.add_argument("--mode", choices=["auto", "pad", "crop"], default="auto")
    s.set_defaults(fn=cmd_export)

    s = sub.add_parser("safe-cut", help="trim clips to their longest passing window")
    s.add_argument("--run", default=None)
    s.add_argument("--threshold", type=float, required=True)
    s.add_argument("--stride", type=int, default=5)
    s.set_defaults(fn=cmd_safecut)

    s = sub.add_parser("review", help="build the HTML review grid")
    s.add_argument("--run", default=None)
    s.set_defaults(fn=cmd_review)

    s = sub.add_parser("status", help="show run state")
    s.add_argument("--run", default=None)
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("runs", help="list runs")
    s.set_defaults(fn=cmd_runs)

    a = p.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
