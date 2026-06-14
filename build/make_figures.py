# =============================================================================
#  make_figures.py  -  Main cross-section chart pack.   *** FIGURE SCRIPT ***
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.  See README.md
#
#  WHAT IT DOES
#    Draws the chart pack from the pooled cross-section: Berkeley & San Diego
#    scatters (admit rate vs % met, dots colored by LCFF+, sized by applicants,
#    case studies circled), a proficiency-decile line chart, and an LCFF+ bar
#    chart. Also saves the two scatters as standalone PNGs.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/make_figures.py
#
#  INPUTS   Panel Build 2026-06-07/pooled_cross_section_2023_2025.csv
#  OUTPUTS  Panel Build 2026-06-07/figures/chart_pack.png
#           Panel Build 2026-06-07/figures/berkeley_scatter.png
#           Panel Build 2026-06-07/figures/ucsd_scatter.png
#
#  ***  TO TWEAK A FIGURE: search this file for  "TWEAK:"  ***
#       Inline notes flag the dot colors, dot size, the >=30-applicant cutoff,
#       which case-study schools get circled, the titles, the figure size, and
#       the output resolution (dpi).
#
#  GOTCHAS / NOTES
#    - Requires numpy + matplotlib. Uses a non-interactive backend (writes PNGs,
#      no window pops up). Re-run after merge_panel.py to refresh the charts.
# =============================================================================

import csv,numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows=[r for r in csv.DictReader(open("Panel Build 2026-06-07/pooled_cross_section_2023_2025.csv"))]
def fl(x):
    try: return float(x)
    except: return None
# TWEAK: minapp=30 = minimum applicants for a school to be plotted. Lower it to include smaller schools.
def sub(campus,minapp=30):
    out=[]
    for r in rows:
        if r["campus"]!=campus: continue
        a=fl(r["applicants_2325"]); rate=fl(r["admit_rate_2325"]); m=fl(r["avg_pct_met"]); upp=fl(r["upp_pct_2425"])
        if a and a>=minapp and rate is not None and m is not None:
            out.append(dict(a=a,rate=rate,m=m,upp=upp,lcff=r["lcff_plus"],name=r["school_name"]))
    return out
# TWEAK: the circled + labelled case-study schools. Add/remove  CEEB : "label"  entries.
CASE={"050290":"Berkeley High","051984":"University High (Irvine)","052980":"Mission HS (SF)"}
def casepts(campus):
    d={}
    for r in rows:
        if r["campus"]==campus and r["ceeb"] in CASE:
            d[r["ceeb"]]=(fl(r["avg_pct_met"]),fl(r["admit_rate_2325"]))
    return d
def scatter(ax,campus):
    d=sub(campus,30)
    x=np.array([p["m"] for p in d]); y=np.array([p["rate"] for p in d]); s=np.array([p["a"] for p in d])
    # TWEAK: dot colors -- #c0392b red = LCFF+ (UPP>=75%), #2c6fbb blue = non-LCFF+.
    col=np.array(["#c0392b" if p["lcff"]=="Y" else "#2c6fbb" for p in d])
    # TWEAK: dot size = applicants/8 clamped to [4,120]; alpha=0.45 is transparency. Change s/8 or the clip range.
    ax.scatter(x,y,s=np.clip(s/8,4,120),c=col,alpha=0.45,edgecolors="none")
    b,a0=np.polyfit(x,y,1); xs=np.array([x.min(),x.max()])
    ax.plot(xs,a0+b*xs,"k--",lw=1.6)
    r=np.corrcoef(x,y)[0,1]
    for ceeb,nm in CASE.items():
        cp=casepts(campus).get(ceeb)
        if cp and cp[0] is not None and cp[1] is not None:
            ax.scatter([cp[0]],[cp[1]],s=160,facecolors="none",edgecolors="black",linewidths=2,zorder=5)
            ax.annotate(nm,(cp[0],cp[1]),textcoords="offset points",xytext=(6,6),fontsize=8,fontweight="bold")
    ax.set_title(f"UC {campus}: admit rate vs school proficiency  (r={r:+.2f}, N={len(d)})",fontsize=11)
    ax.set_xlabel("School avg % met standard (CAASPP gr-11 ELA+Math, 2023-25)"); ax.set_ylabel("Admit rate, pooled 2023-25 (%)")
    ax.grid(alpha=0.2)
def decile(ax):
    for campus,c,mk in [("Berkeley","#2c6fbb","o"),("San Diego","#e67e22","s")]:
        d=sorted(sub(campus,30),key=lambda p:p["m"]); n=len(d); xs=[];ys=[]
        for i in range(10):
            g=d[i*n//10:(i+1)*n//10]
            if g: xs.append(np.mean([p["m"] for p in g])); ys.append(np.mean([p["rate"] for p in g]))
        ax.plot(xs,ys,marker=mk,color=c,label=f"UC {campus}")
    ax.set_title("Mean admit rate by school-proficiency decile",fontsize=11)
    ax.set_xlabel("School avg % met standard (decile midpoint)"); ax.set_ylabel("Mean admit rate (%)"); ax.legend(); ax.grid(alpha=0.2)
def lcffbar(ax):
    labels=[];Y=[];N=[]
    for campus in ("Berkeley","San Diego"):
        d=sub(campus,30); ly=[p["rate"] for p in d if p["lcff"]=="Y"]; ln=[p["rate"] for p in d if p["lcff"]=="N"]
        labels.append(f"UC {campus}"); Y.append(np.mean(ly)); N.append(np.mean(ln))
    x=np.arange(len(labels)); w=0.35
    ax.bar(x-w/2,N,w,label="Non-LCFF+ (UPP<75%)",color="#2c6fbb")
    ax.bar(x+w/2,Y,w,label="LCFF+ (UPP≥75%)",color="#c0392b")
    ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_ylabel("Mean admit rate (%)")
    ax.set_title("Admit rate by LCFF+ status",fontsize=11); ax.legend()
    for i,(nn,yy) in enumerate(zip(N,Y)):
        ax.text(i-w/2,nn+0.4,f"{nn:.1f}",ha="center",fontsize=8); ax.text(i+w/2,yy+0.4,f"{yy:.1f}",ha="center",fontsize=8)
# TWEAK: overall figure size in inches (width, height).
fig,axes=plt.subplots(2,2,figsize=(14,10))
scatter(axes[0,0],"Berkeley"); scatter(axes[0,1],"San Diego"); decile(axes[1,0]); lcffbar(axes[1,1])
fig.suptitle("UC admit rate vs. high-school academic strength (pooled 2023-2025, CA public HS, ≥30 applicants)\nRed = LCFF+ school (UPP≥75%); point size ∝ applicants; circled = case studies",fontsize=12)
fig.tight_layout(rect=[0,0,1,0.96])
# TWEAK: output file + resolution. Raise dpi for a sharper / bigger PNG.
fig.savefig("Panel Build 2026-06-07/figures/chart_pack.png",dpi=130)
# individual scatters too
for campus,fn in [("Berkeley","berkeley_scatter.png"),("San Diego","ucsd_scatter.png")]:
    f2,a2=plt.subplots(figsize=(8,6)); scatter(a2,campus); f2.tight_layout(); f2.savefig(f"Panel Build 2026-06-07/figures/{fn}",dpi=130)
print("figures written:", )
import os
for f in os.listdir("Panel Build 2026-06-07/figures"): print("  ",f, os.path.getsize(f"Panel Build 2026-06-07/figures/{f}")//1024,"KB")
