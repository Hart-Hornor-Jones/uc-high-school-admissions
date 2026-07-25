#!/usr/bin/env python3
"""
repair_crosswalk_20260725.py — hand-verified repair of CEEB<->CDS mis-joins.

WHY. A spot check (2026-07-25) found CEEB 051830 "WESTCHESTER ENRICHED SCIENCE
MAGNET" fuzzy-matched to CDS 19650601939602 — which the CDE School Directory
identifies as West High, Torrance Unified. The first-pass matcher
(build_crosswalk.py) awards score 0.94 whenever one normalized name CONTAINS
the other within a county ("WEST" is contained in "WESTCHESTER ..."), so a
number of schools were joined to a similarly named host school and inherited
its CAASPP, A-G, enrollment, UPP and tract context. A full audit of the 1,549
crosswalk rows (65 CDS codes shared by 2+ CEEBs; 13 further no-token-overlap
fuzzy joins) reviewed every suspect against the current CDE public-schools
directory, the component files, and targeted CDE/web checks.

WHAT IT DOES. Applies the verified decision table below to
data/ceeb_cds_crosswalk.csv IN PLACE (a timestamped backup is written next to
it):
  - REPAIRS: CEEB -> its own correct CDS (match_method becomes hand_verified);
  - UNMATCHES: joins with no valid CDE target (method unmatched_reviewed) —
    the school keeps its UC funnel data but carries no CDE covariates;
  - KEEPS (not listed here) were verified correct and are left untouched;
    notable keeps: renames in place (Sir Francis Drake -> Archie Williams;
    AIMS; Blue Ridge; ABLE; Stella High; San Benito High -> Hollister High;
    CATCH Prep = Crenshaw Arts-Technology Charter), CDE campus consolidations
    (San Diego High complex-era CEEB alongside the school's own), and
    era-split duplicate CEEB records for one school.

Aggregate impact is small (headline correlations move by <= ~0.01); the point
is per-school correctness, which the twin-school and profile views expose.

Run:  python3 build/repair_crosswalk_20260725.py
"""
import csv, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
XW = os.path.join(REPO, "data", "ceeb_cds_crosswalk.csv")

