/* Milestone 3 final presentation — Team Code Blooded.
 * Every number and image comes from the project's own measured output.
 */
const pptx = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const EV = path.join(ROOT, "evidence");
const img = (p) => path.join(EV, p);

const P = new pptx();
P.layout = "LAYOUT_WIDE";           // 13.3 x 7.5
P.author = "Team Code Blooded";
P.title = "Product Fidelity Studio — Milestone 3";

/* ── palette: the product's own identity ───────────────────────────── */
const INK = "131A1F";      // near-black
const INK2 = "2B3A44";     // slate
const TEAL = "0E7D8C";     // single accent
const TEAL_D = "0A5D69";
const MUTED = "6A7B87";
const LINE = "E1E6E9";
const SAND = "F4F1EC";
const PASS = "1A7A52";
const FAIL = "A8342A";
const WHITE = "FFFFFF";

const HFONT = "Cambria";   // safe-list serif for headers
const BFONT = "Calibri";   // safe-list sans for body

const W = 13.3, H = 7.5, M = 0.62;

/* ── helpers ───────────────────────────────────────────────────────── */
function darkSlide() {
  const s = P.addSlide();
  s.background = { color: INK };
  return s;
}
function lightSlide(title, kicker) {
  const s = P.addSlide();
  s.background = { color: WHITE };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: M, y: 0.42, w: 8, h: 0.26, fontFace: BFONT, fontSize: 11, bold: true,
      color: TEAL, charSpacing: 1.6, margin: 0,
    });
  }
  if (title) {
    s.addText(title, {
      x: M, y: kicker ? 0.7 : 0.5, w: W - 2 * M, h: 0.62,
      fontFace: HFONT, fontSize: 30, bold: true, color: INK, margin: 0,
    });
  }
  return s;
}
function note(s, t) { s.addNotes(t); }

/* a labelled statistic block */
function stat(s, x, y, w, value, label, color) {
  s.addText(value, {
    x, y, w, h: 0.58, fontFace: HFONT, fontSize: 34, bold: true,
    color: color || INK, margin: 0,
  });
  s.addText(label, {
    x, y: y + 0.56, w, h: 0.42, fontFace: BFONT, fontSize: 11.5,
    color: MUTED, margin: 0,
  });
}

/* a soft card */
function card(s, x, y, w, h, fill) {
  s.addShape(P.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06,
    fill: { color: fill || SAND }, line: { color: LINE, width: 0.75 },
  });
}

function bullets(s, items, x, y, w, size) {
  s.addText(
    items.map((t, i) => ({
      text: t,
      options: { bullet: true, breakLine: i !== items.length - 1 },
    })),
    { x, y, w, h: 0.4 * items.length + 0.5, fontFace: BFONT,
      fontSize: size || 14, color: INK2, lineSpacing: 20, paraSpaceAfter: 7, margin: 0 }
  );
}

/* ════════════════════════════════ 1 · TITLE ════════════════════════ */
{
  const s = darkSlide();
  s.addText("Product Fidelity Studio", {
    x: M, y: 2.25, w: 9.6, h: 1.0, fontFace: HFONT, fontSize: 46, bold: true,
    color: WHITE, margin: 0,
  });
  s.addText("Quality control for AI-generated fashion advertising", {
    x: M, y: 3.3, w: 9.6, h: 0.5, fontFace: BFONT, fontSize: 18, color: "9FB3BD", margin: 0,
  });
  s.addShape(P.ShapeType.rect, { x: M, y: 4.05, w: 1.1, h: 0.035, fill: { color: TEAL } });
  s.addText("Team Code Blooded", {
    x: M, y: 4.35, w: 6, h: 0.36, fontFace: BFONT, fontSize: 15, bold: true, color: WHITE, margin: 0,
  });
  s.addText("Milestone 3  ·  GigPoint Hackathon, 22 August 2026\nProblem 2 — AI Ad Generation  ·  Client: Kaladhar", {
    x: M, y: 4.72, w: 7, h: 0.7, fontFace: BFONT, fontSize: 12.5, color: MUTED, lineSpacing: 17, margin: 0,
  });
  s.addImage({ path: img("m3_export_frames/ROOFTOP-night.png"), x: 9.55, y: 0.85, w: 1.62, h: 2.88 });
  s.addImage({ path: img("m3_export_frames/MANDAP-dusk.png"), x: 11.3, y: 0.85, w: 1.62, h: 2.88 });
  s.addImage({ path: img("m3_export_frames/BASELINE-courtyard.png"), x: 9.55, y: 3.85, w: 1.62, h: 2.88 });
  s.addText("3", {
    x: 11.3, y: 4.4, w: 1.62, h: 0.8, fontFace: HFONT, fontSize: 44, bold: true,
    color: TEAL, align: "center", margin: 0,
  });
  s.addText("delivered ads\n1080×1920 · 9:16", {
    x: 11.3, y: 5.22, w: 1.62, h: 0.7, fontFace: BFONT, fontSize: 10.5, color: "9FB3BD",
    align: "center", lineSpacing: 14, margin: 0,
  });
  note(s, "One image in, multiple verified vertical ads out. We are the quality layer around an AI video generator, not another generator.");
}

