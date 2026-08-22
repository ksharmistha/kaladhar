"""Central configuration for the Kaladhar ad-variation pipeline.

Everything the rest of the package needs to agree on lives here. Values marked
CALIBRATE are deliberately provisional -- see the note on thresholds below.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
RUNS = ROOT / "runs"
EVIDENCE = ROOT / "evidence"

# ---------------------------------------------------------------- input rules
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}
MIN_SHORT_EDGE = 400          # hard reject below this -- too little detail to score weave
WARN_SHORT_EDGE = 800         # accepted, but flagged: source detail limits weave analysis
MAX_PIXELS = 50_000_000       # decompression-bomb guard
MAX_FILE_BYTES = 40 * 1024 * 1024

# Portrait is expected for fashion product shots. Landscape is accepted with a
# warning because the 9:16 export will have to crop or pad aggressively.
EXPECTED_ASPECT_RANGE = (0.5, 0.9)   # width / height

# ------------------------------------------------------------- working sizes
WORKING_LONG_EDGE = 1152      # matches the generator's native output height
REFERENCE_LONG_EDGE = 1152    # image handed to Ekly as the reference image

# ------------------------------------------------------------- export target
EXPORT_W, EXPORT_H = 1080, 1920      # client requirement: 9:16
EXPORT_ASPECT = EXPORT_W / EXPORT_H  # 0.5625

# --------------------------------------------------------------- generation
# Facts measured from our one real generation. Do not add numbers here that
# were not actually observed.
OBSERVED = {
    "model": "Kling AI Video Pro (via Ekly.ai web UI)",
    "credits_per_generation": 45.50,
    "output_w": 768,
    "output_h": 1152,
    "duration_s": 5.10,
    "fps": 30,
    "codec": "h264",
    "file_mb": 12.31,
    "wall_clock_s": None,        # NOT RECORDED -- measure on the next generation
}

# --------------------------------------------------------------- thresholds
# NOT VALIDATED. No metric had ever been computed at the time this pipeline was
# written, so these start as None and are filled in by calibrate.py from the
# real clips we actually have. Any report that prints a threshold must also
# print the sample size it was calibrated from.
THRESHOLDS_CALIBRATED = False
FIDELITY_PASS = None           # set by calibration

# Frame sampling for per-frame scoring. Scoring all 153 frames is wasteful;
# every 5th frame still resolves the transient drift we observed.
FRAME_STRIDE = 5

CLIP_ONNX_REPO = "Qdrant/clip-ViT-B-32-vision"
