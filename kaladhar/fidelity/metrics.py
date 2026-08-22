"""Primitive drift metrics, all computed INSIDE the product mask only.

A note on alignment, because it drives every design choice here:

The source photograph and a generated video frame are NOT pixel-aligned. The
pose, framing, scene and lighting are all deliberately different -- that is the
entire point of the product. So any metric assuming pixel correspondence
(plain SSIM over the whole frame) would measure the scene change we asked for,
not the product drift we care about.

Three of the four metrics are therefore alignment-free -- they compare
distributions and descriptors within the mask:

    dE2000   colour, via dominant-palette matching in CIELAB
    weave    texture, via a Gabor filter bank + FFT radial spectrum
    clip     identity, via CLIP embedding of the masked garment crop

The fourth, SSIM, needs correspondence, so it is applied only to a BEST-MATCH
ALIGNED PATCH: the border/pallu motif is located in the frame by template
matching before SSIM is computed. That is the Weave Guard region.
"""
from __future__ import annotations

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.metrics import structural_similarity as ssim_fn


# ------------------------------------------------------------------- colour
def dominant_lab(rgb, mask, k=5):
    """k dominant colours of the masked region, in CIELAB, sorted by weight.

    k-means in Lab rather than a mean colour: a saree is not one colour. A mean
    would blend teal body and silver border into one meaningless value and
    would hide a border that had been recoloured.
    """
    sel = rgb[mask > 0]
    if sel.size == 0:
        return np.zeros((k, 3), dtype=np.float32)
    lab = rgb2lab(sel.reshape(-1, 1, 3).astype(np.float32) / 255.0)
    lab = lab.reshape(-1, 3).astype(np.float32)

    if len(lab) > 20000:
        idx = np.random.default_rng(0).choice(len(lab), 20000, replace=False)
        lab = lab[idx]

    k = int(min(k, len(lab)))
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, centres = cv2.kmeans(lab, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.ravel(), minlength=k)
    return centres[np.argsort(-counts)].astype(np.float32)


def palette_delta_e(pal_a, pal_b):
    """Mean dE2000 after greedily matching each source colour to its nearest
    counterpart. Matching first means a reordered palette does not read as
    drift -- only an actually shifted dye does."""
    if pal_a.size == 0 or pal_b.size == 0:
        return 100.0
    a = np.repeat(pal_a.reshape(-1, 1, 3), len(pal_b), axis=1)
    b = np.repeat(pal_b.reshape(1, -1, 3), len(pal_a), axis=0)
    d = deltaE_ciede2000(a, b)
    return float(d.min(axis=1).mean())


# ------------------------------------------------------------------ texture
def _gabor_bank():
    bank = []
    for theta in np.arange(0, np.pi, np.pi / 6):
        for lam in (4.0, 8.0, 16.0):
            bank.append(cv2.getGaborKernel((21, 21), 4.0, theta, lam, 0.5, 0, cv2.CV_32F))
    return bank


_BANK = _gabor_bank()


# The garment occupies a different number of pixels in the 500x724 source than
# in a 768x1152 frame, so raw texture statistics would compare sampling rates
# rather than fabric. Every texture measurement is therefore taken after
# rescaling the garment bounding box to a fixed height.
WEAVE_REF_HEIGHT = 512


