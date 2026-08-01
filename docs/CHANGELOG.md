# Changelog

This project is revised in place rather than issued as numbered releases. Entries are dated by the
change; a figure taken from the site should be cited together with the date of the revision it came
from. Data-layer build dates are printed in each page's footer.

Dates before 2026-07-31 are reconstructed from the project's working record and are accurate to the
day of the change, not necessarily to the day of the commit that carried it.

---

## 2026-08-01 — The long view: fourth companion page (`history/`)

**Added**
- `history/` — per-campus annotated series of the admit-rate × school-achievement correlation,
  1999–2025 (gate ≥25 applicants to the campus, ≥40 schools per point), on two independent
  measurement families: **college-bound** (SAT era-bridged z, ACT %≥21 z; 1999–2020) and
  **census** (STAR Stanford 9 for 2000, CAHSEE for 2002 and 2014–15, STAR CST 2003–2013, CAASPP
  2015–2025), with instrument splices drawn dashed and compressed instruments (Stanford 9,
  CAHSEE) drawn hollow. The census family is new to the site: it extends the census-ruler series
  back from 2015 to 2000 using the STAR/CAHSEE school panel built 2026-07-31. Where the families
  overlap they agree; the between-family correlation is stable at ρ ≈ .79 (mean .794 across
  fifteen pre-2015 years; .78–.81 for SAT × CAASPP 2015–19), which is what licenses the page's
  attenuation disclosure — census-ruler correlations read ≈21% toward zero, so the post-2020
  segment is understated, not inflated, relative to the college-bound era.
- Secondary sections, all precomputed: UC applicants per 100 seniors by fixed advantage quintile,
  1999–2025 (Q1/Q5 ratio 2.96 → 2.63 → 1.95 → 1.98); AP exams per 100 seniors and the share
  scored 3+, by quintile, 1999–2020 (its own fixed panel of 757 schools — exams, not students;
  totals after 2005-06 derived from the score distribution); the enrollee-minus-all-tester SAT
  reading gap, 2006–2015 (mean +76 points, positive in 99.9% of 6,121 school-years, rising
  ≈69 → ≈90); applicant-GPA drift at flat SAT, 2010–2016 (+0.0067 GPA/yr across 301 flat-SAT
  schools, 70% rising), paired with the AP-expansion null (r = +0.04 against the grade-climb
  index; the split halves carry identical indexes, 0.127 vs. 0.126).
- `history/data_history.js` (static, ≈95 KB) built by `build/build_history_data.py` from the
  AP/SAT/ACT test-context panel, the STAR/CAHSEE census panel and spine, the correlation-study
  counts compilation, and the precomputed analysis outputs. Verified by
  `build/verify_history_anchors.py` — 50/50 checks, including the Berkeley 2016 anchor
  (r = +0.4965, n = 440) reproduced from raw sources by an independent code path, every
  census-arc spot value, every two-rulers year, and all secondary-exhibit statistics — and by a
  43-assertion jsdom suite, `build/test_history_page.js`.
- Navigation: `history/` added to the main page's companions paragraph and to the backlink rows
  of `context/`, `trends/` and `denied/`; a companion-page paragraph added to the README.

**Known**
- The correlation series' counts come from the same compilation the correlation study used, not
  `data/dv_admissions_all9.csv`; under the 25-applicant gate the two sources give identical
  results at the anchor (checked exactly: r = +0.4965, n = 440 either way). No usable census
  measure exists for the 2001 admission cycle; CAASPP 2020 and 2021 are absent (cancelled /
  excluded as non-representative); the 2001 CAHSEE administration was a voluntary grade-9
  sitting and is excluded throughout.

## 2026-07-31 — Admitted vs. denied: counts universe repaired

**Fixed**
- The derived denied dataset drew its applicant and admit counts from `school_year_wide.csv` in the
  correlation-matrix working folder, which was assembled for that study and covers only **1,181
  CEEBs**. **355 schools** the GPA extraction knows about are absent from it entirely (0 of 355
  present, against 1,181 of 1,181 for the schools that worked). They reached the page with an
  admitted-GPA series and **no volume at any campus in any year**, and therefore no derivable denied
  series, no scatter dot and no grid row — 23.1% of the listed universe. Six of them collide on name
  and city with a live code and showed as duplicate entries in the school picker (Gompers Prep,
  Crawford and Lincoln in San Diego, Aliso Niguel, Lawndale, East Bay Innovation), which is how the
  defect surfaced.
