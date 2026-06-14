# =============================================================================
#  then_vs_now.py  -  Compute the "then vs now" era statistics.
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.  See README.md
#
#  WHAT IT DOES
#    For three eras (2015 / 2018 / 2024) and each campus, computes the
#    correlation of admit rate with % met and with UPP, the LCFF+ vs non-LCFF+
#    admit-rate gap, and an OLS regression
#        admit_rate ~ %met + LCFF+ + log(applicants).
#    Writes a summary table AND a pickle of the per-era point clouds that the
#    figure script then plots.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/then_vs_now.py
#                 (run this BEFORE then_vs_now_figs.py)
#
#  INPUTS  (under Panel Build 2026-06-07/)
#    ceeb_cds_crosswalk.csv ; components/caaspp_*.csv ;
#    components/upp_lcff.csv ; components/dv_admissions.csv
#  OUTPUTS (under Panel Build 2026-06-07/)
#    then_vs_now_summary.csv
#    .tvn_cross.pkl     (hidden intermediate -> consumed by then_vs_now_figs.py)
#
#  GOTCHAS / NOTES
#    - MUST run before then_vs_now_figs.py (it writes the .tvn_cross.pkl pickle).
#    - The eras are defined in the ERAS list: (CAASPP year, the +/-1-year admit
#      window, the UPP year). Per-school cutoff is >=30 applicants. Needs numpy.
# =============================================================================

import csv,glob,math
import numpy as np
from collections import defaultdict
DIR="Panel Build 2026-06-07"; C=f"{DIR}/components"
xwalk={r["ceeb"]:r["cds14"] for r in csv.DictReader(open(f"{DIR}/ceeb_cds_crosswalk.csv")) if r["cds14"]}
caaspp={}
for fp in glob.glob(f"{C}/caaspp_*.csv"):
    for r in csv.DictReader(open(fp)): caaspp[(r["cds14"],r["year"])]=r
upp={}
for r in csv.DictReader(open(f"{C}/upp_lcff.csv")): upp[(r["cds14"],r["cupc_year"])]=r
dv=list(csv.DictReader(open(f"{C}/dv_admissions.csv")))
def fl(x):
    try:return float(x)
    except:return None
ERAS=[("2015 (then)","2015",[2014,2015,2016],"2016-2017"),
      ("2018 (mid)","2018",[2017,2018,2019],"2018-2019"),
      ("2024 (now)","2024",[2023,2024,2025],"2024-2025")]
def era_cross(campus,cy,years,uy):
    yrs=set(str(y) for y in years)
    agg=defaultdict(lambda:[0.0,0.0]); nm={}
    for r in dv:
        if r["campus"]!=campus or r["year"] not in yrs: continue
        a=fl(r["applicants"]); d=fl(r["admits"])
        if a is None or d is None: continue
        agg[r["ceeb"]][0]+=a; agg[r["ceeb"]][1]+=d; nm[r["ceeb"]]=(r["school_name"],r["county"])
    out=[]
    for ce,(a,d) in agg.items():
        cds=xwalk.get(ce)
        if not cds or a<30: continue
        Cc=caaspp.get((cds,cy)); 
        if not Cc: continue
        ela=fl(Cc["ela_pct_met"]); mth=fl(Cc["math_pct_met"])
        met=None
        if ela is not None and mth is not None: met=(ela+mth)/2
        elif ela is not None: met=ela
        else: continue
        U=upp.get((cds,uy)); up=fl(U["upp_pct"]) if U else None; lc=1 if (U and U["lcff_plus_flag"]=="Y") else (0 if U else None)
        out.append(dict(ce=ce,rate=100*d/a,met=met,upp=up,lcff=lc,apps=a))
    return out
def pear(a,b):
    a=np.array(a);b=np.array(b)
    if len(a)<3: return float('nan')
    return float(np.corrcoef(a,b)[0,1])
def spear(a,b):
    def rk(v):
        v=np.array(v); order=v.argsort(); r=np.empty(len(v)); r[order]=np.arange(len(v)); return r
    return pear(rk(a),rk(b))
def ols(rows):
    R=[r for r in rows if r["upp"] is not None and r["lcff"] is not None]
    if len(R)<10: return None
    y=np.array([r["rate"] for r in R])
    X=np.column_stack([np.ones(len(R)),[r["met"] for r in R],[r["lcff"] for r in R],[math.log(r["apps"]) for r in R]])
    beta,*_=np.linalg.lstsq(X,y,rcond=None)
    resid=y-X@beta; dof=len(R)-X.shape[1]; s2=resid@resid/dof
    cov=s2*np.linalg.inv(X.T@X); se=np.sqrt(np.diag(cov)); t=beta/se
    return dict(n=len(R),b_met=beta[1],t_met=t[1],b_lcff=beta[2],t_lcff=t[2],b_logapp=beta[3],t_logapp=t[3])
rowsout=[]
crosssec={}
print(f"{'campus':9} {'era':12} {'N':>4} {'r(rate,%met)':>12} {'spear':>7} {'r(rate,UPP)':>11} {'LCFF+ %':>8} {'nonLCFF %':>9} {'OLS b_met(t)':>16} {'OLS b_lcff(t)':>16}")
for campus in("Berkeley","San Diego"):
    for label,cy,years,uy in ERAS:
        rows=era_cross(campus,cy,years,uy); crosssec[(campus,label)]=rows
        x=[r["met"] for r in rows]; y=[r["rate"] for r in rows]
        up=[(r["upp"],r["rate"]) for r in rows if r["upp"] is not None]
        ly=[r["rate"] for r in rows if r["lcff"]==1]; ny=[r["rate"] for r in rows if r["lcff"]==0]
        o=ols(rows)
        lcffm=sum(ly)/len(ly) if ly else float('nan'); nonm=sum(ny)/len(ny) if ny else float('nan')
        rmet=pear(x,y); sp=spear(x,y); rupp=pear([a for a,_ in up],[b for _,b in up]) if up else float('nan')
        print(f"{campus:9} {label:12} {len(rows):4d} {rmet:12.3f} {sp:7.3f} {rupp:11.3f} {lcffm:8.1f} {nonm:9.1f} "
              f"{(str(round(o['b_met'],3))+'('+str(round(o['t_met'],1))+')') if o else 'NA':>16} "
              f"{(str(round(o['b_lcff'],2))+'('+str(round(o['t_lcff'],1))+')') if o else 'NA':>16}")
        rowsout.append([campus,label,len(rows),round(rmet,3),round(sp,3),round(rupp,3),round(lcffm,1),round(nonm,1),round(lcffm-nonm,1),
                        o['n'] if o else "",round(o['b_met'],3) if o else "",round(o['t_met'],2) if o else "",
                        round(o['b_lcff'],2) if o else "",round(o['t_lcff'],2) if o else "",round(o['b_logapp'],2) if o else ""])
with open(f"{DIR}/then_vs_now_summary.csv","w",newline="") as f:
    w=csv.writer(f);w.writerow(["campus","era","N_schools","pearson_rate_met","spearman_rate_met","pearson_rate_upp","mean_admit_LCFFplus","mean_admit_nonLCFF","LCFF_gap_pts","OLS_n","OLS_coef_met","OLS_t_met","OLS_coef_lcff","OLS_t_lcff","OLS_coef_logapps"]);w.writerows(rowsout)
# save era cross-sections for plotting
import pickle
pickle.dump(crosssec,open(f"{DIR}/.tvn_cross.pkl","wb"))
print("\nwrote then_vs_now_summary.csv")
