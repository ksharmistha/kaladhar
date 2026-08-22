# Kaladhar — Product Image to Multi-Variation Video Ad Generation

GigPoint Hackathon, 22 August 2026. Team **Code Blooded**. Problem 2.

One product image in. Multiple genuinely different 9:16 video ads out, with the
saree measured for drift at every step so nothing that misrepresents the product
gets exported.

---

## 1. What this is

> **Maximum variation in the scene. Zero variation in the product.**

The brief asks for two things that pull against each other: creative variety
needs the image to change as much as possible, product accuracy needs it to
change as little as possible. We split the frame into two zones with opposite
rules and enforce each one separately.

| Zone | Rule | Enforced by |
|---|---|---|
| Product region (the saree) | must not change | **Fidelity Lock** — Gate 1 |
| Scene region (background, light, camera) | must change, and must differ between variations | **Diversity Engine** — Gate 2 |

Consistency is not asserted. It is measured, per frame, inside the garment mask
only, and anything that drifts too far is rejected.

## 2. What this is NOT

**Ekly.ai exposes no API to us.** There is no API key and no programmatic
access. Video generation is performed by hand through the Ekly web interface.

Nothing in this repository calls, queues, batches or polls Ekly. The pipeline
**pauses** at the generation step and **resumes** when clips are imported. This
is stated in the code, in the CLI output and in the review UI, because it is
more credible than pretending otherwise — and because the client's actual
problem (output comes back repetitive, and the product drifts) is solved before
and after generation, not inside it.

```
  [ automated ]            [ MANUAL ]              [ automated ]
  validate                 Ekly web UI             import + probe
  segment                  Kling AI Video Pro      per-frame Fidelity Lock
  signature        ---->   one clip per brief  ---> diversity selection
  plan briefs              (no API available)      motion / ad-readiness
  export sheet                                     Safe Cut, 9:16 export
```

## 3. Install

Python 3.14 on Windows. No system ffmpeg needed — a static binary ships with
`imageio-ffmpeg`.

```bash
python -m pip install pillow opencv-python scikit-image imageio-ffmpeg "rembg[cpu]" matplotlib onnxruntime huggingface_hub numpy scipy pytest
```

Two models download on first use: `u2net` for segmentation (~176 MB) and
`Qdrant/clip-ViT-B-32-vision` for embeddings (~352 MB). Both run on CPU through
onnxruntime — no PyTorch, which matters on Python 3.14.

## 4. Run it

```bash
python cli.py plan --image assets/source/saree_source.jpg --n 6 --seed 7
```

Ingests the image, segments the garment, extracts the reference signature, and
writes six briefs plus `runs/<id>/briefs/EKLY_SHEET.txt`. The run stops at
`AWAITING_CLIPS`.

**Then, by hand:** open the sheet, generate each brief in Ekly with the
reference image attached, and save the clips as `V01.mp4`, `V02.mp4`, …

```bash
python cli.py import-clips --run <id> --dir <folder-with-clips>
python cli.py score        --run <id>
python cli.py calibrate    --run <id>
python cli.py select       --run <id> --k 6 --threshold <from calibrate>
python cli.py safe-cut     --run <id> --threshold <from calibrate>
python cli.py export       --run <id>
python cli.py review       --run <id>
```

`review` writes a self-contained `review.html` with every candidate, its scores,
the rejected pool, the drift plots and the Weave Guard comparisons.

## 5. How consistency is measured

All four metrics run **inside the garment mask only** — the background is
supposed to change completely — and **on every sampled frame**, because the
drift we observed is transient and a single-frame check would miss it.

| Component | Metric | Catches | Weight |
|---|---|---|---|
| Colour | mean ΔE2000 over matched CIELAB palettes | dye shift | 0.35 |
| Identity | CLIP cosine on the masked garment crop | a different garment entirely | 0.30 |
| Weave | Gabor bank + FFT radial profile + absolute HF energy | handloom rendered as flat plastic fabric | 0.25 |
| Structure | SSIM on the border motif, located by mask-constrained template matching | motif distortion | 0.10 |

These combine into a **Fidelity Score, 0–100**.

The weave metric was rebuilt after the first version failed: cosine distance
over all-positive descriptors collapsed to ~0.0001 for every frame. The current
version is validated in `tests/` — monotonic under increasing blur, saturating
on flat colour, and stable under rescaling.

