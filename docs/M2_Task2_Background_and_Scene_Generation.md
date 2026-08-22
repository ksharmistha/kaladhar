# Milestone 2, Task 2 — Background & Scene Generation

Team Code Blooded — GigPoint Hackathon, 22 August 2026
Problem 2: AI Ad Generation, client Kaladhar

Task as stated on the platform: *"Generate multiple distinct
environments/backgrounds from the same product/model image without making every
output look repetitive."*

---

## 1. The problem being solved

The client's complaint is specific: existing AI tools produce repetitive output —
similar backgrounds, movements, scenes and presentation styles — and variations
that amount to filters rather than genuinely different creatives.

The root cause is how people prompt. Re-prompting the same idea with different
adjectives moves the render a little but not the concept, so ten outputs are ten
versions of one idea.

Our answer is to make variation **structural** rather than verbal. Each scene is
a point in a five-axis grid, and the sampler is required to move along at least
three axes between any two chosen points. Two briefs cannot be near-duplicates,
because the constraint forbids it.

## 2. The variation matrix

| Axis | Values | Count |
|---|---|---|
| Environment | premium studio, luxury interior, cafe, outdoor natural, festive/Diwali, wedding/mandap, travel/heritage | 7 |
| Lighting | softbox studio, golden hour, warm lamp, overcast diffuse, festive practicals, high-key luxury | 6 |
| Camera | slow push-in, slow orbit, vertical reveal, static with subject motion, rack focus, parallax dolly | 6 |
| Concept | heritage craft, occasion/festive, everyday elegance, gifting, premium luxury, styling showcase | 6 |
| Colour grade | neutral true-to-fabric, warm gold, cool editorial, rich saturated festive | 4 |

**6,048 distinct grid points.** Each axis value carries its own prompt fragment,
so a brief is assembled from the grid rather than written by hand.

Camera is an axis rather than a setting because Ekly exposed no camera-path
control, motion-strength slider or seed to us. Camera variation therefore has to
be achieved through differentiated prompt wording, and treating it as a first
class axis is what makes that systematic.

## 3. Coherence rules

Orthogonality alone can produce nonsense — an outdoor garden lit by candle glow,
or a Diwali scene under flat overcast daylight. A set of discouraged
environment/lighting pairs is excluded during sampling. This is a constraint on
pairings, not a ban on any axis value: every value remains available in a
context where it makes sense.

This was added after inspecting a first sample that paired outdoor greenery with
festive practical lighting. It matters more than it might seem, because with
roughly seven affordable generations we cannot spend one on an incoherent scene.

## 4. Sampling

Greedy constrained selection in axis space with random restarts. A candidate is
accepted only if it is coherent and differs from every already-chosen brief on
at least three axes. Among valid sets, the sampler prefers the one with the
greatest total pairwise separation and the least reuse of individual axis
values — six briefs can satisfy the pairwise rule and still all be set in a
studio, and penalising reuse spreads them across the matrix as well.

If the constraint cannot be met for the requested N, the sampler raises rather
than quietly relaxing the rule.

**Result for a six-brief run (seed 7): minimum axis difference achieved = 4,
against the required 3.** The pairwise matrix is produced as evidence:

```
     V01 V02 V03 V04 V05 V06
V01    0   4   5   4   5   5
V02    4   0   4   5   5   4
V03    5   4   0   4   4   4
V04    4   5   4   0   5   4
V05    5   5   4   5   0   5
V06    5   4   4   4   5   0
```

The six briefs:

| ID | Environment | Lighting | Camera | Concept | Grade |
|---|---|---|---|---|---|
| V01 | Wedding / mandap | Festive practicals | Vertical reveal | Gifting | Cool editorial |
| V02 | Outdoor natural | Golden hour | Vertical reveal | Occasion / festive | Rich saturated festive |
| V03 | Outdoor natural | Overcast diffuse | Parallax dolly | Heritage craft | Warm gold |
| V04 | Wedding / mandap | Warm lamp | Slow orbit | Premium luxury | Warm gold |
| V05 | Premium studio | Softbox studio | Parallax dolly | Styling showcase | Neutral true-to-fabric |
| V06 | Travel / heritage | Golden hour | Slow push-in | Everyday elegance | Warm gold |

