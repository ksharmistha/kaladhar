"""Collect every real Milestone 3.3 measurement into one JSON for the report.

Read-only. Nothing is recomputed, nothing is written into any run.
"""
import json, os, glob, pathlib, shutil
AUX = {'summary.json','selection.json','calibration.json','safecut.json','diversity_full.json'}
EV = pathlib.Path("evidence"); (EV/"m33").mkdir(parents=True, exist_ok=True)

def scores_of(d):
    out=[]
    for f in sorted(glob.glob(os.path.join(d,"scores","*.json"))):
        if os.path.basename(f) in AUX: continue
        s=json.load(open(f, encoding="utf-8"))
        if "fidelity_mean" in s: out.append(s)
    return out

def summarise(rid, label):
    d="runs/%s/"%rid
    m=json.load(open(d+"run.json", encoding="utf-8")); src=m.get("source") or {}
    sel=json.load(open(d+"scores/selection.json", encoding="utf-8")) if os.path.exists(d+"scores/selection.json") else {}
    cal=json.load(open(d+"scores/calibration.json", encoding="utf-8")) if os.path.exists(d+"scores/calibration.json") else None
    exp=json.load(open(d+"exports/exports.json", encoding="utf-8")) if os.path.exists(d+"exports/exports.json") else []
    imp=json.load(open(d+"clips/imported.json", encoding="utf-8")) if os.path.exists(d+"clips/imported.json") else []
    rec={"run_id":rid,"label":label,"state":m.get("state"),"product":m.get("product"),
         "source":{"file":src.get("original_name"),
                   "dims":src.get("validation",{}).get("info",{}).get("dimensions"),
                   "garment_fraction":src.get("mask",{}).get("garment_fraction"),
                   "subject_fraction":src.get("mask",{}).get("subject_fraction"),
                   "palette":src.get("palette_hex"),"patch_box":src.get("border_patch_box")},
         "threshold_used":sel.get("threshold_used"),
         "calibrated_here":cal is not None,
         "calibration":cal,
         "imported":[{"id":r["id"],"w":r["probe"]["width"],"h":r["probe"]["height"],
                      "aspect":r["probe"]["aspect"],"dur":r["probe"]["duration_s"],
                      "mb":r["probe"]["file_mb"],"format_ok":r["format_ok"]} for r in imp],
         "clips":[], "gate1_pass":[p["id"] for p in sel.get("gate1_passing",[])],
         "gate1_reject":[{"id":p["id"],"reasons":p["reasons"]} for p in sel.get("gate1_rejected",[])],
         "diversity":sel.get("diversity",{}),
         "exports":[{"id":e["id"],"w":e["probe"]["width"],"h":e["probe"]["height"],
                     "aspect":e["probe"]["aspect"],"mb":e["probe"]["file_mb"],
                     "mode":e["mode"],"conforms":e["conforms"],
                     "retention":e.get("mode_decision",{}).get("min_retention")} for e in exp]}
    for s in scores_of(d):
        pf=[f for f in s["per_frame"] if f.get("found")]
        mf=[f["mask_fraction"] for f in pf if f.get("mask_fraction") is not None]
        rec["clips"].append({
            "id":s.get("id"), "mean":s["fidelity_mean"], "min":s["fidelity_min"], "std":s["fidelity_std"],
            "worst":s.get("worst_frame"), "means":s.get("means"), "motion":s.get("motion"),
            "frames_scored":s.get("frames_scored"), "stride":s.get("stride"),
            "delivered":"%dx%d"%(s["info"]["width"],s["info"]["height"]),
            "mask_peak":max(mf) if mf else None, "mask_min":min(mf) if mf else None,
            "mask_mean":sum(mf)/len(mf) if mf else None,
            "series":[{"t":f["t"],"fid":f["fidelity"],"mask":f.get("mask_fraction")} for f in pf]})
    return rec

data={"saree":summarise("run_m2_real","Saree — reference run"),
      "kurti":summarise("run_20260822_183825","Kurti — second product type")}
data["saree"]["diversity_full"]=json.load(open("runs/run_m2_real/scores/diversity_full.json", encoding="utf-8"))
data["saree"]["safecut"]=json.load(open("runs/run_m2_real/scores/safecut.json", encoding="utf-8"))
data["duplicate_kurti_run"]="run_20260822_182724 holds an identical second pass of the same kurti clip."

# copy the evidence images the report needs, with safe filenames
copies={
 "saree_mask":"runs/run_m2_real/evidence/mask_garment_overlay.png",
 "saree_weaveguard_src":"runs/run_m2_real/evidence/weave_guard_source.png",
 "saree_all_four":"evidence/fidelity_all_four.png",
 "mansion_drift":"runs/run_m2_real/evidence/drift_MANSION-marble.png",
 "mansion_weave":"runs/run_m2_real/evidence/weave_MANSION-marble.png",
 "mansion_diag":"evidence/mansion_mask_diagnosis.png",
 "rooftop_drift":"runs/run_m2_real/evidence/drift_ROOFTOP-night.png",
 "rooftop_weave":"runs/run_m2_real/evidence/weave_ROOFTOP-night.png",
 "raw_frames":"evidence/raw_frame_comparison.png",
 "kurti_mask":"runs/run_20260822_183825/evidence/mask_garment_overlay.png",
 "kurti_weaveguard_src":"runs/run_20260822_183825/evidence/weave_guard_source.png",
}
for k,v in copies.items():
    if os.path.exists(v):
        shutil.copy2(v, EV/"m33"/(k+".png")); print("  copied", k)
    else: print("  MISSING", k, v)
for g in glob.glob("runs/run_20260822_183825/evidence/drift_*.png"):
    shutil.copy2(g, EV/"m33"/"kurti_drift.png"); print("  copied kurti_drift")
for g in glob.glob("runs/run_20260822_183825/evidence/weave_A*.png"):
    shutil.copy2(g, EV/"m33"/"kurti_weave.png"); print("  copied kurti_weave")

json.dump(data, open(EV/"m33_test_results.json","w",encoding="utf-8"), indent=2)
print("\nwrote evidence/m33_test_results.json")
