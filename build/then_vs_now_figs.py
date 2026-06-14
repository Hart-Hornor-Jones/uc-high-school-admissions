# =============================================================================
#  then_vs_now_figs.py  -  Then-vs-now figures.        *** FIGURE SCRIPT ***
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.  See README.md
#
#  WHAT IT DOES
#    Draws the then-vs-now figures from the pickle made by then_vs_now.py:
#    a 2x3 panel (2015 & 2024 scatters plus a correlation-over-time line for
#    each campus) and a 2015-vs-2024 proficiency-decile comparison.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/then_vs_now_figs.py
#                 (run then_vs_now.py FIRST - it creates the input pickle)
#
#  INPUTS   Panel Build 2026-06-07/.tvn_cross.pkl
#  OUTPUTS  Panel Build 2026-06-07/figures/then_vs_now_main.png
#           Panel Build 2026-06-07/figures/then_vs_now_deciles.png
#
#  ***  TO TWEAK A FIGURE: search this file for  "TWEAK:"  ***
#       Inline notes flag the eras plotted, dot colors, dot size, titles,
#       figure size, and output dpi.
#
#  GOTCHAS / NOTES
#    - Fails if .tvn_cross.pkl is missing -> run then_vs_now.py first.
#    - Requires numpy + matplotlib (non-interactive backend).
# =============================================================================

import pickle,numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
DIR="Panel Build 2026-06-07"
cs=pickle.load(open(f"{DIR}/.tvn_cross.pkl","rb"))
# TWEAK: which eras to draw. Each must exist in .tvn_cross.pkl (set by then_vs_now.py's ERAS).
ERAS=["2015 (then)","2018 (mid)","2024 (now)"]
def pear(a,b):
    a=np.array(a);b=np.array(b); return float(np.corrcoef(a,b)[0,1]) if len(a)>2 else np.nan
def scat(ax,campus,era):
    rows=cs[(campus,era)]; x=np.array([r["met"] for r in rows]); y=np.array([r["rate"] for r in rows])
    # TWEAK: dot color (red = LCFF+, blue = non-LCFF+) and size (= applicants/6, clamped [4,90]).
    col=["#c0392b" if r["lcff"]==1 else "#2c6fbb" for r in rows]; s=[max(4,min(90,r["apps"]/6)) for r in rows]
    ax.scatter(x,y,s=s,c=col,alpha=0.45,edgecolors="none")
    b,a0=np.polyfit(x,y,1); xs=np.array([x.min(),x.max()]); ax.plot(xs,a0+b*xs,"k--",lw=1.6)
    ax.set_title(f"{campus} — {era.split(' ')[0]}   (r={pear(x,y):+.2f}, N={len(rows)})",fontsize=10)
    ax.set_xlabel("% met standard"); ax.set_ylabel("admit rate %"); ax.grid(alpha=0.2); ax.set_xlim(0,100)
def trend(ax,campus):
    rm=[];ru=[]
    for e in ERAS:
        rows=cs[(campus,e)]
        rm.append(pear([r["met"] for r in rows],[r["rate"] for r in rows]))
        up=[(r["upp"],r["rate"]) for r in rows if r["upp"] is not None]
        ru.append(pear([a for a,_ in up],[b for _,b in up]))
    xs=[2015,2018,2024]
    ax.axhline(0,color="#888",lw=1)
    ax.plot(xs,rm,"o-",color="#16794a",lw=2,label="r(admit, % met)")
    ax.plot(xs,ru,"s-",color="#b8860b",lw=2,label="r(admit, UPP)")
    ax.set_title(f"{campus}: relationship over time",fontsize=10); ax.set_ylim(-0.8,0.8)
    ax.set_xticks(xs); ax.set_xlabel("era (CAASPP yr / DV window)"); ax.set_ylabel("correlation"); ax.legend(fontsize=8); ax.grid(alpha=0.2)
# TWEAK: overall figure size in inches (width, height).
fig,ax=plt.subplots(2,3,figsize=(16,9))
for i,campus in enumerate(["Berkeley","San Diego"]):
    scat(ax[i,0],campus,"2015 (then)"); scat(ax[i,1],campus,"2024 (now)"); trend(ax[i,2],campus)
# TWEAK: the big title text across the top of the figure.
fig.suptitle("Then vs. Now: UC admit rate vs. high-school academic strength flipped from POSITIVE (2015) to NEGATIVE (2024)\n"
             "Red=LCFF+ (UPP≥75%); size∝applicants; dashed=linear fit. Self-selection existed in 2015 too, so a sign-flip can't be a self-selection artifact.",fontsize=11)
# TWEAK: output file + resolution (dpi).
fig.tight_layout(rect=[0,0,1,0.95]); fig.savefig(f"{DIR}/figures/then_vs_now_main.png",dpi=130)

# deciles then vs now
fig2,ax2=plt.subplots(1,2,figsize=(13,5))
for j,campus in enumerate(["Berkeley","San Diego"]):
    for e,c,mk in [("2015 (then)","#2c6fbb","o"),("2024 (now)","#c0392b","s")]:
        rows=sorted(cs[(campus,e)],key=lambda r:r["met"]); n=len(rows); xs=[];ys=[]
        for i in range(10):
            g=rows[i*n//10:(i+1)*n//10]
            if g: xs.append(np.mean([r["met"] for r in g])); ys.append(np.mean([r["rate"] for r in g]))
        ax2[j].plot(xs,ys,marker=mk,color=c,lw=2,label=e.split(" ")[0])
    ax2[j].set_title(f"UC {campus}: admit rate by proficiency decile",fontsize=11)
    ax2[j].set_xlabel("school % met standard (decile mean)"); ax2[j].set_ylabel("mean admit rate %"); ax2[j].legend(); ax2[j].grid(alpha=0.2)
fig2.suptitle("Then vs. Now by proficiency decile: the gradient tilts from upward (2015) to downward (2024)",fontsize=12)
fig2.tight_layout(rect=[0,0,1,0.95]); fig2.savefig(f"{DIR}/figures/then_vs_now_deciles.png",dpi=130)
print("wrote then_vs_now_main.png, then_vs_now_deciles.png")
