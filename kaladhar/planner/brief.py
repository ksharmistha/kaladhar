"""Turning a matrix point into a ready-to-paste Ekly generation brief.

The prompt structure is not invented here -- it is the structure that was
actually validated in the Milestone 1 prototype: scene first, then explicit
camera direction, then an uppercase PRODUCT ACCURACY block naming every
property that must be preserved, then explicit negative guidance.

That prototype held garment colour strongly and kept the woven border broadly
recognisable, so the shape of the prompt is treated as proven and only the
scene-dependent parts vary.

PRODUCT AGNOSTIC. Nothing here is hardcoded to a saree. The product noun is
supplied per run, and a small vocabulary supplies the construction details
worth naming for that garment type. Unknown products fall back to generic
garment terms rather than failing or silently saying "saree".
"""
from __future__ import annotations

from kaladhar.planner.matrix import AXES, AXIS_ORDER

# Construction details worth naming explicitly for each garment type. These are
# the features a generative model most often reinvents, so the prompt calls them
# out by name. Anything not listed falls back to DEFAULT_DETAILS.
PRODUCT_DETAILS = {
    "saree": "the pallu, border motif, pleats and the way the drape falls",
    "lehenga": "the blouse, dupatta, skirt flare, hem border and waistband",
    "kurti": "the neckline, placket, sleeve length, side slits, hem and print placement",
    "kurta": "the collar, placket, sleeve length, side slits and hem",
    "salwar kameez": "the neckline, sleeve length, hem, dupatta and print placement",
    "anarkali": "the yoke, flare, sleeve length, hem border and neckline",
    "dupatta": "the border, motif placement, weave and the way it drapes",
    "dress": "the neckline, sleeves, waistline, hem and overall silhouette",
    "gown": "the neckline, bodice structure, sleeves, train and overall silhouette",
    "shirt": "the collar, placket, buttons, cuffs, yoke and fit",
    "blouse": "the neckline, sleeve length, back design and fit",
    "top": "the neckline, sleeve length, hem and fit",
    "jacket": "the lapels, buttons, pockets, cuffs and cut",
    "skirt": "the waistband, pleats, flare, hem and length",
    "dress material": "the print placement, motif scale, border and fabric fall",
    "fabric": "the weave, print placement, motif scale and border",
}
DEFAULT_DETAILS = ("the neckline, sleeves, hem, seams, fastenings and overall "
                   "silhouette")

# How the fabric should be described moving. Kept per product because "the pallu
# drifts" is meaningless on a shirt.
PRODUCT_MOTION = {
    "saree": "the pallu drifts gently",
    "lehenga": "the dupatta and skirt flare move gently",
    "dupatta": "it drifts gently",
    "anarkali": "the flare moves gently",
    "gown": "the skirt moves gently",
    "dress": "the skirt moves gently",
    "skirt": "the skirt moves gently",
}
DEFAULT_MOTION = "the fabric falls and moves with her"

# Neutral fallback when no product type is declared. Deliberately NOT "saree":
# an unspecified product must not be silently relabelled as the client's
# best-known category, because that would put a false product noun into every
# prompt and into the operator sheet without anyone choosing it.
DEFAULT_PRODUCT = "garment"


def product_details(product_noun):
    return PRODUCT_DETAILS.get(product_noun.strip().lower(), DEFAULT_DETAILS)


def product_motion(product_noun):
    return PRODUCT_MOTION.get(product_noun.strip().lower(), DEFAULT_MOTION)


def accuracy_block(product_noun):
    """The uppercase preservation block, generic over product type.

    Every fidelity requirement from the original saree-specific block is kept:
    colour, dye tone, pattern, texture and construction must not change, and
    only background, lighting and camera may vary.
    """
    return (
        "PRODUCT ACCURACY - CRITICAL: The %s must remain EXACTLY as in the "
        "reference image. Preserve the exact colour, dye tone, pattern, print "
        "placement, motif scale, fabric texture, weave, silhouette, construction "
        "and %s. Do not redesign, restyle, recolour, embellish, resize or replace "
        "the %s or any part of it. Only the background, lighting and camera may "
        "change." % (product_noun, product_details(product_noun), product_noun)
    )


def negative_guidance(product_noun):
    return (
        "Avoid: changing the %s colour, pattern, texture or construction; "
        "substituting a different garment; adding logos or text; distorted hands "
        "or face; flickering fabric; warped patterns; extra limbs."
        % product_noun
    )


