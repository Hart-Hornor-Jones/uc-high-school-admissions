# =============================================================================
#  review_unmatched.py  -  Human-review export of still-unmatched schools.
# =============================================================================
#  PART OF: the CEEB<->CDS crosswalk build.  See README.md
#
#  WHAT IT DOES
#    DIAGNOSTIC ONLY (does not change the crosswalk). For every still-unmatched
#    UC school it writes its best in-county candidate and best global candidate
#    side by side, ranked by applicant volume, so you can eyeball them in Excel
#    and decide hand-verified matches.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/review_unmatched.py
#
#  INPUTS
#    build_outputs/cde_directory.csv
#    Panel Build 2026-06-07/components/dv_admissions.csv
#    Panel Build 2026-06-07/ceeb_cds_crosswalk.csv
#  OUTPUTS
#    build_outputs/unmatched_review.tsv   (open in Excel; tab-separated)
#
#  GOTCHAS / NOTES
#    - Read-only on the crosswalk. Feeds your decisions into the HV table in
#      finalize_crosswalk.py.
# =============================================================================

import csv,re,sys
from difflib import SequenceMatcher
from collections import defaultdict
ABBR=[(r'\bMT\b','MOUNT'),(r'\bST\b','SAINT'),(r'\bJR\b','JUNIOR'),(r'\bSR\b','')]
STOP=re.compile(r'\b(SENIOR|HIGH|SCHOOL|HS|THE|OF|AND|FOR|AT)\b')
def norm(s):
    s=(s or "").upper().replace("&"," AND ").replace("/"," ").replace("-"," ").replace(".","")
    s=re.sub(r'[^A-Z0-9 ]',' ',s)
    for a,b in ABBR: s=re.sub(a,b,s)
    s=STOP.sub(' ',s); return re.sub(r'\s+',' ',s).strip()
def ncty(s): return re.sub(r'[^A-Z]','',(s or "").upper().replace("COUNTY",""))
# load dir
bycty=defaultdict(list); tokidx=defaultdict(list); meta={}
for r in csv.DictReader(open("build_outputs/cde_directory.csv")):
    nn=r["norm_name"]; cds=r["cds14"]; meta[cds]=(r["raw_name"],r["county"])
    bycty[ncty(r["county"])].append((nn,cds))
    for tok in set(nn.split()):
        if len(tok)>=3: tokidx[tok].append((nn,cds))
# dv volumes
appB=defaultdict(float); appAll=defaultdict(float); yrs=defaultdict(set); info={}
for r in csv.DictReader(open("Panel Build 2026-06-07/components/dv_admissions.csv")):
    try:a=float(r["applicants"])
    except:a=0
    ce=r["ceeb"]; info[ce]=(r["school_name"],r["city"],r["county"]); appAll[ce]+=a; yrs[ce].add(r["year"])
    if r["year"] in ("2023","2024","2025"): appB[ce]+=a
unm=[r for r in csv.DictReader(open("Panel Build 2026-06-07/ceeb_cds_crosswalk.csv")) if r["match_method"]=="unmatched"]
def score(a,b):
    s=SequenceMatcher(None,a,b).ratio()
    if a and b and (a in b or b in a) and min(len(a),len(b))>=5: s=max(s,0.93)
    return s
def best_in(target,county):
    bs=0;bc=None
    for nn,cds in bycty.get(ncty(county),[]):
        s=score(target,nn)
        if s>bs:bs=s;bc=cds
    return bs,bc
def best_global(target):
    seen=set();bs=0;bc=None
    for tok in set(target.split()):
        for nn,cds in tokidx.get(tok,[]):
            if cds in seen:continue
            seen.add(cds); s=score(target,nn)
            if s>bs:bs=s;bc=cds
    return bs,bc
rows=[]
for r in unm:
    ce=r["ceeb"]; nm,city,county=info.get(ce,(r["dv_name"],"",""))
    t=norm(nm); bs,bc=best_in(t,county); gs,gc=best_global(t)
    rows.append((appB.get(ce,0),appAll.get(ce,0),ce,nm,city,county,bs,bc,gs,gc,min(yrs.get(ce,{"?"})),max(yrs.get(ce,{"?"}))))
rows.sort(key=lambda x:-x[0])
with open("build_outputs/unmatched_review.tsv","w") as f:
    f.write("recA\ttotA\tceeb\tdv_name\tcity\tcounty\tinScore\tinCDS\tinName\tinCounty\tglScore\tglCDS\tglName\tglCounty\tyrMin\tyrMax\n")
    for o in rows:
        inm=meta.get(o[7],("",""));gnm=meta.get(o[9],("",""))
        f.write("\t".join(str(x) for x in [o[0],o[1],o[2],o[3],o[4],o[5],f"{o[6]:.2f}",o[7],inm[0],inm[1],f"{o[8]:.2f}",o[9],gnm[0],gnm[1],o[10],o[11]])+"\n")
print(f"unmatched={len(rows)} recA>=20:{sum(1 for o in rows if o[0]>=20)} recA>=5:{sum(1 for o in rows if o[0]>=5)} recA==0:{sum(1 for o in rows if o[0]==0)}")
print(f"\n{'recA':>4} {'ceeb':>6} {'dv_name':40.40} {'cty':10.10} {'in':>4} {'inName':34.34} {'inCty':9.9}")
for o in rows:
    if o[0]>=5:
        inm=meta.get(o[7],("",""))
        print(f"{o[0]:4.0f} {o[2]:>6} {o[3]:40.40} {o[5]:10.10} {o[6]:4.2f} {inm[0]:34.34} {inm[1]:9.9}")
