"""Stage A -- Product Image Input & Processing.

Maps to the GigPoint task: "Build image upload/input handling, validation,
background preparation, resizing and preprocessing."

Turns an arbitrary uploaded photo into the validated, normalised asset set that
every downstream stage consumes. Everything expensive happens exactly once here
and is cached in the run directory.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PIL import Image

from kaladhar.input.preprocess import build_reference_image, normalise
from kaladhar.input.segment import overlay, segment
from kaladhar.input.signature import build_signature
from kaladhar.input.validate import validate_image
from kaladhar.storage.run import Run


class IngestError(RuntimeError):
    pass


def ingest(source, run=None, run_id=None):
    """Validate, normalise, segment and fingerprint a product image.

    Raises IngestError if validation rejects the file -- downstream stages are
    never handed an image we already know is unusable.
    """
    t_all = time.perf_counter()
    run = run or Run.create(run_id)
    src = Path(source)

    # ---------------------------------------------------------- 1. validate
    t = time.perf_counter()
    report = validate_image(src)
    run.write_json("input/validation.json", report.as_dict())
    run.record_timing("validate", time.perf_counter() - t)
    if not report.ok:
        run.set_state("CREATED", "rejected at validation")
        raise IngestError("Image rejected:\n" + report.render())

    run.ingest(src, "input/original" + src.suffix.lower())

    # ------------------------------------------------------- 2. preprocess
    t = time.perf_counter()
    working = normalise(src)
    working.save(run.path("input/working.png"))
    run.record_timing("preprocess", time.perf_counter() - t)

    # -------------------------------------------------------- 3. segment
    t = time.perf_counter()
    masks = segment(working)
    Image.fromarray(masks.garment).save(run.path("input/mask_garment.png"))
    Image.fromarray(masks.subject).save(run.path("input/mask_subject.png"))
    overlay(working, masks.garment).save(run.path("evidence/mask_garment_overlay.png"))
    overlay(working, masks.subject, colour=(0, 128, 255)).save(
        run.path("evidence/mask_subject_overlay.png"))
    run.record_timing("segment", time.perf_counter() - t)

    # Built from the subject mask, so it must follow segmentation: product and
    # person isolated onto neutral grey, background removed entirely.
    reference = build_reference_image(working, subject_mask=masks.subject)
    reference.save(run.path("input/reference.png"))

    if masks.garment_fraction < 0.02:
        raise IngestError(
            "Garment mask covers under 2% of the frame -- segmentation failed. "
            "Try an image where the product is larger in frame.")

    # ------------------------------------------------------- 4. signature
    t = time.perf_counter()
    sig, art = build_signature(working, masks.garment)
    run.write_json("input/signature.json", sig)
    if art["border_patch"] is not None:
        art["border_patch"].save(run.path("input/border_patch.png"))
        art["border_patch"].resize((512, 512), Image.NEAREST).save(
            run.path("evidence/weave_guard_source.png"))
    art["clip_input"].save(run.path("evidence/clip_input_masked.png"))
    run.record_timing("signature", time.perf_counter() - t)

    # ------------------------------------------------------------ 5. persist
    run.meta["source"] = {
        "original_name": src.name,
        "validation": report.as_dict(),
        "working_size": list(working.size),
        "reference_size": list(reference.size),
        "mask": {
            "subject_fraction": round(masks.subject_fraction, 4),
            "garment_fraction": round(masks.garment_fraction, 4),
            "notes": masks.notes,
        },
        "palette_hex": sig["palette_rgb_preview"],
        "border_patch_box": sig["border_patch_box"],
    }
    run.record_timing("ingest_total", time.perf_counter() - t_all)
    run.set_state("PREPROCESSED", f"ingested {src.name}")
    return run


def summary(run):
    s = run.meta.get("source", {})
    v = s.get("validation", {})
    m = s.get("mask", {})
    lines = [
        f"Run            {run.run_id}",
        f"State          {run.meta['state']}",
        f"Source         {s.get('original_name')}  {v.get('info', {}).get('dimensions')}"
        f"  {v.get('info', {}).get('format')}",
        f"Working size   {s.get('working_size')}",
        f"Reference size {s.get('reference_size')}   -> input/reference.png (attach in Ekly)",
        f"Subject mask   {m.get('subject_fraction', 0)*100:.1f}% of frame",
        f"Garment mask   {m.get('garment_fraction', 0)*100:.1f}% of frame",
        f"Palette        {'  '.join(s.get('palette_hex', []))}",
        f"Border patch   {s.get('border_patch_box')}",
    ]
    for w in v.get("warnings", []):
        lines.append(f"  WARNING  {w}")
    for n in m.get("notes", []):
        lines.append(f"  NOTE     {n}")
    t = run.meta.get("timings", {})
    lines.append("Timings (s)    " + "  ".join(f"{k}={v}" for k, v in t.items()))
    return "\n".join(lines)
