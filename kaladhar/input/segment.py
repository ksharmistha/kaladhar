"""Product region segmentation.

Two stages, because they answer different questions:

  1. SUBJECT mask  -- rembg (U2-Net) separates the person+garment from the
     background. This is reliable and is what rembg is actually built for.

  2. GARMENT mask  -- the subject mask still contains face, arms and feet.
     Every fidelity metric must be computed on fabric only, so skin is removed
     with a YCrCb+HSV skin-chrominance heuristic plus a head-region cut.

Stage 2 is a HEURISTIC, not a trained garment segmenter. It is good enough to
keep skin out of the colour statistics, which is what matters here. It is NOT
reliable on sheer fabric, loose thread ends, or fabric whose colour sits inside
the skin-tone chrominance range (undyed cream, beige, gold-on-skin). Those
cases are flagged in the notes rather than silently mis-measured.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

# Pixels above this percentile of the subject's own local texture are treated as
# fabric detail and kept even if their colour reads as skin. Tuned high enough
# that smooth skin is still removed.
TEXTURE_PROTECT_PCT = 80

_SESSION = None


def _session():
    global _SESSION
    if _SESSION is None:
        from rembg import new_session
        _SESSION = new_session("u2net")
    return _SESSION


@dataclass
class MaskResult:
    subject: np.ndarray     # uint8 0/255, person + garment
    garment: np.ndarray     # uint8 0/255, garment only (skin removed)
    notes: list

    @property
    def garment_fraction(self) -> float:
        return float((self.garment > 0).mean())

    @property
    def subject_fraction(self) -> float:
        return float((self.subject > 0).mean())


def _largest_component(mask: np.ndarray) -> np.ndarray:
    """Drop stray blobs -- reflections, background objects rembg kept."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    if n <= 1:
        return mask
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(lab == biggest, 255, 0).astype(np.uint8)


def _skin_mask(rgb: np.ndarray) -> np.ndarray:
    """Skin detection in chrominance space, which is far more robust across
    lighting and skin tone than an RGB rule."""
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    a = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    b = cv2.inRange(hsv, (0, 30, 50), (25, 170, 255))
    skin = cv2.bitwise_and(a, b)
    skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return cv2.dilate(skin, np.ones((5, 5), np.uint8), iterations=1)


def segment(image: Image.Image) -> MaskResult:
    from rembg import remove

    notes = []
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)

    cut = remove(image.convert("RGB"), session=_session())
    alpha = np.asarray(cut.convert("RGBA"))[:, :, 3]
    subject = (alpha > 128).astype(np.uint8) * 255
    subject = cv2.morphologyEx(subject, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    subject = _largest_component(subject)

    if (subject > 0).mean() < 0.05:
        notes.append("Subject mask covers under 5% of the frame -- segmentation likely failed.")

    skin = _skin_mask(rgb)

    # Warm-toned print and woven metallic borders fall inside the skin
    # chrominance range, so the raw skin filter deletes them from the product.
    # Skin is SMOOTH; printed and woven fabric is not. Pixels carrying sustained
    # local texture are therefore protected from skin removal. Sustained rather
    # than per-pixel gradient on purpose: an isolated edge (an eyelid, a knuckle)
    # should not protect a region, a printed panel should.
    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(grey, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(grey, cv2.CV_32F, 0, 1, ksize=3)
    local_texture = cv2.boxFilter(cv2.magnitude(gx, gy), -1, (9, 9))
    inside = subject > 0
    if inside.any():
        thr = float(np.percentile(local_texture[inside], TEXTURE_PROTECT_PCT))
        skin[(local_texture > thr) & inside] = 0

    garment = cv2.bitwise_and(subject, cv2.bitwise_not(skin))

    # The head sits above the garment in a standing full-body shot; hair is not
    # skin and survives the chrominance filter, so cut the band above the subject
    # top. NOTE: this assumes a full-length shot. On a crop that starts at the
    # shoulders it can clip the top of a neckline.
    ys, xs = np.where(subject > 0)
    if len(ys):
        top, bottom = int(ys.min()), int(ys.max())
        head_cut = top + int(0.10 * (bottom - top))
        garment[:head_cut, :] = 0

    garment = cv2.morphologyEx(garment, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    garment = cv2.morphologyEx(garment, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    garment = _largest_component(garment)

    gf = (garment > 0).mean()
    sf = max((subject > 0).mean(), 1e-9)
    if gf < 0.05:
        notes.append("Garment mask is very small -- the skin heuristic may have removed fabric. "
                     "Likely a skin-toned or undyed fabric.")
    if gf > 0.95 * sf:
        notes.append("Skin removal changed almost nothing -- check the mask overlay by eye.")
    notes.append("Garment mask is a heuristic refinement of the rembg subject mask, "
                 "not a trained garment segmenter.")

    return MaskResult(subject=subject, garment=garment, notes=notes)


def overlay(image: Image.Image, mask: np.ndarray, colour=(255, 0, 128), alpha=0.45) -> Image.Image:
    """Visual evidence: mask painted over the source so a human can judge it."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    tint = np.zeros_like(rgb)
    tint[:] = colour
    m = (mask > 0)[:, :, None]
    blended = np.where(m, (rgb * (1 - alpha) + tint * alpha).astype(np.uint8), rgb)
    solid = (mask > 0).astype(np.uint8)
    edges = cv2.dilate(solid, np.ones((3, 3), np.uint8)) - solid
    blended[edges > 0] = (255, 255, 0)
    return Image.fromarray(blended)
