# =============================================================================
#  build_crosswalk.py  -  Build the CEEB <-> CDS crosswalk (first pass).
# =============================================================================
#  PART OF: the CEEB<->CDS crosswalk build.  See README.md
#
#  WHAT IT DOES
#    Bridges the two ID universes: UC uses the 6-digit CEEB code, CDE uses the
#    14-digit CDS code, and there is NO shared key. Starts from the Gardiner
#    seed (known CEEB->CDS pairs) and fuzzy-matches the rest by normalized
#    school name within county.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/build_crosswalk.py
#
#  INPUTS
#    Gardiner/data-jbAKy.csv                     seed pairs (UC string w/ CEEB + CDS)
#    A-G Data/acgr25.txt, acgr24.txt, acgr17.txt  CDE names
#    Headcounts/cupc2526-912.xlsx, cupc2425-912.xlsx, cupc1617-912.xls  more names
#    build_outputs/dv_admissions.csv             the CEEB schools to match
#  OUTPUTS
#    build_outputs/ceeb_cds_crosswalk.csv
#       columns: ceeb, cds14, dv_name, cde_name, match_method, match_score
#
#  GOTCHAS / NOTES
#    - Reads dv_admissions.csv from build_outputs/, so run extract_dv.py first
#      and make sure that copy is present there.
#    - match_method = gardiner_seed / fuzzy_name_county / unmatched.
#      Fuzzy acceptance threshold is score >= 0.86.
#    - This is only pass 1. The output must be COPIED into
#      Panel Build 2026-06-07/  so refine_match / finalize_crosswalk / merge can
#      read it. The remaining unmatched rows are resolved by refine_match.py +
#      finalize_crosswalk.py.  See README.
# =============================================================================

import csv,io,re,sys,glob,os
from difflib import SequenceMatcher
from collections import defaultdict

def readutf16(fp):
    raw=open(fp,'rb').read()
    for enc in ('utf-16','utf-16-le','utf-8-sig','latin-1'):
        try:
            t=raw.decode(enc)
            if ',' in t: return t
        except: pass
    return raw.decode('latin-1')

STOP=re.compile(r'\b(SENIOR|SR|HIGH|SCHOOL|HS|ACADEMY|THE|OF|AND|FOR|AT)\b')
def norm(s):
    s=(s or "").upper()
    s=s.replace("&"," AND ").replace("/"," ").replace("-"," ").replace(".","")
    s=re.sub(r'[^A-Z0-9 ]',' ',s)
    s=STOP.sub(' ',s)
    s=re.sub(r'\s+',' ',s).strip()
    return s
def ncounty(s):
    return re.sub(r'[^A-Z]','',(s or "").upper().replace("COUNTY",""))

# ---------- Gardiner seed: CEEB -> CDS ----------
seed={}
txt=readutf16("Gardiner/data-jbAKy.csv")
R=list(csv.DictReader(io.StringIO(txt)))
for r in R:
    calc=r.get("Calculation1","") or ""
    m=re.search(r'(\d{4,6})\s*$',calc)
    cds=(r.get("CDS Code","") or "").strip()
    if m and cds.isdigit() and len(cds)==14:
        seed[m.group(1).zfill(6)]=cds
sys.stderr.write(f"Gardiner seed pairs: {len(seed)}\n")

# ---------- CDE directory: CDS -> (norm_name, county) ----------
cde=defaultdict(set)          # county -> list of (norm_name, cds, raw)
cds_meta={}
def add_cde(cds,name,county):
    if not cds or len(cds)!=14: return
    nn=norm(name); cc=ncounty(county)
    if not nn: return
    cde[cc].add((nn,cds)); cds_meta[cds]=(name,county)
# A-G names
for fn in ["acgr25.txt","acgr24.txt","acgr17.txt"]:
    with open(f"A-G Data/{fn}",encoding="latin-1",newline="") as f:
        r=csv.DictReader(f,delimiter="\t")
        for row in r:
            if row.get("AggregateLevel")!="S": continue
            cds=(row.get("CountyCode","").zfill(2)+row.get("DistrictCode","").zfill(5)+row.get("SchoolCode","").zfill(7))
            add_cde(cds,row.get("SchoolName",""),row.get("CountyName",""))