## 5. Brief structure

The prompt structure is not invented here. It is the structure validated in our
Milestone 1 prototype, which held saree colour strongly and kept the border
broadly recognisable, so only the scene-dependent parts vary:

1. scene description, assembled from environment and lighting
2. explicit camera direction
3. natural subject motion
4. concept and colour-grade direction
5. an uppercase **PRODUCT ACCURACY** block naming every property to preserve —
   colour, dye tone, border design, motif placement, pattern, weave texture,
   pleat structure — and stating that only background, lighting and camera may
   change
6. explicit negative guidance

Each brief also carries the Ekly settings to use and the reference image path.

## 6. The handoff

**Ekly.ai exposes no API to us.** Briefs are not submitted automatically. The
planner writes `runs/<id>/briefs/EKLY_SHEET.txt`, an operator sheet designed to
be worked through top to bottom with copy and paste. It states the reference
image to attach, the model and settings, the filename to save each clip under,
and a box to record the wall-clock generation time — a number we do not yet have
and will not invent.

The sheet also carries a warning that in our Milestone 1 run the 9:16 setting
still returned a 768x1152 file, so the setting must not be trusted and every
clip is re-probed on import.

Expected cost for six briefs: **273.00 credits**, at the 45.50 per generation we
actually measured.

## 7. Diversity is also measured, not just planned

Planning briefs apart is necessary but not sufficient: two structurally
different briefs can still come back as two similar-looking renders. So each
clip is reduced to a single CLIP embedding — the mean over sampled frames, since
a clip is not one image — and selection uses farthest-point (max-min greedy)
search to maximise the minimum separation of the chosen set.

The **Diversity Score** is the mean pairwise cosine distance across the selected
set, reported alongside the same figure for the pool it came from. If selection
achieved nothing, the two numbers are equal and that is visible.

**Now measured on real videos.** Diversity is computed from the actual generated
files — mean CLIP embedding over sampled frames — with no constructed vectors.

| Measure | Value |
|---|---|
| Diversity Score, all four real videos | **14.44** |
| Diversity Score, Gate-1 passing three | **10.97** |
| Most similar pair | BASELINE-courtyard ↔ ROOFTOP-night (0.0931) |
| Most distinct pair | BASELINE-courtyard ↔ MANSION-marble (0.1999) |

Full pairwise matrix in [M2_Real_Video_Results.md](M2_Real_Video_Results.md).

**The result worth pointing at:** the most distinct clip in the set is
MANSION-marble, which Gate 1 rejected for product drift and a scene cut.
Maximising difference alone would have selected the clip that misrepresents the
product. That is why the two gates are independent, and it emerged from
measurement rather than being designed in.

**Selection was not exercised.** With k=6 requested and only 3 clips passing
Gate 1, all three are selected and the diversity gain is **+0.00**. The engine
reports this rather than implying filtering it did not perform. Farthest-point
selection only discards when the pool exceeds k. The constructed-vector unit
tests remain the evidence that the *selection* logic works; they are clearly
labelled as algorithm-level and separate from these real measurements.

## 8. Evidence

- `runs/<id>/briefs/briefs.json` — full briefs with prompts and axes
- `runs/<id>/briefs/sampling_report.json` — achieved axis difference, value usage
- `runs/<id>/briefs/EKLY_SHEET.txt` — the operator handoff sheet
- Pairwise axis-difference matrix, above and in the review page
- `tests/test_pipeline.py` — constraint enforcement, coherence, determinism,
  and the two diversity-algorithm tests

## 9. What we do not claim

- Briefs are **not** submitted to Ekly automatically. A human generates them.
- Diversity is now measured on real videos, but **selection discarded nothing**,
  because the passing pool (3) is smaller than k (6).
- The six-variation target is **ours**, not a client requirement. The brief
  specifies no number — and **we generated four videos, not six.**
- The four real videos were **not** generated from these six briefs; none of
  their filenames matched a brief ID and the pipeline reported that.
