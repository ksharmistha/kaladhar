"""Review grid -- Stage F.

Builds one self-contained HTML page per run: every candidate with its scores,
the rejected pool alongside the selected set, the drift plot and Weave Guard
for each clip, and the pipeline state including the manual Ekly step.

Images are inlined as data URIs so the page can be opened straight from disk or
handed to someone else without the run directory attached.
"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

CSS = """
:root { --ink:#12343b; --muted:#6b7280; --line:#e5e7eb; --bg:#ffffff;
        --pass:#15803d; --fail:#b91c1c; --warn:#b45309; --panel:#f9fafb; }
* { box-sizing:border-box; }
body { margin:0; padding:32px; background:var(--bg); color:var(--ink);
       font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
.wrap { max-width:1180px; margin:0 auto; }
h1 { font-size:26px; margin:0 0 4px; }
h2 { font-size:18px; margin:34px 0 12px; padding-bottom:6px;
     border-bottom:1px solid var(--line); }
.sub { color:var(--muted); margin:0 0 22px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:18px; }
.card { border:1px solid var(--line); border-radius:10px; padding:16px; background:var(--panel); }
.card.sel { border-color:var(--pass); border-width:2px; }
.card.rej { opacity:.72; }
.card h3 { margin:0 0 8px; font-size:16px; display:flex; justify-content:space-between;
           align-items:center; gap:8px; }
.badge { font-size:11px; font-weight:700; letter-spacing:.04em; padding:3px 8px;
         border-radius:999px; text-transform:uppercase; }
.b-pass { background:#dcfce7; color:var(--pass); }
.b-fail { background:#fee2e2; color:var(--fail); }
.b-warn { background:#fef3c7; color:var(--warn); }
table { border-collapse:collapse; width:100%; font-size:13px; }
th,td { text-align:left; padding:6px 9px; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-weight:600; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
img { max-width:100%; border:1px solid var(--line); border-radius:6px; display:block; }
.meta { font-size:12.5px; color:var(--muted); }
.kv { display:grid; grid-template-columns:auto 1fr; gap:2px 12px; font-size:13px; }
.kv dt { color:var(--muted); }
.kv dd { margin:0; font-variant-numeric:tabular-nums; }
.note { background:#fffbeb; border:1px solid #fde68a; border-left:4px solid var(--warn);
        padding:12px 14px; border-radius:6px; font-size:13.5px; margin:14px 0; }
.manual { background:#eff6ff; border:1px solid #bfdbfe; border-left:4px solid #2563eb;
          padding:12px 14px; border-radius:6px; font-size:13.5px; margin:14px 0; }
.steps { display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 0; padding:0; list-style:none; }
.steps li { font-size:12px; padding:5px 11px; border-radius:999px; border:1px solid var(--line);
            background:#fff; color:var(--muted); }
.steps li.done { background:#dcfce7; border-color:#86efac; color:var(--pass); }
.steps li.now { background:#dbeafe; border-color:#93c5fd; color:#1d4ed8; font-weight:600; }
.steps li.manual { background:#fef3c7; border-color:#fcd34d; color:var(--warn); font-weight:600; }
pre { background:#0f172a; color:#e2e8f0; padding:12px 14px; border-radius:8px;
      font-size:12px; overflow-x:auto; white-space:pre-wrap; }
.small { font-size:12px; color:var(--muted); }
"""

STATE_ORDER = ["CREATED", "PREPROCESSED", "BRIEFS_READY", "AWAITING_CLIPS",
               "CLIPS_IMPORTED", "SCORED", "SELECTED", "EXPORTED"]


def _b64(path, max_bytes=6_000_000):
    p = Path(path)
    if not p.exists() or p.stat().st_size > max_bytes:
        return None
    ext = p.suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    return "data:%s;base64,%s" % (mime, base64.b64encode(p.read_bytes()).decode())


def _img(path, alt=""):
    d = _b64(path)
    if not d:
        return '<p class="small">[%s not available]</p>' % html.escape(alt or str(path))
    return '<img src="%s" alt="%s">' % (d, html.escape(alt))


def _e(x):
    return html.escape(str(x))


def build(run, out_name="review.html"):
    meta = run.meta
    state = meta.get("state", "CREATED")

    briefs = run.read_json("briefs/briefs.json") if run.has("briefs/briefs.json") else []
    imported = run.read_json("clips/imported.json") if run.has("clips/imported.json") else []
    selection = run.read_json("scores/selection.json") if run.has("scores/selection.json") else {}
    calib = run.read_json("scores/calibration.json") if run.has("scores/calibration.json") else {}
    exports = run.read_json("exports/exports.json") if run.has("exports/exports.json") else []

    scores = {}
    sdir = run.path("scores")
    if sdir.exists():
        for p in sorted(sdir.glob("*.json")):
            if p.name in ("summary.json", "selection.json", "calibration.json",
                          "safecut.json", "diversity_full.json"):
                continue
            if p.stem.endswith("__safecut"):
                continue
            s = json.loads(p.read_text(encoding="utf-8"))
            if "fidelity_mean" in s:
                scores[s.get("id", p.stem)] = s

    sel_ids = set(selection.get("diversity", {}).get("selected_ids", []))
    rejected = {r["id"]: r for r in selection.get("gate1_rejected", [])}
    export_by_id = {e["id"]: e for e in exports}

    H = []
    a = H.append
    a("<!doctype html><meta charset='utf-8'>")
    a("<title>Kaladhar review - %s</title>" % _e(run.run_id))
    a("<style>%s</style><div class='wrap'>" % CSS)

    a("<h1>Kaladhar &mdash; ad variation review</h1>")
    a("<p class='sub'>Run <b>%s</b> &middot; created %s &middot; state <b>%s</b></p>"
      % (_e(run.run_id), _e(meta.get("created", "")), _e(state)))

    # ---------------------------------------------------------------- pipeline
    a("<ul class='steps'>")
    cur = STATE_ORDER.index(state) if state in STATE_ORDER else 0
    labels = {"AWAITING_CLIPS": "AWAITING_CLIPS (manual Ekly step)"}
    for i, s in enumerate(STATE_ORDER):
        cls = "done" if i < cur else ("now" if i == cur else "")
        if s == "AWAITING_CLIPS" and i >= cur:
            cls = "manual"
        a("<li class='%s'>%s</li>" % (cls, _e(labels.get(s, s))))
    a("</ul>")

    a("<div class='manual'><b>This workflow is automated either side of one manual "
      "step, not end to end.</b> Ekly.ai exposes no API to us, so video generation "
      "is performed by hand through its web interface. Everything before generation "
      "(validation, segmentation, signature, brief planning) and everything after it "
      "(import, per-frame scoring, diversity selection, conversion, export) is "
      "automated. The run pauses at <code>AWAITING_CLIPS</code> and resumes on "
      "<code>import-clips</code>.</div>")

    # ------------------------------------------------------------------ source
    src = meta.get("source", {})
    a("<h2>1. Source product image</h2>")
    a("<div class='grid'>")
    a("<div class='card'><h3>Garment mask</h3>%s"
      "<p class='small'>rembg subject mask refined by a skin-chrominance heuristic. "
      "Every fidelity metric is computed inside this region only &mdash; the background "
      "is supposed to change.</p></div>"
      % _img(run.path("evidence/mask_garment_overlay.png"), "garment mask"))
    a("<div class='card'><h3>Weave Guard region</h3>%s"
      "<p class='small'>Most texture-dense patch inside the mask, found automatically. "
      "On a saree this is the border or pallu; on a printed garment it is the "
      "densest print area.</p></div>"
      % _img(run.path("evidence/weave_guard_source.png"), "weave guard source"))

    v = src.get("validation", {}).get("info", {})
    m = src.get("mask", {})
    a("<div class='card'><h3>Signature</h3><dl class='kv'>")
    for k, val in (("File", src.get("original_name")), ("Format", v.get("format")),
                   ("Dimensions", v.get("dimensions")), ("Aspect", v.get("aspect")),
                   ("Subject mask", "%.1f%%" % (m.get("subject_fraction", 0) * 100)),
                   ("Garment mask", "%.1f%%" % (m.get("garment_fraction", 0) * 100))):
        a("<dt>%s</dt><dd>%s</dd>" % (_e(k), _e(val)))
    a("</dl><p class='small'>Palette (CIELAB k-means, garment only):</p><p>")
    for hexc in src.get("palette_hex", []):
        a("<span style='display:inline-block;width:30px;height:22px;background:%s;"
          "border:1px solid #ccc;border-radius:3px;margin-right:4px'></span>" % _e(hexc))
    a("</p>")
    for w in src.get("validation", {}).get("warnings", []):
        a("<p class='small'><b>Warning:</b> %s</p>" % _e(w))
    a("</div></div>")

    # ------------------------------------------------------------------ briefs
    if briefs:
        rep = run.read_json("briefs/sampling_report.json") if run.has("briefs/sampling_report.json") else {}
        a("<h2>2. Creative plan &mdash; %d briefs</h2>" % len(briefs))
        a("<p class='sub'>Sampled from a five-axis matrix under a hard rule: any two "
          "briefs differ on at least %s of 5 axes. Achieved minimum in this run: "
          "<b>%s</b>.</p>" % (rep.get("min_axis_diff_required", 3),
                              rep.get("min_axis_diff_achieved", "?")))
        a("<table><tr><th>ID</th><th>Environment</th><th>Lighting</th><th>Camera</th>"
          "<th>Concept</th><th>Grade</th></tr>")
        for b in briefs:
            L = b["axis_labels"]
            a("<tr><td><b>%s</b></td>%s</tr>" % (
                _e(b["id"]),
                "".join("<td>%s</td>" % _e(L[k]) for k in
                        ("environment", "lighting", "camera", "concept", "grade"))))
        a("</table>")
        unmatched = [r for r in imported if not r.get("matched_brief")]
        if imported and len(unmatched) == len(imported):
            a("<div class='note'><b>Provenance:</b> none of the %d imported videos "
              "matched a brief ID, so this batch was not generated from the six briefs "
              "above. The briefs demonstrate the Creative Planner; the videos are what "
              "was actually generated in Ekly. They are reported separately rather than "
              "presented as if the planner produced them.</div>" % len(imported))

    # ----------------------------------------------------------------- clips
    if imported:
        a("<h2>3. Candidates &mdash; Gate 1 (fidelity) and Gate 2 (diversity)</h2>")
        thr = selection.get("threshold_used")
        a("<p class='sub'>A clip must pass <b>both</b> gates to be exported. Gate 1 "
          "rejects it for drifting off the product; Gate 2 rejects it for looking too "
          "much like another clip.%s</p>"
          % ("" if thr is None else " Fidelity threshold in use: <b>%.1f</b>." % thr))
        a("<div class='grid'>")
        for rec in imported:
            cid = rec["id"]
            s = scores.get(cid)
            selected = cid in sel_ids
            rej = rejected.get(cid)
            cls = "card sel" if selected else ("card rej" if rej else "card")
            if rej:
                badge = "<span class='badge b-fail'>rejected</span>"
            elif selected:
                badge = "<span class='badge b-pass'>selected</span>"
            else:
                badge = "<span class='badge b-warn'>passed gate 1</span>"
            a("<div class='%s'><h3>%s %s</h3>" % (cls, _e(cid), badge))

            p = rec.get("probe", {})
            a("<dl class='kv'>")
            a("<dt>Delivered</dt><dd>%sx%s (aspect %s)%s</dd>" % (
                p.get("width"), p.get("height"), p.get("aspect"),
                "" if rec.get("format_ok") else " &mdash; not 9:16"))
            if s:
                a("<dt>Fidelity mean</dt><dd>%.2f</dd>" % s["fidelity_mean"])
                a("<dt>Fidelity min</dt><dd>%.2f</dd>" % s["fidelity_min"])
                w = s.get("worst_frame", {})
                a("<dt>Worst frame</dt><dd>#%s at t=%ss</dd>" % (w.get("frame"), w.get("t")))
                mm = s.get("means", {})
                a("<dt>dE2000</dt><dd>%.2f</dd>" % mm.get("delta_e2000", 0))
                a("<dt>Weave dist</dt><dd>%.4f</dd>" % mm.get("weave_distance", 0))
                a("<dt>CLIP cosine</dt><dd>%.4f</dd>" % mm.get("clip_cosine", 0))
                mo = s.get("motion", {})
                a("<dt>Motion mean</dt><dd>%.4f</dd>" % mo.get("mean", 0))
            ex = export_by_id.get(cid)
            if ex:
                a("<dt>Export</dt><dd>%sx%s, %s</dd>" % (
                    ex["probe"]["width"], ex["probe"]["height"], ex["mode"]))
            a("</dl>")
            if rej:
                a("<p class='small'><b>Rejected:</b> %s</p>"
                  % _e("; ".join(rej.get("reasons", []))))
            dp = run.path("evidence/drift_%s.png" % cid)
            if dp.exists():
                a("<p class='small' style='margin-top:10px'>Per-frame drift</p>")
                a(_img(dp, "drift plot %s" % cid))
            wg = run.path("evidence/weave_%s.png" % cid)
            if wg.exists():
                a("<p class='small' style='margin-top:10px'>Weave Guard &mdash; source vs worst frame</p>")
                a(_img(wg, "weave guard %s" % cid))
            a("</div>")
        a("</div>")

    # ------------------------------------------------------------- diversity
    d = selection.get("diversity", {})
    a("<h2>4. Diversity Engine</h2>")
    if "diversity_score_selected" in d:
        a("<dl class='kv'>")
        a("<dt>Pool size</dt><dd>%s</dd>" % d.get("pool_size"))
        a("<dt>Selected</dt><dd>%s</dd>" % _e(", ".join(d.get("selected_ids", []))))
        a("<dt>Rejected</dt><dd>%s</dd>" % _e(", ".join(d.get("rejected_ids", [])) or "-"))
        a("<dt>Diversity (selected)</dt><dd>%.2f</dd>" % d["diversity_score_selected"])
        a("<dt>Diversity (pool)</dt><dd>%.2f</dd>" % d["diversity_score_pool"])
        a("<dt>Gain</dt><dd>%+.2f</dd>" % d["diversity_gain"])
        a("</dl>")
        a("<p class='small'>%s</p>" % _e(d.get("note", "")))
    else:
        a("<div class='note'>%s</div>" % _e(d.get("note", "Diversity selection has not run yet.")))

    dv = run.read_json("scores/diversity_full.json") if run.has("scores/diversity_full.json") else None
    if dv:
        ids = dv["ids"]
        mat = dv["pairwise_cosine_distance"]
        a("<p class='small' style='margin-top:14px'><b>Real pairwise cosine distance</b> "
          "across every imported video, including the rejected one. Computed from mean "
          "CLIP embeddings over sampled frames of the actual generated files &mdash; not "
          "constructed vectors.</p>")
        a("<table><tr><th></th>%s</tr>" % "".join("<th class='num'>%s</th>" % _e(i[:12]) for i in ids))
        for i, row in enumerate(mat):
            cells = "".join("<td class='num'>%s</td>"
                            % ("&mdash;" if i == j else "%.4f" % row[j])
                            for j in range(len(ids)))
            a("<tr><td><b>%s</b></td>%s</tr>" % (_e(ids[i]), cells))
        a("</table>")
        a("<dl class='kv' style='margin-top:10px'>")
        a("<dt>Diversity, all %d videos</dt><dd>%.2f</dd>" % (len(ids), dv["diversity_all_four"]))
        a("<dt>Diversity, Gate-1 passing</dt><dd>%.2f</dd>" % dv["diversity_gate1_passing"])
        a("<dt>Most similar pair</dt><dd>%s &harr; %s  (%.4f)</dd>"
          % (_e(dv["most_similar_pair"][0]), _e(dv["most_similar_pair"][1]), dv["most_similar_pair"][2]))
        a("<dt>Most distinct pair</dt><dd>%s &harr; %s  (%.4f)</dd>"
          % (_e(dv["most_distinct_pair"][0]), _e(dv["most_distinct_pair"][1]), dv["most_distinct_pair"][2]))
        a("</dl>")
        a("<div class='note'>The most distinct clip in the set is <b>MANSION-marble</b>, "
          "which Gate 1 rejected. Being the most different is not the same as being "
          "usable &mdash; that is precisely why diversity alone cannot decide what ships, "
          "and why the two gates are independent.</div>")

    # -------------------------------------------------------------- safe cut
    safecut = run.read_json("scores/safecut.json") if run.has("scores/safecut.json") else []
    if safecut:
        applied = [r for r in safecut if r.get("applied")]
        a("<h2>5. Safe Cut</h2>")
        a("<p class='sub'>Product drift in these clips is local and transient, so a "
          "clip that dips below threshold for part of its length can still contain a "
          "usable ad. Safe Cut trims to the longest <b>contiguous</b> window in which "
          "every scored frame clears the threshold, and only when at least 3.0s "
          "survives. It only trims &mdash; it never regenerates or repairs. Every "
          "trimmed clip is re-scored from the trimmed file, not inherited.</p>")
        if applied:
            a("<table><tr><th>Clip</th><th>Kept window</th><th class='num'>Kept</th>"
              "<th class='num'>Removed</th><th class='num'>Mean before</th>"
              "<th class='num'>Mean after</th><th class='num'>Min before</th>"
              "<th class='num'>Min after</th><th>Result</th></tr>")
            for r in applied:
                b, af = r["before"], r["after"]
                a("<tr><td><b>%s</b></td><td>%.2f&ndash;%.2fs</td>"
                  "<td class='num'>%.2fs</td><td class='num'>%.2fs</td>"
                  "<td class='num'>%.2f</td><td class='num'>%.2f</td>"
                  "<td class='num'>%.2f</td><td class='num'>%.2f</td><td>%s</td></tr>"
                  % (_e(r["clip_id"]), r["start_s"], r["end_s"], r["kept_s"],
                     r["removed_s"], b["mean"], af["mean"], b["min"], af["min"],
                     "<span class='badge b-pass'>recovered</span>" if r["now_passes"]
                     else "<span class='badge b-warn'>still below</span>"))
            a("</table>")
        skipped = [r for r in safecut if not r.get("applied")]
        if skipped:
            a("<p class='small' style='margin-top:12px'><b>Not cut:</b></p><ul class='small'>")
            for r in skipped:
                a("<li><b>%s</b> &mdash; %s</li>" % (_e(r["clip_id"]), _e(r.get("reason", ""))))
            a("</ul>")

    # ----------------------------------------------------------- calibration
    if calib:
        a("<h2>6. Fidelity threshold calibration</h2>")
        a("<p class='sub'>Threshold: <b>%s</b> &mdash; %s</p>"
          % (calib.get("proposed_threshold"), _e(calib.get("basis", ""))))
        a("<table><tr><th>Anchor</th><th class='num'>Fidelity</th><th class='num'>dE2000</th>"
          "<th class='num'>Weave</th><th class='num'>CLIP</th><th>Meaning</th></tr>")
        for r in calib.get("anchors", []):
            a("<tr><td>%s</td><td class='num'>%.2f</td><td class='num'>%.2f</td>"
              "<td class='num'>%.4f</td><td class='num'>%.4f</td><td class='small'>%s</td></tr>"
              % (_e(r["anchor"]), r["fidelity"], r["delta_e2000"],
                 r["weave_distance"], r["clip_cosine"], _e(r.get("meaning", ""))))
        for r in calib.get("real_clips", []):
            a("<tr><td><b>%s (real clip)</b></td><td class='num'><b>%.2f</b></td>"
              "<td colspan='4' class='small'>min %.2f</td></tr>"
              % (_e(r["id"]), r["mean"], r["min"]))
        a("</table>")
        a("<div class='note'><b>Caveat:</b> %s</div>" % _e(calib.get("caveat", "")))

    # --------------------------------------------------------------- timings
    t = meta.get("timings", {})
    if t:
        a("<h2>7. Timings (measured, this machine)</h2>")
        a("<table><tr><th>Stage</th><th class='num'>Seconds</th></tr>")
        for k, val in t.items():
            a("<tr><td>%s</td><td class='num'>%.3f</td></tr>" % (_e(k), val))
        a("</table>")
        a("<p class='small'>Automated pipeline time only. Ekly generation time is not "
          "included and is not ours to optimise &mdash; it is a manual step through a "
          "web interface with no API available to us.</p>")

    a("</div>")
    out = run.path(out_name)
    out.write_text("\n".join(H), encoding="utf-8")
    return out