# CUPC names (2425, 2526 for current; 1617 for older names)
import openpyxl,xlrd
def cupc_names(fp):
    if fp.lower().endswith(".xls"):
        b=xlrd.open_workbook(fp); s=b.sheet_by_name("School-CALPADS UPC Data (9-12)")
        rows=[[s.cell_value(i,c) for c in range(s.ncols)] for i in range(s.nrows)]
    else:
        wb=openpyxl.load_workbook(fp,read_only=True,data_only=True); ws=wb["School-CALPADS UPC Data (9-12)"]
        rows=[list(r) for r in ws.iter_rows(values_only=True)]
    hdr=None
    for row in rows:
        low=[str(c).lower().replace("\n"," ") for c in row]
        if any("county" in c and "code" in c for c in low) and any("school" in c and "code" in c for c in low):
            idx={'C':[j for j,c in enumerate(low) if "county" in c and "code" in c][0],
                 'D':[j for j,c in enumerate(low) if "district" in c and "code" in c][0],
                 'S':[j for j,c in enumerate(low) if "school" in c and "code" in c][0],
                 'N':[j for j,c in enumerate(low) if "school name" in c][0],
                 'CN':[j for j,c in enumerate(low) if "county name" in c][0]}
            hdr=idx; continue
        if not hdr: continue
        sc=row[hdr['S']]
        if sc in (None,""): continue
        cds=str(row[hdr['C']]).split('.')[0].zfill(2)+str(row[hdr['D']]).split('.')[0].zfill(5)+str(sc).split('.')[0].zfill(7)
        add_cde(cds,row[hdr['N']],row[hdr['CN']])
for fp in ["Headcounts/cupc2526-912.xlsx","Headcounts/cupc2425-912.xlsx","Headcounts/cupc1617-912.xls"]:
    cupc_names(fp)
sys.stderr.write(f"CDE dir: counties={len(cde)} cds_total={len(cds_meta)}\n")

# ---------- DV universe: distinct ceeb -> (name,city,county) ----------
dv={}
for r in csv.DictReader(open("build_outputs/dv_admissions.csv")):
    dv.setdefault(r["ceeb"],(r["school_name"],r["city"],r["county"]))
sys.stderr.write(f"DV distinct CEEBs: {len(dv)}\n")

# ---------- match ----------
out=[]; mseed=mhi=mlo=mno=0
for ceeb,(nm,city,county) in dv.items():
    if ceeb in seed:
        cds=seed[ceeb]; out.append([ceeb,cds,nm,cds_meta.get(cds,("",""))[0],"gardiner_seed","1.00"]); mseed+=1; continue
    cc=ncounty(county); target=norm(nm); best=None;bs=0
    for (cn,cds) in cde.get(cc,()):
        sc=SequenceMatcher(None,target,cn).ratio()
        if target and cn and (target in cn or cn in target): sc=max(sc,0.94)
        if sc>bs: bs=sc; best=cds
    if best and bs>=0.86:
        out.append([ceeb,best,nm,cds_meta.get(best,("",""))[0],"fuzzy_name_county",f"{bs:.2f}"]); 
        mhi+= (bs>=0.93); mlo+= (bs<0.93)
    else:
        out.append([ceeb,"",nm,"","unmatched",f"{bs:.2f}"]); mno+=1
out.sort(key=lambda r:r[0])
with open("build_outputs/ceeb_cds_crosswalk.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["ceeb","cds14","dv_name","cde_name","match_method","match_score"]); w.writerows(out)
sys.stderr.write(f"matched seed={mseed} fuzzy_hi(>=.93)={mhi} fuzzy_lo={mlo} unmatched={mno} total={len(out)}\n")
# case studies
for ceeb,nm in [("050290","BerkeleyHigh"),("051984","UniHighIrvine"),("052980","MissionSF")]:
    row=[r for r in out if r[0]==ceeb]
    print(nm,row[0] if row else "NOT IN DV")
