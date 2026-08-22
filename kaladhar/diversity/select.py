"""Diversity Engine -- Quality Gate 2.

Planning the briefs apart on the variation matrix is necessary but not
sufficient: two structurally different briefs can still come back as two
similar-looking renders. So diversity is measured on the RESULT, not assumed
from the intent.

Each clip is reduced to a single embedding by averaging CLIP vectors over
sampled frames (a clip is not one image, and judging it by its first frame
would miss what the camera does). Selection is farthest-point / max-min
greedy: repeatedly take the candidate whose closest already-selected neighbour
is furthest away. That maximises the minimum separation of the chosen set,
which is exactly the property "not repetitive" describes.

A note on scale, stated plainly because it affects how this should be read:
with roughly 7 generations affordable on the remaining Ekly credits, the pool
is small. The engine still measures and selects correctly, but a 7-into-6
selection is a demonstration of the mechanism, not aggressive filtering. The
ratio is capacity-limited, not a design choice.
"""
from __future__ import annotations

import numpy as np


def clip_embedding(clip_path, stride=10, max_frames=16):
    """One embedding per clip: the mean of its sampled frame embeddings,
    renormalised. Captures the whole clip rather than a single moment."""
    from kaladhar.diversity.embed import embed
    from kaladhar.video.io import sample_frames

    frames = [f for _, f in sample_frames(clip_path, stride=stride, max_frames=max_frames)]
    if not frames:
        raise ValueError("no frames in %s" % clip_path)
    v = embed(frames).mean(axis=0)
    return (v / max(float(np.linalg.norm(v)), 1e-8)).astype(np.float32)


def pairwise_cosine_distance(vectors):
    v = np.asarray(vectors, dtype=np.float32)
    sim = v @ v.T
    return np.clip(1.0 - sim, 0.0, 2.0)


def diversity_score(vectors):
    """Mean pairwise cosine distance across a set, scaled to 0-100.

    Reported for the selected set and for the full pool so the two can be
    compared -- the selected set should score higher than the pool it came from,
    and if it does not, selection achieved nothing.
    """
    v = np.asarray(vectors, dtype=np.float32)
    if len(v) < 2:
        return 0.0
    d = pairwise_cosine_distance(v)
    iu = np.triu_indices(len(v), k=1)
    return float(np.mean(d[iu]) * 100.0)


def farthest_point_select(vectors, k, seed_index=None):
    """Max-min greedy selection. Returns (indices, trace).

    The trace records, for each pick, the min-distance it achieved -- useful
    for showing that later picks are progressively harder to keep distinct.
    """
    v = np.asarray(vectors, dtype=np.float32)
    n = len(v)
    if k >= n:
        return list(range(n)), []
    d = pairwise_cosine_distance(v)

    # Start from the item furthest from the centroid: the least typical
    # candidate, which anchors the set at an extreme rather than the middle.
    if seed_index is None:
        centroid = v.mean(axis=0)
        centroid /= max(float(np.linalg.norm(centroid)), 1e-8)
        seed_index = int(np.argmin(v @ centroid))

    chosen = [seed_index]
    trace = []
    while len(chosen) < k:
        rest = [i for i in range(n) if i not in chosen]
        mins = [min(d[i][j] for j in chosen) for i in rest]
        pick = rest[int(np.argmax(mins))]
        trace.append({"picked": pick, "min_distance_to_selected": round(float(max(mins)), 4)})
        chosen.append(pick)
    return chosen, trace


def select(candidates, k=6):
    """Run the engine over scored candidates.

    `candidates` is a list of dicts each with at least: id, clip path, and a
    precomputed embedding. Returns a report including which were rejected and
    why, so the review UI can show the rejected pool rather than hide it.
    """
    if not candidates:
        return {"error": "no candidates"}

    vecs = np.stack([np.asarray(c["embedding"], dtype=np.float32) for c in candidates])
    ids = [c["id"] for c in candidates]

    pool_div = diversity_score(vecs)
    idx, trace = farthest_point_select(vecs, min(k, len(candidates)))
    sel_div = diversity_score(vecs[idx])

    d = pairwise_cosine_distance(vecs)
    sel_d = d[np.ix_(idx, idx)]
    iu = np.triu_indices(len(idx), k=1)

    return {
        "requested_k": k,
        "pool_size": len(candidates),
        "selected_ids": [ids[i] for i in idx],
        "rejected_ids": [ids[i] for i in range(len(ids)) if i not in idx],
        "diversity_score_selected": round(sel_div, 2),
        "diversity_score_pool": round(pool_div, 2),
        "diversity_gain": round(sel_div - pool_div, 2),
        "min_pairwise_distance_selected": (
            round(float(sel_d[iu].min()), 4) if len(idx) > 1 else None),
        "selection_trace": trace,
        "pairwise_distance_matrix": np.round(d, 4).tolist(),
        "ids": ids,
        "note": ("Selection ratio is limited by available Ekly credits, not by design. "
                 "With a pool close to k, this demonstrates the mechanism rather than "
                 "aggressive filtering."),
    }
