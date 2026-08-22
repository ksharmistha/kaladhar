"""Input validation for uploaded product images.

Rejects what genuinely cannot be used; warns about what will degrade quality
but is still workable. The distinction matters -- our own Kaladhar sample is
500x724, which is below the resolution we would like but is still usable, so a
naive minimum-resolution rule would reject the very image the project is built
around.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageFile, UnidentifiedImageError

from kaladhar.config import (ALLOWED_FORMATS, EXPECTED_ASPECT_RANGE, MAX_FILE_BYTES,
                             MAX_PIXELS, MIN_SHORT_EDGE, WARN_SHORT_EDGE)

ImageFile.LOAD_TRUNCATED_IMAGES = False   # we want truncated files to fail loudly


@dataclass
class ValidationReport:
    ok: bool = True
    path: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    def error(self, msg: str) -> None:
        self.errors.append(msg)
        self.ok = False

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "path": self.path, "errors": self.errors,
                "warnings": self.warnings, "info": self.info}

    def render(self) -> str:
        lines = [f"{'PASS' if self.ok else 'REJECT'}  {Path(self.path).name}"]
        for k, v in self.info.items():
            lines.append(f"    {k}: {v}")
        for e in self.errors:
            lines.append(f"    ERROR   {e}")
        for w in self.warnings:
            lines.append(f"    WARNING {w}")
        return "\n".join(lines)


def validate_image(path: str | Path) -> ValidationReport:
    r = ValidationReport(path=str(path))
    p = Path(path)

    if not p.exists():
        r.error("File does not exist.")
        return r
    if not p.is_file():
        r.error("Path is not a file.")
        return r

    size = p.stat().st_size
    r.info["file_size"] = f"{size/1024:.1f} KB"
    if size == 0:
        r.error("File is empty (0 bytes).")
        return r
    if size > MAX_FILE_BYTES:
        r.error(f"File is {size/1e6:.1f} MB, over the {MAX_FILE_BYTES/1e6:.0f} MB limit.")
        return r

    # Two-pass open: verify() detects corruption but leaves the object unusable,
    # so the file has to be reopened afterwards to actually read pixels.
    try:
        with Image.open(p) as probe:
            probe.verify()
    except UnidentifiedImageError:
        r.error("Not a recognisable image file, or the format is unsupported.")
        return r
    except Exception as exc:
        r.error(f"Image is corrupt or truncated ({type(exc).__name__}: {exc}).")
        return r

    try:
        im = Image.open(p)
        fmt = (im.format or "?").upper()
        w, h = im.size
        mode = im.mode
        im.load()          # forces a full decode -- catches truncation verify() misses
    except Exception as exc:
        r.error(f"Image header parsed but pixel data failed to decode ({exc}).")
        return r

    r.info["format"] = fmt
    r.info["dimensions"] = f"{w}x{h}"
    r.info["mode"] = mode
    r.info["megapixels"] = round(w * h / 1e6, 2)

    if fmt not in ALLOWED_FORMATS:
        r.error(f"Format {fmt} is not supported. Allowed: {', '.join(sorted(ALLOWED_FORMATS))}.")
    if w * h > MAX_PIXELS:
        r.error(f"Image is {w*h/1e6:.0f} MP, over the {MAX_PIXELS/1e6:.0f} MP safety limit.")

    short = min(w, h)
    if short < MIN_SHORT_EDGE:
        r.error(f"Short edge is {short}px, below the {MIN_SHORT_EDGE}px minimum. "
                "Too little detail to assess weave or border accurately.")
    elif short < WARN_SHORT_EDGE:
        r.warn(f"Short edge is {short}px (under {WARN_SHORT_EDGE}px). Usable, but weave-texture "
               "scoring will be limited by source detail, not by the generated clip.")

    aspect = w / h
    r.info["aspect"] = f"{aspect:.3f}"
    lo, hi = EXPECTED_ASPECT_RANGE
    if aspect > 1.0:
        r.warn(f"Landscape image (aspect {aspect:.2f}). Fashion product shots are normally portrait; "
               "the 9:16 export will crop or pad heavily.")
    elif not (lo <= aspect <= hi):
        r.warn(f"Aspect {aspect:.2f} is outside the usual portrait range {lo}-{hi}.")

    if mode not in ("RGB", "RGBA", "L"):
        r.warn(f"Colour mode {mode} will be converted to RGB.")
    if mode == "L":
        r.warn("Image is greyscale. Colour-drift scoring (dE2000) will be meaningless.")

    return r
