"""Reference signature: the baseline every later drift comparison scores against.

Computed once per source image and cached in the run directory. Every metric in
the Fidelity Lock is a comparison between a generated frame and this object, so
it has to capture the product in the three ways the product can be wrong:
wrong colour, wrong texture, wrong garment entirely.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from kaladhar.fidelity.metrics import dominant_lab, find_border_patch, weave_descriptor


def masked_crop(image, mask, pad=8):
    """Tight crop of the product region with everything else blanked to mid
    grey. Feeding this to CLIP rather than the whole frame is what keeps the
    identity score about the garment instead of about the scene."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    m = mask > 0
    if not m.any():
        return image.convert("RGB")
    ys, xs = np.where(m)
    y0 = max(0, ys.min() - pad); y1 = min(rgb.shape[0], ys.max() + 1 + pad)
    x0 = max(0, xs.min() - pad); x1 = min(rgb.shape[1], xs.max() + 1 + pad)
    out = np.where(m[:, :, None], rgb, 128).astype(np.uint8)
    return Image.fromarray(out[y0:y1, x0:x1])


def build_signature(image, mask):
    """Returns (signature_dict, artifacts_dict).

    signature_dict is JSON-serialisable and gets persisted with the run.
    artifacts_dict holds the images worth keeping as visual evidence.
    """
    from kaladhar.diversity.embed import embed

    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)

    palette = dominant_lab(rgb, mask, k=5)
    weave = weave_descriptor(rgb, mask)
    crop = masked_crop(image, mask)
    clip_vec = embed([crop])[0]

    box = find_border_patch(rgb, mask, size=128)
    patch_img = None
    if box is not None:
        x, y, w, h = box
        patch_img = Image.fromarray(rgb[y:y + h, x:x + w])

    sig = {
        "palette_lab": palette.tolist(),
        "palette_rgb_preview": _lab_to_rgb_preview(palette),
        "weave_descriptor": weave.tolist(),
        "clip": clip_vec.tolist(),
        "border_patch_box": list(box) if box else None,
        "mask_fraction": float((mask > 0).mean()),
        "image_size": list(image.size),
    }
    art = {"border_patch": patch_img, "clip_input": crop}
    return sig, art


def _lab_to_rgb_preview(palette):
    """Human-readable hex swatches so the palette can be eyeballed in a report."""
    from skimage.color import lab2rgb
    if palette.size == 0:
        return []
    rgb = lab2rgb(palette.reshape(-1, 1, 3).astype(np.float64)).reshape(-1, 3)
    rgb = np.clip(rgb * 255, 0, 255).astype(int)
    return ["#%02x%02x%02x" % tuple(c) for c in rgb]


def load_signature(sig):
    """Rehydrate the numpy parts of a persisted signature."""
    return {
        "palette_lab": np.array(sig["palette_lab"], dtype=np.float32),
        "weave_descriptor": np.array(sig["weave_descriptor"], dtype=np.float32),
        "clip": np.array(sig["clip"], dtype=np.float32),
        "border_patch_box": sig.get("border_patch_box"),
    }
