import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = pathlib.Path("runs/run_m2_real/scores")
names = ["ROOFTOP-night","MANDAP-dusk","BASELINE-courtyard","MANSION-marble"]
cols  = {"ROOFTOP-night":"#1d4ed8","MANDAP-dusk":"#15803d",
         "BASELINE-courtyard":"#b45309","MANSION-marble":"#b91c1c"}
THR = 51.0

fig, (ax, ax2) = plt.subplots(2,1, figsize=(11,9), sharex=True,
                              gridspec_kw={"height_ratios":[2.4,1]})
for n in names:
    s = json.load(open(R/(n+".json")))
    ok=[f for f in s["per_frame"] if f.get("found")]
    t=[f["t"] for f in ok]; y=[f["fidelity"] for f in ok]
    ls = "--" if n=="MANSION-marble" else "-"
    ax.plot(t,y,color=cols[n],lw=2.2,ls=ls,marker="o",ms=3,
            label="%s   mean %.1f  min %.1f" % (n, s["fidelity_mean"], s["fidelity_min"]))
    ax2.plot(t,[f["mask_fraction"] for f in ok],color=cols[n],lw=1.8,ls=ls)

ax.axhline(THR,color="#e67e22",ls=":",lw=2)
ax.text(0.02,THR+1.2,"calibrated pass threshold %.1f  (n=4 real clips + anchors)"%THR,
        fontsize=9,color="#e67e22")
ax.fill_between([0,5.1],[0,0],[THR,THR],color="#b91c1c",alpha=0.05)
ax.set_ylabel("Fidelity Score (0-100)")
ax.set_title("Product fidelity per frame - four real Ekly / Kling AI Video Pro generations\n"
             "measured inside the garment mask only, every 5th frame", fontsize=12)
ax.legend(loc="lower right",fontsize=9); ax.grid(alpha=0.25); ax.set_xlim(0,5.1)

ax2.axhline(0.357,color="#666",ls=":",lw=1.2)
ax2.text(0.02,0.368,"source garment fraction 0.357",fontsize=8,color="#666")
ax2.set_ylabel("garment fraction\nof frame",fontsize=9)
ax2.set_xlabel("time (seconds)"); ax2.grid(alpha=0.25)
ax2.text(0.995,0.08,"MANSION-marble: product shrinks to ~3-9% of frame",
         transform=ax2.transAxes,fontsize=8,ha="right",color="#b91c1c")
fig.tight_layout()
fig.savefig("evidence/fidelity_all_four.png",dpi=140)
print("saved evidence/fidelity_all_four.png")