/* ════════════════════════════════ 2 · PROBLEM ══════════════════════ */
{
  const s = lightSlide("Two failures make AI ad tools unusable", "The problem");
  s.addText("Kaladhar needs many ads per product but cannot reshoot for each one. AI video solves the cost — and introduces two new problems.", {
    x: M, y: 1.5, w: 7.4, h: 0.7, fontFace: BFONT, fontSize: 14.5, color: MUTED, lineSpacing: 21, margin: 0,
  });

  card(s, M, 2.4, 3.55, 2.5);
  s.addText("Repetitive", { x: M + 0.28, y: 2.62, w: 3, h: 0.4, fontFace: HFONT, fontSize: 20, bold: true, color: INK, margin: 0 });
  s.addText("Re-prompting one idea with different adjectives moves the render, not the concept. Ten outputs, one idea.", {
    x: M + 0.28, y: 3.05, w: 3.0, h: 1.6, fontFace: BFONT, fontSize: 12.5, color: INK2, lineSpacing: 17, margin: 0,
  });

  card(s, M + 3.85, 2.4, 3.55, 2.5);
  s.addText("Product drifts", { x: M + 4.13, y: 2.62, w: 3, h: 0.4, fontFace: HFONT, fontSize: 20, bold: true, color: FAIL, margin: 0 });
  s.addText("Colour shifts, weave flattens, the border is redrawn. The ad no longer shows what is being sold.", {
    x: M + 4.13, y: 3.05, w: 3.0, h: 1.6, fontFace: BFONT, fontSize: 12.5, color: INK2, lineSpacing: 17, margin: 0,
  });

  s.addShape(P.ShapeType.roundRect, {
    x: M, y: 5.2, w: 7.4, h: 1.35, rectRadius: 0.06,
    fill: { color: INK }, line: { color: INK },
  });
  s.addText("Client's hard constraint", {
    x: M + 0.28, y: 5.38, w: 6.9, h: 0.3, fontFace: BFONT, fontSize: 11, bold: true, color: "7FC3CE", charSpacing: 1.2, margin: 0,
  });
  s.addText("“The generated advertisement should not misrepresent the product being sold.”", {
    x: M + 0.28, y: 5.68, w: 6.9, h: 0.7, fontFace: HFONT, fontSize: 15, italic: true, color: WHITE, lineSpacing: 20, margin: 0,
  });

  s.addImage({ path: img("m33/saree_weaveguard_src.png"), x: 8.35, y: 1.5, w: 2.3, h: 2.3 });
  s.addImage({ path: img("m33/mansion_weave.png"), x: 8.35, y: 4.02, w: 4.35, h: 2.71 });
  s.addText("Source weave (left) vs a generated frame where the motif could not be found at all", {
    x: 10.8, y: 1.6, w: 1.95, h: 1.6, fontFace: BFONT, fontSize: 10.5, color: MUTED, lineSpacing: 14, margin: 0,
  });
  note(s, "The client named both failures. That is what makes this problem attackable — we are not guessing at requirements.");
}

/* ════════════════════════════════ 3 · SOLUTION ═════════════════════ */
{
  const s = lightSlide("Maximum variation in the scene. Zero variation in the product.", "Our solution");
  s.addText("The brief asks for two things that pull against each other. We split the frame into two zones with opposite rules and enforce each separately.", {
    x: M, y: 1.55, w: 11.9, h: 0.5, fontFace: BFONT, fontSize: 14.5, color: MUTED, margin: 0,
  });

  card(s, M, 2.25, 5.75, 1.85, "FBF7F6");
  s.addText("PRODUCT REGION", { x: M + 0.3, y: 2.45, w: 4, h: 0.28, fontFace: BFONT, fontSize: 10.5, bold: true, color: FAIL, charSpacing: 1.4, margin: 0 });
  s.addText("must not change", { x: M + 0.3, y: 2.75, w: 5, h: 0.42, fontFace: HFONT, fontSize: 22, bold: true, color: INK, margin: 0 });
  s.addText("Enforced by the Fidelity Lock — Gate 1", { x: M + 0.3, y: 3.28, w: 5.2, h: 0.4, fontFace: BFONT, fontSize: 13, color: INK2, margin: 0 });

  card(s, M + 6.05, 2.25, 5.75, 1.85, "F2F8F9");
  s.addText("SCENE REGION", { x: M + 6.35, y: 2.45, w: 4, h: 0.28, fontFace: BFONT, fontSize: 10.5, bold: true, color: TEAL, charSpacing: 1.4, margin: 0 });
  s.addText("must change", { x: M + 6.35, y: 2.75, w: 5, h: 0.42, fontFace: HFONT, fontSize: 22, bold: true, color: INK, margin: 0 });
  s.addText("Enforced by the Diversity Engine — Gate 2", { x: M + 6.35, y: 3.28, w: 5.2, h: 0.4, fontFace: BFONT, fontSize: 13, color: INK2, margin: 0 });

  s.addText("Consistency is measured, not asserted", {
    x: M, y: 4.45, w: 7, h: 0.45, fontFace: HFONT, fontSize: 19, bold: true, color: INK, margin: 0,
  });
  bullets(s, [
    "Every video is scored per frame, inside the garment mask only",
    "Thresholds are calibrated from the product's own image, not chosen",
    "Anything that drifts too far is rejected before it can ship",
    "We are a QC layer around a generator — not another generator",
  ], M, 4.95, 7.1, 13.5);

  s.addImage({ path: img("m33/raw_frames.png"), x: 7.9, y: 4.6, w: 4.9, h: 1.5 });
  s.addText("Source, then the same saree in four generated scenes", {
    x: 7.9, y: 6.15, w: 4.9, h: 0.3, fontFace: BFONT, fontSize: 10.5, color: MUTED, margin: 0,
  });
  note(s, "This is the whole pitch in one line. The two zones have opposite rules, and each has its own gate.");
}

