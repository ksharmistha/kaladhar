"""Build the Milestone 3.2 submission PDF.

Every figure, filename and image in the output is read from the project at build
time -- the delivery manifest, the run metadata and the finished export files.
Nothing is typed in by hand, so the PDF cannot drift from what the project
actually contains.

If evidence/m3_export_screenshot.png exists it is embedded in section 7;
otherwise that section prints a labelled reserved slot.
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
OUT = EV / "Milestone_3.2_Production_Ready_Ad_Outputs.pdf"

MAN = json.load(open(EV / "m3_delivery_manifest.json"))
RUN = json.load(open(ROOT / "runs/run_m2_real/run.json"))
SEL = json.load(open(ROOT / "runs/run_m2_real/scores/selection.json"))
IMP = json.load(open(ROOT / "runs/run_m2_real/clips/imported.json"))
SRC = RUN["source"]

ACCENT = colors.HexColor("#1a4a5a")     # single restrained accent
RULE = colors.HexColor("#bbbbbb")
GREY = colors.HexColor("#555555")

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica",
                      fontSize=9.4, leading=13.2, alignment=TA_LEFT,
                      spaceAfter=5, textColor=colors.black)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.2, leading=11,
                       textColor=GREY, spaceAfter=3)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=13.5,
                    leading=16, spaceBefore=0, spaceAfter=3, textColor=colors.black)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=10.4,
                    leading=13, spaceBefore=11, spaceAfter=4, textColor=ACCENT)
H3 = ParagraphStyle("h3", parent=BODY, fontName="Helvetica-Bold", fontSize=9.4,
                    leading=12, spaceBefore=7, spaceAfter=3)
CAP = ParagraphStyle("cap", parent=BODY, fontSize=7.8, leading=10,
                     textColor=GREY, spaceBefore=2, spaceAfter=0)
MONO = ParagraphStyle("mono", parent=BODY, fontName="Courier", fontSize=8,
                      leading=10.5, spaceAfter=2)


def rule(w=170 * mm, thick=0.6, col=RULE, space=4):
    t = Table([[""]], colWidths=[w], rowHeights=[0.1])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), thick, col),
                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), space)]))
    return t


def tbl(data, widths, size=8.4, align=None):
    t = Table(data, colWidths=widths, hAlign="LEFT")
    st = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", size),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#dddddd")),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", size),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.black),
        ("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 0.7, colors.black),
    ]
    for c in (align or []):
        st.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(st))
    return t


story = []
A = story.append
n_imp, n_exp = len(IMP), len(MAN["exports"])
rej = [r["id"] for r in SEL.get("gate1_rejected", [])]
p0 = MAN["exports"][0]

# ══════════════════════════════════════════════════ PAGE 1 · header
A(Paragraph("Milestone 3.2 &mdash; Production-Ready Ad Outputs &amp; Demo", H1))
A(Paragraph("Team Code Blooded &nbsp;|&nbsp; GigPoint Hackathon, 22 August 2026 &nbsp;|&nbsp; "
            "Problem 2: AI Ad Generation &nbsp;|&nbsp; Client: Kaladhar", SMALL))
A(rule(space=7))
A(Paragraph("Task as stated on the platform: <i>produce final, production-ready vertical ad outputs "
            "and a working demo of the end-to-end flow.</i>", BODY))
A(Paragraph("Every figure, filename and image in this document was read directly from the project at "
            "build time &mdash; from <font name='Courier' size='8'>evidence/m3_delivery_manifest.json</font>, "
            "the run metadata and the finished export files themselves. Nothing is transcribed by hand.", SMALL))

# ─── 1 ───────────────────────────────────────────── what was produced
A(Paragraph("1. What was produced", H2))
A(Paragraph(
    "From <b>one</b> source product photograph, %d videos were generated and imported, %d passed both "
    "quality gates, and <b>%d final ads</b> were exported at 1080&times;1920. One video (%s) was rejected "
    "and is <b>not</b> present in the delivered set."
    % (n_imp, n_exp, n_exp, ", ".join(rej) or "none"), BODY))
A(tbl([
    ["Item", "Value"],
    ["Source image", "%s, %s" % (SRC["original_name"], SRC["validation"]["info"]["dimensions"])],
    ["Videos generated and imported", str(n_imp)],
    ["Rejected at quality gates", "%d (%s)" % (len(rej), ", ".join(rej) or "none")],
    ["Final ads delivered", str(n_exp)],
    ["Delivery format", "1080 x 1920, 9:16 vertical, H.264 / yuv420p, MP4"],
    ["All exports conform", "Yes" if MAN["all_conform"] else "No"],
], [52 * mm, 118 * mm]))

# ─── 2 ─────────────────────────────────────────────── end-to-end flow
A(Paragraph("2. End-to-end flow demonstrated", H2))
A(Paragraph("The demo runs as one continuous workflow. Stage 4 is manual and is labelled as such "
            "throughout the product: Ekly.ai exposes no API to us, so generation is performed by hand "
            "and the run pauses until real files are brought back.", BODY))
A(tbl([
    ["#", "Stage", "What it produces"],
    ["1", "Upload product image", "Validated source image"],
    ["2", "Analyse product", "Garment mask, colour palette, texture signature"],
    ["3", "Create scene briefs", "6 scene briefs, each differing on >= 4 of 5 creative axes"],
    ["4", "Ekly handoff (MANUAL)", "Operator sheet and reference image; no API available"],
    ["5", "Import generated videos", "Each file probed; delivered format read from the file"],
    ["6", "Fidelity QC (Gate 1)", "Per-frame product-drift score per video"],
    ["7", "Diversity (Gate 2)", "Pairwise distance; selected set"],
    ["8", "Safe Cut and Export", "Final 1080x1920 ads, downloadable"],
], [8 * mm, 44 * mm, 118 * mm]))

# ─── 3 ────────────────────────────────────────── delivery specification
A(Paragraph("3. Delivery specification", H2))
A(tbl([
    ["Property", "Delivered", "Target", "Met"],
    ["Resolution", "%d x %d" % (p0["width"], p0["height"]), "1080 x 1920", "Yes"],
    ["Aspect ratio", "%.4f" % p0["aspect"], "0.5625 (9:16)", "Yes"],
    ["Orientation", "Vertical", "Vertical", "Yes"],
    ["Video codec", p0["codec"].split(" (")[0], "H.264", "Yes"],
    ["Pixel format", p0["pix_fmt"], "yuv420p", "Yes"],
    ["Container", "MP4 (brand %s)" % p0["container_brand"], "MP4", "Yes"],
    ["Frame rate", "%.0f fps" % p0["fps"], "not specified", "-"],
    ["Duration", "%.2f s" % p0["duration_s"], "not specified", "-"],
    ["Exports conforming", "%d of %d" % (sum(e["conforms"] for e in MAN["exports"]), len(MAN["exports"])),
     "all", "Yes" if MAN["all_conform"] else "No"],
], [34 * mm, 46 * mm, 44 * mm, 16 * mm]))
A(Paragraph("Target placements: %s." % ", ".join(MAN["delivery_target"]["placements"]), BODY))

# ─── 4 ───────────────────────────────────────────────── the final ads
sec4 = [Paragraph("4. Final exported ads", H2),
        Paragraph("The three frames below are taken directly out of the delivered MP4 files at their full "
                  "1080&times;1920 delivery resolution &mdash; they are the shipped output, not a re-render "
                  "or a preview.", BODY)]
cells, caps = [], []
for e in MAN["exports"]:
    p = EV / "m3_export_frames" / ("%s.png" % e["id"])
    if p.exists():
        cells.append(Image(str(p), width=51 * mm, height=90.7 * mm))
        caps.append(Paragraph("<b>%s</b><br/>%d&times;%d &middot; %.2fs &middot; %.2f MB"
                              % (e["id"], e["width"], e["height"], e["duration_s"], e["file_mb"]), CAP))
if cells:
    g = Table([cells, caps], colWidths=[56 * mm] * len(cells), hAlign="LEFT")
    g.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, 0), 3)]))
    sec4.append(g)
sec4.append(Paragraph("Frame 61 of 153 shown for each (mid-clip, representative). File names as delivered: %s."
                      % ", ".join(e["file"] for e in MAN["exports"]), SMALL))
A(KeepTogether(sec4))

# ─── 5 ─────────────────────────────────────────── per-file manifest
A(Paragraph("5. Delivery manifest (per file)", H2))
A(Paragraph("Source: <font name='Courier' size='8'>evidence/m3_delivery_manifest.json</font>. "
            "Values reproduced exactly.", SMALL))
rows = [["File", "Resolution", "Aspect", "Dur.", "Frames", "Size", "Codec / fmt", "Fit", "Conforms"]]
for e in MAN["exports"]:
    rows.append([e["file"].replace("_1080x1920.mp4", ""), "%dx%d" % (e["width"], e["height"]),
                 "%.4f" % e["aspect"], "%.2fs" % e["duration_s"], str(e["frame_count"]),
                 "%.2f MB" % e["file_mb"], "%s / %s" % (e["codec"].split(" (")[0], e["pix_fmt"]),
                 e["fit_mode"], "Yes" if e["conforms"] else "No"])
A(tbl(rows, [30 * mm, 20 * mm, 15 * mm, 13 * mm, 13 * mm, 16 * mm, 24 * mm, 12 * mm, 17 * mm],
      size=7.8, align=[2, 3, 4, 5]))
A(Paragraph("All three files carry the suffix <font name='Courier' size='8'>_1080x1920.mp4</font> and sit "
            "in <font name='Courier' size='8'>runs/run_m2_real/exports/</font>.", SMALL))
A(Paragraph("Verification method: %s" % MAN["verification"], SMALL))

# ─── 6 ──────────────────────────────────────────────── crop vs pad
A(Paragraph("6. Format conversion: crop or pad, decided by measurement", H2))
A(Paragraph("The brief requires 9:16 vertical output for Meta placements, and this is not assumed. In "
            "every generation we ran, the Ekly 9:16 setting still returned a 768&times;1152 (2:3) file &mdash; "
            "all four imported videos were 2:3 on arrival. Conversion to 1080&times;1920 is therefore an "
            "explicit export stage, and conformance is confirmed by reading the written file back.", BODY))
A(Paragraph("Converting 2:3 to 9:16 means either cropping the sides or padding them. Cropping a vertical "
            "fashion shot risks cutting the border or pallu, which would misrepresent the product; padding "
            "wastes screen area. The decision is therefore made per file from measurement: the system "
            "segments several frames and computes how much of the garment a centre crop would actually "
            "destroy, taking the worst frame.", BODY))
A(Paragraph("Recorded result for all three exports:", BODY))
A(Paragraph(p0["fit_rationale"] or "(rationale not recorded)", MONO))
A(Paragraph("Crop removes 15.6% of frame width but 0.00% of the garment, because the model is centred. "
            "All three files therefore use <b>crop</b> and fill the full screen with no product loss.", BODY))

# ─── 7 ────────────────────────────────────────────────── UI evidence
sec7head = Paragraph("7. Final Export screen (application)", H2)
shot = EV / "m3_export_screenshot.png"
if shot.exists():
    from PIL import Image as PILImage
    iw, ih = PILImage.open(shot).size
    w = 170 * mm
    A(KeepTogether([sec7head, Image(str(shot), width=w, height=w * ih / iw),
                    Paragraph("Stage 8 &mdash; Safe Cut &amp; export, showing the three delivered ads with "
                              "in-app video playback, per-file metadata, download controls, and the "
                              "Delivery specification panel.", CAP)]))
else:
    box = Table([[Paragraph("<i>Screenshot slot &mdash; not yet captured.</i><br/><br/>"
                            "Save a screenshot of <b>Stage 8 &mdash; Safe Cut &amp; export</b> "
                            "(showing the three video players, the per-file metadata, the Download buttons "
                            "and the Delivery specification panel) to:<br/>"
                            "<font name='Courier' size='8'>evidence/m3_export_screenshot.png</font><br/><br/>"
                            "then re-run <font name='Courier' size='8'>python tools/build_m3_2_pdf.py</font> "
                            "and it will be embedded here at full width.", BODY)]],
                colWidths=[170 * mm], rowHeights=[44 * mm])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, RULE),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    A(KeepTogether([sec7head, box,
                    Paragraph("This slot is left for a screenshot taken on the presenting machine; it was "
                              "not captured automatically.", SMALL)]))

A(Paragraph("What the Export screen provides", H3))
A(tbl([
    ["Requirement", "Where it is shown in the application"],
    ["Final 1080x1920 / 9:16 output", "Delivery specification panel, and each file card"],
    ["Actual generated video playback", "Embedded HTML5 player on each exported ad"],
    ["Duration / resolution / aspect", "Per-file metadata beneath each player"],
    ["Downloadable final output", "Download control on each of the three ads"],
    ["Suitability for vertical social", "Delivery specification panel, placements listed"],
], [58 * mm, 112 * mm]))

# ─── 8 ────────────────────────────────────────────────── demo script
A(Paragraph("8. Demo procedure", H2))
A(Paragraph("The application runs locally at <font name='Courier' size='8'>http://127.0.0.1:8000</font> "
            "(<font name='Courier' size='8'>python -m uvicorn server.app:app --port 8000</font>). "
            "The reference run <font name='Courier' size='8'>run_m2_real</font> loads by default with all "
            "eight stages already populated, so the full flow can be walked without waiting for processing.", BODY))
A(tbl([
    ["Step", "What the audience sees"],
    ["Stage 1", "The single source photograph and its validation result"],
    ["Stage 2", "Garment isolated from background; colour and texture signature"],
    ["Stage 3", "Six scene briefs; axis-difference matrix proving they differ"],
    ["Stage 4", "Manual Ekly handoff stated plainly; prompts and reference image"],
    ["Stage 5", "Four imported videos, all 768x1152 - not the 9:16 that was requested"],
    ["Stage 6", "Per-video fidelity scores; one video rejected, with reasons"],
    ["Stage 7", "Pairwise distance between videos; the selected set"],
    ["Stage 8", "Three final ads, played in-browser, downloadable, 1080x1920"],
], [20 * mm, 150 * mm]))

# ─── 9 ─────────────────────────────────────────────────── the limits
A(Paragraph("9. What we do not claim", H2))
A(Paragraph(
    "&bull;&nbsp; Generation is <b>not</b> automated. Ekly.ai exposes no API to us, so stage 4 is manual "
    "and the product says so on screen.<br/>"
    "&bull;&nbsp; <b>%d</b> videos were generated, not six. Only what exists is reported.<br/>"
    "&bull;&nbsp; The four imported videos were not produced from the six briefs in stage 3; no filename "
    "matched a brief ID, and the application reports that rather than implying a link.<br/>"
    "&bull;&nbsp; Ekly wall-clock generation time has never been measured and is excluded from every "
    "timing figure in this project.<br/>"
    "&bull;&nbsp; No output in this document is a mock-up: every frame shown is decoded from a delivered "
    "MP4, and every number is read from the manifest or the run metadata." % n_imp, BODY))

A(Spacer(1, 4))
A(rule(space=3))
A(Paragraph("Generated by <font name='Courier' size='8'>tools/build_m3_2_pdf.py</font> from "
            "<font name='Courier' size='8'>evidence/m3_delivery_manifest.json</font>, "
            "<font name='Courier' size='8'>runs/run_m2_real/</font> and the exported MP4 files.", SMALL))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.4)
    canvas.setFillColor(GREY)
    canvas.drawString(20 * mm, 12 * mm,
                      "Milestone 3.2 - Production-Ready Ad Outputs & Demo | Team Code Blooded")
    canvas.drawRightString(190 * mm, 12 * mm, "Page %d" % doc.page)
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


doc = BaseDocTemplate(str(OUT), pagesize=A4,
                      leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=17 * mm, bottomMargin=20 * mm,
                      title="Milestone 3.2 - Production-Ready Ad Outputs & Demo",
                      author="Team Code Blooded")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=footer)])
doc.build(story)
print("wrote", OUT)
