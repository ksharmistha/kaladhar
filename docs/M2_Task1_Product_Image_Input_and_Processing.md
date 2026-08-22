# Milestone 2, Task 1 — Product Image Input & Processing

Team Code Blooded — GigPoint Hackathon, 22 August 2026
Problem 2: AI Ad Generation, client Kaladhar

Task as stated on the platform: *"Build image upload/input handling, validation,
background preparation, resizing and preprocessing."*

Sourcing note: figures in this document were measured on our own machine using
the code in this repository. Items marked *our choice* are decisions we made and
are not client requirements.

---

## 1. Objective

Turn an arbitrary uploaded product photo into a validated, normalised asset set
that every later stage consumes, and compute it once so nothing downstream
recomputes it.

Four things come out of this stage:

1. a normalised working image
2. a reference image prepared for the Ekly handoff
3. a binary mask of the garment region
4. a reference signature — the baseline every drift comparison scores against

## 2. Modules

```
kaladhar/input/validate.py     format, size, resolution, aspect, corruption
kaladhar/input/preprocess.py   EXIF, colour mode, resize, reference image
kaladhar/input/segment.py      subject mask, then garment mask
kaladhar/input/signature.py    palette, weave descriptor, CLIP vector, patch
kaladhar/input/ingest.py       orchestration, persistence, timing
kaladhar/storage/run.py        run directory, state, caching, versioning
```

## 3. Validation

Validation distinguishes what cannot be used from what will degrade quality but
is still workable. This distinction is not cosmetic: our own Kaladhar sample is
500x724, below the resolution we would prefer, and a naive minimum-resolution
rule would have rejected the exact image the project is built around.

| Check | Behaviour |
|---|---|
| File exists, non-empty, under 40 MB | reject |
| Decodes as a real image | reject (two-pass: verify, then full decode) |
| Format in JPEG/PNG/WEBP/BMP/TIFF | reject |
| Short edge below 400 px | reject |
| Short edge below 800 px | **warn** and continue |
| Aspect outside 0.5-0.9 portrait | warn |
| Landscape | warn: 9:16 export will crop or pad heavily |
| Greyscale | warn: colour drift scoring becomes meaningless |

Observed on our source image:

```
PASS  saree_source.jpg
    format: JPEG      dimensions: 500x724     aspect: 0.691
    WARNING Short edge is 500px (under 800px). Usable, but weave-texture
            scoring will be limited by source detail, not by the generated clip.
```

Rejection cases were tested and behave correctly — a non-image file and a
missing file both reject with specific messages, and both are covered by tests.

## 4. Preprocessing

- EXIF orientation applied, because phone photos arrive rotated.
- Transparency flattened onto white; everything forced to RGB.
- Fitted so the long edge is 1152 px, matching the generator's native output
  height. **Never upscaled** — inventing pixels would mean the weave metric
  measures our interpolator rather than the fabric.

The reference image handed to Ekly is a faithful copy at the same size. We
considered cropping it to the garment and rejected that: the generator also
needs the model and the drape to reproduce how the saree actually falls.

## 5. Segmentation

Two stages, because they answer different questions.

**Subject mask.** rembg (U2-Net) separates person plus garment from background.
This is what rembg is built for and it is reliable.

**Garment mask.** The subject mask still contains face, arms and feet. Every
fidelity metric must run on fabric only, so skin is removed using a YCrCb plus
HSV chrominance heuristic, followed by a head-region cut, morphological cleanup
and largest-component selection.

Measured on our source image:

| Mask | Coverage of frame |
|---|---|
| Subject | 39.7% |
| Garment | 35.7% |

The 4-point difference is the face, arms and feet, which is the right order of
magnitude. The overlay was checked by eye and correctly covers blouse, drape,
pallu and border while excluding the face, the arm and the hand.

**Stated limitation.** This is a heuristic refinement, *not* a trained garment
segmenter. It is not reliable on sheer fabric, on loose thread ends, or on
fabric whose colour sits inside the skin-tone chrominance range — undyed cream,
beige, or gold against skin. Those cases are flagged in the run notes rather
than silently mis-measured.

## 6. Reference signature

The baseline for all later comparison. It captures the product in the three
ways the product can be wrong.

| Element | Method | Wrongness it detects |
|---|---|---|
| Palette | k-means over CIELAB, garment pixels only, k=5 | dye shift |
| Weave descriptor | Gabor bank (6 orientations x 3 scales) + FFT radial profile + absolute high-frequency energy | texture collapse |
| CLIP vector | 512-d embedding of the masked garment crop | a different garment entirely |
| Border patch | most texture-dense 128 px square inside the mask | the Weave Guard region |

k-means rather than a mean colour, because a saree is not one colour: a mean
would blend teal body and silver border into one meaningless value and would
hide a recoloured border.

Palette extracted from our source: `#31a5bd  #99c6ce  #106784  #4b7c81  #0e3144`
— teal body with the lighter silver of the border, which matches the garment.

The border patch is found automatically rather than hardcoded, and on our source
it selected the pallu brocade motif, which is the correct region.

## 7. Persistence and caching

Each run is a directory under `runs/<run_id>` holding input assets, masks,
signature, briefs, clips, scores, evidence and exports, plus `run.json` carrying
state, history and timings. Everything expensive is computed once here and
reused, which is what makes per-frame scoring affordable later.

The run also carries the pipeline state, including `AWAITING_CLIPS` — the manual
Ekly generation step. That is modelled as a first-class state rather than hidden.

## 8. Measured performance

One image, this machine, cold model load excluded:

| Stage | Seconds |
|---|---|
| validate | 0.009 |
| preprocess | 0.064 |
| segment | 2.060 |
| signature | 1.606 |
| **ingest total** | **3.749** |

## 9. Evidence

- `runs/<id>/evidence/mask_garment_overlay.png` — garment mask over the source
- `runs/<id>/evidence/mask_subject_overlay.png` — subject mask for comparison
- `runs/<id>/evidence/weave_guard_source.png` — magnified border patch
- `runs/<id>/input/signature.json` — full signature
- `runs/<id>/input/validation.json` — validation report
- Rejection cases demonstrated in `tests/test_pipeline.py`

## 10. What we do not claim

- Segmentation is not perfect on sheer fabric or loose threads.
- The garment mask is a heuristic, not a trained model.
- No drift metric is validated by this stage; this stage only produces the
  baseline that the Fidelity Lock scores against.
