# Changelog

This project is revised in place rather than issued as numbered releases. Entries are dated by the
change; a figure taken from the site should be cited together with the date of the revision it came
from. Data-layer build dates are printed in each page's footer.

Dates before 2026-07-31 are reconstructed from the project's working record and are accurate to the
day of the change, not necessarily to the day of the commit that carried it.

---

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