/* ════════════════════════════════ 4 · WORKFLOW ═════════════════════ */
{
  const s = lightSlide("Eight stages, automated either side of one manual step", "How it works");
  const steps = [
    ["1", "Upload", "validate source"],
    ["2", "Analyse", "mask + signature"],
    ["3", "Briefs", "5-axis matrix"],
    ["4", "Ekly", "MANUAL — no API"],
    ["5", "Import", "probe every file"],
    ["6", "Fidelity", "Gate 1"],
    ["7", "Diversity", "Gate 2"],
    ["8", "Export", "1080×1920"],
  ];
  const bw = 1.44, gap = 0.075, x0 = M;
  steps.forEach((st, i) => {
    const x = x0 + i * (bw + gap);
    const manual = i === 3;
    s.addShape(P.ShapeType.roundRect, {
      x, y: 1.95, w: bw, h: 1.5, rectRadius: 0.07,
      fill: { color: manual ? "F3EFFA" : SAND },
      line: { color: manual ? "C9BCEB" : LINE, width: manual ? 1.25 : 0.75 },
    });
    s.addShape(P.ShapeType.ellipse, {
      x: x + 0.12, y: 2.08, w: 0.34, h: 0.34,
      fill: { color: manual ? "5A4A86" : TEAL }, line: { color: manual ? "5A4A86" : TEAL },
    });
    s.addText(st[0], { x: x + 0.12, y: 2.11, w: 0.34, h: 0.28, fontFace: BFONT, fontSize: 12, bold: true, color: WHITE, align: "center", margin: 0 });
    s.addText(st[1], { x: x + 0.12, y: 2.52, w: bw - 0.24, h: 0.3, fontFace: BFONT, fontSize: 13, bold: true, color: INK, margin: 0 });
    s.addText(st[2], { x: x + 0.12, y: 2.84, w: bw - 0.24, h: 0.5, fontFace: BFONT, fontSize: 10.5, color: MUTED, lineSpacing: 13, margin: 0 });
    if (i < steps.length - 1) {
      s.addShape(P.ShapeType.rect, { x: x + bw + 0.005, y: 2.69, w: gap - 0.01, h: 0.02, fill: { color: "C9D2D7" } });
    }
  });

  s.addShape(P.ShapeType.roundRect, {
    x: M, y: 3.85, w: 6.05, h: 1.85, rectRadius: 0.06,
    fill: { color: "F3EFFA" }, line: { color: "C9BCEB", width: 1 },
  });
  s.addText("Stage 4 is manual — and we say so", {
    x: M + 0.28, y: 4.05, w: 5.5, h: 0.35, fontFace: HFONT, fontSize: 17, bold: true, color: "3D3168", margin: 0,
  });
  s.addText("Ekly.ai exposes no API to us. Nothing in the product calls, queues, batches or polls it. The run pauses at AWAITING_CLIPS and resumes when real MP4s come back.\n\nThat is not a workaround. The client's problem is not that generation is unavailable — it is that output comes back repetitive and drifting. Both are solved before and after generation.", {
    x: M + 0.28, y: 4.42, w: 5.5, h: 1.25, fontFace: BFONT, fontSize: 11.5, color: "3D3168", lineSpacing: 15, margin: 0,
  });

  stat(s, 7.15, 3.95, 2.2, "45.50", "credits per generation (measured)", INK);
  stat(s, 9.55, 3.95, 2.2, "4 / 4", "clips came back 2:3, not the 9:16 requested", FAIL);
  stat(s, 7.15, 5.05, 2.2, "221 s", "automated pipeline, 4 clips", INK);
  stat(s, 9.55, 5.05, 2.2, "20 / 20", "algorithm tests passing", PASS);
  note(s, "Judges always ask whether generation is automated. The answer is no, and we lead with it — the value is on either side of that step.");
}

/* ════════════════════════════════ 5 · ANALYSIS ═════════════════════ */
{
  const s = lightSlide("The product is fingerprinted before anything is generated", "Stage 2 — Product analysis");
  s.addImage({ path: img("m33/saree_mask.png"), x: M, y: 1.6, w: 2.6, h: 3.77 });
  s.addText("Garment mask", { x: M, y: 5.45, w: 2.6, h: 0.3, fontFace: BFONT, fontSize: 12.5, bold: true, color: INK, margin: 0 });
  s.addText("rembg subject mask refined by a skin-chrominance heuristic. 35.73% of frame.", {
    x: M, y: 5.74, w: 2.6, h: 0.8, fontFace: BFONT, fontSize: 10.5, color: MUTED, lineSpacing: 14, margin: 0,
  });

  s.addImage({ path: img("m33/saree_weaveguard_src.png"), x: 3.5, y: 1.6, w: 2.6, h: 2.6 });
  s.addText("Weave Guard region", { x: 3.5, y: 4.3, w: 2.6, h: 0.3, fontFace: BFONT, fontSize: 12.5, bold: true, color: INK, margin: 0 });
  s.addText("The most texture-dense patch inside the mask, found automatically — no hardcoded coordinates. On a saree it lands on the pallu brocade.", {
    x: 3.5, y: 4.59, w: 2.6, h: 1.1, fontFace: BFONT, fontSize: 10.5, color: MUTED, lineSpacing: 14, margin: 0,
  });

  s.addText("Reference signature", { x: 6.85, y: 1.62, w: 6, h: 0.4, fontFace: HFONT, fontSize: 20, bold: true, color: INK, margin: 0 });
  s.addText("Computed once per product and reused for every video and every re-score.", {
    x: 6.85, y: 2.02, w: 5.85, h: 0.4, fontFace: BFONT, fontSize: 12.5, color: MUTED, margin: 0,
  });
  const sig = [
    ["Palette", "5 dominant colours, CIELAB k-means, garment pixels only"],
    ["Weave descriptor", "27-d — Gabor bank + FFT radial profile + absolute HF energy"],
    ["Identity vector", "512-d CLIP embedding of the masked garment crop"],
    ["Detail patch", "128×128 highest-texture square inside the mask"],
  ];
  sig.forEach((r, i) => {
    const y = 2.6 + i * 0.72;
    s.addText(r[0], { x: 6.85, y, w: 2.0, h: 0.3, fontFace: BFONT, fontSize: 12.5, bold: true, color: TEAL_D, margin: 0 });
    s.addText(r[1], { x: 8.9, y, w: 3.85, h: 0.62, fontFace: BFONT, fontSize: 11.5, color: INK2, lineSpacing: 15, margin: 0 });
    s.addShape(P.ShapeType.rect, { x: 6.85, y: y + 0.6, w: 5.9, h: 0.008, fill: { color: LINE } });
  });
  s.addText("Every fidelity metric is later measured against this — and only inside the mask, because the background is supposed to change completely.", {
    x: 6.85, y: 5.6, w: 5.9, h: 0.8, fontFace: BFONT, fontSize: 12, italic: true, color: INK2, lineSpacing: 16, margin: 0,
  });
  note(s, "Mask-only measurement is the key design decision. Measuring the whole frame would drown the drift signal in the scene change we asked for.");
}