- The nine per-campus rows are now taken from `data/dv_admissions_all9.csv`, which covers the full
  CEEB universe and carries the 2026-07-30 offset repair. Validated before the swap: against the
  previous file it agrees **exactly on all four fields across 244,944 overlapping cells — zero
  disagreements** — and adds 10,125 applicant and 4,226 admit values it lacked.
  `build/repair_denied_counts_from_dv_20260731.py`, with the pre-repair file preserved as
  `data/school_campus_year_admitted_denied_pre_dv_counts_20260731.csv`.
- Effect: all 355 recover counts, 61 of them now show a derivable denied series (the rest stay masked
  at fewer than 10 denials); the school universe goes **1,536 → 1,607**; displayable denied-GPA
  school-years 129,556 → 129,754. In volume the affected schools are small — 85,745 applications
  against 9,298,231, or 0.91%, median 158 across 32 years against 4,899 — so **every pooled mean on
  the page moved by less than 0.005 GPA** (median 0.00016, max 0.0041). No previously published value
  is contradicted.

**Known, and documented on the page**
- Universitywide rows are unchanged: Universitywide is not the sum of the campuses, the wide file is
  its only source, and `dv_admissions_all9.csv` has no Universitywide column. Schools outside the wide
  file therefore keep a blank systemwide row — blank meaning not published here, never zero.
- For four of the six reissued-code pairs the systemwide row is filed under the later code across the
  whole span while the campus rows follow the code each year was reported under, because the two UC
  files resolve the code change differently. 39 school-years. Applications are conserved across the
  swap (47,295 → 48,002 over the six pairs; the increase is coverage the wide file lacked).

## 2026-07-31 — Admitted vs. denied page: legibility revision

**Changed**
- Section headings are now plain descriptions of what is plotted — *Admitted and denied GPA by year*,
  *GPA by campus and year*, *Every school in one year* — replacing the earlier figurative names
  ("the wedge timeline", "the wall", "the field"). Body copy follows suit.
- **The page now opens on all California public high schools pooled**, not on a single default school.
  The school box starts empty and carries a clear (×) control; typing a name narrows every view to
  that school. Each campus-year therefore shows a marginal: applicants and admits summed over every
  school whose GPA UC published that year, admitted mean = Σ(N_adm·GPA_adm)/ΣN_adm, denied mean = the
  same moment identity applied to the pooled totals. Because it is applied to totals, the pooled
  denied mean is **not** affected by the per-school n<10 mask. Pooled counts are the counts of the
  contributing schools (surfaced on hover and in a new *Schools pooled* table column), not UC's campus
  grand total — a school-year with suppressed GPA cannot enter a GPA-weighted mean.
- *GPA by campus and year*: the color ramp was carrying almost no information (a narrow single-hue
  blue fixed at 3.00–4.35 against values that mostly sit above 3.5). Replaced with a wide-range
  sequential scale (ColorBrewer YlGnBu-9) **fitted to the values on screen**, plus a second mode,
  *Difference from average*, on a diverging color-blind-safe scale (PRGn-9): a selected school
  against the all-school average for the same campus, year and strip; the pooled view against UC
  systemwide. Cells with no data are now a hatched backing rather than white space, so a suppressed
  cell can never be read as a pale value.
- *GPA by campus and year*: row labels split into two columns — campus in one, `admitted` / `denied`
  in the other. The old single `adm / den` sub-label read as a ratio and made the campus name look
  like a total.
- The derivation-and-caveats block moved out of the header to the foot of the page, above *Data
  vintage*; the intro links down to it and the link expands it. It opened the page on a wall of
  method before the reader had seen a chart.