# CEEB -> (correct CDS, confidence, evidence note)
REPAIRS = {
 # --- schools that were wearing another school's data (post-2015 presence first) ---
 "051830": ("19647331939479", 0.98, "Westchester campus: CDE record 'WESM Health/Sports Medicine' (LAUSD, active, magnet=Y) carries the whole campus's CAASPP/A-G/CUPC; was joined to West High, Torrance (19650601939602)"),
 "051677": ("19101991933399", 0.98, "L.A. County High School for the Arts (LACOE); was joined to Los Angeles Senior High"),
 "054387": ("19647330110304", 0.98, "Los Angeles Academy of Arts and Enterprise (charter); was joined to Los Angeles Senior High"),
 "053975": ("19647330102434", 0.98, "Animo South Los Angeles Charter; was joined to Los Angeles Senior High"),
 "054057": ("19647330112870", 0.98, "Contreras Learning Center - Los Angeles School of Global Studies; was joined to Los Angeles Senior High"),
 "054366": ("19647330117754", 0.98, "Los Angeles Teacher Preparatory Academy (closed); was joined to Los Angeles Senior High"),
 "051739": ("19647330122762", 0.98, "Los Angeles Big Picture High (closed); was joined to Los Angeles Senior High"),
 "051231": ("01611920108670", 0.98, "Leadership Public Schools - Hayward; was joined to Hayward High"),
 "053970": ("07617960101477", 0.98, "Leadership Public Schools - Richmond; was joined to Richmond High"),
 "054847": ("07617960132100", 0.98, "Aspire Richmond California College Preparatory; was joined to Richmond High"),
 "050306": ("07617960132100", 0.95, "Richmond Ca. College Preparatory = earlier CEEB record of Aspire Richmond CCP (activity 2011-15 vs 2017-25, disjoint); was joined to Richmond High"),
 "050029": ("01611190106401", 0.98, "Alameda Science and Technology Institute; was joined to Alameda High"),
 "053972": ("01612590130617", 0.98, "Oakland Military Institute, College Preparatory Academy; was joined to Oakland High"),
 "053881": ("01612590102962", 0.98, "East Oakland School of the Arts (closed 2012); was joined to Oakland High"),
 "054624": ("19647330125989", 0.98, "STEM Academy at Bernstein High (Hollywood); was joined to Hollywood Senior High"),
 "053014": ("19101996119945", 0.98, "Magnolia Science Academy (MSA-1, Reseda); was joined to Reseda Senior High"),
 "054475": ("19101990115212", 0.98, "Magnolia Science Academy 2 (Van Nuys); was joined to MSA-1's CDS"),
 "054510": ("19101990115030", 0.98, "Magnolia Science Academy 3 (Carson); was joined to MSA-1's CDS"),
 "054641": ("43104390120261", 0.98, "Magnolia Science Academy Santa Clara (closed); was joined to Santa Clara High"),
 "054539": ("15101570119669", 0.98, "Wonderful College Prep Academy (Delano); was joined to Delano High"),
 "051518": ("19642871996479", 0.98, "Opportunities for Learning - Baldwin Park; was joined to Baldwin Park High"),
 "054939": ("19644690139535", 0.98, "Options For Youth - Duarte; was joined to Pasadena High"),
 "052426": ("19643371996099", 0.98, "Options for Youth - Burbank Charter (closed); was joined to Burbank High"),
 "050057": ("19643370131573", 0.98, "Burbank Unified Independent Learning Academy; was joined to Burbank High"),
 "051536": ("16639820110205", 0.98, "Lemoore Middle College High; was joined to Lemoore High"),
 "051131": ("16639251630169", 0.98, "Hanford West High; was joined to Hanford High"),
 "053981": ("19645920100354", 0.98, "Hawthorne Math and Science Academy; was joined to Hawthorne High"),
 "054525": ("19647330124529", 0.98, "Rancho Dominguez Preparatory (LAUSD); was joined to Dominguez High (Compton)"),
 "052537": ("19649071996495", 0.98, "Village Academy High School at Indian Hill (Pomona Unified); was joined to New Village Girls Academy's CDS"),
 "054498": ("19647330120071", 0.98, "New Designs Charter School - Watts; was joined to New Designs Charter (main)"),
 "052961": ("19647330137091", 0.98, "University Pathways Public Service Academy; was joined to University Senior High"),
 "051569": ("19647331932128", 0.95, "Crenshaw High: CDE's continuing record for the campus is 'Crenshaw Science, Technology, Engineering, Math Magnet'; was joined to Crenshaw Arts-Technology Charter's CDS"),
 "050301": ("19647330132084", 0.98, "Alliance Marine - Innovation and Technology 6-12 Complex; was joined to Alliance Ouchi-O'Donovan"),
 "754196": ("19647330114942", 0.95, "Alliance College-Ready Academy High #7 (closed); was joined to Alliance Collins Family's CDS"),
 "054633": ("19647330126490", 0.98, "Augustus F. Hawkins High B Community Health Advocates (own CDS, closed); was joined to the Hawkins campus record"),
 "054634": ("19647330126508", 0.98, "Augustus F. Hawkins High C RISE (own CDS, closed); was joined to the Hawkins campus record"),
 "054432": ("19647330122283", 0.98, "School of Law & Government at Roosevelt High (closed SLC); was unmatched"),
 "054433": ("19647330122291", 0.98, "Humanitas Art School at Roosevelt High (closed SLC); was joined to Humanitas Academy at Torres"),
 "054434": ("19647330122325", 0.98, "Academy of Medical & Health Sciences at Roosevelt High (closed SLC); was unmatched"),
 "054435": ("19647330122309", 0.98, "School of Science, Technology, Engineering & Math at Roosevelt High (closed SLC); was joined to Girls Academic Leadership Academy's CDS"),
 "053907": ("37683380107029", 0.98, "San Diego International Studies (own CDS, closed); was joined to San Diego High's CDS"),
 "053908": ("37683380107037", 0.98, "San Diego LEADS (closed SLC, own CDS); was joined to San Diego High's CDS"),
 "053909": ("37683380107482", 0.95, "San Diego Metro Career and Tech; was joined to High Tech High's CDS"),
 "053900": ("37683380107086", 0.98, "Kearny School of Biomedical Science and Technology; was joined to High Tech High's CDS"),
 "054600": ("37683380122788", 0.98, "School for Entrepreneurship and Technology; was joined to High Tech High's CDS"),
 "053894": ("37683380107201", 0.98, "Crawford IDEA (closed SLC, own CDS); was joined to Crawford High"),
 "053896": ("37683380107185", 0.98, "Crawford CHAMPS (closed SLC, own CDS); was joined to Crawford High"),
 "053897": ("37683380107193", 0.98, "Crawford Law and Business (closed SLC, own CDS); was joined to Crawford High"),
 "052895": ("37683383733326", 0.98, "Kearny Senior High (closed 2004; successor small schools carry their own CEEBs); was unmatched"),
 "052942": ("37683383731320", 0.98, "Cortez Hill Academy (closed); was unmatched"),
 "053922": ("37683380106799", 0.98, "Learning Choice Academy (San Diego); was joined to San Diego High's CDS"),
 "051192": ("37735690136267", 0.95, "Coastal Academy Charter (active K-12; carries the high school's grade-11 data); was joined to Oceanside High"),
 "052929": ("37681633731239", 0.98, "Julian Charter (independent-study charter, distinct from Julian Union High); was joined to Julian High"),
 "052409": ("58727365830138", 0.98, "Marysville Charter Academy for the Arts; was joined to Marysville High"),
 "059728": ("33672490123844", 0.95, "San Jacinto Leadership Academy; was joined to San Jacinto High"),
 "055007": ("19101990140681", 0.98, "Environmental Charter High - Gardena (opened 2024); was joined to the Lawndale flagship's CDS"),
 "054257": ("41690620118232", 0.95, "Aspire East Palo Alto Phoenix Academy (own CDS, closed 2020; no component coverage - covariates become blank rather than another school's); was joined to East Palo Alto Academy"),
 "050352": ("01100170136101", 0.98, "Connecting Waters Charter - East Bay; was joined to the Waterford flagship's CDS"),
 "054271": ("19650940112706", 0.98, "California Virtual Academy @ Los Angeles; was joined to CAVA @ Sutter's CDS"),
 "051443": ("19646420136127", 0.98, "Sage Oak Charter School - Keppel; was joined to Sage Oak (Helendale) CDS"),
 "054980": ("42750100138891", 0.98, "California Online Public Schools Central Coast; was joined to Coast High (Orange County)"),
 "054777": ("37680236037980", 0.95, "Bayfront Charter High School: absent from the CDE directory as its own record; CDE reports it under Mueller Charter (Robert L.) (Chula Vista Elementary), whose CDS carries the grade-11 CAASPP and 9-12 CUPC rows; was unmatched"),
 "052046": ("56739405630371", 0.98, "The High School at Moorpark College; was sharing Moorpark High's CDS"),
 "050744": ("30665973030673", 0.98, "Orange Coast Middle College High (closed); was joined to Coast High"),
 "050991": ("30103060133959", 0.98, "Unity Middle College High (closed 2023); was joined to Middle College High (Santa Ana)"),
 # --- pre-2015 / hygiene repairs (no site-visible covariates; recorded for correctness) ---
 "052313": ("19647331936566", 0.95, "Palisades Senior High (pre-charter record, closed); was joined to Palisades Charter High's CDS"),
 "053052": ("38684783839404", 0.98, "Woodrow Wilson High, San Francisco (closed 1994); was joined to LAUSD's Wilson"),
 "989927": ("19647331932979", 0.95, "Hamilton High School Magnet (merged); was joined to School for the Visual Arts and Humanities"),
 "989915": ("19647331933191", 0.90, "Cleveland H.S. Magnet (merged); was unmatched"),
 "052213": ("01100170109835", 0.98, "FAME Public Charter (closed); was unmatched"),
 "052956": ("38684783830353", 0.98, "International Studies Academy, SF (closed); was unmatched"),
 "052995": ("38684783830072", 0.98, "McAteer (J. Eugene) High (closed); was unmatched"),
 "053961": ("43104390102905", 0.95, "Leadership Public Schools - San Jose (closed); was unmatched"),
 "053002": ("43694274330601", 0.95, "MACSA Academica Calmecac (closed); was unmatched"),
 "053202": ("01612590130591", 0.98, "University Preparatory Charter Academy (Oakland, closed); was unmatched"),
 "053859": ("01612590100834", 0.95, "Media College Preparatory (Oakland, closed); was unmatched"),
 "053882": ("01612590107417", 0.95, "Leadership Preparatory High (Oakland, closed); was unmatched"),
 "053902": ("01612590100826", 0.98, "Mandela High (Oakland, closed); was unmatched"),
 "054100": ("01612590100859", 0.95, "YES - Youth Empowerment School (Oakland, closed); was unmatched"),
 "054031": ("01612590110171", 0.95, "Business, Entrepreneurial School of Technology (Oakland, closed); was unmatched"),
 "053947": ("38684780109769", 0.90, "Marin School of Arts & Technology, relocated/renamed Metropolitan Arts & Technology (closed); was unmatched"),
 "054107": ("38684780109769", 0.98, "Metropolitan Arts & Technology High (closed); same school as 053947's later era; was unmatched"),
 "053996": ("41764300110015", 0.98, "High Tech High Bayshore (closed); was unmatched"),
 "054215": ("19647330112540", 0.98, "Lou Dantzler Preparatory Charter High (closed); was unmatched"),
 "054295": ("19647330117739", 0.98, "Civitas School of Leadership (closed); was unmatched"),
 "054179": ("19647330112557", 0.98, "Frederick Douglass Academy High (closed); was unmatched"),
 "051708": ("19647330112862", 0.98, "Student Empowerment Academy (closed); was unmatched"),
 "051572": ("19647331996636", 0.98, "Community Harvest Charter (closed); was unmatched"),
 "051049": ("19647331933290", 0.95, "George Kiriyama Community Adult (closed adult school; no grade-11 covariates exist); was unmatched"),
 "054235": ("19647330111617", 0.98, "Animo Locke Technology High (closed); was joined to Animo Venice's CDS"),
 "054369": ("19647330118596", 0.98, "Animo Locke II College Preparatory (closed); was joined to Animo Venice's CDS"),
 "051656": ("19647330118570", 0.98, "Animo Locke Charter High School #3 (closed); was joined to Alain Leroy Locke College Prep's CDS"),
 "052243": ("01612590130526", 0.95, "Merritt Middle College High (Alternative), Oakland (closed); was joined to Unity Middle College (Orange County)"),
 "051951": ("23655812330322", 0.90, "Mendocino Community Day (the district's continuation program, closed); was joined to Mendocino High"),
}

