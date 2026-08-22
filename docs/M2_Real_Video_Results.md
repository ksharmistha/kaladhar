# Milestone 2 — Results on the Real Generated Videos

Team Code Blooded — GigPoint Hackathon, 22 August 2026
Problem 2: AI Ad Generation, client Kaladhar

Every number in this document was measured by the pipeline in this repository on
the four actual Ekly / Kling AI Video Pro outputs. Nothing is estimated.

Run: `runs/run_m2_real`. Reproduce with the commands in section 9.

---

## 1. What we actually have

**Four real generated videos.** Not six. The Creative Planner produces six
briefs and that is what it is scored on, but only four videos were generated
before we stopped spending credits, so only four are evaluated here.

| ID | Scene |
|---|---|
| BASELINE-courtyard | garden / heritage courtyard, daylight |
| MANDAP-dusk | Indian wedding mandap at dusk, red and gold |
| MANSION-marble | grand luxury mansion interior, white marble |
| ROOFTOP-night | modern high-rise rooftop terrace at night |

All four share identical delivered specs, which strengthens a Milestone 1
finding from n=1 to n=4: **the Ekly 9:16 setting does not produce a 9:16 file.**

| Property | All four videos |
|---|---|
| Delivered resolution | 768x1152 |
| Aspect | 0.6667 (2:3), **not** 9:16 |
| Duration | 5.10 s |
| Frames / rate | 153 @ 30 fps |
| Codec | H.264 |

**Provenance.** None of the four filenames matched a planner brief ID, so this
batch was not generated from the six briefs the planner emitted. The pipeline
detected and reported this rather than assuming a mapping. The briefs evidence
the Creative Planner; these videos evidence the scoring, selection and export
stages. They are reported separately.

## 2. Results table — Fidelity Lock

Per-frame, inside the garment mask only, every 5th frame (31 frames per clip).

| Clip | Fidelity mean | min | std | Worst frame | dE2000 | Weave dist | CLIP cos | SSIM | Motion mean | Motion max | Garment fraction (mean) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ROOFTOP-night | **75.57** | 71.28 | 3.39 | #130 @ 4.333s | 4.88 | 0.1150 | 0.9411 | 0.2189 | 0.0132 | 0.0518 | 0.288 |
| MANDAP-dusk | **71.77** | 65.09 | 3.85 | #130 @ 4.333s | 5.39 | 0.1969 | 0.9377 | 0.4041 | 0.0268 | 0.1228 | 0.160 |
| BASELINE-courtyard | **71.23** | 61.06 | 7.47 | #85 @ 2.833s | 3.24 | 0.2047 | 0.9100 | 0.2216 | 0.0411 | 0.0560 | 0.302 |
| MANSION-marble | **44.89** | 37.87 | 7.99 | #5 @ 0.167s | 8.98 | 0.2788 | 0.8765 | 0.1405 | 0.0214 | **0.2683** | **0.065** |

Source garment fraction, for reference: **0.357**.

## 3. Calibrated threshold

**51.0**, now calibrated from **four** real clips plus the controlled degradation
anchors, rather than the single clip available at Milestone 1.

| Anchor | Fidelity | dE2000 | Weave | CLIP |
|---|---|---|---|---|
| source (identity) | 100.00 | 0.00 | 0.0000 | 1.0000 |
| hue shift 5 deg | 93.14 | 3.60 | 0.0306 | 0.9965 |
| hue shift 10 deg | 76.13 | 8.28 | 0.0779 | 0.9858 |
| hue shift 20 deg | 59.77 | 11.58 | 0.1721 | 0.9693 |
| blur k=5 | 78.34 | 1.66 | 0.3033 | 0.9720 |
| blur k=9 | 73.06 | 1.46 | 0.3506 | 0.9549 |
| desaturate 0.6 | 83.33 | 5.60 | 0.0862 | 0.9836 |

Basis: a constructed limit clip with colour pushed to dE2000 8.28 (a 10-degree
hue shift, a visible dye change) and weave to 0.303 (blur k=5, weave collapse),
holding identity and structure at the **median** across the real clips.

**Change made for this batch.** The earlier version held identity and structure
at the *weakest* real clip. With a genuinely failing clip now in the pool that
was backwards — the failing clip would drag the floor down far enough to admit
itself. Switching to the median fixes it. This is a real correction, not a
tuning choice.

