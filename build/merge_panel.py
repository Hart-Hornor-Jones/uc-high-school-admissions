# =============================================================================
#  merge_panel.py  -  THE MASTER JOIN: assemble the analysis-ready panel.
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.  See README.md
#
#  WHAT IT DOES
#    Joins the DV (admissions) to CAASPP %met, A-G eligibility, and UPP/LCFF+
#    through the crosswalk, producing (a) the long school-year panel and
#    (b) a pooled 2023-2025 cross-section (one row per school) that the figures
#    use. Prints the headline Pearson r for Berkeley and San Diego.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/merge_panel.py
#
#  INPUTS  (all under Panel Build 2026-06-07/)
#    ceeb_cds_crosswalk.csv
#    components/dv_admissions.csv
#    components/caaspp_*.csv          (caaspp_2021 is skipped on purpose)
#    components/ag_eligibility.csv
#    components/upp_lcff.csv
#  OUTPUTS (under Panel Build 2026-06-07/)
#    school_year_panel.csv                 one row per CEEB x campus x year
#    pooled_cross_section_2023_2025.csv    one row per school (feeds the charts)
#
#  GOTCHAS / NOTES
#    - 2021 CAASPP is deliberately excluded.
#    - Year alignment: helper agk() maps a CAASPP year to its A-G year and
#      cuk() to its CUPC year. The pooled rate sums applicants+admits ONLY over
#      years where both are observed (avoids a pooling bias).
#    - admit_rate is blank when admits are suppressed.
# =============================================================================

import csv,glob
from collections import defaultdict
DIR="Panel Build 2026-06-07"; C=f"{DIR}/components"
xwalk={};xmeta={}
for r in csv.DictReader(open(f"{DIR}/ceeb_cds_crosswalk.csv")):
    xwalk[r["ceeb"]]=r["cds14"]; xmeta[r["ceeb"]]=(r["match_method"],r["match_score"])
caaspp={}
for fp in glob.glob(f"{C}/caaspp_*.csv"):
    if "caaspp_2021" in fp: continue  # 2021 COVID non-representative -> excluded from panel
    for r in csv.DictReader(open(fp)): caaspp[(r["cds14"],r["year"])]=r
ag={};cupc={}
for r in csv.DictReader(open(f"{C}/ag_eligibility.csv")): ag[(r["cds14"],r["ag_year"])]=r
for r in csv.DictReader(open(f"{C}/upp_lcff.csv")): cupc[(r["cds14"],r["cupc_year"])]=r
def f(x):
    try:return float(x)
    except:return None
def agk(y):y=int(y);return f"{y-1}-{str(y)[2:]}"
def cuk(y):y=int(y);return f"{y-1}-{y}"
rows=[]
for r in csv.DictReader(open(f"{C}/dv_admissions.csv")):
    ce=r["ceeb"];yr=r["year"];cds=xwalk.get(ce,"");mm,ms=xmeta.get(ce,("",""))
    app=f(r["applicants"]);adm=f(r["admits"]);enr=f(r["enrollees"])
    rate=round(100*adm/app,2) if (app and adm is not None and app>0) else ""
    C2=caaspp.get((cds,yr)) if cds else None
    ela=f(C2["ela_pct_met"]) if C2 else None;math=f(C2["math_pct_met"]) if C2 else None
    avg=round((ela+math)/2,2) if(ela is not None and math is not None) else (ela if ela is not None else math)
    A=ag.get((cds,agk(yr))) if cds else None
    agc=f(A["ag_cohort"]) if A else None;agm=f(A["ag_met_uccsu_count"]) if A else None
    ape=round(adm/agm,4) if(adm is not None and agm) else ""
    U=cupc.get((cds,cuk(yr))) if cds else None
    upp=f(U["upp_pct"]) if U else None;lcff=U["lcff_plus_flag"] if U else "";en912=U["enroll_9_12"] if U else ""
    rows.append([ce,cds,r["campus"],yr,r["school_name"],r["city"],r["county"],
        int(app) if app else "",int(adm) if adm is not None else "",int(enr) if enr is not None else "",rate,r["adm_gpa"],
        (yr if C2 else ""),ela if ela is not None else "",math if math is not None else "",avg if avg is not None else "",
        (agk(yr) if A else ""),int(agc) if agc else "",int(agm) if agm else "",ape,
        (cuk(yr) if U else ""),en912,upp if upp is not None else "",lcff,mm,ms])
