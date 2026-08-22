"""Tests for the claims this project actually makes.

Each test is here because a specific claim in the documentation would be false
if it failed.

Scope note: these are ALGORITHM-level tests on constructed or fixed inputs. They
prove the logic behaves as documented. They are deliberately separate from the
REAL-VIDEO measurements, which live in runs/run_m2_real and are reported in the
Milestone 2 documents. Where a test uses constructed vectors it says so, so the
two kinds of evidence are never confused.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kaladhar.diversity.select import (diversity_score, farthest_point_select,  # noqa: E402
                                       pairwise_cosine_distance)
from kaladhar.fidelity.lock import (colour_subscore, identity_subscore,  # noqa: E402
                                    structure_subscore, weave_subscore)
from kaladhar.fidelity.metrics import weave_descriptor, weave_distance  # noqa: E402
from kaladhar.input.validate import validate_image  # noqa: E402
from kaladhar.planner.matrix import AXIS_ORDER, axis_distance, is_coherent  # noqa: E402
from kaladhar.planner.sampler import MIN_AXIS_DIFF, sample  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "source" / "saree_source.jpg"


# ------------------------------------------------------------------ validation
def test_rejects_non_image():
    r = validate_image(ROOT / "cli.py")
    assert not r.ok
    assert r.errors


def test_rejects_missing_file():
    assert not validate_image(ROOT / "does_not_exist.jpg").ok


@pytest.mark.skipif(not SOURCE.exists(), reason="sample source image not present")
def test_accepts_real_source_with_low_res_warning():
    r = validate_image(SOURCE)
    assert r.ok
    # 500x724 is usable but below our preferred detail level; the warning is the
    # documented behaviour, so losing it would be a regression.
    assert any("Short edge" in w for w in r.warnings)


# --------------------------------------------------------------------- planner
def test_sampler_enforces_min_axis_difference():
    """The >=3-axes rule is the structural guarantee behind 'genuinely
    different, not filters'. It is enforced, not hoped for."""
    points, report = sample(n=6, seed=3)
    assert len(points) == 6
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            assert axis_distance(points[i], points[j]) >= MIN_AXIS_DIFF
    assert report["min_axis_diff_achieved"] >= MIN_AXIS_DIFF


def test_sampler_only_emits_coherent_scene_lighting_pairs():
    points, _ = sample(n=6, seed=11)
    assert all(is_coherent(p) for p in points)


def test_sampler_is_deterministic_for_a_seed():
    a, _ = sample(n=6, seed=5)
    b, _ = sample(n=6, seed=5)
    assert a == b


def test_every_brief_covers_all_five_axes():
    points, _ = sample(n=4, seed=2)
    for p in points:
        assert set(p) == set(AXIS_ORDER)


# ---------------------------------------------------------------- weave metric
@pytest.mark.skipif(not SOURCE.exists(), reason="sample source image not present")
def test_weave_metric_is_monotonic_under_blur():
    """The original cosine-based weave metric returned ~0.0001 for everything and
    was useless. This test exists so that failure cannot come back silently."""
    import cv2
    from PIL import Image

    img = np.asarray(Image.open(SOURCE).convert("RGB"))
    mask = np.full(img.shape[:2], 255, dtype=np.uint8)

    base = weave_descriptor(img, mask)
    dists = [weave_distance(base, weave_descriptor(cv2.GaussianBlur(img, (k, k), 0), mask))
             for k in (3, 5, 9, 15)]

    assert weave_distance(base, base) < 1e-6          # identical -> zero
    assert dists == sorted(dists)                     # worse blur -> larger distance
    assert dists[0] > 0.05                            # and it actually moves


@pytest.mark.skipif(not SOURCE.exists(), reason="sample source image not present")
def test_weave_metric_is_robust_to_rescaling():
    """Source and generated frames are different resolutions. If the metric
    reacted to sampling rate it would measure the wrong thing entirely."""
    import cv2
    from PIL import Image

    img = np.asarray(Image.open(SOURCE).convert("RGB"))
    mask = np.full(img.shape[:2], 255, dtype=np.uint8)
    base = weave_descriptor(img, mask)

    up = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    up_mask = np.full(up.shape[:2], 255, dtype=np.uint8)
    rescale_dist = weave_distance(base, weave_descriptor(up, up_mask))

    blur_dist = weave_distance(
        base, weave_descriptor(cv2.GaussianBlur(img, (5, 5), 0), mask))
    assert rescale_dist < blur_dist


# ------------------------------------------------------------------- subscores
def test_subscores_are_bounded_and_ordered():
    assert colour_subscore(0.0) == 100.0
    assert colour_subscore(100.0) == 0.0
    assert colour_subscore(3.0) > colour_subscore(8.0)

    assert weave_subscore(0.0) == 100.0
    assert weave_subscore(1.0) == 0.0

    assert identity_subscore(1.0) == 100.0
    assert identity_subscore(0.0) == 0.0
    assert identity_subscore(0.95) > identity_subscore(0.75)


