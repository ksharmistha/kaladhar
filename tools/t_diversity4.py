import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
from kaladhar.diversity.select import clip_embedding, pairwise_cosine_distance, diversity_score
from kaladhar.storage.run import Run

run = Run.load("run_m2_real")
names = ["BASELINE-courtyard","MANDAP-dusk","MANSION-marble","ROOFTOP-night"]
vecs = np.stack([clip_embedding("runs/run_m2_real/clips/%s.mp4" % n) for n in names])
d = pairwise_cosine_distance(vecs)

print("REAL pairwise cosine distance (mean CLIP embedding per clip, all 4 videos)")
print("%-20s %s" % ("", "  ".join("%-10s" % n[:10] for n in names)))
for i,n in enumerate(names):
    print("%-20s %s" % (n, "  ".join("%-10.4f" % d[i][j] for j in range(len(names)))))
iu = np.triu_indices(4,k=1)
print()
print("Overall diversity, all 4 real videos      : %.2f" % diversity_score(vecs))
print("Min pairwise distance                     : %.4f" % d[iu].min())
print("Max pairwise distance                     : %.4f" % d[iu].max())
keep = [0,1,3]
print()
print("Gate-1 passing set (3 videos)             : %.2f" % diversity_score(vecs[keep]))
dk = d[np.ix_(keep,keep)]; iuk = np.triu_indices(3,k=1)
print("Min pairwise within passing set           : %.4f" % dk[iuk].min())
pairs = [(names[i],names[j],float(d[i][j])) for i,j in zip(*iu)]
pairs.sort(key=lambda x:x[2])
print()
print("Most similar pair : %s <-> %s  (%.4f)" % pairs[0])
print("Most distinct pair: %s <-> %s  (%.4f)" % pairs[-1])
run.write_json("scores/diversity_full.json", {
    "ids": names,
    "pairwise_cosine_distance": np.round(d,4).tolist(),
    "diversity_all_four": round(float(diversity_score(vecs)),2),
    "diversity_gate1_passing": round(float(diversity_score(vecs[keep])),2),
    "most_similar_pair": pairs[0], "most_distinct_pair": pairs[-1],
    "note": "Computed from real generated video embeddings (mean CLIP vector over sampled frames). Not synthetic."})
print()
print("saved scores/diversity_full.json")
