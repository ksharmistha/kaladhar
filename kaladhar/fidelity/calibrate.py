"""Deriving a pass threshold honestly from a very small sample.

The problem: we have exactly one real generated clip. One sample supports no
statistics at all, so picking a threshold from it alone would be inventing a
number and dressing it as calibration.

The approach instead ANCHORS THE SCALE with controlled degradations of the
source image itself. We know exactly how wrong each anchor is, because we made
it wrong on purpose:

    hue shift      a dye change -- the failure the client called
                   misrepresentation. A shift a customer would notice on
                   arrival must score below the threshold.
    blur           weave collapse -- handloom rendered as flat fabric.
    desaturation   washed-out dye.

Scoring those through the same Fidelity Lock gives reference points on the same
0-100 scale as the real clip, so the threshold can be placed between "clearly
still the product" and "clearly misrepresented" rather than guessed.

This is still a small-sample calibration and every report says so. The anchors
constrain the scale; they do not substitute for more real clips.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from kaladhar.fidelity.lock import (WEIGHTS, colour_subscore, identity_subscore,
                                    structure_subscore, weave_subscore)
from kaladhar.fidelity.metrics import (aligned_ssim, dominant_lab, palette_delta_e,
                                       weave_descriptor, weave_distance)
from kaladhar.input.signature import masked_crop


def _hue_shift(rgb, degrees):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.int16)
    hsv[:, :, 0] = (hsv[:, :, 0] + int(degrees / 2)) % 180      # OpenCV hue is 0-179
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def _desaturate(rgb, factor):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 1] *= factor
    return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB)


def _score_variant(rgb, mask, sig, src_patch):
    """Run the same four metrics the Fidelity Lock uses, on a still image."""
    from kaladhar.diversity.embed import embed

    pal = dominant_lab(rgb, mask, k=5)
    d_e = palette_delta_e(np.array(sig["palette_lab"], dtype=np.float32), pal)
    wv = weave_descriptor(rgb, mask)
    w_d = weave_distance(np.array(sig["weave_descriptor"], dtype=np.float32), wv)
    crop = masked_crop(Image.fromarray(rgb), mask)
    cos = float(np.dot(np.array(sig["clip"], dtype=np.float32), embed([crop])[0]))
    s, conf, _ = aligned_ssim(src_patch, rgb, mask) if src_patch is not None else (0, 0, None)

    subs = {
        "colour": colour_subscore(d_e),
        "weave": weave_subscore(w_d),
        "identity": identity_subscore(cos),
        "structure": structure_subscore(s, conf),
    }
    return {
        "delta_e2000": round(d_e, 3),
        "weave_distance": round(w_d, 4),
        "clip_cosine": round(cos, 4),
        "ssim": round(s, 4),
        "fidelity": round(sum(subs[k] * WEIGHTS[k] for k in WEIGHTS), 2),
    }


def calibrate(run):
    img = np.asarray(Image.open(run.path("input/working.png")).convert("RGB"))
    mask = np.asarray(Image.open(run.path("input/mask_garment.png")).convert("L"))
    sig = run.read_json("input/signature.json")
    pp = run.path("input/border_patch.png")
    patch = np.asarray(Image.open(pp).convert("RGB")) if pp.exists() else None

    anchors = [("source (identity)", img, "upper bound -- the product itself")]
    for deg in (5, 10, 20):
        anchors.append(("hue shift %d deg" % deg, _hue_shift(img, deg),
                        "dye change, a customer-visible misrepresentation"))
    for k in (5, 9):
        anchors.append(("blur k=%d" % k, cv2.GaussianBlur(img, (k, k), 0),
                        "weave collapse -- flat, plastic-looking fabric"))
    anchors.append(("desaturate 0.6", _desaturate(img, 0.6), "washed-out dye"))

    rows = []
    for name, variant, why in anchors:
        r = _score_variant(variant, mask, sig, patch)
        r["anchor"] = name
        r["meaning"] = why
        rows.append(r)

    # Real clips already scored in this run.
    real = []
    for p in sorted(run.path("scores").glob("*.json")):
        if p.name in ("summary.json", "selection.json", "calibration.json"):
            continue
        s = run.read_json("scores/%s" % p.name)
        if "fidelity_mean" in s:
            real.append({"id": s.get("id", p.stem), "mean": s["fidelity_mean"],
                         "min": s["fidelity_min"]})

    # ---------------------------------------------------------------------
    # Comparing AGGREGATE scores across the two families would be invalid, and
    # the measured numbers show exactly why: the synthetic anchors degrade the
    # very same pixels, so their aligned SSIM stays near 0.97-0.99, while a
    # generated clip REDRAWS the motif and lands near 0.14. Judging both on one
    # aggregate would rank the real clip below a 20-degree dye shift, which is
    # not what the underlying metrics actually say.
    #
    # So the anchors are used only where they are like-for-like -- the colour
    # and weave components -- and the threshold is built from a CONSTRUCTED
    # LIMIT CLIP: colour and weave pushed to their anchored limits of
    # acceptability, with identity and structure held at what the real clip
    # actually achieved. That produces a floor on the same footing as a real
    # clip rather than one borrowed from a different failure mode.
    # ---------------------------------------------------------------------
    by_name = {r["anchor"]: r for r in rows}
    de_limit = by_name["hue shift 10 deg"]["delta_e2000"]      # visible dye change
    weave_limit = by_name["blur k=5"]["weave_distance"]        # weave collapse

    worst_real = min((r["mean"] for r in real), default=None)

    if not real:
        threshold, basis = None, "no real clips scored yet"
    else:
        # Identity and structure are held at the MEDIAN across real clips, not at
        # the weakest one. With a genuinely failing clip in the pool the weakest
        # clip would drag the floor down far enough to admit itself, which is
        # exactly backwards. The median represents a normally-performing
        # generation, which is what the limit clip is supposed to model.
        idents, structs = [], []
        for r in real:
            s_r = run.read_json("scores/%s.json" % r["id"])
            sc = [f for f in s_r["per_frame"] if f.get("found")]
            if not sc:
                continue
            idents.append(s_r["means"]["clip_cosine"])
            structs.append(sum(f["subscores"]["structure"] for f in sc) / len(sc))
        ident_obs = float(np.median(idents))
        struct_obs = float(np.median(structs))

        limit_score = (colour_subscore(de_limit) * WEIGHTS["colour"]
                       + weave_subscore(weave_limit) * WEIGHTS["weave"]
                       + identity_subscore(ident_obs) * WEIGHTS["identity"]
                       + struct_obs * WEIGHTS["structure"])
        threshold = round(limit_score, 1)
        basis = ("constructed limit clip -- colour pushed to dE2000 %.2f (a "
                 "10-degree hue shift, a visible dye change) and weave to distance "
                 "%.3f (blur k=5, weave collapse), with identity and structure held "
                 "at the median of the real clips. A clip at or below this "
                 "score has drifted as far as a customer-visible misrepresentation."
                 % (de_limit, weave_limit))
        if worst_real is not None and worst_real <= threshold:
            basis += (" NOTE: the weakest real clip (%.1f) does NOT clear this floor."
                      % worst_real)

    report = {
        "anchors": rows,
        "real_clips": real,
        "proposed_threshold": threshold,
        "basis": basis,
        "sample_size_real_clips": len(real),
        "caveat": ("Calibrated from %d real clip(s) plus controlled degradations of "
                   "the source. Identity and structure are held at the median across "
                   "real clips. The anchors fix the scale; they are not a substitute "
                   "for more real generations. Re-run after each new batch."
                   % len(real)),
    }

    lines = ["=" * 72, "FIDELITY THRESHOLD CALIBRATION", "=" * 72, "",
             "Controlled degradation anchors (same metrics, known-wrong inputs):",
             "", "  %-22s %8s %8s %8s %8s" % ("anchor", "fidelity", "dE2000",
                                              "weave", "clipcos")]
    for r in rows:
        lines.append("  %-22s %8.2f %8.2f %8.4f %8.4f"
                     % (r["anchor"], r["fidelity"], r["delta_e2000"],
                        r["weave_distance"], r["clip_cosine"]))
    lines += ["", "Real generated clips:"]
    for r in real:
        lines.append("  %-22s %8.2f (min %.2f)" % (r["id"], r["mean"], r["min"]))
    lines += ["", "PROPOSED THRESHOLD: %s" % (threshold if threshold is not None else "n/a"),
              "  basis: %s" % basis, "",
              "  CAVEAT: %s" % report["caveat"], "=" * 72]
    report["render"] = "\n".join(lines)

    run.write_json("scores/calibration.json",
                   {k: v for k, v in report.items() if k != "render"})
    return report