# CEEBs whose join is wrong but no valid CDE target exists (or identity cannot
# be established): covariates are removed rather than borrowed.
UNMATCH = {
 "052190": "Castlemont Business & Information Technology School (2005-11 small school): no surviving CDE record distinct from Castlemont High",
 "053899": "San Diego School of Media, Visual & Performing Arts (2005-13 complex school): no surviving CDE record",
 "054402": "Southeast Academy High School (Norwalk-La Mirada program): no CDE school record serving 9-12 found",
 "054140": "Leadership Public Schools College Park (Oakland): cannot be separated from Leadership Preparatory High's record with confidence",
 "051850": "VSC - Emerson Learning Center: no CDE record identified",
 "051185": "San Benito County Evening High: no CDE record (evening/adult program)",
}

def main():
    rows = list(csv.DictReader(open(XW, encoding="utf-8")))
    backup = XW.replace(".csv", "_pre_repair_20260725.csv")
    if not os.path.exists(backup):
        shutil.copyfile(XW, backup)
    byceeb = {r["ceeb"]: r for r in rows}
    nrep = nun = 0
    for ceeb, (cds, conf, note) in REPAIRS.items():
        r = byceeb.get(ceeb)
        if r is None:
            print("  !! CEEB not in crosswalk:", ceeb); continue
        if r["cds14"] == cds and r["match_method"] == "hand_verified": continue
        r["cds14"] = cds; r["match_method"] = "hand_verified"; r["match_score"] = f"{conf:.2f}"
        nrep += 1
    for ceeb, note in UNMATCH.items():
        r = byceeb.get(ceeb)
        if r is None:
            print("  !! CEEB not in crosswalk:", ceeb); continue
        r["cds14"] = ""; r["cde_name"] = ""; r["match_method"] = "unmatched_reviewed"; r["match_score"] = "0.00"
        nun += 1
    # refresh cde_name for repaired rows from the components-era directory when available
    dirfile = os.path.join(REPO, "..", "build_outputs", "cde_directory.csv")
    names = {}
    for cand in (dirfile, os.path.join(REPO, "data", "cde_directory.csv")):
        if os.path.exists(cand):
            for d in csv.DictReader(open(cand, encoding="utf-8")):
                names[d["cds14"]] = d["raw_name"]
            break
    for ceeb in REPAIRS:
        r = byceeb.get(ceeb)
        if r is not None and r["cds14"] in names:
            r["cde_name"] = names[r["cds14"]]
    with open(XW, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ceeb", "cds14", "dv_name", "cde_name", "match_method", "match_score"])
        w.writeheader(); w.writerows(rows)
    print(f"repaired {nrep} joins; unmatched {nun}; backup at {os.path.basename(backup)}")

if __name__ == "__main__":
    main()