/* ════════════════════════════════ 6 · MATRIX ═══════════════════════ */
{
  const s = lightSlide("Variation is structural, not verbal", "Stage 3 — Scene briefs");
  s.addText("Re-prompting one idea with different adjectives is exactly the failure the client complained about. Instead every brief is a point on a five-axis grid.", {
    x: M, y: 1.55, w: 7.3, h: 0.6, fontFace: BFONT, fontSize: 14, color: MUTED, lineSpacing: 20, margin: 0,
  });

  const axes = [
    ["Environment", "6", "mansion · mandap · palace · café · resort · rooftop"],
    ["Lighting", "6", "softbox · golden hour · lamp · overcast · practicals · high-key"],
    ["Camera", "6", "push-in · orbit · vertical reveal · static · rack focus · parallax"],
    ["Concept", "6", "heritage · occasion · everyday · gifting · luxury · styling"],
    ["Colour grade", "4", "neutral · warm gold · cool editorial · rich festive"],
  ];
  axes.forEach((a, i) => {
    const y = 2.35 + i * 0.62;
    s.addShape(P.ShapeType.roundRect, { x: M, y, w: 0.52, h: 0.44, rectRadius: 0.05, fill: { color: TEAL }, line: { color: TEAL } });
    s.addText(a[1], { x: M, y: y + 0.05, w: 0.52, h: 0.32, fontFace: BFONT, fontSize: 13, bold: true, color: WHITE, align: "center", margin: 0 });
    s.addText(a[0], { x: M + 0.68, y: y + 0.02, w: 1.75, h: 0.32, fontFace: BFONT, fontSize: 13, bold: true, color: INK, margin: 0 });
    s.addText(a[2], { x: M + 2.5, y: y + 0.04, w: 4.85, h: 0.34, fontFace: BFONT, fontSize: 11, color: MUTED, margin: 0 });
  });

  stat(s, M, 5.65, 2.3, "5,184", "distinct grid points");
  stat(s, M + 2.5, 5.65, 2.3, "4 of 5", "axes differ, minimum achieved", PASS);
  stat(s, M + 5.0, 5.65, 2.4, "≥ 3 of 5", "axes differ, hard rule enforced");

  s.addShape(P.ShapeType.roundRect, { x: 8.35, y: 1.6, w: 4.4, h: 3.35, rectRadius: 0.06, fill: { color: SAND }, line: { color: LINE, width: 0.75 } });
  s.addText("How the rule is guaranteed", { x: 8.63, y: 1.82, w: 3.9, h: 0.35, fontFace: HFONT, fontSize: 16, bold: true, color: INK, margin: 0 });
  bullets(s, [
    "Environment assigned deterministically — all six always used",
    "Camera and concept drawn without replacement",
    "Three axes unique ⇒ every pair differs on ≥ 3 by construction",
    "Incoherent pairings excluded (no candlelit overcast rooftop)",
    "Sampler raises rather than quietly relaxing the rule",
  ], 8.63, 2.25, 3.85, 11.5);

  s.addShape(P.ShapeType.roundRect, { x: 8.35, y: 5.15, w: 4.4, h: 1.4, rectRadius: 0.06, fill: { color: INK }, line: { color: INK } });
  s.addText("Ekly exposes no API", { x: 8.63, y: 5.32, w: 3.9, h: 0.3, fontFace: BFONT, fontSize: 11, bold: true, color: "7FC3CE", charSpacing: 1.2, margin: 0 });
  s.addText("Briefs are exported as a copy-paste operator sheet with the reference image. A human generates them. Expected cost: 273.00 credits for six.", {
    x: 8.63, y: 5.62, w: 3.9, h: 0.85, fontFace: BFONT, fontSize: 11, color: "C9D6DC", lineSpacing: 14, margin: 0,
  });
  note(s, "The ≥3-axis rule is not hoped for — it is guaranteed by construction and then verified. That is what makes 'genuinely different' a claim we can defend.");
}

/* ════════════════════════════════ 7 · FIDELITY LOCK ════════════════ */
{
  const s = lightSlide("Four metrics, inside the mask, on every 5th frame", "Gate 1 — Fidelity Lock");
  const metrics = [
    ["Colour", "ΔE2000", "0.35", "Dye shift — what a customer notices on arrival", FAIL],
    ["Identity", "CLIP cosine", "0.30", "A different garment substituted entirely", TEAL_D],
    ["Weave", "Gabor + FFT", "0.25", "Handloom rendered as flat plastic fabric", "8A5D00"],
    ["Structure", "Aligned SSIM", "0.10", "Border motif distorted or redrawn", INK2],
  ];
  metrics.forEach((m, i) => {
    const x = M + i * 3.02;
    s.addShape(P.ShapeType.roundRect, { x, y: 1.6, w: 2.82, h: 2.25, rectRadius: 0.06, fill: { color: SAND }, line: { color: LINE, width: 0.75 } });
    s.addText(m[2], { x: x + 0.22, y: 1.75, w: 2.4, h: 0.5, fontFace: HFONT, fontSize: 26, bold: true, color: m[4], margin: 0 });
    s.addText("weight", { x: x + 0.22, y: 2.24, w: 2.4, h: 0.24, fontFace: BFONT, fontSize: 9.5, color: MUTED, charSpacing: 1, margin: 0 });
    s.addText(m[0], { x: x + 0.22, y: 2.55, w: 2.4, h: 0.3, fontFace: BFONT, fontSize: 14, bold: true, color: INK, margin: 0 });
    s.addText(m[1], { x: x + 0.22, y: 2.84, w: 2.4, h: 0.26, fontFace: BFONT, fontSize: 10.5, color: TEAL_D, margin: 0 });
    s.addText(m[3], { x: x + 0.22, y: 3.14, w: 2.42, h: 0.62, fontFace: BFONT, fontSize: 10.5, color: MUTED, lineSpacing: 13, margin: 0 });
  });

  s.addText("Why per frame, not per clip", { x: M, y: 4.15, w: 6, h: 0.4, fontFace: HFONT, fontSize: 19, bold: true, color: INK, margin: 0 });
  s.addText("Drift is transient. On our baseline clip fidelity starts at 87, dips to 61.1 at t = 2.83 s, then recovers. A single-frame check at t = 0 would have passed it.", {
    x: M, y: 4.58, w: 6.1, h: 0.85, fontFace: BFONT, fontSize: 13, color: INK2, lineSpacing: 18, margin: 0,
  });
  bullets(s, [
    "31 of 153 frames scored per clip, at stride 5",
    "Combined into a Fidelity Score of 0–100",
    "Threshold calibrated from the product's own image",
    "Motion check catches frozen clips and hard cuts",
  ], M, 5.45, 6.1, 12.5);

  s.addImage({ path: img("m33/rooftop_drift.png"), x: 7.05, y: 4.05, w: 2.55, h: 2.8 });
  s.addImage({ path: img("m33/mansion_drift.png"), x: 9.9, y: 4.05, w: 2.55, h: 2.8 });
  s.addText("PASS — ROOFTOP-night", { x: 7.05, y: 3.76, w: 2.55, h: 0.26, fontFace: BFONT, fontSize: 11, bold: true, color: PASS, margin: 0 });
  s.addText("REJECT — MANSION-marble", { x: 9.9, y: 3.76, w: 2.6, h: 0.26, fontFace: BFONT, fontSize: 11, bold: true, color: FAIL, margin: 0 });
  note(s, "The weights were set from how each metric actually behaved in testing, not from how good it sounded. Colour is highest because a shifted dye is the most commercially damaging failure.");
}

