#!/usr/bin/env python3
"""
repair_crosswalk_20260730.py — UC-site crosswalk repair, round 2
(the reconciliation-worksheet pass + the Thurgood Marshall fix).

WHY. The 2026-07-29 repo-vs-v2 reconciliation (hs data/ceeb_cds_reconciliation_
worksheet.csv, 66 CEEBs) found that the repo still carried ~2 dozen first-pass
fuzzy joins that the CSU web-verification rounds had overturned — the same
WESM/West-High defect class repaired on 2026-07-25, surfacing on different
rows (Hogan/Logan, Oasis Fallbrook/Oakland, OFY Acton-Fontana glued to Fontana
High, Sacramento High -> SCOE special-ed record, MSA-5, Vaughn -> Century High,
Camino Nuevo, ...). Hart adjudicated the worksheet 2026-07-29/30; the verdicts
below apply every row whose `resolution` was filled. Rows deliberately left
OPEN (the Crawford/SD-complex/Palisades/Hamilton/Mendocino "own closed CDS vs
parent successor" POLICY convention, 050446 Santa Cruz Alternative, and 053892
Crawford Multimedia) are NOT touched here.

Additionally: the 2026-07-30 Mission High fact-check found CEEB 053066
THURGOOD MARSHALL ACADEMIC HS (San Francisco, per UC's own dimension) joined
to 19734371996057 = Thurgood Marshall K-12, COMPTON Unified — wrong county,
wrong school (panel showed enrollment 51 vs the real ~420). Both the repo copy
and ceeb_cds_crosswalk_v2 share this defect; this script repairs the repo side
and the row was added to the reconciliation worksheet for the v2 side.

WHAT IT DOES. Applies the decision table below to data/ceeb_cds_crosswalk.csv
IN PLACE (timestamped backup written next to it once; do NOT commit the
backup):
  - REPAIRS: CEEB -> verdict CDS (match_method becomes hand_verified). Four
    of these create DOCUMENTED shared-CDS pairs (Locke 3 joins the Locke
    same-school share 051523/054367; Camino Nuevo joins Dalzell Lance 054693;
    San Benito Evening shares Hollister High's record with 051180; Castlemont
    BIT shares Castlemont High's record with 054611).
  - NULLS: 051737 LA River School — the fuzzy value was another school's CDS
    (LA Senior High); no verdict CDS exists yet, so covariates are removed
    rather than borrowed (match_method unmatched_reviewed).

Idempotent: rerunning after a successful pass changes nothing. A row whose
current cds14 matches neither the expected pre-repair value nor the verdict
is left alone with a loud warning (the file has moved under us — investigate).

After running, rebuild the chain:
  python3 scripts/build_panel_all9.py
  python3 scripts/make_site_data.py
  python3 scripts/make_context_data.py
  python3 scripts/scan_local_correlation.py

Run:  python3 build/repair_crosswalk_20260730.py
"""
import csv, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
XW = os.path.join(REPO, "data", "ceeb_cds_crosswalk.csv")

