"""Video probing, frame extraction and encoding.

ffmpeg is not installed system-wide on the build machine, so the static binary
that ships with imageio-ffmpeg is used instead. That keeps the project working
with no external install step. OpenCV handles decode for frame sampling because
it lets us seek and take every Nth frame without writing intermediates to disk.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(path):
    """Read real properties off the file.

    Every clip is probed on import rather than trusted, because in our
    Milestone 1 run the Ekly 9:16 setting still produced a 768x1152 (2:3) file.
    The setting is not evidence; the file is.
    """
    path = str(path)
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("Cannot open video: %s" % path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    info = {
        "path": path,
        "width": w,
        "height": h,
        "fps": round(fps, 3),
        "frame_count": n,
        "duration_s": round(n / fps, 3) if fps else None,
        "aspect": round(w / h, 4) if h else None,
        "file_mb": round(Path(path).stat().st_size / 1e6, 2),
    }
    info["is_9_16"] = abs(info["aspect"] - 0.5625) < 0.01 if info["aspect"] else False
    info["is_1080x1920"] = (w, h) == (1080, 1920)
    return info


def sample_frames(path, stride=5, max_frames=None):
    """Yield (frame_index, PIL.Image) every `stride` frames.

    Sampling rather than scoring all 153 frames is the single biggest speed
    lever in the pipeline, and it is safe here: the drift we are looking for
    lasts far longer than 1/6 of a second.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("Cannot open video: %s" % path)
    out = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % stride == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out.append((idx, Image.fromarray(rgb)))
            if max_frames and len(out) >= max_frames:
                break
        idx += 1
    cap.release()
    return out


def to_9_16(src, dst, mode="pad", width=1080, height=1920, crf=18):
    """Convert a clip to the required 1080x1920 / 9:16 delivery format.

    Two modes, because neither is free and the choice is a real trade-off on a
    vertical fashion shot:

      pad   -- fit the whole frame inside 1080x1920 and letterbox the sides.
               Nothing is lost. Costs screen area, and the bars are visible.
      crop  -- fill 1080x1920 and cut the overflow. Uses the full screen, but
               on a 768x1152 (2:3) source it removes about 16% of the width,
               which on a saree shot can clip the pallu or the border.

    pad is the default precisely because the product must not be misrepresented,
    and a cropped-off border is a misrepresentation.
    """
    src, dst = str(src), str(dst)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)

    if mode == "pad":
        vf = ("scale=%d:%d:force_original_aspect_ratio=decrease,"
              "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
              % (width, height, width, height))
    elif mode == "crop":
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,"
              "crop=%d:%d,setsar=1" % (width, height, width, height))
    else:
        raise ValueError("mode must be pad or crop")

    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-i", src,
           "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: %s" % r.stderr[-800:])
    return probe(dst)


def trim(src, dst, start_s, end_s, crf=18):
    """Cut [start_s, end_s] out of a clip.

    Re-encoded rather than stream-copied on purpose: a stream copy can only cut
    on keyframes, which would move the boundary by up to a second and defeat the
    point of trimming a precisely located bad section.
    """
    src, dst = str(src), str(dst)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    dur = max(0.0, float(end_s) - float(start_s))
    if dur <= 0:
        raise ValueError("trim window is empty")
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error",
           "-ss", "%.3f" % float(start_s), "-i", src, "-t", "%.3f" % dur,
           "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg trim failed: %s" % r.stderr[-800:])
    return probe(dst)


def motion_profile(path, stride=2, resize=256):
    """Frame-to-frame difference over the clip.

    Two failure modes matter for ad-readiness and they sit at opposite ends of
    this curve: a frozen clip (no motion at all, the generator ignored the
    camera direction) and a jitter/flicker clip (large erratic spikes).
    """
    cap = cv2.VideoCapture(str(path))
    prev, diffs, idx = None, [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % stride == 0:
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            g = cv2.resize(g, (resize, resize), interpolation=cv2.INTER_AREA)
            g = g.astype(np.float32) / 255.0
            if prev is not None:
                diffs.append(float(np.abs(g - prev).mean()))
            prev = g
        idx += 1
    cap.release()
    if not diffs:
        return {"mean": 0.0, "max": 0.0, "std": 0.0, "series": []}
    a = np.array(diffs, dtype=np.float32)
    return {
        "mean": float(a.mean()),
        "max": float(a.max()),
        "std": float(a.std()),
        "series": [round(float(x), 5) for x in a],
    }