- Prose set in American spelling throughout (color, gray, enrollment).
- *Every school in one year*: axes now auto-fit to the schools (≈0.8 GPA points across rather than a
  fixed ≈1.2 with the cloud in one corner; 99.3% of dots land inside the frame at the default view),
  and the panels are **zoomable — scroll to zoom, drag to pan, double-click or *Reset zoom* to
  restore**, with all three years locked to one view. Both axes keep an identical GPA scale, so the
  admitted = denied diagonal stays at 45°. Added a pooled all-schools marker on every panel and a
  *Schools that moved furthest* shortcut row (largest displacement in the admitted/denied GPA plane
  between the outer two selected years, applicants ≥ 40 in both).

**Verified**
- 54/54 headless assertions in a real browser: payload-vs-rendered dot and cell counts, the pooled
  arithmetic, two-column labels, ramp coverage, neutrality of the systemwide row in relative mode,
  auto-fit coverage, wheel-zoom / drag-pan / reset, wheel not stealing page scroll, label containment,
  school search including the CEEB traps, campus switching, and no console errors.
- **24,053 rendered table values across 130 school × campus selections** re-derived independently from
  `data/school_campus_year_admitted_denied.csv` in Python — 0 mismatches. The pooled moment identity
  holds for all 299 campus-years.
- `denied/data_denied.js` was rebuilt and is identical to the previous payload except for the new
  `agg` block: `schools` and `series` compare equal element-for-element.

## 2026-07-31 — Admitted vs. denied page

**Added**
- A third companion page, [`denied/`](../denied/): the GPA gap between the students a campus admitted
  and the students it denied, per California public high school × campus (9 + Universitywide) × year,
  fall 1994–2025. Three views — a dumbbell *wedge timeline* (dot area = students), a paired-row
  heatmap *wall* (all campuses × all years on one screen), and an all-school *field* (admitted GPA vs.
  denied GPA, three year snapshots on shared axes).
- Denied volume = applicants − admits; denied mean GPA recovered by moment arithmetic,
  (N<sub>app</sub>·GPA<sub>app</sub> − N<sub>adm</sub>·GPA<sub>adm</sub>) / N<sub>denied</sub> — exact given the
  published means. Derived denied GPA is masked at build time when fewer than 10 students were denied
  (noise-dominated) or the value falls outside (0, 5); suppressed cells stay blank, never zero.
- `data/school_campus_year_admitted_denied.csv` (the derived dataset; GPA carries the 2026-07-30
  campus-label-offset repair) and `scripts/make_denied_data.py`, which builds `denied/data_denied.js`
  from it over the site's school-name universe (community-college and unidentifiable source codes
  excluded). NB: the counts universe was repaired on 2026-07-31, below — the figures stated in this
  entry (1,536 schools; 69 of 129,625 displayable denied-GPA school-years) are the pre-repair ones.
- Verified: den_gpa re-derives from the published counts and means in all 481 sampled rows where both
  exist; a 616 school-year sample of *rendered* page values matches an independent recompute from the
  CSV digit-for-digit; CEEB traps asserted in the build (052980 Mission SF ≠ 052904 San Fernando,
  051984 University HS Irvine, 052970 Lowell).

**Changed**
- The explorer's companions paragraph and the context/trends backlink rows now link `denied/`.
  No anchors or chart logic on the existing pages were touched.

## 2026-07-31 — Housekeeping

**Added**
- A uniform *Data vintage* block on the explorer, the context page and the trends page, stating the
  coverage of every input series and the date of last revision.
- Series-identity notes on the trends page: each chart now carries a line naming the publisher and
  universe of the series drawn, and the methods panel tabulates the differences between the
  systemwide, campus-dashboard, per-school and federal series.
- This changelog, and a suggested-citation line in the README.

**Changed**
- `scripts/scan_local_correlation.py` extended to the five school racial-composition variables added
  on 2026-07-09; `data/local_correlation_scan.csv` regenerated (360 → 450 cells; the 360 previously
  published cells are unchanged to the digit).
- The unduplicated-pupil axis on the explorer was still labeled *Poverty / high-need — UPP %*, the
  gloss the rest of the site dropped on 2026-06-16. It now reads *Unduplicated pupils — UPP %
  (FRPM/EL/foster, gr 9–12)*, matching the context page and the README.
- The copyright line in `LICENSE` was brought into line with the repository's name; the terms are
  unchanged.

