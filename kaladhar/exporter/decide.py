"""Choosing between crop and pad per clip, from measurement rather than policy.

The source is 768x1152 (2:3) and delivery is 1080x1920 (9:16), so something has
to give. The handover flagged this as an open decision, and it turns out not to
have one right answer:

  crop  fills the whole screen but discards 15.6% of the frame width. On a
        vertical fashion shot that can slice off the pallu or the border, and a
        cropped-off border is exactly the misrepresentation the client ruled out.
  pad   keeps every pixel but letterboxes the sides, losing screen area on a
        format where full-bleed matters.

Measured on our real clip, cropping removed 15.6% of the frame and 0.00% of the
GARMENT, because the model is centred. So the honest answer is per clip: measure
how much of the product a crop would actually destroy, then crop when it costs
nothing and pad when it does not.
"""
from __future__ import annotations

import cv2
import numpy as np

from kaladhar.config import EXPORT_ASPECT
from kaladhar.input.segment import segment
from kaladhar.video.io import sample_frames

# A crop is only taken when it costs essentially none of the product. The bar is
# deliberately high: losing a slice of border is not a rounding error, it is the
# thing the client said must not happen.
RETENTION_REQUIRED = 0.995
SEG_LONG_EDGE = 512


def garment_retention(clip_path, samples=5):
    """Fraction of garment pixels that survive a centre crop to 9:16.

    Checked across several frames, not one: the model moves, and a crop that is
    safe at t=0 can clip the pallu once she turns. The MINIMUM across frames is
    what matters.
    """
    frames = sample_frames(clip_path, stride=1, max_frames=None)
    if not frames:
        raise ValueError("no frames in %s" % clip_path)
    step = max(1, len(frames) // samples)
    picks = frames[::step][:samples]

    per_frame = []
    for idx, frame in picks:
        w, h = frame.size
        scale = SEG_LONG_EDGE / max(w, h)
        small = frame.resize((max(1, round(w * scale)), max(1, round(h * scale)))) \
            if scale < 1 else frame
        mask = cv2.resize(segment(small).garment, (w, h), interpolation=cv2.INTER_NEAREST)
        total = float((mask > 0).sum())
        if total < 1:
            continue

        keep_w = int(round(h * EXPORT_ASPECT))
        if keep_w >= w:
            per_frame.append({"frame": idx, "retention": 1.0})
            continue
        x0 = (w - keep_w) // 2
        kept = float((mask[:, x0:x0 + keep_w] > 0).sum())
        per_frame.append({"frame": idx, "retention": round(kept / total, 5)})

    if not per_frame:
        return {"min_retention": 0.0, "per_frame": [], "note": "no garment found"}

    return {
        "min_retention": min(p["retention"] for p in per_frame),
        "mean_retention": round(float(np.mean([p["retention"] for p in per_frame])), 5),
        "per_frame": per_frame,
    }


def choose_mode(clip_path, samples=5):
    """Return (mode, rationale_dict)."""
    r = garment_retention(clip_path, samples=samples)
    keep = r["min_retention"] >= RETENTION_REQUIRED
    r["mode"] = "crop" if keep else "pad"
    r["required_retention"] = RETENTION_REQUIRED
    r["rationale"] = (
        "crop keeps %.2f%% of the garment across sampled frames (>= %.1f%% required), "
        "so the full screen is used with no product loss"
        % (r["min_retention"] * 100, RETENTION_REQUIRED * 100)
        if keep else
        "crop would remove %.2f%% of the garment at its worst frame, so the clip is "
        "padded instead to avoid cutting the product"
        % ((1 - r["min_retention"]) * 100)
    )
    return r["mode"], r
