import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from PIL import Image
from kaladhar.storage.run import Run
from kaladhar.fidelity.report import drift_plot, weave_guard

run = Run.load("run_demo")
score = run.read_json("scores/proto_01.json")
p1 = drift_plot(score, "evidence/drift_plot_proto_01.png", title="proto_01 (Kling AI Video Pro)")
patch = np.asarray(Image.open(run.path("input/border_patch.png")).convert("RGB"))
p2 = weave_guard(patch, score, "assets/clips/proto_01.mp4", "evidence/weave_guard_proto_01.png")
print("wrote", p1)
print("wrote", p2)