## 6. How the threshold is set

We have **four** real generated clips — still a small sample, so rather than
invent a number we anchor the scale with controlled degradations of the source
image — hue shifts (dye change), blur (weave collapse), desaturation — scored
through the same Fidelity Lock.

Aggregate scores are **not** compared across the two families, because the
measurements show why that would be invalid: synthetic anchors degrade the same
pixels and keep aligned SSIM near 0.97–0.99, whereas a generated clip redraws
the motif and lands near 0.14. So the anchors are used only where they are
like-for-like (colour and weave), and the threshold comes from a constructed
limit clip holding identity and structure at the **median** across real clips.
(It previously used the weakest clip; with a genuinely failing clip in the pool
that let the failure drag the floor down far enough to admit itself.) See
`kaladhar/fidelity/calibrate.py`.

**Calibrated threshold: 51.0.**

Every report prints the sample size behind its threshold.

## 7. Repository layout

```
kaladhar/
  config.py            constants, export target, measured facts
  input/               validate, preprocess, segment, signature   [Stage A]
  planner/             variation matrix, sampler, brief renderer  [Stage B]
  video/io.py          probe, frame sampling, 9:16 conversion, motion
  fidelity/            metrics, lock, calibrate, safecut, report  [Gate 1]
  diversity/           CLIP embeddings, farthest-point selection  [Gate 2]
  exporter/decide.py   per-clip crop-vs-pad decision
  review/build.py      self-contained HTML review grid            [Stage F]
  pipeline.py          orchestration with the manual pause
cli.py                 command line entry point
tests/                 20 algorithm-level tests over the claims made here
evidence/              drift plots, masks, weave guard, export comparison
```

## 8. Measured facts

Nothing below is estimated. Full results:
[docs/M2_Real_Video_Results.md](docs/M2_Real_Video_Results.md).

**Four real generated videos** were evaluated — not six. Generation is finished
for Milestone 2 and no further credits will be spent.

| Clip | Fidelity mean | min | Decision |
|---|---|---|---|
| ROOFTOP-night | 75.57 | 71.28 | KEEP |
| MANDAP-dusk | 71.77 | 65.09 | KEEP |
| BASELINE-courtyard | 71.23 | 61.06 | KEEP |
| MANSION-marble | 44.89 | 37.87 | REJECT — below threshold and a 0.268 motion spike (hard cut); product falls to 3–9% of frame |

| Fact | Value |
|---|---|
| Ekly generation cost | 45.50 credits per clip |
| Raw Ekly output, all four | 768×1152, 2:3, 5.10 s, 153 frames, 30 fps, H.264 |
| 9:16 UI setting | **did not** produce a 9:16 file — 4 out of 4; every clip is re-probed |
| Calibrated fidelity threshold | 51.0 (4 real clips + degradation anchors) |
| Diversity, all four videos | 14.44 (real CLIP embeddings, not constructed) |
| Diversity, Gate-1 passing three | 10.97 — selection discarded nothing (pool 3 < k 6) |
| Export | 1080×1920, 9:16, all three verified conforming, crop chosen with 100% garment retained |
| Safe Cut | cut nothing at threshold 51.0 — no clip has a ≥3 s recoverable window |
| Automated pipeline | ≈221 s for 4 clips (~45 s scoring per 5 s clip) |
| Ekly wall-clock generation time | **not recorded** — the operator sheet asks for it |

## 9. Known limits

- The garment mask is a heuristic refinement of the rembg subject mask, not a
  trained garment segmenter. It will struggle on sheer fabric, loose thread ends
  and fabric whose colour sits inside the skin-tone range.
- Thresholds are calibrated from **four** real clips plus synthetic anchors.
- Diversity is **measured** on real video embeddings, but **selection discarded
  nothing** — the passing pool (3) is smaller than k (6), so farthest-point
  selection had nothing to remove. The selection *logic* is covered by
  algorithm-level tests on constructed vectors, kept clearly separate.
- **Safe Cut recovered nothing** on this batch; the one trim shown in the docs
  is a labelled code-path verification at a stricter bar, not a shipped output.
- The four videos were **not** generated from the planner's six briefs.
- **Tier 3 product compositing is not built and is not claimed.** It remains a
  design fallback only.
- Our source image is 500×724, which limits weave analysis by source detail
  rather than by the generated clip.
