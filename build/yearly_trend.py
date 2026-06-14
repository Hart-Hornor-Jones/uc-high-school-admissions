# =============================================================================
#  yearly_trend.py  -  Year-by-year trend (computes AND plots).  *** FIGURE ***
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.  See README.md
#
#  WHAT IT DOES
#    The year-by-year version of then-vs-now. For each CAASPP year 2015-2025
#    (2020/2021 absent) and each campus it computes r(admit, %met),
#    r(admit, UPP) and the LCFF+ gap, then plots the two correlation series
#    with a shaded COVID gap. Self-contained: no pickle dependency.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/yearly_trend.py
#
#  INPUTS  (under Panel Build 2026-06-07/)
#    ceeb_cds_crosswalk.csv ; components/caaspp_*.csv (skips 2021) ;
#    components/upp_lcff.csv ; components/dv_admissions.csv
#  OUTPUTS
#    Panel Build 2026-06-07/then_vs_now_yearly.csv
#    Panel Build 2026-06-07/figures/then_vs_now_yearly.png
#
#  ***  TO TWEAK A FIGURE: search this file for  "TWEAK:"  ***
#       Inline notes flag which years are used, the >=30-applicant cutoff, the
#       grey COVID band, the titles, the figure size, and the output dpi.
#
#  GOTCHAS / NOTES
#    - Requires numpy + matplotlib (non-interactive backend).
# =============================================================================

import csv,glob,numpy as np
from collections import defaultdict
DIR="Panel Build 2026-06-07"; C=f"{DIR}/components"
xwalk={r["ceeb"]:r["cds14"] for r in csv.DictReader(open(f"{DIR}/ceeb_cds_crosswalk.csv")) if r["cds14"]}
caaspp={}
for fp in glob.glob(f"{C}/caaspp_*.csv"):
    if "2021" in fp: continue
    for r in csv.DictReader(open(fp)): caaspp[(r["cds14"],r["year"])]=r
upp={}
for r in csv.DictReader(open(f"{C}/upp_lcff.csv")): upp[(r["cds14"],r["cupc_year"])]=r
dv=list(csv.DictReader(open(f"{C}/dv_admissions.csv")))
def fl(x):
    try:return float(x)
    except:return None
def uppkey(y):
    k=f"{y-1}-{y}"; return k if any(kk==k for (_,kk) in upp) else "2016-2017"
# TWEAK: which CAASPP years to compute/plot (2020 cancelled, 2021 excluded).
YEARS=[2015,2016,2017,2018,2019,2022,2023,2024,2025]
def pear(a,b):
    return float(np.corrcoef(a,b)[0,1]) if len(a)>2 else float('nan')
rows=[]
series=defaultdict(lambda:defaultdict(list))
for campus in ("Berkeley","San Diego"):
    for Y in YEARS:
        win=set(str(y) for y in (Y-1,Y,Y+1))
        agg=defaultdict(lambda:[0.0,0.0])
        for r in dv:
            if r["campus"]!=campus or r["year"] not in win: continue
            a=fl(r["applicants"]); d=fl(r["admits"])
            if a is None or d is None: continue
            agg[r["ceeb"]][0]+=a; agg[r["ceeb"]][1]+=d
        X=[];Yr=[];U=[];L=[]
        uk=uppkey(Y)
        for ce,(a,d) in agg.items():
            # TWEAK: >=30 applicants minimum per school for a year to count.
            if a<30: continue
            cds=xwalk.get(ce)
            if not cds: continue
            Cc=caaspp.get((cds,str(Y)))
            if not Cc: continue
            ela=fl(Cc["ela_pct_met"]); mth=fl(Cc["math_pct_met"])
            met=(ela+mth)/2 if (ela is not None and mth is not None) else ela
            if met is None: continue
            rate=100*d/a; X.append(met); Yr.append(rate)
            Uu=upp.get((cds,uk))
            if Uu and fl(Uu["upp_pct"]) is not None:
                U.append(fl(Uu["upp_pct"])); L.append(1 if Uu["lcff_plus_flag"]=="Y" else 0)
            else:
                U.append(None); L.append(None)
        rmet=pear(X,Yr)
        upp_pairs=[(u,y) for u,y in zip(U,Yr) if u is not None]
        rupp=pear([u for u,_ in upp_pairs],[y for _,y in upp_pairs]) if upp_pairs else float('nan')
        ly=[y for y,l in zip(Yr,L) if l==1]; ny=[y for y,l in zip(Yr,L) if l==0]
        gap=(sum(ly)/len(ly)-sum(ny)/len(ny)) if ly and ny else float('nan')
        rows.append([campus,Y,len(X),round(rmet,3),round(rupp,3),round(gap,1)])
        series[campus]["yr"].append(Y); series[campus]["rmet"].append(rmet); series[campus]["rupp"].append(rupp); series[campus]["gap"].append(gap)
        print(f"{campus:9} {Y} N={len(X):4d} r(rate,%met)={rmet:+.3f} r(rate,UPP)={rupp:+.3f} LCFFgap={gap:+.1f}")
with open(f"{DIR}/then_vs_now_yearly.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["campus","caaspp_year","N_schools","pearson_rate_met","pearson_rate_upp","LCFF_gap_pts"]); w.writerows(rows)
# figure
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
# TWEAK: overall figure size in inches (width, height).
fig,ax=plt.subplots(1,2,figsize=(14,5.2),sharey=True)
for i,campus in enumerate(["Berkeley","San Diego"]):
    s=series[campus]; ax[i].axhline(0,color="#888",lw=1)
    ax[i].plot(s["yr"],s["rmet"],"o-",color="#16794a",lw=2,label="r(admit rate, % met)")
    ax[i].plot(s["yr"],s["rupp"],"s-",color="#b8860b",lw=2,label="r(admit rate, UPP)")
    ax[i].set_title(f"UC {campus}",fontsize=11); ax[i].set_xlabel("CAASPP year (admit pooled ±1 yr)")
    ax[i].grid(alpha=0.2); ax[i].set_ylim(-0.8,0.8)
    if i==0: ax[i].set_ylabel("correlation with admit rate")
    # TWEAK: the grey COVID band (no 2020/2021 testing). Adjust the x-range or remove.
    ax[i].legend(fontsize=8); ax[i].axvspan(2019.5,2021.5,color="#eee",alpha=0.6)
    ax[i].text(2020.5,-0.75,"COVID\n(no 20/21)",ha="center",fontsize=7,color="#888")
fig.suptitle("Year-by-year: UC admit rate vs. school proficiency (green) flips negative while vs. school poverty/UPP (gold) flips positive, ~2015→2024",fontsize=11)
# TWEAK: output file + resolution (dpi).
fig.tight_layout(rect=[0,0,1,0.95]); fig.savefig(f"{DIR}/figures/then_vs_now_yearly.png",dpi=130)
print("\nwrote then_vs_now_yearly.csv + figures/then_vs_now_yearly.png")
