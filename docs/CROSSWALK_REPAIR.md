# CEEB ↔ CDS crosswalk repair (2026-07-25)

UC reports admissions by source school under 6-digit CEEB codes; every California
covariate (CAASPP, A–G, enrollment, UPP, tract context) is keyed by 14-digit CDS
codes. The two universes share no key, so the panel joins them through
`data/ceeb_cds_crosswalk.csv`. This note documents a defect found in that
crosswalk's fuzzy matches, the audit that scoped it, and the repair applied by
`build/repair_crosswalk_20260725.py`.

## The defect

A spot check of a twin-schools pair surfaced it: CEEB 051830, "WESTCHESTER
ENRICHED SCIENCE MAGNET" (Los Angeles), was joined to CDS `19650601939602` —
which the CDE School Directory identifies as **West High, Torrance Unified**.
Every CDE-side value on that school's dot (CAASPP ≈ 63% average met, A–G
eligible counts, enrollment, UPP, and the census tract in Torrance) belonged to
West High; only the UC funnel counts were Westchester's. The school's real CDE
record (`19647331939479`, the Westchester campus, listed as "WESM Health/Sports
Medicine") tests near 24% average met with UPP above 80%.

The mechanism is in the first-pass matcher (`build/build_crosswalk.py`): after
normalization it awards a score of 0.94 whenever one name **contains** the
other within a county — and `WEST` is contained in `WESTCHESTER ...`. The same
rule glued a number of smaller schools, academies and charters to a similarly
named host school in the same county.

## The audit

All 1,549 crosswalk rows were audited: 65 CDS codes were shared by two or more
CEEBs, and 13 further fuzzy joins had no name-token overlap at all. Every
suspect was reviewed against the current CDE public-schools directory, the
component files (which CDS codes actually carry CAASPP/A–G/CUPC rows), and
targeted CDE-directory checks. Three findings shaped the repair:

1. **Name disagreement is evidence, not proof.** Several apparent mismatches
   are renames in place and were verified correct and kept: Sir Francis Drake →
   Archie Williams High; AIMS College Prep; Blue Ridge Academy (ex-Inspire
   Kern); ABLE Charter; Stella High Charter Academy; San Benito High →
   Hollister High; CATCH Prep = Crenshaw Arts-Technology Charter High.
2. **Some sharing is real.** CDE sometimes consolidates a campus under one
   record while UC carried era- or program-specific CEEBs. Verified cases are
   kept and documented rather than "fixed": era-split duplicate CEEB records of
   one school (e.g., Palisades, Gompers, Lincoln (San Diego), Crawford, Locke,
   Hanford West, Aliso Niguel, Lawndale, EBIA, Aspire Richmond), the San Diego
   High complex-era CEEB alongside the school's own (funnel counts split across
   both records in 2006–2016), and Bayfront Charter High, which CDE reports
   under Mueller Charter (Robert L.).
