import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.input.ingest import ingest, summary
from kaladhar.storage.run import Run

run = Run.load("run_20260822_181833")
ingest(run.meta["upload"]["path"], run=run)
run = Run.load("run_20260822_181833")
print(summary(run))