cols=["ceeb","cds14","campus","year","school_name","city","county","applicants","admits","enrollees","admit_rate","adm_gpa","caaspp_year","ela_pct_met","math_pct_met","avg_pct_met","ag_year","ag_cohort","ag_met_uccsu_count","admits_per_eligible","cupc_year","enroll_9_12","upp_pct","lcff_plus","match_method","match_score"]
open(f"{DIR}/school_year_panel.csv","w",newline="").close()
with open(f"{DIR}/school_year_panel.csv","w",newline="") as fh:
    w=csv.writer(fh);w.writerow(cols);w.writerows(rows)
# pooled (pair apps+admits only in jointly-observed years)
pool=defaultdict(lambda:defaultdict(float));meta={};ela=defaultdict(list);math=defaultdict(list)
for r in rows:
    if r[3] not in("2023","2024","2025"):continue
    k=(r[2],r[0]);a=f(r[7]) if r[7]!="" else None;d=f(r[8]) if r[8]!="" else None
    if a is not None and d is not None: pool[k]["app"]+=a;pool[k]["adm"]+=d
    meta[k]=(r[1],r[4],r[5],r[6],r[24],r[25])
    if r[13]!="":ela[k].append(r[13])
    if r[14]!="":math[k].append(r[14])
pr=[]
for k,d in pool.items():
    campus,ce=k;cds,nm,city,county,mm,ms=meta[k];app=d["app"];adm=d["adm"]
    rate=round(100*adm/app,2) if app>0 else ""
    e=sum(ela[k])/len(ela[k]) if ela[k] else None;m=sum(math[k])/len(math[k]) if math[k] else None
    avg=round((e+m)/2,2) if(e is not None and m is not None) else ""
    U=cupc.get((cds,"2024-2025")) if cds else None;upp=U["upp_pct"] if U else "";lcff=U["lcff_plus_flag"] if U else ""
    A=ag.get((cds,"2024-25")) if cds else None;agm=A["ag_met_uccsu_count"] if A else "";agc=A["ag_cohort"] if A else ""
    ape=round(adm/float(agm),4) if(agm not in("",None) and float(agm)>0 and adm>0) else ""
    pr.append([campus,ce,cds,nm,city,county,int(app),int(adm),rate,round(e,2) if e is not None else "",round(m,2) if m is not None else "",avg,upp,lcff,agc,agm,ape,mm,ms])
pr.sort(key=lambda r:(r[0],-r[6]))
pcols=["campus","ceeb","cds14","school_name","city","county","applicants_2325","admits_2325","admit_rate_2325","ela_pct_met_avg","math_pct_met_avg","avg_pct_met","upp_pct_2425","lcff_plus","ag_cohort_2425","ag_met_2425","admits_per_eligible","match_method","match_score"]
with open(f"{DIR}/pooled_cross_section_2023_2025.csv","w",newline="") as fh:
    w=csv.writer(fh);w.writerow(pcols);w.writerows(pr)
# report
def pear(a,b):
    ma,mb=sum(a)/len(a),sum(b)/len(b);cov=sum((p-ma)*(q-mb) for p,q in zip(a,b))
    return cov/((sum((p-ma)**2 for p in a)**.5)*(sum((q-mb)**2 for q in b)**.5))
print("panel rows:",len(rows),"| pooled rows:",len(pr))
for campus in("Berkeley","San Diego"):
    d=[r for r in pr if r[0]==campus and r[11]!="" and r[8]!="" and r[6]>=30]
    x=[float(r[11]) for r in d];y=[float(r[8]) for r in d]
    print(f"{campus} (>=30 apps): N={len(d)}  r(rate,%met)={pear(x,y):+.3f}")
    b=[r for r in pr if r[0]==campus]
    print(f"   {campus} pooled schools={len(b)}, analyzable(rate+CAASPP)={len(d)}")
