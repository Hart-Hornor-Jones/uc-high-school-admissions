# =============================================================================
#  refine_match.py  -  Second-pass matcher for still-unmatched UC schools.
# =============================================================================
#  PART OF: the CEEB<->CDS crosswalk build.  See README.md
#
#  WHAT IT DOES
#    Takes the rows the first crosswalk left as "unmatched" and tries harder:
#    token-overlap on distinctive shared words, both within county and globally.
#    Confident hits are AUTO-ACCEPTED to a file; the rest are printed as a
#    REVIEW list ranked by recent (2023-25) applicant volume so a human can
#    decide the high-impact ones.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/refine_match.py
#
#  INPUTS
#    build_outputs/cde_directory.csv
#    Panel Build 2026-06-07/components/dv_admissions.csv
#    Panel Build 2026-06-07/ceeb_cds_crosswalk.csv     (its 'unmatched' rows)
#  OUTPUTS
#    build_outputs/auto_accepted.csv
#       columns: ceeb, cds14, dv_name, cde_name, county, recA, rule, score, shared
#
#  GOTCHAS / NOTES
#    - Reads the crosswalk + DV from the Panel Build folder, so those copies
#      must already be in place (see README copy steps).
#    - Prints the leftover REVIEW list (recent applicants >= 5) to the screen;
#      use it to fill the hand-verified table in finalize_crosswalk.py.
# =============================================================================

import csv,re,sys
from difflib import SequenceMatcher
from collections import defaultdict
ABBR=[(r'\bMT\b','MOUNT'),(r'\bST\b','SAINT'),(r'\bJR\b','JUNIOR'),(r'\bSR\b','')]
STOP=re.compile(r'\b(SENIOR|HIGH|SCHOOL|HS|THE|OF|AND|FOR|AT)\b')
GENERIC=set("ACADEMY ACADEMIES CHARTER COLLEGE PREP PREPARATORY MAGNET COMMUNITY LEARNING CENTER COMPLEX PUBLIC ONLINE VIRTUAL INTERNATIONAL EARLY TECH TECHNOLOGY ARTS ARTE SCIENCE SCIENCES ACAD UNIV UNIVERSITY GLOBAL LEADERSHIP COLLEGIATE STUDIES MATH MATHEMATICS MEDIA PERFORMING VISUAL SOCIAL JUSTICE HUMANITAS NEXT CENTURY SCHOOLS PROFESSIONS HEALTH BUSINESS DESIGN ENGINEERING CONSTRUCT CONSTRUCTION TRADE PATHWAYS MEDICAL".split())
def norm(s):
    s=(s or "").upper().replace("&"," AND ").replace("/"," ").replace("-"," ").replace(".","")
    s=re.sub(r'[^A-Z0-9 ]',' ',s)
    for a,b in ABBR: s=re.sub(a,b,s)
    s=STOP.sub(' ',s); return re.sub(r'\s+',' ',s).strip()
def ncty(s): return re.sub(r'[^A-Z]','',(s or "").upper().replace("COUNTY",""))
def toks(s): return set(t for t in s.split() if len(t)>=3)
bycty=defaultdict(list); tokidx=defaultdict(list); meta={}
for r in csv.DictReader(open("build_outputs/cde_directory.csv")):
    nn=r["norm_name"];cds=r["cds14"];meta[cds]=(r["raw_name"],r["county"])
    bycty[ncty(r["county"])].append((nn,cds))
    for t in toks(nn): tokidx[t].append((nn,cds))
appB=defaultdict(float);info={}
for r in csv.DictReader(open("Panel Build 2026-06-07/components/dv_admissions.csv")):
    try:a=float(r["applicants"])
    except:a=0
    info[r["ceeb"]]=(r["school_name"],r["city"],r["county"])
    if r["year"] in("2023","2024","2025"):appB[r["ceeb"]]+=a
unm=[r["ceeb"] for r in csv.DictReader(open("Panel Build 2026-06-07/ceeb_cds_crosswalk.csv")) if r["match_method"]=="unmatched"]
def overlap(a,b):
    A=toks(a);B=toks(b)
    if not A:return 0,set()
    inter=A&B; return len(inter)/len(A), {t for t in inter if t not in GENERIC}
def best(target,pool):
    bs=0;bc=None;bdist=set()
    for nn,cds in pool:
        ov,dist=overlap(target,nn); rat=SequenceMatcher(None,target,nn).ratio()
        sc=max(ov,rat)
        if sc>bs: bs=sc;bc=cds;bdist=dist
    return bs,bc,bdist
accepted=[];review=[]
for ce in unm:
    nm,city,county=info.get(ce,("","",""));t=norm(nm)
    cs,cc,cdist=best(t,bycty.get(ncty(county),[]))
    # global via token index
    gp=set()
    for tk in toks(t):
        for x in tokidx.get(tk,[]): gp.add(x)
    gs,gc,gdist=best(t,list(gp))
    # accept rule: same-county candidate, >=1 distinctive shared token, overlap/ratio>=0.55
    if cc and cdist and cs>=0.55:
        accepted.append((ce,cc,nm,meta[cc][0],county,appB.get(ce,0),"incty",round(cs,2),";".join(sorted(cdist))))
    elif gc and gdist and gs>=0.62 and len(gdist)>=1:
        accepted.append((ce,gc,nm,meta[gc][0],meta[gc][1],appB.get(ce,0),"global",round(gs,2),";".join(sorted(gdist))))
    else:
        review.append((appB.get(ce,0),ce,nm,county,round(cs,2),meta.get(cc,("",""))[0],round(gs,2),meta.get(gc,("",""))[0],meta.get(gc,("",""))[1],";".join(sorted(gdist))))
review.sort(key=lambda x:-x[0])
with open("build_outputs/auto_accepted.csv","w",newline="") as f:
    w=csv.writer(f);w.writerow(["ceeb","cds14","dv_name","cde_name","county","recA","rule","score","shared"]);w.writerows(accepted)
print(f"AUTO-ACCEPTED: {len(accepted)}  | still REVIEW: {len(review)} (recA>=5: {sum(1 for r in review if r[0]>=5)})")
print(f"\n--- REVIEW (no confident match) recA>=5 ---")
print(f"{'recA':>4} {'ceeb':>7} {'dv_name':38.38} {'cty':9.9} {'gScore':>6} {'globalBestCand':32.32} {'gCty':9.9}")
for r in review:
    if r[0]>=5:
        print(f"{r[0]:4.0f} {r[1]:>7} {r[2]:38.38} {r[3]:9.9} {r[6]:6.2f} {r[7]:32.32} {r[8]:9.9}")