# CEEB -> (expected old CDS, verdict CDS, CDE name, confidence, evidence note)
REPAIRS = {
 # --- worksheet conflict rows: CSU web rounds overturned repo fuzzy joins, Hart adjudicated ---
 "050013": ("01611190130625", "01100170130625", "Alternatives in Action", 0.95,
   "worksheet verdict (Hart): Alternatives in Action, Alameda COE vintage (Active); repo had the Alameda City USD vintage of the same charter. Test panels 1998-2020: Bay Area School of Enterprise 2001-13 -> Alternatives in Action 2014-19"),
 "050412": ("37771070136473", "37103710136473", "Altus Schools South Bay", 0.95,
   "worksheet verdict (Hart): Altus Schools South Bay, SD COE vintage (Active); repo had a stale district prefix"),
 "050711": ("36738903631199", "36738903630274", "Silver Valley High", 0.95,
   "worksheet verdict (Hart): Silver Valley High (Active); repo fuzzy had Silver Valley ACADEMY, the district's other school. Test panels: Silver Valley High 1998-2019"),
 "050800": ("15737420165100", "15636851531987", "Desert Junior-Senior High", 0.95,
   "worksheet verdict (Hart): Desert Junior-Senior High, Muroc Joint USD (Active); repo fuzzy had a Kern county namesake. Test panels: Desert High/Desert Junior-Senior High (Muroc) 1998-2019"),
 "050899": ("19764970115725", "19734370115725", "Lifeline Education Charter", 0.95,
   "worksheet verdict (Hart): Lifeline Education Charter, Compton USD (Active); repo had the SBE-authorizer vintage of the same school (test panels: SBE 2007-16 -> Compton 2017-19)"),
 "051656": ("19647330118570", "19647330118588", "Alain Leroy Locke College Preparatory Academy", 0.95,
   "worksheet verdict (Hart, explicit CDS): Animo Locke 3 -> the recombined Alain Leroy Locke College Prep Academy (Active); harmonizes with CEEBs 051523/054367 (documented same-school share). Supersedes the 2026-07-25 repair's own-closed-CDS choice"),
 "051763": ("19647251996503", "19647330101683", "Renaissance Arts Academy", 0.95,
   "worksheet verdict (Hart): Renaissance Arts Academy, LAUSD (Active); repo fuzzy had Long Beach's Renaissance HS for the Arts. Test panels: Renaissance Arts Academy (LAUSD) 2004-19"),
 "052735": ("34103480106302", "34674390102038", "Sacramento Charter High", 0.95,
   "worksheet verdict (Hart): Sacramento Charter High (St. HOPE), Sacramento City USD (Active); repo fuzzy had the SCOE SPECIAL-ED record. Test panels: Sacramento Charter High 2003-19"),
 "052795": ("37764710137067", "37103710137067", "High Tech High Mesa", 0.95,
   "worksheet verdict (Hart): High Tech High Mesa, SD COE vintage (Active); repo had the SBC-authorizer vintage"),
 "053571": ("30665483030368", "30103063030632", "OCCS:CHEP/PCHS", 0.95,
   "worksheet verdict (validation override, Hart-confirmed): OCCS:CHEP/PCHS (OCDE, Tustin) = Pacific Coast High's reporting record (test panels 2004-19); repo value was Coast High's CDS, owned by CEEB 051684"),
 "053603": ("01612420134668", "48705814833950", "Hogan High", 0.95,
   "worksheet verdict (validation override, Hart-confirmed): Hogan High, Vallejo City USD (Closed 2011); repo fuzzy2_token value was James LOGAN High, New Haven USD, Alameda county — the Hogan/Logan name trap. Test panels: Hogan High (Vallejo) 1998-2010"),
 "053686": ("36679343630761", "36103633630761", "Excelsior Charter", 0.95,
   "worksheet verdict (Hart): Excelsior Charter, SB COE vintage (Active, test panels 2018-19); repo had the Victor Valley UHSD vintage (panels 1998-2017)"),
 "053845": ("44697650100305", "44104470100305", "Santa Cruz County Cypress Charter High", 0.95,
   "worksheet verdict (Hart): Santa Cruz County Cypress Charter High, SC COE vintage (panels 2019); repo had the Live Oak Elementary authorizer vintage (panels 2004-18)"),
 "053914": ("33670330135574", "33670823330503", "Academy of Innovation", 0.95,
   "worksheet verdict (validation + Hart-confirmed): Academy of Innovation, Hemet USD (Active; UC dim city=Hemet); repo fuzzy had CNUSD Hybrid School of Innovation, Corona-Norco"),
 "053946": ("37681223730967", "01612590107169", "Oasis High", 0.95,
   "worksheet verdict (Hart): Oasis High, Oakland USD (Closed, test panels 2006-08); repo fuzzy2_token had Oasis High (Alternative), Fallbrook Union — wrong county"),
 "053991": ("19647330127910", "19647330106435", "Camino Nuevo Charter High", 0.95,
   "worksheet verdict (Hart): Camino Nuevo Charter High (Closed, panels 2006-19); repo had Camino Nuevo High #2. Documented same-school share with 054693 Dalzell Lance"),
 "054015": ("19757131930122", "19647336019715", "Vaughn Next Century Learning Center", 0.95,
   "worksheet verdict (Hart): Vaughn Next Century Learning Center, LAUSD (Active, panels 2007-19); repo fuzzy had CENTURY High, Alhambra USD"),
 "054121": ("19647331935352", "19772890109942", "Los Angeles College Prep Academy", 0.95,
   "worksheet verdict (Hart): LA College Prep Academy, SBE (Closed 2024, panels 2019); repo fuzzy had Los Angeles SENIOR High's CDS"),
 "054313": ("37764710114678", "37103710114678", "High Tech High Chula Vista", 0.95,
   "worksheet verdict (Hart): High Tech High Chula Vista, SD COE vintage (Active); the gardiner seed carried the SBC-authorizer vintage"),
 "054483": ("19647330117630", "19101990137679", "Magnolia Science Academy 5", 0.95,
   "worksheet verdict (Hart): Magnolia Science Academy 5, LA COE (Active, panels 2018-19); repo had the LAUSD vintage (panels 2012-17)"),
 "054614": ("19647330141572", "19647330125963", "Leadership in Entertainment and Media Arts (LEMA)", 0.95,
   "worksheet verdict (Hart): LEMA, LAUSD (Closed, panels 2012-15); repo fuzzy2_token value was a different LAUSD record"),
 "054704": ("01612590126748", "01100170126748", "LPS Oakland R & D Campus", 0.95,
   "worksheet verdict (Hart): LPS Oakland R&D, Alameda COE vintage (Active); repo had the Oakland USD vintage (panels 2013-19)"),
 "054979": ("36679346059562", "36679340137638", "Lakeview Leadership Academy", 0.95,
   "worksheet verdict (Hart): Lakeview Leadership Academy, Victor Valley UHSD (Active, panels 2018-19); repo fuzzy had another VVUHSD record"),
 "055005": ("36677103633302", "36103630140012", "Entrepreneur High Fontana", 0.95,
   "worksheet verdict (Hart): Entrepreneur High Fontana, SB COE (Active); repo fuzzy had FONTANA High's CDS"),
 "251237": ("36677103633302", "19753090136648", "Options for Youth-Acton", 0.95,
   "worksheet verdict (Hart): Options for Youth-Acton (Fontana site), Acton-Agua Dulce USD (Active, panels 2017-19); repo fuzzy had FONTANA High's CDS — wrong county"),
 # --- v2-only fills the repo lacked (2026-07-25 pass had left these unmatched) ---
 "051185": ("", "35675383537008", "Hollister High", 0.90,
   "worksheet verdict: v2 web_verified_share — San Benito County Evening High reports under San Benito/Hollister High's record (documented program share with CEEB 051180); repo had null"),
 "052190": ("", "01612590125161", "Castlemont High", 0.90,
   "worksheet verdict: v2 web_verified_share — Castlemont Business & Information Technology (2005-11 small school) shares Castlemont High's record (documented share with CEEB 054611); repo had null (2026-07-25 unmatch superseded)"),
 # --- found by the 2026-07-30 Mission High fact-check; shared by repo AND v2 ---
 "053066": ("19734371996057", "38684783830403", "Marshall (Thurgood) High", 0.98,
   "2026-07-30 fact-check: UC dim city/county = San Francisco; joined record was Thurgood Marshall K-12, COMPTON Unified (panel enrollment 51 vs the real ~420). Correct CDE record: Marshall (Thurgood) High, SFUSD, Active since 1994. v2 shares the defect — row added to the reconciliation worksheet"),
}