def test_structure_subscore_refuses_low_confidence_matches():
    """A high SSIM against a bad template match is not evidence of anything."""
    assert structure_subscore(0.9, conf=0.1) == 0.0
    assert structure_subscore(0.9, conf=0.8) > 0.0


# --------------------------------------------------------------------- gate 2
def test_farthest_point_picks_one_per_cluster():
    """ALGORITHM-LEVEL TEST on constructed vectors.

    This proves the selection logic in isolation: given three tight clusters,
    max-min selection must take one from each rather than three from the same
    cluster. Real-video diversity is measured separately on the four actual
    generations and reported in the Milestone 2 documents.
    """
    rng = np.random.default_rng(0)
    centres = np.eye(3, 8, dtype=np.float32)
    vecs = []
    labels = []
    for ci, c in enumerate(centres):
        for _ in range(4):
            v = c + rng.normal(0, 0.02, size=8).astype(np.float32)
            vecs.append(v / np.linalg.norm(v))
            labels.append(ci)
    vecs = np.stack(vecs)

    idx, _ = farthest_point_select(vecs, k=3)
    assert len({labels[i] for i in idx}) == 3


def test_selection_raises_diversity_above_the_pool():
    rng = np.random.default_rng(1)
    centres = np.eye(4, 12, dtype=np.float32)
    vecs = []
    for c in centres:
        for _ in range(5):
            v = c + rng.normal(0, 0.03, size=12).astype(np.float32)
            vecs.append(v / np.linalg.norm(v))
    vecs = np.stack(vecs)

    idx, _ = farthest_point_select(vecs, k=4)
    assert diversity_score(vecs[idx]) > diversity_score(vecs)


def test_distance_matrix_is_symmetric_with_zero_diagonal():
    rng = np.random.default_rng(2)
    v = rng.normal(size=(6, 10)).astype(np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    d = pairwise_cosine_distance(v)
    assert np.allclose(d, d.T, atol=1e-5)
    assert np.allclose(np.diag(d), 0, atol=1e-5)


# --------------------------------------------------------------------- export
def test_export_target_is_9_16():
    from kaladhar.config import EXPORT_ASPECT, EXPORT_H, EXPORT_W
    assert (EXPORT_W, EXPORT_H) == (1080, 1920)
    assert abs(EXPORT_ASPECT - 0.5625) < 1e-6


# ------------------------------------------------------------------ safe cut
def _fake_score(fids, fps=30.0, stride=5):
    """Build a minimal score dict with a chosen per-frame fidelity series."""
    per = [{"found": True, "frame": i * stride, "t": round(i * stride / fps, 3),
            "fidelity": f} for i, f in enumerate(fids)]
    dur = round((len(fids) - 1) * stride / fps, 3)
    return {"per_frame": per, "info": {"duration_s": dur, "fps": fps},
            "fidelity_mean": sum(fids) / len(fids), "fidelity_min": min(fids),
            "clip": "fake.mp4"}


def test_safecut_declines_when_nothing_fails():
    from kaladhar.fidelity.safecut import analyse
    r = analyse(_fake_score([80] * 40), threshold=51.0)
    assert not r["applicable"]
    assert "nothing to cut" in r["reason"]


def test_safecut_declines_when_clip_fails_throughout():
    from kaladhar.fidelity.safecut import analyse
    r = analyse(_fake_score([30] * 40), threshold=51.0)
    assert not r["applicable"]
    assert "no contiguous passing window" in r["reason"]


def test_safecut_declines_when_window_too_short():
    """A recoverable window that is too short must leave the clip rejected
    rather than produce an unusably brief ad."""
    from kaladhar.fidelity.safecut import analyse
    fids = [80] * 6 + [30] * 34          # 6 frames at stride 5 = 0.83s of good footage
    r = analyse(_fake_score(fids), threshold=51.0)
    assert not r["applicable"]
    assert "under the 3.0s minimum" in r["reason"]


def test_safecut_picks_the_longest_contiguous_window():
    from kaladhar.fidelity.safecut import analyse
    # short good run, a failure, then a long good run
    fids = [80] * 5 + [30] * 3 + [80] * 32
    r = analyse(_fake_score(fids), threshold=51.0)
    assert r["applicable"]
    # the long tail run starts at index 8 -> frame 40 -> t = 1.333s
    assert r["start_s"] > 1.0
    assert r["kept_s"] >= 3.0


def test_safecut_unscored_frames_break_a_window():
    """A frame we could not measure cannot be claimed as clean."""
    from kaladhar.fidelity.safecut import analyse
    s = _fake_score([80] * 40)
    s["per_frame"][20]["found"] = False
    r = analyse(s, threshold=51.0, min_keep=1.0)
    # still no failing frames, so nothing to cut -- but the run is broken in two
    from kaladhar.fidelity.safecut import _passing_runs
    assert len(_passing_runs(s["per_frame"], 51.0)) == 2
