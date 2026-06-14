# =============================================================================
#  extract_dv.py  -  Build the DEPENDENT VARIABLE: UC applicants/admits/enrollees
#                    per high school, by campus and year.
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.
#           Full pipeline & run order -> build_scripts_documented/README.md
#
#  WHAT IT DOES
#    Reads the UC freshman "consolidated_lean" admissions tables and collapses
#    them to one row per (CEEB school x campus x year): applicants, admits,
#    enrollees, and average GPA. Only the campuses listed in CAMPUS are kept.
#
#  *** RUN FROM:  the  admissions_source_school_consolidated_lean/  folder ***
#    (NOT the project root - this script reads its inputs by bare filename and
#     writes one level up into ../build_outputs/.)
#
#  HOW TO RUN
#    cd "admissions_source_school_consolidated_lean"
#    python "../build_scripts_documented/extract_dv.py"
#
#  INPUTS  (in the run-from folder)
#    admissions_freshman_state_coverage.csv      state_key -> campus + fall term
#    admissions_freshman_school_dimension.csv     school_id -> CEEB, name, city, county
#    admissions_freshman_counts_observed_long.csv applicant/admit/enrollee counts
#    admissions_freshman_gpa_observed_long.csv    GPA by status
#
#  OUTPUTS
#    ../build_outputs/dv_admissions.csv
#       columns: ceeb, campus, year, applicants, admits, enrollees,
#                app_gpa, adm_gpa, enr_gpa, school_name, city, county
#
#  ARGUMENTS: none
#
#  GOTCHAS / NOTES
#    - Blank counts mean "SUPPRESSED", not zero (~1/3 of Berkeley applicant
#      schools have suppressed admits). Blanks are written as empty, never 0.
#    - Downstream scripts expect dv_admissions.csv in TWO places:
#        build_outputs/   (used by build_crosswalk.py)
#        Panel Build 2026-06-07/components/   (used by merge_panel.py + analyses)
#      So after running, copy it into components/ -- see README "copy steps".
#    - Prints a sanity check for Berkeley High / Univ High Irvine / Mission SF.
#
#  WHAT YOU MIGHT WANT TO CHANGE
#    - CAMPUS = {"Berkeley","San Diego"}  (near the top): add a campus here,
#      e.g. "Los Angeles", to widen the DV. You'd then re-run the crosswalk and
#      merge so the new campus flows through.
# =============================================================================

import csv,sys
from collections import defaultdict
BASE="."
CAMPUS={"Berkeley","San Diego"}
def load_keys(tab):
    keys={}
    for r in csv.DictReader(open("admissions_freshman_state_coverage.csv",encoding="utf-8")):
        if r["source_tab"]==tab and r["campus"] in CAMPUS and r["school_type"]=="California public high school" and r["present"]=="True":
            keys[r["state_key"]]=(r["campus"],r["fall_term"])
    return keys
eth=load_keys("fr-eth-by-yr"); gpa=load_keys("fr-gpa-by-yr")
sys.stderr.write(f"eth_keys={len(eth)} gpa_keys={len(gpa)}\n")
dim={}
for r in csv.DictReader(open("admissions_freshman_school_dimension.csv",encoding="utf-8")):
    dim[r["school_id"]]=(r["source_school_code_6"],r["school_name"],r["city"],r["county_state_country"])
counts=defaultdict(lambda: defaultdict(float))  # (ceeb,campus,year)->status->count
meta={}
miss=0
with open("admissions_freshman_counts_observed_long.csv",encoding="utf-8") as f:
    next(f)
    for line in f:
        p=line.rstrip("\n").split(",")
        if len(p)!=8: continue
        sk=p[0]
        if sk not in eth: continue
        if p[5]!="race_ethnicity" or p[6]!="All": continue
        d=dim.get(p[1])
        if not d: miss+=1; continue
        ceeb=d[0]; campus,year=eth[sk]
        k=(ceeb,campus,year); counts[k][p[4]]+=float(p[7])
        meta[k]=(d[1],d[2],d[3])
# GPA
gpaval=defaultdict(dict)
with open("admissions_freshman_gpa_observed_long.csv",encoding="utf-8") as f:
    next(f)
    for line in f:
        p=line.rstrip("\n").split(",")
        if len(p)!=6: continue
        sk=p[0]
        if sk not in gpa: continue
        d=dim.get(p[1])
        if not d: continue
        campus,year=gpa[sk]; k=(d[0],campus,year)
        try: gpaval[k][p[4]]=float(p[5])
        except: pass
out=[]
for k,sc in counts.items():
    ceeb,campus,year=k; nm,city,county=meta[k]; g=gpaval.get(k,{})
    out.append([ceeb,campus,year,
                int(sc.get("applicants",0)) or "", int(sc.get("admits",0)) or "", int(sc.get("enrollees",0)) or "",
                g.get("applicants",""),g.get("admits",""),g.get("enrollees",""),nm,city,county])
out.sort(key=lambda r:(r[1],r[2],r[0]))
with open("../build_outputs/dv_admissions.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["ceeb","campus","year","applicants","admits","enrollees","app_gpa","adm_gpa","enr_gpa","school_name","city","county"]); w.writerows(out)
sys.stderr.write(f"dim_miss={miss} rows={len(out)}\n")
# validation
def show(ceeb,nm):
    print(f"\n{nm} ({ceeb}) Berkeley:")
    for r in out:
        if r[0]==ceeb and r[1]=="Berkeley" and r[2] in ("2022","2023","2024","2025"):
            ap,ad=r[3],r[4]; rate=(100*ad/ap) if (ap and ad) else None
            print(f"  {r[2]}: app={ap} adm={ad} enr={r[5]} rate={rate:.1f}%" if rate else f"  {r[2]}: app={ap} adm={ad} (admits suppressed)")
for c,n in [("050290","Berkeley High"),("051984","University High Irvine"),("052980","Mission HS SF")]: show(c,n)
