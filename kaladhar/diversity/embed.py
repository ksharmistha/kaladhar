"""CLIP image embeddings via ONNX Runtime.

We use the vision tower only (Qdrant/clip-ViT-B-32-vision, 512-d output). No
text encoder is needed: every question we ask is image-to-image -- "is this
still the same saree?" and "is this clip different enough from that one?".

Running through onnxruntime rather than PyTorch is a deliberate choice: the
machine is on Python 3.14, and a ~350 MB ONNX file loads in seconds where a
torch install is multiple GB. onnxruntime was already present.
"""
from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
from PIL import Image

from kaladhar.config import CLIP_ONNX_REPO

# CLIP's published preprocessing constants (preprocessor_config.json).
_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
_SIZE = 224


@lru_cache(maxsize=1)
def _session():
    import onnxruntime as ort
    from huggingface_hub import snapshot_download
    path = os.path.join(snapshot_download(CLIP_ONNX_REPO), "model.onnx")
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(path, opts, providers=["CPUExecutionProvider"])


def _preprocess(im: Image.Image) -> np.ndarray:
    """Resize shortest edge to 224 then centre-crop, as CLIP expects."""
    im = im.convert("RGB")
    w, h = im.size
    scale = _SIZE / min(w, h)
    im = im.resize((max(_SIZE, round(w * scale)), max(_SIZE, round(h * scale))), Image.BICUBIC)
    w, h = im.size
    left, top = (w - _SIZE) // 2, (h - _SIZE) // 2
    im = im.crop((left, top, left + _SIZE, top + _SIZE))
    a = np.asarray(im, dtype=np.float32) / 255.0
    a = (a - _MEAN) / _STD
    return a.transpose(2, 0, 1)


def embed(images, batch_size: int = 16) -> np.ndarray:
    """L2-normalised embeddings, shape (n, 512). Batched -- one session call
    per batch is markedly faster than one per image."""
    if isinstance(images, Image.Image):
        images = [images]
    if not images:
        return np.zeros((0, 512), dtype=np.float32)

    sess = _session()
    name = sess.get_inputs()[0].name
    out = []
    for i in range(0, len(images), batch_size):
        batch = np.stack([_preprocess(im) for im in images[i:i + batch_size]])
        vecs = sess.run(None, {name: batch})[0]
        out.append(vecs)
    v = np.concatenate(out).astype(np.float32)
    return v / np.clip(np.linalg.norm(v, axis=1, keepdims=True), 1e-8, None)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two normalised vectors."""
    return float(np.dot(a, b))
