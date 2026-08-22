"""Build the Milestone 3.3 submission PDF (Product Consistency & Quality Testing).

Read-only with respect to every run. All figures come from
evidence/m33_test_results.json (gathered by tools/t_m33_gather.py) and from the
calibration files inside the runs themselves.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

ROOT = pathlib.Path(".")
EV = ROOT / "evidence"
IMG = EV / "m33"
OUT = EV / "Milestone_3.3_Product_Consistency_Quality_Testing.pdf"

D = json.load(open(EV / "m33_test_results.json", encoding="utf-8"))
SAR, KUR = D["saree"], D["kurti"]
KCAL = json.load(open(ROOT / "runs/run_20260822_183825/scores/calibration.json", encoding="utf-8"))
SCAL = SAR["calibration"]
DV = SAR["diversity_full"]

ACCENT = colors.HexColor("#1a4a5a")
RULE = colors.HexColor("#bbbbbb")
GREY = colors.HexColor("#555555")

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.3,
                      leading=13, alignment=TA_LEFT, spaceAfter=5, textColor=colors.black)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.1, leading=10.8, textColor=GREY, spaceAfter=3)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=13.5, leading=16,
                    spaceBefore=0, spaceAfter=3)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=10.4, leading=13,
                    spaceBefore=11, spaceAfter=4, textColor=ACCENT)
H3 = ParagraphStyle("h3", parent=BODY, fontName="Helvetica-Bold", fontSize=9.3, leading=12,
                    spaceBefore=7, spaceAfter=3)
CAP = ParagraphStyle("cap", parent=BODY, fontSize=7.7, leading=10, textColor=GREY,
                     spaceBefore=2, spaceAfter=0)
MONO = ParagraphStyle("mono", parent=BODY, fontName="Courier", fontSize=7.8, leading=10.2, spaceAfter=2)


def rule(space=4):
    t = Table([[""]], colWidths=[170 * mm], rowHeights=[0.1])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.6, RULE),
                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), space)]))
    return t


def tbl(data, widths, size=8.2, align=None, hi=None):
    t = Table(data, colWidths=widths, hAlign="LEFT")
    st = [("FONT", (0, 0), (-1, -1), "Helvetica", size),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
          ("LEFTPADDING", (0, 0), (-1, -1), 4),
          ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#dddddd")),
          ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", size),
          ("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.black),
          ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.black),
          ("LINEBELOW", (0, -1), (-1, -1), 0.7, colors.black)]
    for c in (align or []):
        st.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    for r in (hi or []):
        st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f6eceb")))
    t.setStyle(TableStyle(st))
    return t


def img(name, w_mm, cap=None):
    from PIL import Image as PI
    p = IMG / (name + ".png")
    if not p.exists():
        return [Paragraph("[%s not available]" % name, SMALL)]
    iw, ih = PI.open(p).size
    out = [Image(str(p), width=w_mm * mm, height=w_mm * mm * ih / iw)]
    if cap:
        out.append(Paragraph(cap, CAP))
    return out


story = []
A = story.append
sar_clips = {c["id"]: c for c in SAR["clips"]}
MAN = sar_clips["MANSION-marble"]
ROO = sar_clips["ROOFTOP-night"]
KC = KUR["clips"][0]

# ══════════════════════════════════════════════════ header
A(Paragraph("Milestone 3.3 &mdash; Product Consistency &amp; Quality Testing", H1))
A(Paragraph("Team Code Blooded &nbsp;|&nbsp; GigPoint Hackathon, 22 August 2026 &nbsp;|&nbsp; "
            "Problem 2: AI Ad Generation &nbsp;|&nbsp; Client: Kaladhar", SMALL))
A(rule(7))
A(Paragraph("The client's hard requirement is that a generated advertisement must not misrepresent the "
            "product. This document sets out how that is tested, and reports what the tests actually "
            "found &mdash; including a video that failed and a threshold problem the testing exposed.", BODY))
A(Paragraph("All numbers are produced by the pipeline in this repository. Nothing here is estimated, and "
            "where something has not been tested it is listed in section 11 rather than left implied.", SMALL))

# ─── 1 · scope
A(Paragraph("1. What was actually tested", H2))
A(tbl([
    ["Product", "Run", "Source image", "Videos", "Own calibration", "Gates run"],
    ["Saree", "run_m2_real", "%s, %s" % (SAR["source"]["file"], SAR["source"]["dims"]),
     str(len(SAR["clips"])), "Yes (threshold %.1f)" % SCAL["proposed_threshold"], "Gate 1 + Gate 2"],
    ["Kurti", "run_20260822_183825", "%s, %s" % (KUR["source"]["file"], KUR["source"]["dims"]),
     str(len(KUR["clips"])), "Added for this report (%.1f)" % KCAL["proposed_threshold"],
     "Gate 1 only (single clip)"],
], [16 * mm, 33 * mm, 37 * mm, 13 * mm, 40 * mm, 31 * mm], size=7.9))
A(Paragraph("<b>Two product types have been tested on real generated video: a saree and a kurti.</b> "
            "No other garment type has been run end to end, and none is claimed. A second kurti run "
            "(run_20260822_182724) holds an identical repeat pass of the same clip and is not counted "
            "as an independent test.", BODY))

# ─── 2 · the checks
A(Paragraph("2. What the system checks, and why", H2))
A(Paragraph("Every check below is implemented and runs on every video. All four fidelity metrics are "
            "computed <b>inside the garment mask only</b> &mdash; the background is supposed to change "
            "completely, so measuring it would drown the signal &mdash; and on <b>every 5th frame</b>, "
            "because the drift observed is transient.", BODY))
A(tbl([
    ["Check", "What it detects", "Why it matters"],
    ["Garment segmentation", "Which pixels are the product", "Everything else is measured inside this region"],
    ["Colour ΔE2000", "Dye shift in the garment palette", "The failure a customer notices on arrival"],
    ["CLIP identity", "A different garment substituted", "Catches wholesale replacement, not just tint"],
    ["Weave / texture", "Handloom rendered as flat fabric", "Weave is what a handloom brand sells"],
    ["Border / structure", "Motif distorted or redrawn (SSIM)", "Border and pallu are the identifying detail"],
    ["Per-frame drift", "Brief failures mid-clip", "A single-frame check misses transient drift"],
    ["Motion / flicker", "Frozen clips and hard cuts", "Both are unusable as an advertisement"],
    ["Garment occupancy", "Product shrinking in frame", "A product ad needs a visible product"],
    ["Gate 1 (Fidelity Lock)", "Overall product drift", "Blocks misrepresentation before delivery"],
    ["Gate 2 (Diversity)", "Near-duplicate outputs", "Answers the repetitiveness complaint"],
    ["Safe Cut", "Recoverable clean sections", "Salvages footage without laundering a bad clip"],
], [34 * mm, 57 * mm, 79 * mm]))

# ─── 3 · methodology
A(Paragraph("3. Test methodology", H2))
A(Paragraph("<b>Per-frame, not per-clip.</b> 31 of 153 frames are scored per video, at stride 5. The four "
            "component scores are combined into a Fidelity Score of 0&ndash;100 using fixed weights "
            "(colour 0.35, identity 0.30, weave 0.25, structure 0.10).", BODY))
A(Paragraph("<b>Thresholds are calibrated, not guessed.</b> The scale is anchored by deliberately damaging "
            "the run's own source image in known ways &mdash; hue shifts (dye change), blur (weave "
            "collapse), desaturation &mdash; and scoring those through the identical pipeline. The pass "
            "mark is then built from a constructed limit clip. This is why the two products end up with "
            "different thresholds.", BODY))

A(Paragraph("3.1 Metric validation against known degradation", H3))
A(Paragraph("Before trusting the weave metric on real video it was tested against damage of known "
            "severity. It must rise monotonically as texture is destroyed, and stay near zero when the "
            "same fabric is merely rescaled.", BODY))
A(tbl([
    ["Variant applied to the source", "Weave distance", "High-freq. ratio", "Expected"],
    ["identical", "0.0000", "0.0088", "zero"],
    ["gaussian blur k=3", "0.2423", "0.0028", "rising"],
    ["gaussian blur k=5", "0.3033", "0.0013", "rising"],
    ["gaussian blur k=9", "0.3506", "0.0002", "rising"],
    ["gaussian blur k=15", "0.3604", "0.0001", "rising"],
    ["rescaled x1.5 (same fabric)", "0.0255", "0.0095", "near zero"],
    ["flat colour, no weave at all", "0.3668", "0.0000", "maximum"],
], [56 * mm, 30 * mm, 30 * mm, 26 * mm], align=[1, 2]))
A(Paragraph("Monotonic under increasing blur, saturating on flat colour, and near zero under rescaling. "
            "An earlier cosine-based version of this metric returned ~0.0001 for every frame and was "
            "replaced; a regression test now locks this behaviour in.", SMALL))

A(Paragraph("3.2 Algorithm-level test suite", H3))
A(Paragraph("20 automated tests cover the logic behind the checks: <b>20 passed, 0 failed.</b> They "
            "include validation accept/reject cases, the brief sampler's minimum-difference rule, weave "
            "monotonicity and rescale robustness, subscore bounds, the structure check refusing "
            "low-confidence matches, diversity selection across clusters, and five Safe Cut refusal cases. "
            "These are algorithm tests on fixed inputs and are kept separate from the real-video "
            "measurements reported below.", BODY))

# ─── 4 · calibration results
A(Paragraph("4. Calibration results per product", H2))
A(Paragraph("The same anchor procedure gives different thresholds for different products, which is the "
            "point &mdash; a mostly-white printed kurti and a dyed teal saree do not fail in the same way.", BODY))
srows = [["Anchor (deliberate damage)", "Saree fidelity", "Kurti fidelity"]]
for a in SCAL["anchors"]:
    k = next((x for x in KCAL["anchors"] if x["anchor"] == a["anchor"]), None)
    srows.append([a["anchor"], "%.2f" % a["fidelity"], "%.2f" % k["fidelity"] if k else "-"])
srows.append(["Calibrated pass mark", "%.1f" % SCAL["proposed_threshold"], "%.1f" % KCAL["proposed_threshold"]])
A(tbl(srows, [62 * mm, 34 * mm, 34 * mm], align=[1, 2], hi=[len(srows) - 1]))
A(Paragraph("A 10-degree hue shift costs the saree 23.9 points but the kurti only 6.3, because the kurti "
            "is largely white and neutral &mdash; a hue rotation barely moves its palette. The kurti's "
            "pass mark is therefore higher (63.2 against 51.0).", SMALL))

# ─── 5 · saree results
A(Paragraph("5. Results &mdash; saree run (4 videos)", H2))
rows = [["Video", "Mean", "Min", "ΔE2000", "Weave", "CLIP", "SSIM", "Motion max", "Garment %", "Gate 1"]]
order = ["ROOFTOP-night", "MANDAP-dusk", "BASELINE-courtyard", "MANSION-marble"]
hi = []
for i, cid in enumerate(order, start=1):
    c = sar_clips[cid]
    rejected = cid in [r["id"] for r in SAR["gate1_reject"]]
    if rejected:
        hi.append(i)
    rows.append([cid, "%.2f" % c["mean"], "%.2f" % c["min"], "%.2f" % c["means"]["delta_e2000"],
                 "%.3f" % c["means"]["weave_distance"], "%.3f" % c["means"]["clip_cosine"],
                 "%.3f" % c["means"]["ssim"], "%.3f" % c["motion"]["max"],
                 "%.1f-%.1f" % (c["mask_min"] * 100, c["mask_peak"] * 100),
                 "REJECT" if rejected else "PASS"])
A(tbl(rows, [32 * mm, 14 * mm, 13 * mm, 16 * mm, 15 * mm, 14 * mm, 14 * mm, 19 * mm, 19 * mm, 16 * mm],
      size=7.6, align=[1, 2, 3, 4, 5, 6, 7], hi=hi))
A(Paragraph("Pass mark %.1f, calibrated on this product. Three videos passed; one was rejected."
            % SCAL["proposed_threshold"], SMALL))

# ─── 6 · PASS example
A(Paragraph("6. PASS example &mdash; ROOFTOP-night", H2))
A(Paragraph("The product stays faithful for the whole clip. Its weakest single frame (%.2f) still clears "
            "the pass mark of %.1f by a wide margin, and the standard deviation of %.2f shows the score "
            "barely moves." % (ROO["min"], SCAL["proposed_threshold"], ROO["std"]), BODY))
A(tbl([
    ["Measure", "Value", "Reading"],
    ["Fidelity mean", "%.2f" % ROO["mean"], "well above the %.1f pass mark" % SCAL["proposed_threshold"]],
    ["Fidelity minimum", "%.2f" % ROO["min"], "worst frame still clears the mark"],
    ["Standard deviation", "%.2f" % ROO["std"], "most stable of the four videos"],
    ["Colour ΔE2000", "%.2f" % ROO["means"]["delta_e2000"], "dye held"],
    ["Weave distance", "%.4f" % ROO["means"]["weave_distance"], "lowest texture loss of the four"],
    ["CLIP identity", "%.4f" % ROO["means"]["clip_cosine"], "same garment throughout"],
    ["Motion max", "%.4f" % ROO["motion"]["max"], "smooth, no cut or flicker"],
    ["Garment occupancy", "%.1f%% to %.1f%% of frame" % (ROO["mask_min"] * 100, ROO["mask_peak"] * 100),
     "product stays large in frame"],
], [34 * mm, 44 * mm, 92 * mm]))
A(KeepTogether(img("rooftop_drift", 128,
                   "ROOFTOP-night: per-frame fidelity with the component metrics beneath. "
                   "The curve stays flat and high for the full 5.1 seconds.")))

# ─── 7 · REJECT example
A(Paragraph("7. REJECT example &mdash; MANSION-marble", H2))
A(Paragraph("This is the main quality-testing result. The video was rejected by Gate 1 on <b>two "
            "independent checks</b>, and the rejection was confirmed by inspecting frames rather than "
            "trusted from the score alone.", BODY))
A(tbl([
    ["Measure", "Value", "Verdict"],
    ["Fidelity mean", "%.2f" % MAN["mean"], "below the %.1f pass mark, and below it for essentially the whole clip" % SCAL["proposed_threshold"]],
    ["Fidelity minimum", "%.2f" % MAN["min"], "worst frame at t = %.2fs" % MAN["worst"]["t"]],
    ["Motion max", "%.4f" % MAN["motion"]["max"], "exceeds the 0.25 limit - a hard scene cut"],
    ["Garment occupancy", "%.1f%% falling to %.1f%%" % (MAN["mask_peak"] * 100, MAN["mask_min"] * 100),
     "product collapses to a few percent of frame"],
    ["Colour ΔE2000", "%.2f" % MAN["means"]["delta_e2000"], "high, but see the note below"],
], [34 * mm, 44 * mm, 92 * mm], hi=[1, 3, 4]))
A(Paragraph("<b>This was not primarily a dye-colour failure.</b> The colour figure of %.2f is elevated, but "
            "with the garment at only a few percent of the frame that number is not reliable evidence of a "
            "dye change &mdash; it largely reflects the product being tiny and washed out against bright "
            "marble. Frame inspection confirms the saree is still teal. The actual failure is <b>product "
            "visibility collapsing after a hard scene cut</b>." % MAN["means"]["delta_e2000"], BODY))
A(Paragraph("Recorded Gate 1 reason, verbatim:", BODY))
A(Paragraph("; ".join(SAR["gate1_reject"][0]["reasons"]), MONO))

A(KeepTogether(img("mansion_drift", 128,
                   "MANSION-marble: fidelity sits below the pass mark for the whole clip, "
                   "unlike the transient dip seen in the passing videos.")))
A(KeepTogether(img("mansion_diag", 170,
                   "Frame-level diagnosis. Frame 0 is a near-copy of the reference (38% of frame); after a "
                   "hard cut the model is tiny in a marble hall for the remaining five seconds. The mask "
                   "(pink) tracks correctly &mdash; the product really is that small.")))
A(KeepTogether(img("mansion_weave", 150,
                   "Weave Guard for the worst frame: the motif could not be confidently located anywhere "
                   "on the garment, which is itself the finding.")))

# ─── 8 · kurti
A(Paragraph("8. Second product type &mdash; kurti", H2))
A(Paragraph("A real kurti image (2500&times;2500) was analysed and a real Ekly-generated kurti video was "
            "scored through the identical pipeline. Segmentation, palette extraction and the detail-watch "
            "region all worked on a product with a completely different construction &mdash; a mostly white "
            "garment with dense printed panels rather than a dyed weave.", BODY))
A(tbl([
    ["Measure", "Kurti value", "Note"],
    ["Source image", "%s, %s" % (KUR["source"]["file"], KUR["source"]["dims"]), "square, not portrait"],
    ["Garment mask", "%.2f%% of frame" % (KUR["source"]["garment_fraction"] * 100), "vs %.2f%% for the saree" % (SAR["source"]["garment_fraction"] * 100)],
    ["Delivered video", KC["delivered"], "square 1:1, not the 9:16 requested"],
    ["Fidelity mean / min", "%.2f / %.2f" % (KC["mean"], KC["min"]), "worst frame at t = %.2fs" % KC["worst"]["t"]],
    ["Colour ΔE2000", "%.2f" % KC["means"]["delta_e2000"], "moderate"],
    ["Weave distance", "%.4f" % KC["means"]["weave_distance"], "print detail partly lost"],
    ["CLIP identity", "%.4f" % KC["means"]["clip_cosine"], "garment recognisable"],
    ["Motion max", "%.4f" % KC["motion"]["max"], "smooth, no cut"],
    ["Garment occupancy", "%.1f%% to %.1f%%" % (KC["mask_min"] * 100, KC["mask_peak"] * 100), "small but stable"],
    ["Export", "1080x1920, crop mode", "100% of garment retained; conforms to 9:16"],
], [34 * mm, 56 * mm, 80 * mm]))

A(Paragraph("8.1 A threshold problem the testing exposed", H3))
A(Paragraph("When the operator ran this kurti through the application it was scored against a pass mark of "
            "<b>51.0</b> &mdash; the value calibrated on the <b>saree</b>, carried over in the interface. "
            "Against that number the clip passed at %.2f. Calibrating the same procedure on the kurti's own "
            "source image gives a pass mark of <b>%.1f</b>, and against its own product the clip "
            "<b>does not pass</b>." % (KC["mean"], KCAL["proposed_threshold"]), BODY))
A(tbl([
    ["Pass mark applied", "Origin", "Kurti clip (%.2f)" % KC["mean"], "Outcome"],
    ["51.0", "calibrated on the saree", "%.2f" % KC["mean"], "PASS"],
    ["%.1f" % KCAL["proposed_threshold"], "calibrated on the kurti", "%.2f" % KC["mean"], "REJECT"],
], [30 * mm, 50 * mm, 40 * mm, 50 * mm], hi=[2]))
A(Paragraph("This is reported as a finding, not corrected after the fact: the run's stored result is left "
            "exactly as it was measured. The lesson is that <b>the pass mark is a property of the product, "
            "not of the system</b>, and must be calibrated per product before its videos are judged.", BODY))
A(KeepTogether(img("kurti_mask", 118,
                   "Kurti garment mask. The printed panels are retained after the texture-protection fix; "
                   "the plain white trousers and the handbag remain part of the subject.")))

# ─── 9 · two gates
A(Paragraph("9. The two-gate quality system", H2))
A(Paragraph("<b>Gate 1 &mdash; is the product still faithful?</b> Per-frame drift inside the garment mask, "
            "plus motion checks. Rejects a video for misrepresenting the product.<br/>"
            "<b>Gate 2 &mdash; are the accepted videos actually different from each other?</b> Each video is "
            "reduced to one CLIP embedding averaged over sampled frames, and pairwise cosine distance is "
            "measured. Rejects a video for being a near-duplicate. A video must pass <b>both</b>.", BODY))
ids = DV["ids"]
mat = DV["pairwise_cosine_distance"]
rows = [[""] + [i[:11] for i in ids]]
for i, r in enumerate(mat):
    rows.append([ids[i][:16]] + ["-" if i == j else "%.4f" % r[j] for j in range(len(ids))])
A(tbl(rows, [34 * mm, 34 * mm, 34 * mm, 34 * mm, 34 * mm], size=7.6, align=[1, 2, 3, 4]))
A(Spacer(1, 6))
A(tbl([
    ["Measure", "Value"],
    ["Diversity, all four videos", "%.2f" % DV["diversity_all_four"]],
    ["Diversity, Gate-1 passing set", "%.2f" % DV["diversity_gate1_passing"]],
    ["Closest pair", "%s / %s (%.4f)" % (DV["most_similar_pair"][0], DV["most_similar_pair"][1], DV["most_similar_pair"][2])],
    ["Most distinct pair", "%s / %s (%.4f)" % (DV["most_distinct_pair"][0], DV["most_distinct_pair"][1], DV["most_distinct_pair"][2])],
], [54 * mm, 116 * mm]))
A(Paragraph("<b>The most important result of the whole exercise.</b> The most visually distinct video in "
            "the set is <b>MANSION-marble</b> &mdash; the one Gate 1 rejected. Optimising for variety alone "
            "would have selected the video that misrepresents the product. This came out of the "
            "measurements, not the design, and it is why the two gates are kept independent.", BODY))
A(Paragraph("Gate 2 measured real distances but discarded nothing here: three videos passed Gate 1 against "
            "a request for six, so the selection step had nothing to remove. The filtering itself has not "
            "been exercised on real video.", SMALL))

# ─── 10 · safe cut
A(KeepTogether([
    Paragraph("10. Safe Cut protection", H2),
    Paragraph("Safe Cut trims a video to its longest continuous passing stretch, but only if at least 3.0 "
              "seconds survive. It only trims &mdash; it never regenerates, recolours or repairs &mdash; and "
              "the trimmed file is re-scored from the output rather than inheriting the parent's score.", BODY),
    tbl([["Video", "Outcome", "Reason recorded"]] +
        [[r["clip_id"], "not cut", r.get("reason", "")] for r in SAR["safecut"]],
        [34 * mm, 20 * mm, 116 * mm], size=7.8)]))
A(Paragraph("Nothing was cut, and that is the correct outcome. Three videos had nothing to remove. "
            "MANSION-marble fails throughout rather than transiently, so its longest clean window is 0.00s "
            "&mdash; the guard that stops Safe Cut being used to launder a failing video into a passing one.", BODY))

# ─── 11 · gaps
A(Paragraph("11. What has not been tested", H2))
A(Paragraph(
    "&bull;&nbsp; <b>Only two product types</b> have been run on real generated video: saree and kurti. "
    "Lehenga, dress, shirt and the rest of the product vocabulary are supported in code but untested.<br/>"
    "&bull;&nbsp; <b>The kurti was tested with one video only.</b> Gate 2 could not run on it, so diversity "
    "has never been exercised on a second product.<br/>"
    "&bull;&nbsp; <b>Gate 2 has never rejected anything on real video.</b> The passing pool has always been "
    "smaller than the number of ads requested.<br/>"
    "&bull;&nbsp; <b>Safe Cut has never fired on real footage.</b> Its logic is covered by five unit tests, "
    "but no real clip has yet met the conditions for a trim.<br/>"
    "&bull;&nbsp; <b>No human ground truth.</b> The Fidelity Score has not been validated against human "
    "judgement of whether a video shows the same garment. Thresholds rest on the degradation anchors and "
    "small real samples (4 saree clips, 1 kurti clip).<br/>"
    "&bull;&nbsp; <b>Segmentation limits stand.</b> The garment mask is a heuristic refinement of a subject "
    "mask, not a trained garment segmenter, and it keeps accessories such as the kurti model's handbag.", BODY))

# ─── 12 · conclusion
A(Paragraph("12. Conclusion", H2))
A(Paragraph("The system does perform product consistency testing rather than asserting it. Eleven distinct "
            "checks run on every video; the metrics were validated against damage of known severity before "
            "being trusted; thresholds are derived from the product's own image rather than chosen; and the "
            "testing produced a real rejection (MANSION-marble, on two independent grounds) alongside real "
            "passes.", BODY))
A(Paragraph("The testing also did what good testing is supposed to do &mdash; it found a problem in our own "
            "process. Applying the saree's pass mark to a kurti flipped that clip's verdict from PASS to "
            "REJECT once the kurti was calibrated on its own product. That is now documented in section 8.1 "
            "and is the single most important thing to fix before this is used on a wider catalogue.", BODY))

A(Spacer(1, 4))
A(rule(3))
A(Paragraph("Generated by <font name='Courier' size='7.6'>tools/build_m3_3_pdf.py</font> from "
            "<font name='Courier' size='7.6'>evidence/m33_test_results.json</font> and the run directories "
            "<font name='Courier' size='7.6'>runs/run_m2_real/</font> and "
            "<font name='Courier' size='7.6'>runs/run_20260822_183825/</font>.", SMALL))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.3)
    canvas.setFillColor(GREY)
    canvas.drawString(20 * mm, 12 * mm,
                      "Milestone 3.3 - Product Consistency & Quality Testing | Team Code Blooded")
    canvas.drawRightString(190 * mm, 12 * mm, "Page %d" % doc.page)
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=17 * mm, bottomMargin=20 * mm,
                      title="Milestone 3.3 - Product Consistency & Quality Testing",
                      author="Team Code Blooded")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin,
                                                         doc.width, doc.height, id="f")],
                                   onPage=footer)])
doc.build(story)
print("wrote", OUT)