/* ════════════════════════════════ 8 · REAL RESULTS ═════════════════ */
{
  const s = lightSlide("Four real generations. Three passed, one rejected.", "Real results — saree");
  s.addImage({ path: img("m33/saree_all_four.png"), x: M, y: 1.5, w: 6.35, h: 5.2 });
  s.addText("Per-frame fidelity for all four clips against the calibrated pass mark of 51.0. Garment occupancy underneath.", {
    x: M, y: 6.72, w: 6.35, h: 0.35, fontFace: BFONT, fontSize: 10.5, color: MUTED, margin: 0,
  });

  const rows = [
    ["Video", "Mean", "Min", "Verdict"],
    ["ROOFTOP-night", "75.57", "71.28", "PASS"],
    ["MANDAP-dusk", "71.77", "65.09", "PASS"],
    ["BASELINE-courtyard", "71.23", "61.06", "PASS"],
    ["MANSION-marble", "44.89", "37.87", "REJECT"],
  ];
  s.addTable(
    rows.map((r, i) => r.map((c, j) => ({
      text: c,
      options: {
        bold: i === 0 || (j === 3 && i > 0),
        color: i === 0 ? MUTED : (i === 4 ? FAIL : (j === 3 ? PASS : INK)),
        fill: { color: i === 4 ? "FCEFED" : WHITE },
        align: j === 0 ? "left" : "right",
        fontSize: i === 0 ? 10.5 : 12.5,
      },
    }))),
    { x: 7.3, y: 1.55, w: 5.4, colW: [2.25, 1.0, 1.0, 1.15], rowH: 0.36,
      fontFace: BFONT, border: { type: "solid", color: LINE, pt: 0.5 }, valign: "middle" }
  );

  s.addText("Pass mark 51.0, calibrated on this product", {
    x: 7.3, y: 3.5, w: 5.4, h: 0.3, fontFace: BFONT, fontSize: 11, italic: true, color: MUTED, margin: 0,
  });

  s.addShape(P.ShapeType.roundRect, { x: 7.3, y: 3.88, w: 5.4, h: 3.05, rectRadius: 0.06, fill: { color: "FCEFED" }, line: { color: "F0CDC8", width: 1 } });
  s.addText("Why MANSION-marble was rejected", { x: 7.58, y: 4.06, w: 4.9, h: 0.35, fontFace: HFONT, fontSize: 16, bold: true, color: "7D1F18", margin: 0 });
  bullets(s, [
    "Fidelity 44.89 vs a 51.0 pass mark — below it for the whole clip",
    "Motion spike 0.268 vs a 0.25 limit — a hard cut in the first 0.13 s",
    "Garment occupancy collapsed from 38% of frame to 3–9%",
  ], 7.58, 4.46, 4.85, 11);
  s.addText("Not primarily a dye failure. ΔE2000 reads 8.98, but with the garment at a few percent of frame that is not evidence of a dye change — frame inspection confirms the saree is still teal.", {
    x: 7.58, y: 5.98, w: 4.85, h: 0.85, fontFace: BFONT, fontSize: 10.5, bold: true, color: "7D1F18", lineSpacing: 13, margin: 0,
  });
  note(s, "Two independent checks caught this. And we checked frames before calling it — the colour number is real but it is not the reason.");
}

/* ════════════════════════════════ 9 · MANSION CLOSE-UP ═════════════ */
{
  const s = lightSlide("The rejection, frame by frame", "Evidence — MANSION-marble");
  s.addImage({ path: img("m33/mansion_diag.png"), x: M, y: 1.5, w: 12.06, h: 3.67 });
  s.addText("Frame 0 is a near-copy of the reference (38% of frame). After a hard cut the model is tiny in a marble hall for the remaining five seconds. The mask (pink) tracks correctly — the product really is that small.", {
    x: M, y: 5.28, w: 12.06, h: 0.4, fontFace: BFONT, fontSize: 11.5, color: MUTED, margin: 0,
  });

  stat(s, M, 5.85, 2.3, "44.89", "fidelity mean vs 51.0 mark", FAIL);
  stat(s, M + 2.6, 5.85, 2.3, "37.87", "worst frame, at t = 0.17 s", FAIL);
  stat(s, M + 5.2, 5.85, 2.3, "0.268", "motion spike vs 0.25 limit", FAIL);
  stat(s, M + 7.8, 5.85, 2.3, "38% → 3%", "garment occupancy collapse", FAIL);
  s.addText("Rejected on two\nindependent grounds", {
    x: M + 10.4, y: 5.88, w: 2.2, h: 0.9, fontFace: HFONT, fontSize: 14, bold: true, color: INK, lineSpacing: 18, margin: 0,
  });
  note(s, "This slide is the proof that the QC is real. A judge can see the product shrink and the mask following it correctly.");
}