3. **The rest were wearing another school's data.** Examples repaired to their
   own CDS: L.A. County High School for the Arts (was on Los Angeles Senior
   High), Oakland Military Institute (was on Oakland High), the three Magnolia
   Science Academies, Leadership Public Schools Hayward and Richmond, STEM
   Academy at Bernstein (was on Hollywood High), Alliance Marine-Innovation and
   Technology (was on Alliance Ouchi-O'Donovan), Wonderful College Prep
   (was on Delano High), Village Academy (Pomona), Crenshaw High (to the
   campus's continuing record, Crenshaw STEM Magnet), the Roosevelt and San
   Diego High complex small schools, and Westchester itself.

## The repair

`build/repair_crosswalk_20260725.py` applies the verified decision table to
`data/ceeb_cds_crosswalk.csv` in place (writing a `*_pre_repair_20260725.csv`
backup): **95 joins repaired** to the school's own CDS (`match_method:
hand_verified`, with the evidence recorded in the script) and **6 set to
`unmatched_reviewed`** where no valid CDE target exists (Castlemont
Business & Information Technology, the San Diego Media/Visual & Performing Arts
complex school, Southeast Academy, Leadership Public Schools College Park,
VSC-Emerson, San Benito County Evening) — those schools keep their UC funnel
data and simply carry no CDE covariates. Shared CDS codes fell from 65 to 22,
all of the documented kinds above. Rebuilding the panel from the repaired
crosswalk changed rows for exactly the repaired CEEBs and no others.

## Effect on results

Aggregate statistics barely move; per-school displays are the point. Pooled
2023–25, ≥30 applicants, campus admit rate (site conventions):

| Campus | r(achievement → admit) | r(SES → admit) | partial r(ach \| SES) |
|---|---|---|---|
| Berkeley | −0.231 → −0.223 | −0.346 → −0.343 | −0.064 → −0.054 |
| Los Angeles | −0.158 → −0.150 | −0.203 → −0.199 | −0.061 → −0.055 |
| San Diego | −0.548 → −0.543 | −0.562 → −0.566 | −0.366 → −0.355 |

Application-behavior conditioning is likewise stable (Berkeley partial r given
own-campus application rate −0.179 → −0.173; San Diego −0.415 → −0.410; given
application rate and UPP together, San Diego +0.000). Every page statistic was
re-verified after the rebuild against an independent implementation (171
comparisons, agreement at 1e-9).

## Rebuild order

```bash
python3 build/repair_crosswalk_20260725.py     # (already applied; idempotent)
python3 scripts/build_panel_all9.py            # panel_all9_by_year.csv
python3 scripts/make_site_data.py              # data.js + cross_section_all9.csv
python3 scripts/make_context_data.py --skip-extract   # context/data_context.js
python3 scripts/scan_local_correlation.py      # local_correlation_scan.csv
```

## Remaining limitations

- The 22 remaining shared CDS codes are documented sharing (era splits, campus
  consolidations), not mis-joins; where both CEEB records were active in the
  same years (San Diego High 2006–2016; Palisades pre-2008; smaller cases) the
  school's applicants are split across two dots for those years.
- Six reviewed schools have no covariates by design (`unmatched_reviewed`), and
  three long-closed records (`unmatched`) remain from the original build.
- Schools repaired to long-closed CDS records may predate the component files
  (CAASPP starts 2015; A–G 2017; CUPC 2016) and so carry funnel data only.

---

# Round 2: the reconciliation-worksheet pass (2026-07-30)

The CSU crosswalk project independently re-verified CDS assignments for the
same CEEB universe (web-verification rounds, 2026-07-29). Reconciling that
lineage against this repo's repaired copy (`hs data/ceeb_cds_reconciliation_
worksheet.csv`, 66 CEEBs) showed the repo still carried ~2 dozen first-pass
fuzzy joins of the same defect class that round 1 fixed — surfacing on rows
round 1's audit had no reason to suspect (they shared no CDS and had name-token
overlap). It also validated round 1: 59 of its repairs were independently
re-confirmed by the web rounds.

## The repair

`build/repair_crosswalk_20260730.py` applies Hart's worksheet adjudications
(2026-07-29/30) plus one further find, in place, with a
`*_pre_repair_20260730.csv` backup (not committed):

- **26 conflict rows remapped** to the verdict CDS. Typical of the class:
  Dr. James J. Hogan High (Vallejo) had James **Logan** High (Alameda county);
  Oasis High (Oakland) had Oasis (Fallbrook); Sacramento High had the SCOE
  special-ed record; Vaughn Next Century had Century High (Alhambra); both
  Fontana-area OFY/Entrepreneur CEEBs had Fontana High itself; Renaissance Arts
  Academy (LAUSD) had Long Beach's Renaissance HS for the Arts.
- **2 nulls filled from v2 evidence** (San Benito County Evening → shares
  Hollister High's record; Castlemont BIT → shares Castlemont High's record),
  superseding round 1's `unmatched_reviewed` for those two.
- **1 nulled**: LA River School's fuzzy value was Los Angeles Senior High's
  CDS; no verdict record exists yet, so covariates are removed, not borrowed.
- **Thurgood Marshall Academic HS (053066)**, found by the 2026-07-30 Mission
  High fact-check: was joined to Thurgood Marshall K-12, **Compton** Unified;
  UC's own dimension places it in San Francisco. Now `38684783830403`
  (Marshall (Thurgood) High, SFUSD). Both the repo and the CSU v2 crosswalk
  shared this defect; the worksheet gained the row for the v2 side.

Rows Hart deliberately left OPEN are untouched: the 8 program/complex POLICY
rows (own closed CDS vs parent/Active successor — Crawford ×3, SD Intl/LEADS,
Palisades, Hamilton, Mendocino), 050446 Santa Cruz Alternative, and 053892
Crawford Multimedia.

## Verification

Rebuilt panel → data.js → cross_section_all9 → data_context.js → scan.
The data.js diff touches exactly 23 CEEBs (the 29 applied rows minus 6 with no
post-2015 site presence), and within changed schools the UC funnel counts and
GPA columns are bit-identical — only CDS-keyed covariates moved. A jsdom pass
over the live page shows 14 of 18 campus×period anchor correlations unchanged
at two decimals; four move by 0.01 (LA p2325 −0.15→−0.14, Davis −0.23→−0.22,
Riverside +0.49→+0.50, LA p1619 +0.01→+0.02). The round-1 sensitivity bound
still holds in its own terms: **dropping** the affected schools moves anchors
by ≤ 0.0023; the visible movement comes from corrected covariates *entering*
(e.g., Renaissance Arts' real CAASPP is 89% average met, not Long Beach's 32%;
Vaughn and Sacramento Charter enter with their own records).

## Cost worth knowing: same-school vintage remaps

For several verdicts the old and new CDS are the *same school* under two
authorizer/district vintages, and the component files carry the school's
history under the **old** prefix. Those schools lose site covariates until the
join becomes vintage-aware (a CDS-alias table would fix it): High Tech High
Chula Vista (90 campus-year rows), LPS Oakland R&D (63), High Tech High Mesa
(36), Altus South Bay-Sweetwater, Santa Cruz Cypress Charter, and part of
Alternatives in Action's span. Across all applied rows the panel's covariate
coverage is net-flat (276 school-campus-years gained, 276 lost); the losses are
either wrong-school data removed (the point) or this vintage effect.
