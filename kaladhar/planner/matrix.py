"""The five-axis orthogonal variation matrix.

The client complaint we are answering is that AI ad tools produce repetitive
output. The root cause is that people re-prompt the same idea with different
adjectives, which moves the render a little but not the concept. So variation
here is structural: every brief is a POINT IN A GRID, and the sampler is
required to move along at least three axes between any two chosen points.

Axis values carry their own prompt fragments, so a brief is assembled from the
grid rather than written by hand each time.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Value:
    id: str
    label: str
    prompt: str


ENVIRONMENT = [
    Value("mansion", "Luxury Mansion Interior",
          "the interior of a grand luxury mansion with polished white marble floors, "
          "a sweeping curved staircase and tall arched windows, in bright late-morning "
          "daylight that floods the hall and reflects off the marble"),
    Value("mandap", "Indian Wedding Mandap",
          "an ornate Indian wedding mandap at dusk, with four carved pillars, thick "
          "marigold garlands and deep red ceremonial drapes, lit by warm brass lamps "
          "against a darkening sky"),
    Value("palace", "Royal Palace Interior",
          "a royal palace hall in the evening, with frescoed archways, gilded "
          "mirrorwork on the walls and a large crystal chandelier casting warm pools "
          "of light across patterned stone"),
    Value("cafe", "Modern Luxury Cafe",
          "a modern luxury cafe at midday, with brass fittings, walnut panelling and "
          "marble tabletops, soft even daylight coming through floor-to-ceiling glass"),
    Value("resort", "Luxury Resort Terrace",
          "an open luxury resort terrace at golden hour, with a turquoise infinity "
          "pool, long palm shadows across pale stone and warm low sun coming off the "
          "sea behind her"),
    Value("rooftop", "City Rooftop at Night",
          "a city rooftop terrace at night, with a glass safety railing, the lit "
          "skyline and neon signage falling away into bokeh behind her, under cool "
          "blue ambient light"),
]

LIGHTING = [
    Value("softbox", "Softbox studio",
          "even soft studio lighting from a large frontal softbox with gentle "
          "wraparound shadow"),
    Value("golden", "Golden hour",
          "late golden-hour sunlight raking in from the left, warm and directional "
          "with long soft shadows"),
    Value("lamp", "Warm lamp",
          "warm practical lamp light from one side, intimate and low-key with a "
          "gentle falloff"),
    Value("overcast", "Overcast diffuse",
          "flat diffuse overcast daylight with no hard shadows and very even "
          "colour rendition"),
    Value("practical", "Festive practicals",
          "warm festive practical lights and candle glow scattered through the "
          "scene, sparkling highlights"),
    Value("highkey", "High-key luxury",
          "bright high-key lighting with clean bright tones and a luminous, "
          "airy feel"),
]

CAMERA = [
    Value("pushin", "Slow push-in",
          "The camera performs a slow smooth push-in from a full-body wide shot to "
          "a mid-shot, keeping the garment fully in frame."),
    Value("orbit", "Slow orbit",
          "The camera orbits slowly around her by a few degrees, revealing the "
          "drape from a changing angle."),
    Value("reveal", "Vertical reveal",
          "The camera tilts slowly upward from the hem to the shoulder in one "
          "continuous vertical reveal of the garment."),
    Value("static", "Static, subject moves",
          "The camera holds completely static in a full-body framing while she "
          "moves within the frame."),
    Value("rack", "Rack focus",
          "The camera holds its framing and racks focus from the background to the "
          "fabric, bringing the weave into sharp focus."),
    Value("parallax", "Parallax dolly",
          "The camera dollies laterally, creating parallax between her and the "
          "background while framing stays on the garment."),
]

CONCEPT = [
    Value("heritage_craft", "Heritage craft",
          "The mood is heritage handloom craftsmanship -- unhurried, artisanal and "
          "respectful of the weave."),
    Value("occasion", "Occasion / festive",
          "The mood is celebratory occasion-wear, joyful and full of festive "
          "energy."),
    Value("everyday", "Everyday elegance",
          "The mood is understated everyday elegance, natural and effortless."),
    Value("gifting", "Gifting",
          "The mood is a considered gift -- warm, personal and quietly premium."),
    Value("luxury_premium", "Premium luxury",
          "The mood is high-end luxury fashion, poised, editorial and expensive."),
    Value("styling", "Styling showcase",
          "The mood is a styling showcase, presenting how the drape falls and how "
          "the garment is worn."),
]

GRADE = [
    Value("neutral", "Neutral true-to-fabric",
          "Colour grade is neutral and true to fabric, with accurate white balance "
          "and no colour cast."),
    Value("warmgold", "Warm gold",
          "Colour grade is warm and golden in the highlights, while the garment "
          "colour itself stays accurate."),
    Value("cool", "Cool editorial",
          "Colour grade is cool and editorial in the shadows, while the garment "
          "colour itself stays accurate."),
    Value("richfestive", "Rich saturated festive",
          "Colour grade is rich and saturated in the surroundings, while the "
          "garment colour itself stays accurate."),
]

AXES = {
    "environment": ENVIRONMENT,
    "lighting": LIGHTING,
    "camera": CAMERA,
    "concept": CONCEPT,
    "grade": GRADE,
}
AXIS_ORDER = ["environment", "lighting", "camera", "concept", "grade"]

# Combinations that would read as incoherent to a viewer. Not a hard ban on the
# axis values themselves -- only on pairing them with each other.
ALLOWED_LIGHTING = {
    # Each environment already fixes its own time of day and architecture, so the
    # lighting axis may only supply a key light that could actually exist there.
    # This is what stops a night rooftop being lit by flat overcast daylight.
    "mansion": {"highkey", "softbox", "overcast"},   # bright daylight interior
    "mandap":  {"practical", "lamp", "golden"},      # dusk, ceremonial lamps
    "palace":  {"lamp", "practical", "softbox"},     # evening, chandelier
    "cafe":    {"overcast", "softbox", "highkey"},   # midday daylight
    "resort":  {"golden", "highkey"},                # golden hour, open sky
    "rooftop": {"practical", "lamp"},                # night, city light only
}

DISCOURAGED = {(env, lig.id) for env, allowed in ALLOWED_LIGHTING.items()
               for lig in LIGHTING if lig.id not in allowed}

TOTAL_POINTS = 1
for _a in AXIS_ORDER:
    TOTAL_POINTS *= len(AXES[_a])


def is_coherent(point) -> bool:
    return (point["environment"], point["lighting"]) not in DISCOURAGED


def axis_distance(a, b) -> int:
    """How many of the five axes differ between two points."""
    return sum(1 for ax in AXIS_ORDER if a[ax] != b[ax])


def difference_matrix(points):
    """Pairwise axis-difference table. This is the artifact that proves the
    >=3-axes rule actually holds, rather than being asserted."""
    n = len(points)
    return [[axis_distance(points[i], points[j]) if i != j else 0
             for j in range(n)] for i in range(n)]


def min_axis_difference(points) -> int:
    if len(points) < 2:
        return 5
    return min(axis_distance(a, b) for a, b in combinations(points, 2))