def _normalised_garment_patch(rgb, mask):
    """Garment bounding box, gaps filled with the region mean, rescaled to a
    fixed height so texture is measured at a comparable sampling rate."""
    m = mask > 0
    ys, xs = np.where(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    patch = g[y0:y1, x0:x1]
    pm = m[y0:y1, x0:x1]
    patch = np.where(pm, patch, float(patch[pm].mean()))

    scale = WEAVE_REF_HEIGHT / patch.shape[0]
    new_w = max(16, int(round(patch.shape[1] * scale)))
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    patch = cv2.resize(patch, (new_w, WEAVE_REF_HEIGHT), interpolation=interp)
    pm = cv2.resize(pm.astype(np.uint8), (new_w, WEAVE_REF_HEIGHT),
                    interpolation=cv2.INTER_NEAREST) > 0
    return patch, pm


def weave_descriptor(rgb, mask):
    """Thread-level texture signature, in three parts.

    gabor    normalised energy across 6 orientations x 3 scales -- the SHAPE of
             the texture, i.e. which directions and scales carry the weave.
    radial   normalised FFT radial profile -- how energy is spread over spatial
             frequency.
    hf       ABSOLUTE high-frequency energy ratio, deliberately not normalised
             away. This is the one that catches handloom being rendered as flat
             plastic-looking fabric: the colour stays perfectly correct while
             the fine thread detail simply disappears.
    """
    m = mask > 0
    if m.sum() < 100:
        return np.zeros(len(_BANK) + 8 + 1, dtype=np.float32)

    patch, pm = _normalised_garment_patch(rgb, mask)

    gab = np.array([float(np.abs(cv2.filter2D(patch, cv2.CV_32F, k))[pm].mean())
                    for k in _BANK], dtype=np.float32)
    gab /= max(float(gab.sum()), 1e-8)

    win = np.outer(np.hanning(patch.shape[0]), np.hanning(patch.shape[1]))
    spec = np.abs(np.fft.fftshift(np.fft.fft2(patch * win))) ** 2
    cy, cx = np.array(spec.shape) // 2
    yy, xx = np.ogrid[:spec.shape[0], :spec.shape[1]]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    rmax = float(r.max())

    radial = []
    for lo, hi in zip(np.linspace(0, 0.8, 8), np.linspace(0.1, 0.9, 8)):
        band = spec[(r >= rmax * lo) & (r < rmax * hi)]
        radial.append(float(band.mean()) if band.size else 0.0)
    radial = np.array(radial, dtype=np.float32)
    radial /= max(float(radial.sum()), 1e-8)

    total = float(spec.sum())
    hf = float(spec[r >= 0.25 * rmax].sum()) / max(total, 1e-8)

    return np.concatenate([gab, radial, np.array([hf], dtype=np.float32)])


def weave_distance(a, b):
    """Distance between weave descriptors, 0 = identical texture.

    Cosine was tried first and proved useless here: every descriptor component
    is non-negative, so all descriptors point into the same orthant and the
    cosine distance collapsed to ~0.0001 across an entire clip. Distribution
    distances are used instead, plus a relative comparison of the absolute
    high-frequency term.
    """
    n = len(_BANK)
    if a.size < n + 9 or b.size < n + 9:
        return 1.0

    gab_d = 0.5 * float(np.abs(a[:n] - b[:n]).sum())            # L1/2 on a simplex -> [0,1]
    rad_d = 0.5 * float(np.abs(a[n:n + 8] - b[n:n + 8]).sum())  # ditto
    hf_a, hf_b = float(a[-1]), float(b[-1])
    hf_d = min(1.0, abs(hf_a - hf_b) / max(hf_a, 1e-6))

    return float(np.clip(0.40 * gab_d + 0.25 * rad_d + 0.35 * hf_d, 0.0, 1.0))


def weave_hf_ratio(descriptor):
    """The absolute high-frequency term, exposed for reporting."""
    return float(descriptor[-1]) if descriptor.size else 0.0


# ------------------------------------------------- aligned patch / weave guard
def find_border_patch(rgb, mask, size=128):
    """Pick the most texture-dense square inside the product mask.

    On a saree this lands on the border or pallu motif; on a printed kurti or
    dress it lands on the densest print. It is deliberately not told what a
    product looks like -- it only looks for detail.

    The first version scored boxes by the MEAN OF SQUARED LAPLACIAN, and that
    turned out to be the wrong statistic: squaring lets a handful of extreme
    pixels dominate, so a box containing one hard seam or fold edge but
    otherwise blank fabric beat a box of broad, even print. On a white kurti
    with printed panels it selected plain white cloth next to a single edge.

    Two changes fix it, and both are about being outlier-resistant:

      COVERAGE   what fraction of the box carries detail, thresholded against
                 this product's own texture distribution. Broad print wins;
                 one edge in an otherwise empty box does not.
      STRENGTH   mean gradient magnitude, capped at the 98th percentile so a
                 single very strong edge cannot inflate the average.

    Coverage is weighted higher because "most of this square is patterned" is
    what actually makes a good visual reference.
    """
    m = mask > 0
    if m.sum() < 16:
        return None

    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)

    vals = mag[m]
    detail_thr = float(np.percentile(vals, 60))
    cap = float(np.percentile(vals, 98))

    detail = ((mag >= detail_thr) & m).astype(np.float32)
    capped = np.minimum(mag, cap) * m.astype(np.float32)

    box = (size, size)
    coverage = cv2.boxFilter(detail, cv2.CV_32F, box, normalize=True)
    strength = cv2.boxFilter(capped, cv2.CV_32F, box, normalize=True)
    cov = cv2.boxFilter(m.astype(np.float32), cv2.CV_32F, box, normalize=True)

    peak = float(strength.max())
    strength_n = strength / peak if peak > 1e-6 else strength
    score = 0.65 * coverage + 0.35 * strength_n

    score[cov < 0.95] = 0                 # the patch must sit fully on product
    h, w = score.shape
    half = size // 2
    score[:half, :] = 0
    score[h - half:, :] = 0
    score[:, :half] = 0
    score[:, w - half:] = 0
    if float(score.max()) <= 0:
        return None
    cy, cx = np.unravel_index(int(np.argmax(score)), score.shape)
    return (int(cx - half), int(cy - half), size, size)


