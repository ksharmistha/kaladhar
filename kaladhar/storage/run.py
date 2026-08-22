"""Run storage: one directory per run, keyed by run id.

A run is the unit of work: one source image -> briefs -> imported clips ->
scores -> exports. Everything expensive (mask, signature, embeddings) is
computed once and cached here so later stages never recompute it.

The run also carries the pipeline STATE, because the pipeline is not a single
uninterrupted process: it stops at the Ekly handoff and resumes when clips are
imported by hand.
"""
from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from kaladhar.config import RUNS

# The pipeline is deliberately resumable. AWAITING_CLIPS is not a failure
# state -- it is the manual Ekly generation step, which has no API.
STATES = [
    "CREATED",
    "PREPROCESSED",
    "BRIEFS_READY",
    "AWAITING_CLIPS",   # <-- manual handoff: a human generates in Ekly
    "CLIPS_IMPORTED",
    "SCORED",
    "SELECTED",
    "EXPORTED",
]


def new_run_id() -> str:
    return time.strftime("run_%Y%m%d_%H%M%S")


@dataclass
class Run:
    run_id: str
    root: Path
    meta: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------- lifecycle
    @classmethod
    def create(cls, run_id: str | None = None) -> "Run":
        run_id = run_id or new_run_id()
        root = RUNS / run_id
        for sub in ("input", "briefs", "clips", "frames", "scores", "exports", "evidence"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        run = cls(run_id=run_id, root=root, meta={
            "run_id": run_id,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "state": "CREATED",
            "history": [],
            "timings": {},
        })
        run.save()
        return run

    @classmethod
    def load(cls, run_id: str) -> "Run":
        root = RUNS / run_id
        mf = root / "run.json"
        if not mf.exists():
            raise FileNotFoundError(f"No such run: {run_id}")
        return cls(run_id=run_id, root=root, meta=json.loads(mf.read_text(encoding="utf-8")))

    @classmethod
    def latest(cls) -> "Run":
        runs = sorted([p for p in RUNS.glob("run_*") if (p / "run.json").exists()])
        if not runs:
            raise FileNotFoundError("No runs exist yet. Create one first.")
        return cls.load(runs[-1].name)

    @classmethod
    def list_all(cls) -> list[str]:
        return sorted(p.name for p in RUNS.glob("run_*") if (p / "run.json").exists())

    # --------------------------------------------------------------- helpers
    def save(self) -> None:
        (self.root / "run.json").write_text(
            json.dumps(self.meta, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_state(self, state: str, note: str = "") -> None:
        if state not in STATES:
            raise ValueError(f"Unknown state {state!r}")
        self.meta["state"] = state
        self.meta.setdefault("history", []).append({
            "state": state, "at": time.strftime("%H:%M:%S"), "note": note})
        self.save()

    def record_timing(self, stage: str, seconds: float) -> None:
        self.meta.setdefault("timings", {})[stage] = round(seconds, 3)
        self.save()

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def write_json(self, rel: str, obj: Any) -> Path:
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return p

    def read_json(self, rel: str) -> Any:
        return json.loads(self.path(rel).read_text(encoding="utf-8"))

    def has(self, rel: str) -> bool:
        return self.path(rel).exists()

    def ingest(self, src: Path | str, rel: str) -> Path:
        dst = self.path(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return dst


class Stopwatch:
    """Timing instrumentation. Feeds the Milestone 3 speed task with real
    numbers rather than estimates."""

    def __init__(self, run: Run, stage: str):
        self.run, self.stage = run, stage

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.run.record_timing(self.stage, time.perf_counter() - self.t0)
        return False
