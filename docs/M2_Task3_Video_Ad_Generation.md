# Milestone 2, Task 3 — Video Ad Generation

Team Code Blooded — GigPoint Hackathon, 22 August 2026
Problem 2: AI Ad Generation, client Kaladhar

Task as stated on the platform: *"Convert the generated scenes into short video
ad variations using motion, camera effects, transitions and creative elements."*

---

## 1. Scope

Generation itself happens in Ekly, by hand, because no API is available to us.
This task covers everything that turns raw Ekly output into evaluated ad
variations: import, probing, per-frame product scoring, motion and ad-readiness
checks, and the pass/fail decision.

The important claim of this task is not that we can generate video — many tools
can. It is that we can tell, automatically and per frame, whether the generated
video still shows the product that is being sold.

## 2. Import and probing

Clips are associated with the brief that produced them by filename, as the
operator sheet instructs. Anything that does not match a brief is still
imported and flagged rather than dropped.

**Every clip is probed rather than trusted.** In Milestone 1 the Ekly 9:16
setting produced a 768x1152 (2:3) file. The setting is not evidence; the file
is. Observed on import for all four real videos:

```
!! BASELINE-courtyard 768x1152  aspect 0.667  5.10s  NOT 9:16
!! MANDAP-dusk        768x1152  aspect 0.667  5.10s  NOT 9:16
!! MANSION-marble     768x1152  aspect 0.667  5.10s  NOT 9:16
!! ROOFTOP-night      768x1152  aspect 0.667  5.10s  NOT 9:16
   Clips not in 9:16 are converted to 1080x1920 at export.
```

Four out of four. The Milestone 1 observation was n=1; it is now n=4.

None of the four filenames matched a planner brief ID, and the pipeline said so
rather than inventing a mapping. This batch was generated from the team's own
prompts, not from the six briefs the planner emitted.

ffmpeg is not installed system-wide on the build machine, so the static binary
shipped with `imageio-ffmpeg` is used. OpenCV handles decode for frame sampling.

## 3. Status: evaluated on four real videos

This task is now evidenced on **four real Ekly / Kling AI Video Pro generations**,
not one. Full measured results are in
[M2_Real_Video_Results.md](M2_Real_Video_Results.md); the summary is:

| Clip | Fidelity mean | min | Decision |
|---|---|---|---|
| ROOFTOP-night | 75.57 | 71.28 | KEEP |
| MANDAP-dusk | 71.77 | 65.09 | KEEP |
| BASELINE-courtyard | 71.23 | 61.06 | KEEP |
| MANSION-marble | 44.89 | 37.87 | REJECT |

Calibrated threshold **51.0** (from 4 real clips plus degradation anchors).
All four were delivered at 768x1152 (2:3), confirming from n=4 that the Ekly
9:16 setting does not produce a 9:16 file.

## 4. Per-frame scoring, and why it must be per frame

The single most important finding from Milestone 1 was that the drift is **local
and transient** — it appeared during the model's turn and passed — so a person
checking one frame would very likely miss it.

That finding is now confirmed numerically. Scoring every 5th frame of
BASELINE-courtyard:

- Fidelity starts at **81.5** at t=0
- falls to **61.1** at t=2.83 s
- recovers to about **69** by t=5.0 s

A single-frame check at t=0 would have passed this clip at 81.5 and never seen
the dip. This is the justification for the entire Fidelity Lock, and it is now
evidence rather than an assertion.

Three independent components agree on the same event:

| Metric | Behaviour across the clip |
|---|---|
| dE2000 (colour) | 3.0 rising to a peak of **5.00** at t=2.83 s, then back to ~2.2 |
| weave distance | 0.128 rising to **0.263**, then partially recovering to 0.172 |
| CLIP cosine (identity) | declining steadily from **0.981** to **0.842** |

## 5. The four metrics

All computed **inside the garment mask only** — the background is supposed to
change completely, and measuring it would drown the signal in the variation we
asked for.

A note on alignment, because it drives the design. The source photograph and a
generated frame are not pixel-aligned: pose, framing, scene and lighting are all
deliberately different. So three of the four metrics are alignment-free and
compare distributions and descriptors, not pixels:

| Component | Method | Weight |
|---|---|---|
| Colour | mean dE2000 after greedily matching CIELAB palettes | 0.35 |
| Identity | CLIP cosine on the masked garment crop | 0.30 |
| Weave | Gabor bank + FFT radial profile + absolute high-frequency energy | 0.25 |
| Structure | SSIM on the border motif, located by template matching | 0.10 |

Colour carries the most weight because a shifted dye is the most commercially
damaging failure — it is what a customer notices on arrival and calls a
misrepresentation.

## 6. Two metric failures we found and fixed

Reporting these because they materially affect how the numbers should be read.

**The weave metric was broken in its first version.** Cosine distance over
descriptors whose components are all non-negative collapsed: every clip returned
a distance between 0.0001 and 0.0002, a spread of 0.0001 across an entire clip.
The metric had no discriminative range at all.

It was rebuilt with distribution distances over normalised Gabor and radial
profiles, plus an *absolute* high-frequency energy term that is deliberately not
normalised away — that term is what catches handloom rendered as flat plastic
fabric, where the colour stays perfectly correct while the thread detail
disappears. Texture is now measured after rescaling the garment box to a fixed
height, so the metric compares fabric rather than sampling rate.

Validated against known degradation:

