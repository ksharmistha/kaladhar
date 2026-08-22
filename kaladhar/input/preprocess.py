"""Normalise an accepted image into the working asset the pipeline consumes,
and build the reference image that gets attached in Ekly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from kaladhar.config import REFERENCE_LONG_EDGE, WORKING_LONG_EDGE


def _fit_long_edge(im: Image.Image, long_edge: int) -> Image.Image:
    """Scale so the longer side equals long_edge. Never upscales -- inventing
    pixels would make weave scoring measure our interpolator, not the fabric."""
    w, h = im.size
    scale = long_edge / max(w, h)
    if scale >= 1.0:
        return im.copy()
    return im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)


def normalise(src: str | Path) -> Image.Image:
    """EXIF-correct, flatten transparency, force RGB, fit to working size."""
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)          # phone photos arrive rotated
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, (255, 255, 255))
        flat.paste(im, mask=im.split()[-1])
        im = flat
    else:
        im = im.convert("RGB")
    return _fit_long_edge(im, WORKING_LONG_EDGE)


def build_reference_image(working: Image.Image, subject_mask=None,
                          grey: int = 128) -> Image.Image:
    """The image handed to Ekly's '+ ref image' control.

    When a subject mask is supplied the product and the person are ISOLATED onto
    a flat neutral grey field. Everything outside the rembg subject mask is
    replaced, so the generator receives the product and nothing else -- no
    garden, no architecture, no colour cast from the original location that
    could bias the new scene it is being asked to build.

    Neutral grey rather than white or black on purpose: it is photometrically
    non-committal, so it neither lifts nor crushes the garment's own tones the
    way a pure white or pure black field would.

    If no mask is given the image is passed through unchanged, so the function
    is still safe to call before segmentation has run.
    """
    if subject_mask is None:
        return _fit_long_edge(working, REFERENCE_LONG_EDGE)

    rgb = np.asarray(working.convert("RGB"), dtype=np.uint8)
    m = (np.asarray(subject_mask) > 0)[:, :, None]
    flat = np.full_like(rgb, grey)
    out = np.where(m, rgb, flat).astype(np.uint8)
    return _fit_long_edge(Image.fromarray(out), REFERENCE_LONG_EDGE)


def to_array(im: Image.Image) -> np.ndarray:
    return np.asarray(im, dtype=np.uint8)