**Fixed**
- On screens near 390 px wide, the context page's four-view switcher was laid out in a half-width
  cell. Its buttons could not shrink below their own minimum width, so they overflowed the control
  and were clipped: *Twin schools* and *What explains more?* could not be reached on a phone. The
  switcher now takes the full row and wraps to two rows of two.

---

## 2026-07-30 — GPA axes repaired; school-identity repair, round 2

**Fixed**
- A one-position campus-label offset in the source's GPA tab — whose campus list begins with a
  Universitywide row, unlike the counts tabs — had assigned each school's applicant, admit and
  enrollee GPA to the neighboring campus. The offset was corrected and the whole chain rebuilt.
  Corrected values for the correlation of admit rate with applicant-pool GPA and with admit GPA
  (pooled 2023–2025, schools with at least 30 applicants): Berkeley −0.06 / −0.16, San Diego
  −0.46 / −0.57. Counts, admit rates and every statistic not involving GPA were never affected.
  Figures on the GPA axes circulated before this date should be replaced.

**Changed**
- 29 further entries in the CEEB↔CDS school crosswalk resolved against the schools'
  own records: 26 contested joins decided on evidence, 2 filled, 1 set to unmatched, and 1
  district correction. Aggregate correlations move by no more than 0.01; the effect is on
  individual school profiles and matched pairs.
- An internal metric-role identifier was renamed for consistency. No user-facing text changed.

---

## 2026-07-25 — Application behavior; context divergence flag; school-identity repair, round 1

**Added**
- Context page: an *Application behavior — who applies* group of context variables — the school's
  application rate to the selected campus, its application rate to the other eight campuses, and its
  raw applicant volume — so that the achievement–admissions association can be conditioned on who
  applies rather than only on where the school sits.
- Context page: applicant-pool GPA and admit GPA selectable as outcomes, with GPA-aware axes,
  gaps and slopes throughout.
- Context page: a second *also hold fixed* control, giving partial correlations and matched pairs
  conditioned on two variables at once.
- Context page: a flag on schools whose student-body need diverges from that of the surrounding
  tract, stating the direction of the divergence, the school's own unduplicated-pupil percentage and
  the statewide median for reference. Levels of tract poverty and unduplicated-pupil percentage are
  not commensurable; the comparison is made in rank space.

**Changed**
- 95 crosswalk joins repaired to the school's own CDE record and 6 with no valid CDE target set
  to unmatched, after an audit of all 1,549 joins. The most visible case had one school carrying a
  similarly named neighbor's academic profile.

---

## 2026-07-09 — School racial composition

**Added**
- Context page: five school-level composition variables — the grade 9–12 shares Hispanic/Latino,
  White, Asian (including Filipino), African American, and underrepresented — from CDE enrollment
  files, 2013–2025, keyed to the same grade-11 alignment as the other school measures.

---

## 2026-07-06 — School student measures; local-correlation view

**Added**
- Context page: the grade-11 shares socioeconomically disadvantaged and English learner, taken from
  the per-group reported enrollment in the CAASPP research files (the district workbooks publish only
  the combined unduplicated-pupil percentage). Context variables are now grouped into school-level
  and neighborhood-level sets.
- Context page: a *local correlation* view — the conditional correlation function, Gaussian-kernel
  estimated on the context percentile rank, with a permutation no-variation envelope and a linear
  moderation test. `scripts/scan_local_correlation.py` reproduces the same estimator independently
  and writes `data/local_correlation_scan.csv`.

---

## 2026-07-02 — Two companion pages

**Added**
- `context/` — a neighborhood-context companion. Tract-level American Community Survey measures are
  assigned to each school from its coordinates via the Census Geocoder and joined to the panel, and
  the page asks how much of the achievement–admissions association survives conditioning on them:
  a conditioning scatter with a brushable context band, matched *twin schools* with near-identical
  contexts and large achievement gaps, and a per-campus variance decomposition.