| Variant | Distance | HF ratio |
|---|---|---|
| identical | 0.0000 | 0.0088 |
| gaussian blur k=3 | 0.2423 | 0.0028 |
| gaussian blur k=5 | 0.3033 | 0.0013 |
| gaussian blur k=9 | 0.3506 | 0.0002 |
| rescaled x1.5 (same fabric) | 0.0255 | 0.0095 |
| flat colour, no weave | 0.3668 | 0.0000 |

Monotonic under increasing blur, saturating on flat colour, and near-zero under
rescaling. This behaviour is locked in by tests so the failure cannot return
silently.

**Template matching was searching the whole frame.** The garment mask was being
passed to the aligned-SSIM function and then ignored, so the matcher could and
did lock onto smooth background — in one case producing a Weave Guard image
showing a wall and foliage rather than fabric. The search is now confined to
regions at least 90% covered by garment pixels. SSIM values before this fix were
partly measuring background and should be disregarded.

## 7. Motion and ad-readiness

Frame-to-frame difference over the clip catches two opposite failures: a frozen
clip, where the generator ignored the camera direction entirely, and a
jitter/flicker clip with erratic spikes. Measured across all four:

| Clip | Motion mean | Motion max | Reading |
|---|---|---|---|
| ROOFTOP-night | 0.0132 | 0.0518 | smooth, no spikes |
| MANDAP-dusk | 0.0268 | 0.1228 | smooth |
| BASELINE-courtyard | 0.0411 | 0.0560 | smooth, consistent with the requested push-in |
| MANSION-marble | 0.0214 | **0.2683** | **spike above the 0.25 limit — a hard scene cut** |

The MANSION-marble motion series is `[0.2683, 0.0158, 0.0122, 0.0104, ...]`: a
cut inside the first ~0.13 s, then a nearly static clip. This check rejected the
clip independently of its fidelity score.

## 8. Threshold calibration

The scale is anchored with controlled degradations of the source — hue shifts,
blur, desaturation — scored through the same Fidelity Lock, so the threshold sits
between "clearly still the product" and "clearly misrepresented" rather than
being guessed. With four real clips this is still a small sample, and every
report prints the sample size.

We do **not** compare aggregate scores across the two families, because the
measurements show why that would be invalid: synthetic anchors degrade the same
pixels and keep aligned SSIM at 0.97-0.99, whereas a generated clip redraws the
motif and lands near 0.14. Judged on one aggregate, the real clip would appear
worse than a 20-degree dye shift, which is not what the underlying metrics say.

So anchors are used only where they are like-for-like — colour and weave — and
the threshold is built from a constructed limit clip with colour pushed to a
visible dye change and weave to collapse, holding identity and structure at the
median across the real clips.

**Calibrated threshold: 51.0**, from four real clips plus the anchors. Three
clips clear it; MANSION-marble at 44.89 does not. Every report prints the sample
size behind the threshold.

One correction was needed once a genuinely failing clip entered the pool: the
limit clip previously held identity and structure at the *weakest* real clip,
which let the failing clip drag the floor down far enough to admit itself. It
now uses the **median** across real clips.

## 9. Measured performance

| Stage | Seconds |
|---|---|
| score four 5.1 s clips, 124 frames total | 180.0 |
| score one clip (average) | ~45 |
| diversity embedding, four clips | 5.5 |
| export three clips to 1080x1920 | 26.3 |

The largest speed lever is frame stride: 31 of 153 frames are scored per clip,
so scoring touches 4.9x fewer frames than a full pass.

**Correction to an earlier figure in this document.** It previously stated that
segmenting at 512 px rather than 1152 px ran "about 8x faster (4.15 s to
0.54 s per frame)". That was wrong. The 4.15 s measurement was a *cold* first
call that included loading the 176 MB U2-Net model; the 0.54 s was a warm call.
A proper warm A/B over 5 alternating repetitions gives a median of **0.543 s at
full frame against 0.473 s reduced — a 1.15x speed-up**, because rembg resizes
every input to 320x320 internally before inference, so model cost barely varies
with input size. The reduction is retained because it is a real if small win and
lowers peak memory, not because it is a large one. The garment fraction moves
only 0.379 to 0.382, so the mask itself is unaffected.

## 10. Evidence

- `evidence/fidelity_all_four.png` — all four fidelity curves against the
  calibrated threshold, with garment-fraction underneath
- `runs/run_m2_real/evidence/drift_<clip>.png` — per-frame fidelity plus all
  three component curves, one per clip, worst frame marked
- `runs/run_m2_real/evidence/weave_<clip>.png` — Weave Guard, source vs worst frame
- `evidence/raw_frame_comparison.png` — source against one frame from each clip
- `evidence/mansion_mask_diagnosis.png` — why MANSION-marble failed
- `runs/run_m2_real/scores/*.json` — full per-frame series per clip
- `runs/run_m2_real/scores/calibration.json` — anchors and threshold basis

The Weave Guard on BASELINE-courtyard shows the source pallu carrying an
intricate silver brocade motif, and the worst generated frame showing plain teal
fabric with the motif absent. The panel states its own confidence: the motif
could not be confidently located anywhere on the garment in that frame, which is
itself the finding.

## 11. What we do not claim

- Ekly generation is **not** automated. There is no API available to us.
- Tier 3 product compositing is **not** built and is not claimed.
- Thresholds are calibrated from four real clips plus synthetic anchors.
- MANSION-marble fails on product visibility and a scene cut, **not** a dye
  shift. Raw frames confirm the saree is still teal.
- SSIM remains the weakest of the four components and is weighted accordingly.