/* ════════════════════════════════ 10 · DIVERSITY ═══════════════════ */
{
  const s = lightSlide("Being different is not the same as being usable", "Gate 2 — Diversity Engine");
  s.addText("Two structurally different briefs can still render similarly, so diversity is measured on the result. Each video becomes one CLIP embedding averaged over sampled frames; pairwise cosine distance decides.", {
    x: M, y: 1.55, w: 7.1, h: 0.7, fontFace: BFONT, fontSize: 13.5, color: MUTED, lineSpacing: 19, margin: 0,
  });

  const dv = [
    ["", "BASELINE", "MANDAP", "MANSION", "ROOFTOP"],
    ["BASELINE-courtyard", "—", "0.1147", "0.1999", "0.0931"],
    ["MANDAP-dusk", "0.1147", "—", "0.1412", "0.1213"],
    ["MANSION-marble", "0.1999", "0.1412", "—", "0.1961"],
    ["ROOFTOP-night", "0.0931", "0.1213", "0.1961", "—"],
  ];
  s.addTable(
    dv.map((r, i) => r.map((c, j) => ({
      text: c,
      options: {
        bold: i === 0 || j === 0,
        color: i === 0 || j === 0 ? INK : INK2,
        fill: { color: (i === 3 || j === 3) && i !== 0 && j !== 0 ? "FCEFED" : WHITE },
        align: j === 0 ? "left" : "right",
        fontSize: 10.5,
      },
    }))),
    { x: M, y: 2.45, w: 7.1, colW: [2.3, 1.2, 1.2, 1.2, 1.2], rowH: 0.34,
      fontFace: BFONT, border: { type: "solid", color: LINE, pt: 0.5 }, valign: "middle" }
  );

  stat(s, M, 4.5, 2.3, "14.44", "diversity, all four videos");
  stat(s, M + 2.5, 4.5, 2.3, "10.97", "diversity, passing set");
  stat(s, M + 5.0, 4.5, 2.1, "+0.00", "gain — nothing was dropped", MUTED);
  s.addText("Selection had nothing to remove: three videos passed Gate 1 against a request for six. The distances are real measurements; the filtering step was simply not exercised.", {
    x: M, y: 5.55, w: 7.1, h: 0.7, fontFace: BFONT, fontSize: 11.5, italic: true, color: MUTED, lineSpacing: 15, margin: 0,
  });

  s.addShape(P.ShapeType.roundRect, { x: 8.15, y: 1.55, w: 4.6, h: 4.9, rectRadius: 0.06, fill: { color: INK }, line: { color: INK } });
  s.addText("The result that justifies two gates", {
    x: 8.45, y: 1.8, w: 4.0, h: 0.65, fontFace: HFONT, fontSize: 19, bold: true, color: WHITE, lineSpacing: 24, margin: 0,
  });
  s.addText("0.1999", { x: 8.45, y: 2.62, w: 4.0, h: 0.7, fontFace: HFONT, fontSize: 40, bold: true, color: "7FC3CE", margin: 0 });
  s.addText("the largest pairwise distance in the set — BASELINE ↔ MANSION", {
    x: 8.45, y: 3.3, w: 4.0, h: 0.55, fontFace: BFONT, fontSize: 11.5, color: "9FB3BD", lineSpacing: 15, margin: 0,
  });
  s.addText("The most visually distinct video in the set is the one Gate 1 rejected.\n\nOptimising for variety alone would have shipped the video that misrepresents the product.\n\nThis came out of the measurements, not the design — and it is why the two gates are kept independent.", {
    x: 8.45, y: 4.0, w: 4.0, h: 2.2, fontFace: BFONT, fontSize: 12.5, color: WHITE, lineSpacing: 17, margin: 0,
  });
  note(s, "This is our strongest single finding. It was not designed in — the numbers produced it.");
}

/* ════════════════════════════════ 11 · PERFORMANCE ═════════════════ */
{
  const s = lightSlide("Where the time actually goes", "Milestone 3.1 — Performance");
  s.addChart(P.ChartType.bar, [{
    name: "Seconds",
    labels: ["plan_briefs", "validate", "preprocess", "signature", "diversity_embed", "segment", "export", "score_all"],
    values: [0.003, 0.02, 0.145, 3.455, 5.533, 5.682, 26.283, 180.037],
  }], {
    x: M, y: 1.55, w: 7.05, h: 3.5,
    barDir: "bar", chartColors: [TEAL], showTitle: false, showLegend: false,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9.5,
    dataLabelColor: INK2, dataLabelFormatCode: "0.00",
    catAxisLabelColor: INK2, catAxisLabelFontSize: 10,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 9,
    valGridLine: { color: "EDF1F3", size: 0.75 }, catGridLine: { style: "none" },
    valAxisMinVal: 0, valAxisMaxVal: 200, barGapWidthPct: 45,
  });
  s.addText("Measured by the application while it ran, over four clips. Ekly generation time is excluded — a manual web step with no API, never measured.", {
    x: M, y: 5.15, w: 7.05, h: 0.5, fontFace: BFONT, fontSize: 11, color: MUTED, lineSpacing: 14, margin: 0,
  });
  stat(s, M, 5.8, 2.3, "221.2 s", "total automated");
  stat(s, M + 2.5, 5.8, 2.3, "81.4%", "is scoring alone", FAIL);
  stat(s, M + 5.0, 5.8, 2.05, "45.0 s", "per 5-second clip");

  s.addText("Optimisations, and what each is worth", { x: 8.15, y: 1.6, w: 4.6, h: 0.4, fontFace: HFONT, fontSize: 18, bold: true, color: INK, margin: 0 });
  const opt = [
    ["Frame sampling", "31 of 153 frames scored — 4.9× fewer than a full pass. The largest lever."],
    ["Cached model sessions", "Segmentation 4.70 → 0.59 → 0.51 s; CLIP 2.00 → 0.05 → 0.05 s across three calls."],
    ["Signature once per product", "Mask, palette, texture and CLIP vector reused for every video and re-score."],
    ["Batched embeddings", "CLIP runs 16 images per session call."],
    ["Reduced-resolution masks", "0.543 → 0.473 s — a 1.15× win, not the 8× an earlier note claimed."],
  ];
  opt.forEach((o, i) => {
    const y = 2.15 + i * 0.87;
    s.addText(o[0], { x: 8.15, y, w: 4.6, h: 0.28, fontFace: BFONT, fontSize: 12.5, bold: true, color: TEAL_D, margin: 0 });
    s.addText(o[1], { x: 8.15, y: y + 0.27, w: 4.6, h: 0.5, fontFace: BFONT, fontSize: 10.5, color: MUTED, lineSpacing: 13, margin: 0 });
  });
  s.addText("We corrected our own number: the earlier 8× claim compared a cold call including model load against a warm one.", {
    x: 8.15, y: 6.5, w: 4.6, h: 0.5, fontFace: BFONT, fontSize: 10.5, italic: true, color: FAIL, lineSpacing: 13, margin: 0,
  });
  note(s, "Scoring is the honest bottleneck at 81%. It is CPU inference — we did not optimise it away, and we say so.");
}

