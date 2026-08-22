# Milestone 2, Task 4 — End-to-End Workflow Integration

Team Code Blooded — GigPoint Hackathon, 22 August 2026
Problem 2: AI Ad Generation, client Kaladhar

Task as stated on the platform: *"Connect image input, scene generation and
video generation into one working process that can produce multiple outputs."*

---

## 1. The shape of the workflow

One runnable flow from a product image to exported 1080x1920 ads, with the
manual Ekly generation step modelled explicitly as a pause rather than hidden.

```
  SOURCE PRODUCT IMAGE
        |
   [A] INPUT & PROCESSING          validate, normalise, segment, signature
        |
   [B] CREATIVE PLANNER            sample matrix, build briefs, write sheet
        |
   ===== state: AWAITING_CLIPS =====
   ===== MANUAL - Ekly web UI, Kling AI Video Pro, no API available to us =====
        |
   [C] IMPORT                      probe every file, associate with brief
        |
   [D] FIDELITY LOCK  - GATE 1     per-frame, mask-only, 4 metrics -> 0-100
        |
   [E] DIVERSITY ENGINE - GATE 2   CLIP embed, farthest-point, diversity score
        |
   [F] REVIEW                      self-contained HTML grid, scores, rejects
        |
   [G] EXPORT                      crop-vs-pad decision, 1080x1920, H.264
        |
   FINAL ADS - 9:16, 1080x1920, Meta-ready
```

**This is deliberately not a single uninterrupted function.** Ekly exposes no
API to us, so the honest shape of the workflow is two automated halves either
side of one clearly marked manual step. That is stated in the code, in the CLI
output and in the review UI. Writing code that claimed to call, queue or batch
Ekly would be writing code that does not work.

## 2. Two independent quality gates

A clip must pass **both** to be exported.

| Gate | Rejects a clip for | Basis |
|---|---|---|
| 1 — Fidelity Lock | drifting off the product | per-frame score below threshold, or motion failure |
| 2 — Diversity Engine | looking too much like another clip | embedding distance within the selected set |

Gate 1 also rejects two ad-readiness failures directly: a clip that is
effectively static, meaning the generator ignored the camera direction, and a
clip with a motion spike indicating flicker or an unintended cut.

## 3. State machine and resumability

The run carries state through `CREATED, PREPROCESSED, BRIEFS_READY,
AWAITING_CLIPS, CLIPS_IMPORTED, SCORED, SELECTED, EXPORTED`, with a history of
transitions and timings. `AWAITING_CLIPS` is a first-class state, not an error.

Everything expensive — mask, signature, embeddings — is computed once per run
and cached, so resuming after the manual step recomputes nothing. Runs are
independent directories, which gives versioning for free: a second planning pass
over the same image is a new run and does not overwrite the first.

## 4. Command line

```
python cli.py plan         --image <path> [--n 6] [--seed 0]
python cli.py import-clips --run <id> --dir <folder>
python cli.py score        --run <id> [--stride 5]
python cli.py calibrate    --run <id>
python cli.py select       --run <id> [--k 6] [--threshold 51.0]
python cli.py safe-cut     --run <id> --threshold 51.0
python cli.py export       --run <id> [--mode auto|pad|crop]
python cli.py review       --run <id>
python cli.py status       [--run <id>]
python cli.py runs
```

`status` on a paused run prints the path to the operator sheet and states that
the run is waiting on the manual Ekly step.

The full flow has been run end to end on the four real generated videos. Results
are in [M2_Real_Video_Results.md](M2_Real_Video_Results.md); run directory
`runs/run_m2_real`.

## 4a. Safe Cut

Between scoring and export, Safe Cut can recover a clip that dips below
threshold for part of its length, by trimming to the longest **contiguous**
window in which every scored frame passes. It only trims — never regenerates or
repairs — the kept window must be a single run of at least 3.0s, and the trimmed
file is **re-scored from the output**, never inherited.

**On this batch it cut nothing, which is the correct result.** Three clips were
already fully above threshold; MANSION-marble fails throughout rather than
transiently, so its longest passing window is 0.00s. No threshold between 55 and
72 yields a 3s clean window in any of the four — these are 5.10s clips with
mid-clip dips, so trimming always leaves too little. Safe Cut suits longer
generations; on 5s clips it will rarely fire.

The trim-and-re-score path was verified once against ROOFTOP-night at a
deliberately stricter bar (threshold 72.0, minimum lowered to 2.0s): it produced
a 2.30s file that re-scored at mean 76.48 / min 71.70. That is labelled a
code-path verification, not a shipping decision, and no trimmed clip is
exported.

## 5. Export: settling the crop-vs-pad question

The source is 768x1152 (2:3) and delivery is 1080x1920 (9:16), so something has
to give. Milestone 1 left this open and flagged cropping as risky.

