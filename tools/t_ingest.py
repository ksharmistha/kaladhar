import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kaladhar.input.ingest import ingest, summary
run = ingest("assets/source/saree_source.jpg", run_id="run_demo")
print(summary(run))