/* ════════════════════════════════ 12 · OUTPUTS ═════════════════════ */
{
  const s = lightSlide("Three validated ads, verified by reading the files back", "Milestone 3.2 — Production output");
  const ads = [
    ["BASELINE-courtyard", "6.37 MB"],
    ["MANDAP-dusk", "6.99 MB"],
    ["ROOFTOP-night", "3.70 MB"],
  ];
  ads.forEach((a, i) => {
    const x = M + i * 2.36;
    s.addImage({ path: img("m3_export_frames/" + a[0] + ".png"), x, y: 1.55, w: 2.1, h: 3.73 });
    s.addText(a[0], { x, y: 5.36, w: 2.1, h: 0.28, fontFace: BFONT, fontSize: 11, bold: true, color: INK, margin: 0 });
    s.addText("1080×1920 · 5.10 s · " + a[1], { x, y: 5.62, w: 2.1, h: 0.28, fontFace: BFONT, fontSize: 10, color: MUTED, margin: 0 });
  });

  s.addText("Delivery specification", { x: 7.9, y: 1.6, w: 4.9, h: 0.4, fontFace: HFONT, fontSize: 19, bold: true, color: INK, margin: 0 });
  const spec = [
    ["Resolution", "1080 × 1920"],
    ["Aspect", "0.5625 (9:16)"],
    ["Codec / format", "H.264 · yuv420p · MP4"],
    ["Frame rate", "30 fps · 153 frames"],
    ["Fit mode", "crop — 100% of garment retained"],
    ["Conforming", "3 of 3"],
  ];
  spec.forEach((r, i) => {
    const y = 2.12 + i * 0.5;
    s.addText(r[0], { x: 7.9, y, w: 2.0, h: 0.3, fontFace: BFONT, fontSize: 12, color: MUTED, margin: 0 });
    s.addText(r[1], { x: 9.95, y, w: 2.85, h: 0.3, fontFace: BFONT, fontSize: 12, bold: true, color: INK, margin: 0 });
    s.addShape(P.ShapeType.rect, { x: 7.9, y: y + 0.34, w: 4.9, h: 0.008, fill: { color: LINE } });
  });
  s.addText("Read back from the written files, not taken from encoder settings.", {
    x: 7.9, y: 5.2, w: 4.9, h: 0.3, fontFace: BFONT, fontSize: 10.5, italic: true, color: MUTED, margin: 0,
  });

  s.addShape(P.ShapeType.roundRect, { x: 7.9, y: 5.65, w: 4.9, h: 1.15, rectRadius: 0.06, fill: { color: SAND }, line: { color: LINE, width: 0.75 } });
  s.addText("Crop or pad is decided per file from measurement — the system computes how much garment a centre crop would destroy. Crop removed 15.6% of width and 0.00% of the garment.", {
    x: 8.15, y: 5.82, w: 4.45, h: 0.85, fontFace: BFONT, fontSize: 11, color: INK2, lineSpacing: 14, margin: 0,
  });
  note(s, "All four inputs arrived at 768x1152, not the 9:16 the generator was told to produce. Conversion is an explicit stage and conformance is verified from the file.");
}

/* ════════════════════════════════ 13 · CROSS-PRODUCT ═══════════════ */
{
  const s = lightSlide("A second product — and a problem the testing found", "Milestone 3.3 — Cross-product testing");
  s.addImage({ path: img("m33/kurti_mask.png"), x: M, y: 1.55, w: 3.1, h: 3.1 });
  s.addText("Kurti garment mask", { x: M, y: 4.72, w: 3.1, h: 0.28, fontFace: BFONT, fontSize: 12, bold: true, color: INK, margin: 0 });
  s.addText("Printed panels retained after a fix to the skin filter, which had been deleting warm-toned print. Source 2500×2500, garment 10.95% of frame.", {
    x: M, y: 5.0, w: 3.1, h: 1.0, fontFace: BFONT, fontSize: 10.5, color: MUTED, lineSpacing: 14, margin: 0,
  });

  s.addText("Real kurti video scored through the identical pipeline", {
    x: 4.05, y: 1.58, w: 4.3, h: 0.6, fontFace: HFONT, fontSize: 15, bold: true, color: INK, lineSpacing: 20, margin: 0,
  });
  const k = [["Fidelity mean / min", "55.04 / 38.67"], ["Delivered", "960×960 square"],
             ["ΔE2000", "5.00"], ["Weave distance", "0.2611"], ["CLIP identity", "0.8479"],
             ["Motion max", "0.0407"], ["Garment occupancy", "6.6% – 8.7%"], ["Export", "1080×1920, conforms"]];
  k.forEach((r, i) => {
    const y = 2.3 + i * 0.42;
    s.addText(r[0], { x: 4.05, y, w: 2.4, h: 0.28, fontFace: BFONT, fontSize: 11, color: MUTED, margin: 0 });
    s.addText(r[1], { x: 6.5, y, w: 1.9, h: 0.28, fontFace: BFONT, fontSize: 11, bold: true, color: INK, margin: 0 });
  });

  s.addShape(P.ShapeType.roundRect, { x: 8.6, y: 1.55, w: 4.15, h: 5.1, rectRadius: 0.06, fill: { color: "FFF8E6" }, line: { color: "EED9A4", width: 1.25 } });
  s.addText("The finding", { x: 8.88, y: 1.75, w: 3.6, h: 0.3, fontFace: BFONT, fontSize: 11, bold: true, color: "8A5D00", charSpacing: 1.3, margin: 0 });
  s.addText("The kurti was judged against the saree's pass mark", {
    x: 8.88, y: 2.08, w: 3.6, h: 0.85, fontFace: HFONT, fontSize: 17, bold: true, color: "6B4A00", lineSpacing: 22, margin: 0,
  });
  const cmp = [["51.0", "calibrated on the saree", "PASS", PASS], ["63.2", "calibrated on the kurti", "REJECT", FAIL]];
  cmp.forEach((c, i) => {
    const y = 3.1 + i * 1.0;
    s.addText(c[0], { x: 8.88, y, w: 1.1, h: 0.45, fontFace: HFONT, fontSize: 24, bold: true, color: "6B4A00", margin: 0 });
    s.addText(c[1], { x: 8.88, y: y + 0.45, w: 2.2, h: 0.3, fontFace: BFONT, fontSize: 10.5, color: "8A5D00", margin: 0 });
    s.addText(c[2], { x: 11.1, y: y + 0.06, w: 1.4, h: 0.35, fontFace: BFONT, fontSize: 13, bold: true, color: c[3], align: "right", margin: 0 });
  });
  s.addText("Same clip, 55.04, opposite verdicts. The kurti is mostly white, so a 10° hue shift costs it only 6.3 points against the saree's 23.9 — its floor is legitimately higher.\n\nThe pass mark is a property of the product, not of the system. We report this rather than quietly correcting it.", {
    x: 8.88, y: 5.15, w: 3.6, h: 1.35, fontFace: BFONT, fontSize: 10.5, color: "6B4A00", lineSpacing: 13.5, margin: 0,
  });
  note(s, "Good testing finds problems in your own process. This is the single most important thing to fix before a wider catalogue.");
}