- **crop** fills the screen but discards 15.6% of the frame width, and on a
  vertical fashion shot that can slice the pallu or border — exactly the
  misrepresentation the client ruled out.
- **pad** keeps every pixel but letterboxes, losing screen area on a format
  where full-bleed matters.

Rather than pick one globally, the decision is **made per clip from
measurement**. The system segments several frames and computes what fraction of
*garment pixels* a centre crop would actually destroy, taking the minimum across
frames because a crop that is safe at t=0 can clip the pallu once she turns.
Crop is used only if at least 99.5% of the garment survives; otherwise the clip
is padded.

Measured across all three exported clips: cropping removes 15.6% of frame width
and **0.00% of the garment** in every case, because the model is centred. The
system chose crop for all three and said why:

```
BASELINE-courtyard -> 1080x1920  mode=crop  6.37 MB  CONFORMS 9:16 1080x1920
MANDAP-dusk        -> 1080x1920  mode=crop  6.99 MB  CONFORMS 9:16 1080x1920
ROOFTOP-night      -> 1080x1920  mode=crop  3.70 MB  CONFORMS 9:16 1080x1920
    crop keeps 100.00% of the garment across sampled frames
    (>= 99.5% required), so the full screen is used with no product loss
```

Both outputs were verified by probing the written file, not by trusting the
encoder settings.

## 6. Review UI

`python cli.py review` writes a self-contained `review.html` — images inlined as
data URIs, so it opens from disk and can be handed to someone without the run
directory attached. It contains:

- the pipeline state, with the manual Ekly step highlighted
- the source image with the garment mask overlaid, the auto-selected Weave Guard
  region, and the extracted palette
- the brief table with the achieved minimum axis difference
- a candidate card per clip: delivered format, fidelity mean/min, worst frame,
  component metrics, motion, export format, and rejection reasons where
  applicable
- the per-frame drift plot and Weave Guard comparison inline for each clip
- the diversity report, plus the full real pairwise-distance matrix across every
  imported video including the rejected one
- the Safe Cut table, showing what was cut and what was left alone with reasons
- the calibration table with its caveat printed, not buried
- measured timings, labelled as automated stages only
- a provenance note when imported clips do not match any planner brief

## 7. Measured end-to-end performance

One source image, four real clips, this machine (`runs/run_m2_real`):

| Stage | Seconds |
|---|---|
| validate | 0.020 |
| preprocess | 0.145 |
| segment | 5.682 |
| signature | 3.455 |
| plan briefs | 0.003 |
| score_all (4 clips, 124 frames) | 180.037 |
| diversity_embed (4 clips) | 5.533 |
| export (3 clips) | 26.283 |
| **total automated** | **≈ 221** |

Roughly 45 s of scoring per 5 s clip. No performance improvement is claimed
against any earlier state; these are simply what this run measured.

Ekly generation time is **not** included and is **not recorded** — we did not
measure it during the Milestone 1 run. The operator sheet now asks for it. We
report our pipeline time separately from generation time rather than blending
them, because generation throughput is not ours to optimise: it is limited to
what one person can run through a web interface.

## 8. Testing

20 tests, all passing. Each exists because a specific claim in the documentation
would be false if it failed: validation rejects and accepts correctly, the
sampler enforces the axis-difference rule and emits only coherent pairs and is
deterministic per seed, the weave metric is monotonic under blur and robust to
rescaling, subscores are bounded and ordered, structure refuses low-confidence
matches, farthest-point selection picks across clusters and raises diversity above the
pool, and Safe Cut declines correctly in each of its four refusal cases while
picking the longest passing run when one exists.

These are **algorithm-level** tests on constructed or fixed inputs, kept
deliberately separate from the **real-video measurements** in
[M2_Real_Video_Results.md](M2_Real_Video_Results.md). Where a test uses
constructed vectors it says so, so the two kinds of evidence are never confused.

## 9. Credit constraint

45.50 credits per generation, measured. **Generation is now finished for
Milestone 2** — four videos exist and no further credits will be spent.

This is why nothing in the design assumes a large candidate pool, and why the
diversity report states plainly that selection discarded nothing: with three
clips passing Gate 1 against k=6, farthest-point selection has nothing to
discard.

## 10. What we do not claim

- The workflow is **not** fully automated end to end. It is automated either
  side of one clearly marked manual step, and says so in the UI and the docs.
- Tier 3 product compositing is **not** built.
- **We have four real videos, not six.** The planner emits six briefs; four
  videos were generated, and the four did not come from those briefs.
- Diversity is measured on real videos, but **selection discarded nothing**.
- Safe Cut **recovered nothing** on this batch.
- Ekly wall-clock generation time is unmeasured and is not estimated anywhere.