- `trends/` — an outcomes-over-time companion covering entering cohorts back to 1999. One chart
  engine, eight comparisons: systemwide retention, graduation, time to degree and final GPA split by
  ethnicity, Pell and first-generation status and their crosses; the nine campuses' federal six-year
  completion; per-high-school and per-community-college series; GPA-band rates; degrees conferred by
  field; and earnings and debt. Each chart carries its universe badge, cohort sizes and a CSV
  download, and cells whose completion window has not closed are withheld rather than shown as zero.
- Later rounds through 2026-07-06 added full-precision GPA-band rates in place of estimated ones,
  a UC San Diego series by school of major, and a UC Berkeley series by detailed race, gender,
  first-generation status and access-program markers.

---

## 2026-06-16 — Public text

**Changed**
- User-facing text made neutral throughout: the axis and its explanations now speak of academic
  strength, anchored to schools rather than to individuals, and evaluative wording was removed.
  Methodological caveats were kept and only their tone adjusted.
- The color axis is described by its actual definition — the CALPADS/LCFF unduplicated-pupil
  percentage, being the share of a school's students who are low-income, English learners or foster
  youth, counted once — rather than glossed as a poverty rate. Schools above the 75 percent
  threshold are marked LCFF+.
- Documentation rewritten in an impersonal voice and made self-contained, with no references to
  files outside the repository.
- The repository was renamed; the previous Pages address is preserved by a redirect.

---

## 2026-06-09 — UC retention and graduation by high school

**Added**
- The UC Information Center freshman-outcomes dashboard, per source high school and entry cohort
  1999–2024, integrated as four measures: prior six-year completion, weighted over the cohorts
  observable by decision time, as an academic measure; and the period's own first-year retention,
  four-year and six-year completion as outcomes. Campus-specific versions of the outcome measures
  followed, alongside the UC-wide ones.
- A mobile layout: stacked controls, viewport-sized chart, one-finger page scroll with zoom on
  wheel or two touches, and a tapped school's profile scrolled into view.

**Fixed**
- Graduation measures pooled across all campuses were not labeled as such on a single-campus view,
  which made a school with no admits at the selected campus appear to have a retention rate there.
  Scope is now stated in every label, tooltip and caveat.
- A school profile summed suppressed funnel cells as zero. Counts suppressed in every year of the
  selected period now render as an em dash, with a legend noting that blank is not zero.

---

## 2026-06-07 — First public version

**Added**
- The interactive explorer: one dot per California high school, a campus selector, a year or pooled
  period selector, a scatter with a least-squares fit and a live Pearson correlation, and a
  strip/beeswarm alternative. Academic and context measures on the horizontal axis; eight funnel
  rates — admit rate, yield, application rate, and counts against A–G eligible and against grade
  9–12 enrollment — on the vertical. Color by unduplicated-pupil percentage or LCFF+ status, a
  minimum-applicant filter, school search, and a per-school profile with a sparkline.
- A per-year panel covering all nine undergraduate campuses, rebuilt from the source dump, and the
  scripts that regenerate every published file from it.
- Applicant-pool GPA and admit GPA as academic axes, from UC's recalculated weighted-capped
  high-school GPA. The admit GPA is partly downstream of the admission decision and is flagged as
  such in the page.
- A–G eligibility cleaning. CDE's published *met UC/CSU* count collapses to near zero for a number of
  school-years — a course-data reporting failure, not an admissions fact — which left raw produces
  impossible rates above one. Isolated collapses flanked by healthy years are imputed from the
  school's own history; collapses without a safe estimate and chronic non-reporters are suppressed
  rather than guessed.

**Fixed**
- Rates computed as a ratio of sums over jointly observed years collapse when the numerator is
  suppressed in precisely the high-count years, producing artifacts such as a 100 percent yield on
  three admits. A coverage gate now requires at least half the denominator mass to fall in years
  where the numerator is also observed; rates below it are drawn hollow, excluded from the headline
  correlation and shown in the profile with the count of suppressed years. Recomputing instead from
  funnel totals — which would treat a suppressed cell as zero — was rejected as it inverts the sign.
- Strip-plot dots are pinned to their value on the horizontal axis, so a dot's position always
  matches the value in the side panel.
- School-years whose funnel count exceeds their recorded grade 9–12 enrollment, from corrupted or
  mis-joined enrollment figures, are dropped from the per-enrollment measures rather than plotted.
