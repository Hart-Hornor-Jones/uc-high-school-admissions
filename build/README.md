> _Note: paths in this runbook are relative to the original project layout. In this repository the curated outputs live in `../data/`. This is the historical pipeline runbook, preserved for reproducibility._

---
output:
  word_document: default
  html_document: default
---
# UC Admissions × School-Merit — Build Scripts (documented)

This folder holds **documented copies** of the build scripts. The code is **byte-for-byte
identical** to the originals in `build_scripts/` — only explanatory comments were added
(verified: every script compiles and has an identical syntax tree to its original). So you
can read, run, and tweak the copies here, and the originals stay as an untouched backup.

Every script also has a full explanation block at the very top (purpose, where to run it
from, how to run it, its inputs and outputs, and what you'd change). This README is the
map that ties them together.

---

## Three rules that explain almost every "file not found"

**1. Run from the project root — with one exception.**
Almost every script uses paths like `CAASPP Data/...` and `Panel Build 2026-06-07/...`
that are relative to the project root. Open a terminal, `cd` into the project-root folder,
and launch scripts as `python build_scripts_documented/<name>.py`.
The **one exception is `extract_dv.py`**, which must be run from *inside* the
`admissions_source_school_consolidated_lean/` folder (its header explains why).

**2. The output folder name is hard-coded: `Panel Build 2026-06-07`.**
That dated string is written into the scripts. If you keep using that folder, everything
just works. If you ever want a fresh dated folder, do a find-and-replace of
`Panel Build 2026-06-07` across the scripts (and create the new folder + its `components/`
and `figures/` subfolders first).

**3. A few intermediate files have to be copied into the panel folder.**
Some scripts *write* a file to `build_outputs/` but later scripts *read* it from
`Panel Build 2026-06-07/`. That copy is a manual step. The three copies are spelled out in
the run order below; if a script can't find an input, a missing copy is the usual reason.

---

## What you need installed

Python 3 with: `numpy`, `matplotlib`, `openpyxl`, `xlrd`.

```
pip install numpy matplotlib openpyxl xlrd
```

(The Excel readers — `openpyxl` for `.xlsx`, `xlrd` for the one `.xls` file — are only
needed by the CUPC / directory scripts.)

---

## Just want to re-make or tweak a figure?

The figures come from three scripts. Each has `# TWEAK:` comments inline marking the colors,
dot sizes, the ≥30-applicant cutoff, titles, figure size, and output resolution — search the
file for `TWEAK:`. None of them re-parse raw data; they read the already-built panel files,
so they're quick and safe to re-run.

```
:: from the project root
python build_scripts_documented\make_figures.py        :: main cross-section chart pack
python build_scripts_documented\then_vs_now.py         :: (run this first — it makes the data)
python build_scripts_documented\then_vs_now_figs.py    :: then-vs-now figures
python build_scripts_documented\yearly_trend.py         :: year-by-year figure (self-contained)
```

Outputs land in `Panel Build 2026-06-07/figures/`. Note `then_vs_now_figs.py` depends on
`then_vs_now.py` having run (it reads a `.tvn_cross.pkl` that the first script writes).

---

## Full rebuild, in order

Commands are shown for **cmd.exe** run from the project root. Two scripts read a file on
standard input with `<` (see the PowerShell note below them).

### Stage A — parse the four raw sources into clean components

```
:: 1) Dependent variable (UC applicants/admits/enrollees). Note the different folder!
cd "admissions_source_school_consolidated_lean"
python "..\build_scripts_documented\extract_dv.py"
cd ..
copy "build_outputs\dv_admissions.csv" "Panel Build 2026-06-07\components\"   :: <-- copy #1

:: 2) CAASPP %met, one year at a time (file piped in on stdin; args set the layout)
python build_scripts_documented\parse_caaspp_year.py 2015 contig15 47 51 < "CAASPP Data\sb_ca2015_all_ascii_v3.txt"
python build_scripts_documented\parse_caaspp_year.py 2018 contig   40 44 < "CAASPP Data\sb_ca2018_all_ascii_v3.txt"
python build_scripts_documented\parse_caaspp_year.py 2023 contig   40 44 < "CAASPP Data\sb_ca2023_all_ascii_v1.txt"
python build_scripts_documented\parse_caaspp_year.py 2024 modern         < "CAASPP Data\sb_ca2024_all_ascii_v1.txt"
python build_scripts_documented\parse_caaspp_year.py 2025 modern         < "CAASPP Data\sb_ca2025_all_ascii_v1.txt"
::  (2016, 2017, 2019, 2022 are already built in components/. They were made the same way
::   with their own offsets; only rebuild them if you delete them — use diag.py to find the
::   offset, mirroring the 2018/2023 pattern.)

:: 3) A-G eligibility  ->  writes straight into components/
python build_scripts_documented\parse_ag.py

:: 4) UPP / LCFF+
python build_scripts_documented\parse_cupc.py
copy "build_outputs\upp_lcff.csv" "Panel Build 2026-06-07\components\"        :: <-- copy #2
```

> **PowerShell note:** Windows PowerShell does not accept `<` for input. For the two
> stdin scripts (`parse_caaspp_year.py` and `diag.py`), either run them from **cmd.exe**,
> or in PowerShell pipe the file in instead:
> `Get-Content "CAASPP Data\sb_ca2024_all_ascii_v1.txt" | python build_scripts_documented\parse_caaspp_year.py 2024 modern`

### Stage B — build the CEEB↔CDS crosswalk

The UC files key on the 6-digit **CEEB** code; the CDE files key on the 14-digit **CDS**
code; there is no shared key, so this stage builds the bridge.

```
python build_scripts_documented\build_cde_dir.py        :: CDE directory (CDS -> name, county)
python build_scripts_documented\build_crosswalk.py      :: pass 1: Gardiner seed + fuzzy match
copy "build_outputs\ceeb_cds_crosswalk.csv" "Panel Build 2026-06-07\"          :: <-- copy #3

python build_scripts_documented\refine_match.py         :: pass 2: token matches -> auto_accepted.csv
python build_scripts_documented\review_unmatched.py     :: (optional) human-review TSV of leftovers
python build_scripts_documented\finalize_crosswalk.py   :: apply hand-verified + auto matches (in place)
```

`finalize_crosswalk.py` overwrites the crosswalk in the panel folder (keeping a
`..._v1_pre_handverify.csv` backup). Manual matches live in the `HV` table at the top of
that script.

### Stage C — merge, then analyze + plot

```
python build_scripts_documented\merge_panel.py          :: the master join -> panel + pooled cross-section
python build_scripts_documented\make_figures.py         :: cross-section chart pack
python build_scripts_documented\then_vs_now.py          :: era stats + .tvn_cross.pkl
python build_scripts_documented\then_vs_now_figs.py     :: then-vs-now figures
python build_scripts_documented\yearly_trend.py          :: year-by-year stats + figure
```

---

## Per-script reference

"Run from" is the working directory; **root** = the project-root folder. `PB` =
`Panel Build 2026-06-07`.

| Script | Run from | Reads | Writes |
|---|---|---|---|
| `extract_dv.py` | `admissions_source_school_consolidated_lean/` | `admissions_freshman_*.csv` | `build_outputs/dv_admissions.csv` |
| `parse_caaspp_year.py` | root | CAASPP file on **stdin** | `PB/components/caaspp_{year}.csv` |
| `parse_caaspp.py` | root | `CAASPP Data/sb_ca*` (5 yrs) | `build_outputs/caaspp_grade11.csv` *(reference; not used by panel)* |
| `parse_ag.py` | root | `A-G Data/acgr*.txt` | `PB/components/ag_eligibility.csv` |
| `parse_cupc.py` | root | `Headcounts/cupc*-912.xls*` | `build_outputs/upp_lcff.csv` |
| `build_cde_dir.py` | root | `A-G Data/`, `Headcounts/` | `build_outputs/cde_directory.csv` |
| `build_crosswalk.py` | root | `Gardiner/`, `A-G`, `Headcounts/`, `build_outputs/dv_admissions.csv` | `build_outputs/ceeb_cds_crosswalk.csv` |
| `refine_match.py` | root | `build_outputs/cde_directory.csv`, `PB/components/dv_admissions.csv`, `PB/ceeb_cds_crosswalk.csv` | `build_outputs/auto_accepted.csv` |
| `review_unmatched.py` | root | same as refine_match | `build_outputs/unmatched_review.tsv` *(diagnostic)* |
| `finalize_crosswalk.py` | root | `build_outputs/auto_accepted.csv`, `cde_directory.csv`, `PB/ceeb_cds_crosswalk.csv` | `PB/ceeb_cds_crosswalk.csv` (+ backup) |
| `merge_panel.py` | root | `PB/ceeb_cds_crosswalk.csv`, `PB/components/*` | `PB/school_year_panel.csv`, `PB/pooled_cross_section_2023_2025.csv` |
| `make_figures.py` | root | `PB/pooled_cross_section_2023_2025.csv` | `PB/figures/chart_pack.png` (+ 2 scatters) |
| `then_vs_now.py` | root | `PB/ceeb_cds_crosswalk.csv`, `PB/components/*` | `PB/then_vs_now_summary.csv`, `PB/.tvn_cross.pkl` |
| `then_vs_now_figs.py` | root | `PB/.tvn_cross.pkl` | `PB/figures/then_vs_now_main.png`, `..._deciles.png` |
| `yearly_trend.py` | root | `PB/ceeb_cds_crosswalk.csv`, `PB/components/*` | `PB/then_vs_now_yearly.csv`, `PB/figures/then_vs_now_yearly.png` |
| `diag.py` | anywhere | CAASPP file on **stdin** | *(prints only)* |

---

## Things worth knowing before you change anything

**Blank ≠ zero.** In the admissions data, a blank admit count means *suppressed* (fewer than
~3 admits), not zero. Roughly a third of Berkeley applicant-schools have suppressed admits.
The scripts write blanks as empty cells and leave admit rate blank — they never treat a
blank as 0.

**2021 is excluded on purpose.** CAASPP 2020 was cancelled and 2021 had only ~⅓ normal
participation, so the merge and the yearly trend skip `caaspp_2021` even though the file
exists.

**Common edits, and where to make them:**

- *Add a campus* (e.g. UCLA): the `CAMPUS` set near the top of `extract_dv.py`, then re-run
  the crosswalk and merge stages.
- *Change which schools are circled in the charts:* the `CASE` dictionary in
  `make_figures.py` (and the same idea in the figure scripts).
- *Add a hand-verified crosswalk match:* the `HV` table at the top of
  `finalize_crosswalk.py` — add `"CEEB": ("CDS14", confidence)`.
- *Change the minimum-applicants cutoff (default 30) or figure styling:* the `# TWEAK:`
  comments in the three figure scripts.

**Two ID universes.** UC sources (admissions) use the 6-digit CEEB code; CDE sources (CAASPP,
A-G, CUPC) use the 14-digit CDS code. The crosswalk is the only thing connecting them, which
is why so much of the pipeline is about building and finalizing it.