/* ════════════════════════════════ 14 · LIMITATIONS ═════════════════ */
{
  const s = lightSlide("What we have not tested", "Honesty");
  s.addText("Stating these is not a weakness in the submission — every one of them is a claim we refused to make.", {
    x: M, y: 1.5, w: 8.5, h: 0.4, fontFace: BFONT, fontSize: 13.5, color: MUTED, margin: 0,
  });
  const lim = [
    ["Two product types only", "Saree and kurti on real video. Lehenga, dress and shirt are supported in code but untested."],
    ["Gate 2 never rejected anything", "The passing pool has always been smaller than the number of ads requested."],
    ["Safe Cut never fired on real footage", "Covered by 5 unit tests; no real clip has met the conditions for a trim."],
    ["No human ground truth", "The Fidelity Score has not been validated against human judgement of sameness."],
    ["Small calibration samples", "4 saree clips, 1 kurti clip, plus controlled degradation anchors."],
    ["Segmentation is a heuristic", "Not a trained garment segmenter; it keeps accessories such as the kurti model's handbag."],
  ];
  lim.forEach((l, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = M + col * 6.2, y = 2.15 + row * 1.5;
    s.addShape(P.ShapeType.roundRect, { x, y, w: 5.85, h: 1.28, rectRadius: 0.05, fill: { color: SAND }, line: { color: LINE, width: 0.75 } });
    s.addText(l[0], { x: x + 0.25, y: y + 0.17, w: 5.35, h: 0.32, fontFace: BFONT, fontSize: 13, bold: true, color: INK, margin: 0 });
    s.addText(l[1], { x: x + 0.25, y: y + 0.52, w: 5.35, h: 0.65, fontFace: BFONT, fontSize: 11, color: MUTED, lineSpacing: 14, margin: 0 });
  });
  s.addText("We also corrected two of our own errors mid-project: a weave metric that returned ~0.0001 for every frame, and an 8× speed-up claim that was really 1.15×.", {
    x: M, y: 6.75, w: 12.06, h: 0.4, fontFace: BFONT, fontSize: 11.5, italic: true, color: INK2, margin: 0,
  });
  note(s, "Judges test claims. Everything here is something we could have hidden and chose not to.");
}

/* ════════════════════════════════ 15 · TAKEAWAY ════════════════════ */
{
  const s = darkSlide();
  s.addText("What we built", {
    x: M, y: 0.75, w: 8, h: 0.4, fontFace: BFONT, fontSize: 12, bold: true, color: TEAL, charSpacing: 1.6, margin: 0,
  });
  s.addText("A generator can't tell you when it broke your product.\nThis can.", {
    x: M, y: 1.2, w: 11.5, h: 1.35, fontFace: HFONT, fontSize: 32, bold: true, color: WHITE, lineSpacing: 42, margin: 0,
  });

  const wins = [
    ["11", "quality checks run on every video"],
    ["2", "independent gates before anything ships"],
    ["4 + 1", "real videos scored across two products"],
    ["3", "validated 1080×1920 ads delivered"],
  ];
  wins.forEach((w, i) => {
    const x = M + i * 3.05;
    s.addText(w[0], { x, y: 2.95, w: 2.8, h: 0.75, fontFace: HFONT, fontSize: 40, bold: true, color: "7FC3CE", margin: 0 });
    s.addText(w[1], { x, y: 3.72, w: 2.8, h: 0.6, fontFace: BFONT, fontSize: 12, color: "9FB3BD", lineSpacing: 16, margin: 0 });
  });

  s.addShape(P.ShapeType.rect, { x: M, y: 4.6, w: 12.06, h: 0.012, fill: { color: "2B3A44" } });

  s.addText("Why it matters for Kaladhar", {
    x: M, y: 4.9, w: 5.6, h: 0.35, fontFace: BFONT, fontSize: 13, bold: true, color: WHITE, margin: 0,
  });
  s.addText("Ads can be produced from one photograph instead of a reshoot — and every one that ships has been measured against the real product, per frame, inside the garment. Anything that misrepresents it is stopped before delivery.", {
    x: M, y: 5.3, w: 5.9, h: 1.3, fontFace: BFONT, fontSize: 12.5, color: "C9D6DC", lineSpacing: 17, margin: 0,
  });

  s.addText("The result we'd point a judge at", {
    x: 7.0, y: 4.9, w: 5.6, h: 0.35, fontFace: BFONT, fontSize: 13, bold: true, color: WHITE, margin: 0,
  });
  s.addText("The most visually distinct video in our set was the one the fidelity gate rejected. Chasing variety alone would have shipped the ad that misrepresents the saree. That is the case for two gates, and the measurements made it, not us.", {
    x: 7.0, y: 5.3, w: 5.65, h: 1.3, fontFace: BFONT, fontSize: 12.5, color: "C9D6DC", lineSpacing: 17, margin: 0,
  });

  s.addText("Team Code Blooded  ·  Product Fidelity Studio  ·  Milestone 3", {
    x: M, y: 6.85, w: 12.06, h: 0.3, fontFace: BFONT, fontSize: 10.5, color: MUTED, margin: 0,
  });
  note(s, "Close on the two-gate finding. It is memorable, it is ours, and it came from the data.");
}

const OUT = path.join(EV, "Milestone_3_Final_Presentation.pptx");
P.writeFile({ fileName: OUT }).then(() => console.log("wrote " + OUT));