# CEEB -> (expected old CDS, evidence note): wrong join, no verdict CDS yet.
NULLS = {
 "051737": ("19647331935352",
   "worksheet: LA River School's fuzzy row hung it on Los Angeles SENIOR High's CDS; CSU round 3 removed it as wrong. True CDS is open review work — covariates removed rather than borrowed"),
}

def main():
    rows = list(csv.DictReader(open(XW, encoding="utf-8")))
    backup = XW.replace(".csv", "_pre_repair_20260730.csv")
    if not os.path.exists(backup):
        shutil.copyfile(XW, backup)
    byceeb = {r["ceeb"]: r for r in rows}
    owners = {}
    for r in rows: owners.setdefault(r["cds14"], []).append(r["ceeb"])
    nrep = nnull = nskip = 0
    for ceeb, (old, cds, name, conf, note) in REPAIRS.items():
        r = byceeb.get(ceeb)
        if r is None:
            print("  !! CEEB not in crosswalk:", ceeb); continue
        if r["cds14"] == cds and r["match_method"] == "hand_verified":
            nskip += 1; continue                      # already applied (idempotent rerun)
        if r["cds14"] != old:
            print(f"  !! {ceeb}: current cds14={r['cds14']!r} != expected {old!r} — NOT touching"); continue
        share = [o for o in owners.get(cds, []) if o != ceeb]
        if share: print(f"  (documented share) {ceeb} joins CDS {cds} with {','.join(share)}")
        r["cds14"] = cds; r["cde_name"] = name
        r["match_method"] = "hand_verified"; r["match_score"] = f"{conf:.2f}"
        nrep += 1
    for ceeb, (old, note) in NULLS.items():
        r = byceeb.get(ceeb)
        if r is None:
            print("  !! CEEB not in crosswalk:", ceeb); continue
        if r["cds14"] == "" and r["match_method"] == "unmatched_reviewed":
            nskip += 1; continue
        if r["cds14"] != old:
            print(f"  !! {ceeb}: current cds14={r['cds14']!r} != expected {old!r} — NOT touching"); continue
        r["cds14"] = ""; r["cde_name"] = ""
        r["match_method"] = "unmatched_reviewed"; r["match_score"] = "0.00"
        nnull += 1
    with open(XW, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ceeb", "cds14", "dv_name", "cde_name", "match_method", "match_score"])
        w.writeheader(); w.writerows(rows)
    print(f"repaired {nrep} joins; nulled {nnull}; already-applied {nskip}; backup at {os.path.basename(backup)}")

if __name__ == "__main__":
    main()