def _value(axis, vid):
    for v in AXES[axis]:
        if v.id == vid:
            return v
    raise KeyError("%s=%s" % (axis, vid))


def render_brief(point, index, product_noun=DEFAULT_PRODUCT):
    product_noun = (product_noun or "garment").strip().lower()
    env = _value("environment", point["environment"])
    lig = _value("lighting", point["lighting"])
    cam = _value("camera", point["camera"])
    con = _value("concept", point["concept"])
    gra = _value("grade", point["grade"])

    prompt = (
        "A model wearing the exact %s from the reference image stands in %s. "
        "The scene is lit by %s. %s She moves naturally and %s. "
        "%s %s Cinematic premium fashion advertisement, shallow depth "
        "of field on the background only, vertical 9:16 framing."
        "\n\n%s\n\n%s"
    ) % (product_noun, env.prompt, lig.prompt, cam.prompt,
         product_motion(product_noun), con.prompt, gra.prompt,
         accuracy_block(product_noun), negative_guidance(product_noun))

    return {
        "id": "V%02d" % index,
        "product": product_noun,
        "axes": dict(point),
        "axis_labels": {
            "environment": env.label,
            "lighting": lig.label,
            "camera": cam.label,
            "concept": con.label,
            "grade": gra.label,
        },
        "prompt": prompt,
        "ekly_settings": {
            "model": "Kling AI Video Pro",
            "reference_image": "input/reference.png",
            "aspect": "9:16",
            "duration_s": 5,
            "quality": "standard",
            # Measured on our one real generation, not an estimate.
            "expected_credits": 45.50,
        },
    }


def build_briefs(points, product_noun=DEFAULT_PRODUCT):
    return [render_brief(p, i + 1, product_noun) for i, p in enumerate(points)]


def as_operator_sheet(briefs, run_id, reference_path):
    """The handoff document a human actually works from at the Ekly web UI.

    Ekly exposes no API to us, so this sheet IS the interface between our
    pipeline and generation. It is written to be worked through top to bottom
    with copy and paste, and it records what to bring back.
    """
    total = sum(b["ekly_settings"]["expected_credits"] for b in briefs)
    product = briefs[0].get("product", "garment") if briefs else "garment"
    bar = "=" * 78
    lines = [
        bar,
        "EKLY GENERATION SHEET - run %s" % run_id,
        bar,
        "",
        "Product type declared for this run: %s" % product.upper(),
        "",
        "MANUAL STEP. Ekly.ai exposes no API to us, so these briefs are generated",
        "by hand through the Ekly web interface. The pipeline is paused at state",
        "AWAITING_CLIPS until the finished clips are imported back.",
        "",
        "Reference image to attach via [+ ref image]:",
        "    %s" % reference_path,
        "",
        "Briefs: %d     Expected credit cost: %.2f" % (len(briefs), total),
        "  (45.50 per generation, measured on our Milestone 1 run)",
        "",
        "For each brief below:",
        "  1. Ekly -> Video -> model Kling AI Video Pro",
        "  2. Attach the reference image above via [+ ref image]",
        "  3. Set 9:16, 5 seconds, standard quality",
        "  4. Paste the PROMPT block verbatim",
        "  5. Generate, then download the clip under the FILENAME given",
        "  6. Note the wall-clock generation time in the box provided",
        "",
        "NOTE: in our Milestone 1 run the 9:16 setting still returned a 768x1152",
        "(2:3) file. Do not assume the setting applied. Every clip is re-probed",
        "on import and converted to 1080x1920 at export.",
        "",
    ]
    for b in briefs:
        axes_line = "  |  ".join(
            "%s=%s" % (k, b["axis_labels"][k]) for k in AXIS_ORDER)
        lines += [
            "-" * 78,
            "BRIEF %s" % b["id"],
            "-" * 78,
            "  Axes: " + axes_line,
            "  Save downloaded clip as:  %s.mp4" % b["id"],
            "  Wall-clock generation time: ______ s   (please record)",
            "",
            "  PROMPT (copy everything between the markers)",
            "  >>>>>>>>",
            b["prompt"],
            "  <<<<<<<<",
            "",
        ]
    lines += [
        bar,
        "WHEN DONE: put the downloaded .mp4 files in a folder and run",
        "    python cli.py import-clips --run %s --dir <folder>" % run_id,
        bar,
    ]
    return "\n".join(lines)
