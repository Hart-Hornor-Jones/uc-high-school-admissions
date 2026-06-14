# =============================================================================
#  parse_ag.py  -  Parse CDE A-G / ACGR files into UC-eligibility per school.
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.  See README.md
#
#  WHAT IT DOES
#    Reads the CDE Adjusted Cohort Graduation Rate (ACGR) files and pulls the
#    "Met UC/CSU requirements" cohort + count + rate per school per year. This
#    is the UC-eligibility denominator (how many graduates were UC-eligible).
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/parse_ag.py
#
#  INPUTS   A-G Data/acgr*.txt   (tab-delimited, has header; acgr17 .. acgr25)
#  OUTPUTS  Panel Build 2026-06-07/components/ag_eligibility.csv
#           columns: cds14, ag_year, ag_cohort,
#                    ag_met_uccsu_count, ag_met_uccsu_rate
#           (creates the components/ folder if missing)
#
#  GOTCHAS / NOTES
#    - Keeps AggregateLevel=S (school) and ReportingCategory=TA (total).
#    - Newer files (2021-22+) list each school once with its real Charter/DASS;
#      older files have an All/All rollup. The parser prefers All/All when it
#      exists, else the single TA row (the 'pri' priority logic).
#    - ag_year comes from the filename: acgrNN -> 20(NN-1)-NN.
# =============================================================================

import csv,sys,glob,re,os
DIR="Panel Build 2026-06-07"
def find(cols,*subs):
    for c in cols:
        cl=c.lower().lstrip("﻿")
        if all(s in cl for s in subs): return c
    return None
allout=[]; summary=[]
for p in sorted(glob.glob("A-G Data/acgr*.txt")):
    m=re.search(r'acgr(\d{2})',os.path.basename(p)); yy=int(m.group(1)); yr=f"{2000+yy-1}-{yy:02d}"
    with open(p,encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f,delimiter="\t"); cols=r.fieldnames
        kCoh=find(cols,"cohort"); kCnt=find(cols,"met uc","count"); kRate=find(cols,"met uc","rate")
        kAgg=find(cols,"aggregate"); kCh=find(cols,"charter","school"); kD=find(cols,"dass"); kRC=find(cols,"reporting")
        kC=find(cols,"countycode"); kDi=find(cols,"districtcode"); kS=find(cols,"schoolcode")
        best={}
        for row in r:
            if row.get(kAgg)!="S" or row.get(kRC)!="TA": continue
            cds=row[kC].strip().zfill(2)+row[kDi].strip().zfill(5)+row[kS].strip().zfill(7)
            ch=row.get(kCh); da=row.get(kD)
            pri=2 if(ch=="All" and da=="All") else (1 if da=="All" else 0)
            if cds not in best or pri>best[cds][0]: best[cds]=(pri,row)
        n=0
        for cds,(pri,row) in best.items():
            coh=row.get(kCoh,"").strip()
            if coh in ("","*"): continue
            cnt=row.get(kCnt,"").strip(); rate=row.get(kRate,"").strip()
            allout.append([cds,yr,coh,cnt if cnt not in("","*") else "",rate if rate not in("","*") else ""]); n+=1
    summary.append((os.path.basename(p),yr,n))
os.makedirs(f"{DIR}/components",exist_ok=True)
with open(f"{DIR}/components/ag_eligibility.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["cds14","ag_year","ag_cohort","ag_met_uccsu_count","ag_met_uccsu_rate"]); w.writerows(allout)
for s in summary: sys.stderr.write(f"{s[0]:16} {s[1]}  schools={s[2]}\n")
print("ag_eligibility.csv total rows:",len(allout),"| distinct years:",len({y for _,y,_,_,_ in allout}))
