"""Sampling the variation matrix under the >=3-axes-differ rule.

The constraint is what makes the output structurally varied instead of
superficially varied, so it is enforced rather than hoped for: a candidate set
is only returned if every pair of briefs differs on at least MIN_AXIS_DIFF
axes. If that is impossible for the requested N, the sampler raises instead of
quietly relaxing the rule.

Two additions on top of that, both of which STRENGTHEN the guarantee rather
than weaken it:

  * ENVIRONMENT is assigned deterministically, cycling through the environment
    list in order, so a six-brief set always covers all six environments and
    V01..V06 map to them in the order they are declared. Environment is the
    single biggest driver of how different two outputs look at thumbnail size,
    so leaving it to chance was the weakest part of the previous sampler.

  * Any other axis with at least as many values as briefs requested is drawn
    WITHOUT REPLACEMENT, so camera movement and creative concept are unique
    across the set too.

With environment, camera and concept all unique, every pair of briefs already
differs on three axes by construction. The pairwise check still runs and still
has to pass -- it is now a verification rather than the only line of defence.
"""
from __future__ import annotations

import random

from kaladhar.planner.matrix import (AXES, AXIS_ORDER, axis_distance, is_coherent,
                                     min_axis_difference)

MIN_AXIS_DIFF = 3

# Axes drawn without replacement when there are enough values to go round.
# Lighting is deliberately NOT in this list: each environment only permits the
# key lights that could physically exist in it, so forcing unique lighting on
# top of that can be infeasible.
UNIQUE_AXES = ("camera", "concept")


def _assign_environments(n):
    """Deterministic, in declaration order, cycling if more briefs than values."""
    envs = AXES["environment"]
    return [envs[i % len(envs)].id for i in range(n)]


def _draw(axis, n, rng):
    """Without replacement where possible, otherwise a shuffled cycle."""
    vals = [v.id for v in AXES[axis]]
    if axis in UNIQUE_AXES and n <= len(vals):
        pool = vals[:]
        rng.shuffle(pool)
        return pool[:n]
    out = []
    while len(out) < n:
        pool = vals[:]
        rng.shuffle(pool)
        out.extend(pool)
    return out[:n]


def _reuse_count(chosen):
    """How often axis values repeat across the set."""
    total = 0
    for ax in AXIS_ORDER:
        seen = {}
        for c in chosen:
            seen[c[ax]] = seen.get(c[ax], 0) + 1
        total += sum(v - 1 for v in seen.values())
    return total


def sample(n=6, seed=0, attempts=4000, restarts=48):
    """Build a brief set. Returns (points, report).

    Raises ValueError if a valid set cannot be built.
    """
    rng = random.Random(seed)
    environments = _assign_environments(n)
    best_score, best_set = None, None

    for _ in range(restarts):
        cameras = _draw("camera", n, rng)
        concepts = _draw("concept", n, rng)
        grades = _draw("grade", n, rng)

        chosen = []
        ok = True
        for i in range(n):
            env = environments[i]
            # Only lightings that can physically exist in this environment.
            lits = [v.id for v in AXES["lighting"]
                    if is_coherent({"environment": env, "lighting": v.id})]
            if not lits:
                ok = False
                break
            rng.shuffle(lits)
            placed = False
            for lit in lits:
                cand = {"environment": env, "lighting": lit, "camera": cameras[i],
                        "concept": concepts[i], "grade": grades[i]}
                if all(axis_distance(cand, c) >= MIN_AXIS_DIFF for c in chosen):
                    chosen.append(cand)
                    placed = True
                    break
            if not placed:
                ok = False
                break
        if not ok or len(chosen) < n:
            continue

        spread = sum(axis_distance(chosen[i], chosen[j])
                     for i in range(n) for j in range(i + 1, n))
        score = (min_axis_difference(chosen), spread, -_reuse_count(chosen))
        if best_score is None or score > best_score:
            best_score, best_set = score, chosen

    if best_set is None:
        raise ValueError(
            "Could not place %d briefs at least %d axes apart. "
            "Reduce n or widen the matrix." % (n, MIN_AXIS_DIFF))

    usage = {}
    for ax in AXIS_ORDER:
        counts = {}
        for c in best_set:
            counts[c[ax]] = counts.get(c[ax], 0) + 1
        usage[ax] = counts

    report = {
        "n": n,
        "seed": seed,
        "min_axis_diff_required": MIN_AXIS_DIFF,
        "min_axis_diff_achieved": min_axis_difference(best_set),
        "total_pairwise_spread": best_score[1],
        "axis_value_reuse": -best_score[2],
        "axis_value_usage": usage,
        "environment_assignment": "deterministic, in declaration order",
        "unique_axes": list(UNIQUE_AXES),
    }
    return best_set, report
