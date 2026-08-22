"""Fidelity Lock -- Quality Gate 1.

Scores how far the product has drifted between the source image and each
generated clip, and rejects clips that drift too far.

Two design decisions carry the whole thing, and both come from what the
Milestone 1 prototype actually showed:

  1. PER-FRAME, NOT PER-CLIP. The drift observed in the prototype was local and
     transient -- it appeared during the model turn and passed. A single-frame
     check would very likely have missed it. So every sampled frame is scored
     and the series is kept, not just its average.

  2. INSIDE THE MASK ONLY. The background is supposed to change completely;
     measuring it would drown the signal we care about in the variation we
     asked for.

The 0-100 Fidelity Score is a DESIGNED aggregate, not a validated one. The
transfer functions and weights below are documented choices, and the pass
threshold is calibrated separately (see calibrate.py) from the real clips we
have. Any report that prints a score must also carry the sample size behind
its threshold.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from PIL import Image

from kaladhar.fidelity.metrics import (aligned_ssim, dominant_lab, palette_delta_e,
                                       weave_descriptor, weave_distance)
from kaladhar.input.segment import segment
from kaladhar.input.signature import masked_crop
from kaladhar.video.io import motion_profile, probe, sample_frames

# Segmentation resolution. Dropping the long edge from 1152 to 512 leaves the
# measured garment fraction essentially unchanged (0.379 -> 0.382 on a real
# frame) and is modestly cheaper: a warm A/B of 5 alternating reps gives a
# median 0.543s at full frame vs 0.473s reduced, a 1.15x speed-up.
#
# CORRECTION: an earlier comment here claimed 8x. That was wrong -- it compared
# a COLD first call (which includes loading the 176 MB U2-Net model) against a
# warm one. rembg resizes every input to 320x320 internally before inference,
# so model cost is near-constant in input size; the saving is only in decode,
# resize and post-processing. The reduction is kept because it is a real if
# small win and lowers peak memory, not because it is a large one.
#
# The mask is a region, not fine detail, so it upsamples cleanly and the
# metrics still run on full-resolution pixels.
SEG_LONG_EDGE = 512

# Component weights, set from how well each metric actually behaved when tested
# rather than from how good it sounded on paper.
#
#   colour     0.35  strongest and most commercially damaging failure. A shifted
#                    dye is what a customer notices on arrival and calls a
#                    misrepresentation.
#   identity   0.30  CLIP cosine moved cleanly across the real clip (0.98 -> 0.84),
#                    so it carries real signal.
#   weave      0.25  validated against known degradation: monotonic under
#                    increasing blur, saturating on flat colour, and stable
#                    under rescaling (see tools/t_weave.py).
#   structure  0.10  weakest of the four. Aligned SSIM on a re-rendered motif is
#                    inherently noisy, so it informs the score without dominating.
WEIGHTS = {"colour": 0.35, "identity": 0.30, "weave": 0.25, "structure": 0.10}


def _clamp01(x):
    return float(max(0.0, min(1.0, x)))


def colour_subscore(delta_e):
    """dE2000 below ~2 is imperceptible to a human; by ~14 it is plainly a
    different colour. Linear in between."""
    return 100.0 * _clamp01(1.0 - (delta_e - 2.0) / 12.0)


def weave_subscore(dist):
    """Cosine distance between Gabor+FFT texture descriptors."""
    return 100.0 * _clamp01(1.0 - dist / 0.35)


def identity_subscore(cos):
    """CLIP cosine on the masked garment crop. Below ~0.55 the model has
    effectively put a different garment on the person."""
    return 100.0 * _clamp01((cos - 0.55) / 0.40)


def structure_subscore(ssim, conf):
    """Aligned SSIM on the border/pallu motif, gated by match confidence.

    If the motif cannot be located confidently the structural evidence is
    treated as weak rather than as a pass -- a high SSIM against a bad match
    means nothing.
    """
    if conf < 0.30:
        return 0.0
    gate = _clamp01((conf - 0.30) / 0.30)
    return 100.0 * _clamp01(ssim / 0.60) * gate


def _mask_for(frame):
    """Garment mask for a frame, computed small and upsampled."""
    w, h = frame.size
    scale = SEG_LONG_EDGE / max(w, h)
    if scale < 1.0:
        small = frame.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                             Image.BILINEAR)
    else:
        small = frame
    m = segment(small)
    mask = cv2.resize(m.garment, (w, h), interpolation=cv2.INTER_NEAREST)
    return mask, m


def score_frame(frame, sig, src_patch):
    """All four metrics for one frame. Returns a dict of raw values and
    sub-scores, or None if the product could not be found at all."""
    from kaladhar.diversity.embed import embed

    rgb = np.asarray(frame.convert("RGB"), dtype=np.uint8)
    mask, mres = _mask_for(frame)

    if (mask > 0).mean() < 0.01:
        return {"found": False, "reason": "no garment region detected in frame"}

    pal = dominant_lab(rgb, mask, k=5)
    d_e = palette_delta_e(np.array(sig["palette_lab"], dtype=np.float32), pal)

    wv = weave_descriptor(rgb, mask)
    w_d = weave_distance(np.array(sig["weave_descriptor"], dtype=np.float32), wv)

    crop = masked_crop(frame, mask)
    vec = embed([crop])[0]
    cos = float(np.dot(np.array(sig["clip"], dtype=np.float32), vec))

    if src_patch is not None:
        s, conf, box = aligned_ssim(src_patch, rgb, mask)
    else:
        s, conf, box = 0.0, 0.0, None

    subs = {
        "colour": colour_subscore(d_e),
        "weave": weave_subscore(w_d),
        "identity": identity_subscore(cos),
        "structure": structure_subscore(s, conf),
    }
    total = sum(subs[k] * WEIGHTS[k] for k in WEIGHTS)

    return {
        "found": True,
        "delta_e2000": round(d_e, 3),
        "weave_distance": round(w_d, 4),
        "clip_cosine": round(cos, 4),
        "ssim": round(s, 4),
        "ssim_confidence": round(conf, 4),
        "ssim_box": box,
        "mask_fraction": round(float((mask > 0).mean()), 4),
        "subscores": {k: round(v, 2) for k, v in subs.items()},
        "fidelity": round(total, 2),
    }


def score_clip(clip_path, sig, src_patch=None, stride=5, progress=False):
    """Score every sampled frame of a clip and aggregate.

    The per-frame series is the point: it is what turns "the saree looks a bit
    off somewhere in the middle" into a curve with a dip you can point at.
    """
    t0 = time.perf_counter()
    info = probe(clip_path)
    frames = sample_frames(clip_path, stride=stride)

    per_frame = []
    for n, (idx, frame) in enumerate(frames):
        r = score_frame(frame, sig, src_patch)
        r["frame"] = idx
        r["t"] = round(idx / info["fps"], 3) if info["fps"] else None
        per_frame.append(r)
        if progress:
            print("    frame %3d/%d  fidelity=%s" % (
                n + 1, len(frames), r.get("fidelity", "n/a")), flush=True)

    ok = [f for f in per_frame if f.get("found")]
    if not ok:
        return {"clip": str(clip_path), "info": info, "error": "no scorable frames",
                "per_frame": per_frame}

    vals = np.array([f["fidelity"] for f in ok], dtype=np.float32)
    worst = min(ok, key=lambda f: f["fidelity"])

    motion = motion_profile(clip_path)

    return {
        "clip": str(clip_path),
        "info": info,
        "frames_scored": len(ok),
        "frames_sampled": len(per_frame),
        "stride": stride,
        "fidelity_mean": round(float(vals.mean()), 2),
        "fidelity_min": round(float(vals.min()), 2),
        "fidelity_std": round(float(vals.std()), 2),
        "worst_frame": {"frame": worst["frame"], "t": worst["t"],
                        "fidelity": worst["fidelity"]},
        "means": {
            "delta_e2000": round(float(np.mean([f["delta_e2000"] for f in ok])), 3),
            "weave_distance": round(float(np.mean([f["weave_distance"] for f in ok])), 4),
            "clip_cosine": round(float(np.mean([f["clip_cosine"] for f in ok])), 4),
            "ssim": round(float(np.mean([f["ssim"] for f in ok])), 4),
        },
        "motion": {k: motion[k] for k in ("mean", "max", "std")},
        "motion_series": motion["series"],
        "per_frame": per_frame,
        "scoring_seconds": round(time.perf_counter() - t0, 2),
    }