Caveat printed with every report: calibrated from 4 real clips plus synthetic
anchors. The anchors fix the scale; they are not a substitute for more real
generations.

## 4. KEEP / REJECT

| Clip | Decision | Why |
|---|---|---|
| ROOFTOP-night | **KEEP** | Highest fidelity of the set (75.57) and the most stable (std 3.39, min 71.28 — never near the floor). Smoothest motion (max 0.0518). Product held at 28.8% of frame. |
| MANDAP-dusk | **KEEP** | Fidelity 71.77, min 65.09. Best structural match of the four (SSIM 0.4041) — the border motif stayed locatable. Product smaller in frame (16.0%) but well above the failure case. |
| BASELINE-courtyard | **KEEP** | Fidelity 71.23. Largest transient dip of the passing three (std 7.47, min 61.06 at t=2.83s during the model turn) but recovers and never approaches the threshold. |
| MANSION-marble | **REJECT** | Failed **two independent automatic checks.** |

**MANSION-marble, in detail.** Both failures were detected automatically, and
the diagnosis was confirmed by inspecting frames rather than assumed:

1. **Fidelity 44.89, below the 51.0 threshold**, and below it for essentially
   the whole clip — not a transient dip.
2. **Motion spike 0.2683**, above the 0.25 limit. The motion series is
   `[0.2683, 0.0158, 0.0122, 0.0104, ...]` — a hard scene cut inside the first
   ~0.13 s, after which the clip is nearly static.

The root cause is scale, not dye. Frame 0 is a near-copy of the reference image
(garment fraction 0.385), then the clip cuts to a wide shot of a vast marble
hall where **the product occupies only 3-9% of the frame** for the remaining
five seconds. Raw-frame inspection confirms the saree is still teal; it is
simply too small to read as a product ad, and at that scale the colour also
washes out against blown-out marble highlights (dE2000 8.98).

We are explicit that this is a *product-visibility and scene-cut* failure. It
would be wrong to describe it as a dye shift.

## 5. Diversity Engine — on real video embeddings

Computed from the actual generated files: mean CLIP embedding over sampled
frames of each video. **No constructed or synthetic vectors are used anywhere in
this section.**

Real pairwise cosine distance:

| | BASELINE | MANDAP | MANSION | ROOFTOP |
|---|---|---|---|---|
| **BASELINE-courtyard** | — | 0.1147 | 0.1999 | 0.0931 |
| **MANDAP-dusk** | 0.1147 | — | 0.1412 | 0.1213 |
| **MANSION-marble** | 0.1999 | 0.1412 | — | 0.1961 |
| **ROOFTOP-night** | 0.0931 | 0.1213 | 0.1961 | — |

| Measure | Value |
|---|---|
| Diversity Score, all four videos | **14.44** |
| Diversity Score, Gate-1 passing three | **10.97** |
| Most similar pair | BASELINE-courtyard ↔ ROOFTOP-night (0.0931) |
| Most distinct pair | BASELINE-courtyard ↔ MANSION-marble (0.1999) |

**Selection.** With k=6 requested and only 3 clips passing Gate 1, all three are
selected and the diversity gain is **+0.00**. The engine reports this honestly
rather than implying filtering it did not perform. Farthest-point selection
needs a pool larger than k to discard anything.

**The most important result in this section:** the most distinct clip in the
whole set is MANSION-marble — the one Gate 1 rejected. Maximising difference
alone would have selected the clip that misrepresents the product. This is the
clearest possible demonstration of why the two gates must be independent, and it
came out of real measurements rather than being designed in.

## 6. Safe Cut

Safe Cut trims a clip to the longest **contiguous** window in which every scored
frame clears the threshold, and only ships the result if at least 3.0 s survives.
It only trims — it never regenerates, recolours or repairs — and the trimmed file
is **re-scored from the trimmed output**, never inherited from the parent.

**Result at the shipping threshold of 51.0: no clip was cut.**

| Clip | Outcome | Reason |
|---|---|---|
| BASELINE-courtyard | not cut | every scored frame already clears 51.0 — nothing to cut |
| MANDAP-dusk | not cut | every scored frame already clears 51.0 |
| ROOFTOP-night | not cut | every scored frame already clears 51.0 |
| MANSION-marble | not cut | longest passing window 0.00 s, far under the 3.0 s minimum |