def aligned_ssim(src_patch, frame_rgb, frame_mask=None):
    """Locate the source border patch inside the frame by template matching,
    then compute SSIM on the aligned crop.

    Returns (ssim, match_confidence, located_box). Confidence matters: if the
    motif genuinely is not present any more, the best match is a poor one, and
    a low-confidence high SSIM must not be read as a pass.
    """
    sg = cv2.cvtColor(src_patch, cv2.COLOR_RGB2GRAY)
    fg = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

    # The search MUST be confined to the garment. Without this the matcher
    # happily locks onto a smooth patch of background wall or foliage, which
    # produces a meaningless SSIM and a Weave Guard image showing scenery
    # instead of fabric.
    valid = None
    if frame_mask is not None and (frame_mask > 0).any():
        valid = (frame_mask > 0).astype(np.uint8)

    best_conf, best_loc, best_shape = -1.0, None, None
    for scale in (0.6, 0.75, 0.9, 1.0, 1.15, 1.35, 1.6):
        t = cv2.resize(sg, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        th, tw = t.shape
        if th >= fg.shape[0] or tw >= fg.shape[1]:
            continue
        res = cv2.matchTemplate(fg, t, cv2.TM_CCOEFF_NORMED)

        if valid is not None:
            # A candidate is only allowed where the template window sits almost
            # entirely on garment pixels.
            cov = cv2.boxFilter(valid.astype(np.float32), -1, (tw, th),
                                normalize=True, borderType=cv2.BORDER_CONSTANT)
            # boxFilter is centre-anchored; matchTemplate results are top-left
            # anchored, so line them up before using the coverage map.
            cov = cov[th // 2: th // 2 + res.shape[0], tw // 2: tw // 2 + res.shape[1]]
            if cov.shape != res.shape:
                cov = cv2.resize(cov, (res.shape[1], res.shape[0]))
            res = np.where(cov >= 0.90, res, -1.0)
            if float(res.max()) <= -1.0:
                continue

        _, mx, _, loc = cv2.minMaxLoc(res)
        if mx > best_conf:
            best_conf, best_loc, best_shape = float(mx), loc, t.shape
    if best_loc is None:
        return 0.0, 0.0, None
    x, y = best_loc
    crop = fg[y:y + best_shape[0], x:x + best_shape[1]]
    if crop.shape != best_shape:
        return 0.0, best_conf, None
    tmpl = cv2.resize(sg, (best_shape[1], best_shape[0]), interpolation=cv2.INTER_AREA)
    s = float(ssim_fn(tmpl, crop, data_range=255))
    return s, best_conf, (int(x), int(y), int(best_shape[1]), int(best_shape[0]))
