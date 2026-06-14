# =============================================================================
#  finalize_crosswalk.py  -  Apply hand-verified + auto-accepted matches.
# =============================================================================
#  PART OF: the CEEB<->CDS crosswalk build.  See README.md
#
#  WHAT IT DOES
#    Writes the human decisions into the crosswalk: a hard-coded table HV of
#    hand-verified CEEB->CDS pairs (each with a confidence), PLUS the token
#    matches from auto_accepted.csv. Saves a pre-edit backup first, then
#    overwrites the Panel Build crosswalk IN PLACE.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/finalize_crosswalk.py
#
#  INPUTS
#    build_outputs/auto_accepted.csv     (from refine_match.py)
#    build_outputs/cde_directory.csv
#    Panel Build 2026-06-07/ceeb_cds_crosswalk.csv     (read + overwritten)
#  OUTPUTS
#    Panel Build 2026-06-07/ceeb_cds_crosswalk.csv                  (updated)
#    Panel Build 2026-06-07/ceeb_cds_crosswalk_v1_pre_handverify.csv (backup)
#
#  GOTCHAS / NOTES
#    - OVERWRITES the crosswalk (a v1 backup is saved alongside).
#    - The HV dict near the top is where hand-verified matches live:
#      add  "CEEB": ("CDS14", confidence)  entries to fix specific schools.
#    - For touched rows, match_method becomes hand_verified or fuzzy2_token.
# =============================================================================

import csv,glob
from collections import defaultdict
DIR="Panel Build 2026-06-07"
# hand-verified (CDE School Directory / web-confirmed). conf: 0.98 exact dir name, 0.90 CDE-web, 0.70 medium
HV={
"054376":("19647330119727",0.98),"054092":("30664640106765",0.98),"054542":("19647330124388",0.98),
"054028":("19647330107011",0.95),"054695":("19647330127795",0.98),"054515":("38684780119875",0.98),
"051621":("19647330124511",0.95),"054555":("19647330124370",0.98),"054053":("19647330112029",0.95),
"054563":("19647330124396",0.98),"053833":("48705814830196",0.95),"054701":("19647330127803",0.98),
"051538":("29663570112367",0.95),"054046":("19647330108878",0.98),"054845":("19647330131821",0.98),
"050514":("19651360117234",0.92),"053984":("34674390108951",0.98),"051686":("19647330137083",0.98),
"054250":("31669280116459",0.90),"053164":("43696664330585",0.85),"053555":("25735934737250",0.95),
"052645":("34674134835302",0.92),"051620":("19647330124487",0.95),"054544":("19647330124495",0.95),
"054452":("19647330122341",0.95),"054451":("19647330122358",0.95),"054444":("19647330122366",0.95),
"054450":("19647330122374",0.95),"054441":("19647330122382",0.95),"054601":("19647330124404",0.95),
"054368":("19647330120360",0.92),"053066":("19734371996057",0.90),"054693":("19647330106435",0.70),
"054649":("19647330126540",0.70),"054642":("19647330126557",0.85),"051799":("36750510136960",0.95),
"051243":("36750510136432",0.90),"054344":("36750510115089",0.90),"054111":("44698070110007",0.90),
"054907":("19753090135145",0.85),"054044":("49709040101923",0.65),"054850":("49709040101923",0.65),
}
auto={r["ceeb"]:r["cds14"] for r in csv.DictReader(open("build_outputs/auto_accepted.csv"))}
dirname={r["cds14"]:r["raw_name"] for r in csv.DictReader(open("build_outputs/cde_directory.csv"))}
rows=list(csv.DictReader(open(f"{DIR}/ceeb_cds_crosswalk.csv")))
# backup
with open(f"{DIR}/ceeb_cds_crosswalk_v1_pre_handverify.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
nh=na=0
for r in rows:
    ce=r["ceeb"]
    if ce in HV:
        cds,conf=HV[ce]; r["cds14"]=cds; r["cde_name"]=dirname.get(cds,r.get("cde_name","")); r["match_method"]="hand_verified"; r["match_score"]=f"{conf:.2f}"; nh+=1
    elif ce in auto and r["match_method"]=="unmatched":
        cds=auto[ce]; r["cds14"]=cds; r["cde_name"]=dirname.get(cds,r.get("cde_name","")); r["match_method"]="fuzzy2_token"; r["match_score"]="0.80"; na+=1
with open(f"{DIR}/ceeb_cds_crosswalk.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
from collections import Counter
c=Counter(r["match_method"] for r in rows)
print("hand_verified added:",nh," auto(token) added:",na)
print("crosswalk methods now:",dict(c)," total:",len(rows)," still unmatched:",c.get("unmatched",0))