This is the correct outcome, not a gap. MANSION-marble fails throughout rather
than transiently, so trimming cannot recover it — which is exactly the guard
that stops Safe Cut being used to launder a bad clip into a good one.

We also checked whether *any* threshold would yield a recoverable window:

| Clip | thr 55 | thr 60 | thr 65 | thr 70 | thr 72 |
|---|---|---|---|---|---|
| BASELINE-courtyard | — | — | (1.63 s) | (0.80 s) | (0.80 s) |
| MANDAP-dusk | — | — | — | (1.80 s) | (1.13 s) |
| MANSION-marble | (0.00) | (0.00) | (0.00) | (0.00) | (0.00) |
| ROOFTOP-night | — | — | — | — | (2.30 s) |

*(x) = longest window found but under the 3.0 s minimum; — = nothing to cut.*

**No clip yields a 3 s clean window at any threshold.** These are 5.10 s clips
and the drift, where present, sits mid-clip, so trimming to one side always
leaves too little. Safe Cut is the right tool for longer generations; on 5 s
clips it will rarely fire.

**Functional verification.** So that Safe Cut is evidenced rather than untested
code, the trim-and-re-score path was executed once against ROOFTOP-night at a
deliberately stricter bar (threshold 72.0, minimum window lowered to 2.0 s):

```
kept window 0.10-2.40s   (2.30s kept, 2.80s removed)
before  mean 75.57  min 71.28  5.10s
after   mean 76.48  min 71.70  2.30s     <- re-scored from the trimmed file
now_passes: false   (min 71.70 still below the 72.0 bar; min must clear too)
```

This is labelled a **code-path verification, not a shipping decision.** The
production minimum remains 3.0 s and no trimmed clip is exported.

Safe Cut logic is additionally covered by 5 unit tests: it declines when nothing
fails, declines when a clip fails throughout, declines when the window is too
short, picks the longest of several passing runs, and treats an unscored frame
as breaking a window.

## 7. Export

All three KEEP clips converted and verified by probing the written file.

| Clip | Mode | Output | Size | Conforms |
|---|---|---|---|---|
| BASELINE-courtyard | crop | 1080x1920 | 6.37 MB | yes |
| MANDAP-dusk | crop | 1080x1920 | 6.99 MB | yes |
| ROOFTOP-night | crop | 1080x1920 | 3.70 MB | yes |

The crop-vs-pad decision is made per clip from measurement. For all three,
cropping to 9:16 removed 15.6% of frame width and **100.00% of garment pixels
were retained** across sampled frames, so crop was chosen and the full screen is
used with no product loss.

## 8. Measured performance

Four videos, one source image, this machine.

| Stage | Seconds |
|---|---|
| validate | 0.020 |
| preprocess | 0.145 |
| segment | 5.682 |
| signature | 3.455 |
| plan briefs | 0.003 |
| score_all (4 clips, 124 frames total) | 180.037 |
| diversity_embed (4 clips) | 5.533 |
| export (3 clips) | 26.283 |
| **Total automated** | **≈ 221 s** |

Roughly **45 s of scoring per 5 s clip**. Ekly generation time is still not
recorded and is not estimated; it is excluded from every figure above.

## 9. Reproducing this run

```bash
python cli.py plan         --image assets/source/saree_source.jpg --n 6 --seed 7 --run run_m2_real
python cli.py import-clips --run run_m2_real --dir <folder with the four mp4s>
python cli.py score        --run run_m2_real
python cli.py calibrate    --run run_m2_real
python cli.py select       --run run_m2_real --k 6 --threshold 51.0
python cli.py safe-cut     --run run_m2_real --threshold 51.0
python cli.py export       --run run_m2_real
python cli.py review       --run run_m2_real
```

## 10. What we do not claim

- **We did not generate six videos.** Four exist; four were evaluated.
- The four videos were **not** produced from the planner's six briefs.
- Ekly generation is **not** automated. No API is available to us.
- **Tier 3 product compositing is not built.**
- Safe Cut recovered nothing on this batch; the one trim shown is a labelled
  code-path verification at a stricter bar, not a shipped output.
- Diversity selection discarded nothing, because the passing pool (3) is smaller
  than k (6). The measurement is real; the filtering was not exercised.
- No performance improvement is claimed over any prior state; the timings are
  simply what this run measured.
