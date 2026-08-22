"""Visual evidence for the Fidelity Lock.

Two artifacts:

  drift_plot   the per-frame Fidelity Score and its component metrics across a
               clip. This is the artifact that turns the Milestone 1 finding
               ("the drift is local and transient, a human checking one frame
               would miss it") from a claim into something you can point at.

  weave_guard  a magnified side-by-side of the border/pallu motif, source
               against the worst-scoring frame. For a handloom brand the weave
               is the product, so this is the most legible check there is.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import matplotlib
import numpy as np
from PIL import Image, ImageDraw

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def drift_plot(score, out_path, threshold=None, title=None):
    """Per-frame fidelity and components. Returns the path written."""
    ok = [f for f in score["per_frame"] if f.get("found")]
    if not ok:
        raise ValueError("nothing scorable to plot")

    t = [f["t"] for f in ok]
    fid = [f["fidelity"] for f in ok]
    de = [f["delta_e2000"] for f in ok]
    wv = [f["weave_distance"] for f in ok]
    cl = [f["clip_cosine"] for f in ok]

    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True,
                             gridspec_kw={"height_ratios": [2.2, 1, 1, 1]})
    name = title or Path(score["clip"]).stem

    ax = axes[0]
    ax.plot(t, fid, color="#12343b", lw=2.2, marker="o", ms=3.5)
    ax.fill_between(t, fid, min(fid) - 4, color="#12343b", alpha=0.07)
    worst = score["worst_frame"]
    ax.axvline(worst["t"], color="#c0392b", ls="--", lw=1.2, alpha=0.8)
    ax.annotate("worst frame\nt=%.2fs  score %.1f" % (worst["t"], worst["fidelity"]),
                xy=(worst["t"], worst["fidelity"]),
                xytext=(worst["t"] + 0.25, worst["fidelity"] + 4),
                fontsize=9, color="#c0392b",
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1))
    if threshold is not None:
        ax.axhline(threshold, color="#e67e22", ls=":", lw=1.6)
        ax.text(t[0], threshold + 0.6, "pass threshold %.1f" % threshold,
                fontsize=8, color="#e67e22")
    ax.set_ylabel("Fidelity Score (0-100)")
    ax.set_title("Product fidelity per frame  -  %s\nmean %.1f   min %.1f   std %.1f"
                 % (name, score["fidelity_mean"], score["fidelity_min"],
                    score["fidelity_std"]), fontsize=11)
    ax.grid(alpha=0.25)

    for axis, series, label, colour, note in (
        (axes[1], de, "dE2000 (colour)", "#2980b9", "higher = more colour drift"),
        (axes[2], wv, "weave distance", "#8e44ad", "higher = texture lost"),
        (axes[3], cl, "CLIP cosine (identity)", "#27ae60", "lower = different garment"),
    ):
        axis.plot(t, series, color=colour, lw=1.8, marker=".", ms=4)
        axis.axvline(worst["t"], color="#c0392b", ls="--", lw=1, alpha=0.5)
        axis.set_ylabel(label, fontsize=9)
        axis.grid(alpha=0.25)
        axis.text(0.995, 0.06, note, transform=axis.transAxes, fontsize=7.5,
                  ha="right", color="#666")

    axes[-1].set_xlabel("time (seconds)")
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def weave_guard(source_patch, score, clip_path, out_path, zoom=4):
    """Magnified motif comparison: source vs the worst-scoring frame.

    The frame crop is taken from the location the template matcher actually
    aligned to, so the two panels show the same piece of the garment.
    """
    from kaladhar.video.io import sample_frames

    worst_idx = score["worst_frame"]["frame"]
    frames = dict(sample_frames(clip_path, stride=1, max_frames=None))
    frame = frames.get(worst_idx)
    if frame is None:
        raise ValueError("worst frame %s not found in clip" % worst_idx)

    rec = next((f for f in score["per_frame"] if f.get("frame") == worst_idx), None)
    box = rec.get("ssim_box") if rec else None
    fr = np.asarray(frame.convert("RGB"))
    if box:
        x, y, w, h = box
        crop = fr[max(0, y):y + h, max(0, x):x + w]
    else:
        crop = fr[:128, :128]

    sp = np.asarray(Image.fromarray(source_patch).convert("RGB"))
    size = 320
    a = cv2.resize(sp, (size, size), interpolation=cv2.INTER_NEAREST)
    b = cv2.resize(crop, (size, size), interpolation=cv2.INTER_NEAREST)

    pad, top = 16, 46
    canvas = Image.new("RGB", (size * 2 + pad * 3, size + top + pad + 46), (255, 255, 255))
    canvas.paste(Image.fromarray(a), (pad, top))
    canvas.paste(Image.fromarray(b), (pad * 2 + size, top))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 10), "WEAVE GUARD  -  product texture detail, magnified", fill=(0, 0, 0))
    d.text((pad, 28), "SOURCE (reference)", fill=(0, 0, 0))
    d.text((pad * 2 + size, 28), "GENERATED  frame %d  (t=%.2fs, worst)"
           % (worst_idx, score["worst_frame"]["t"]), fill=(0, 0, 0))
    conf = rec.get("ssim_confidence", 0)
    d.text((pad, size + top + 8),
           "SSIM %.3f at match confidence %.2f   |   weave distance %.3f   |   dE2000 %.2f"
           % (rec.get("ssim", 0), conf, rec.get("weave_distance", 0),
              rec.get("delta_e2000", 0)),
           fill=(60, 60, 60))

    # State what a weak match actually means, so the panel is not over-read. The
    # search is confined to the garment, so a low-confidence result means the
    # motif could not be found ON THE FABRIC -- which is itself the finding.
    verdict = ("Motif located on the garment with reasonable confidence."
               if conf >= 0.60 else
               "Motif could NOT be confidently located anywhere on the garment in this "
               "frame. The panel shows the closest fabric region found.")
    d.text((pad, size + top + 22), verdict, fill=(150, 40, 30) if conf < 0.60 else (60, 60, 60))
    d.rectangle([pad - 1, top - 1, pad + size, top + size], outline=(0, 0, 0))
    d.rectangle([pad * 2 + size - 1, top - 1, pad * 2 + size * 2, top + size],
                outline=(192, 57, 43))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return out_path
