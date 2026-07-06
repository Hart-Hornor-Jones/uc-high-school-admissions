#!/usr/bin/env python3
"""
parse_caaspp_groups.py — grade-11 student-group composition from CAASPP research files.

For each school and test year, reads the CAASPP Smarter Balanced research file and
extracts the grade-11 "Total CAASPP Enrollment" for three student groups:
  001 All Students, 031 Socioeconomically disadvantaged, 160 English learner (excl. RFEP)
and writes per-school composition rates:
  sed_pct = enrolled SED / enrolled all,  el_pct = enrolled EL / enrolled all.

Enrollment counts are census (CALPADS) fields, not test outcomes, so they are present
even in low-participation years (2021 is kept here although scores are excluded from
the panel). A group row that is absent for a school counts as 0 students; a row whose
enrollment field is suppressed/unparseable is treated as missing (school dropped for
that rate). ELA rows only (subject 01), so no double counting.

Layouts follow parse_caaspp_year.py: "modern" (2024+) has fixed positions; earlier
years are "contig" with a year-specific byte offset for the grade+subject field —
known offsets are hardcoded, unknown years are probed automatically.

RUN FROM the folder containing "CAASPP Data" (or pass --caaspp-dir):
  python3 build/parse_caaspp_groups.py --caaspp-dir "CAASPP Data" \
      --out data/components/school_group_context.csv
"""
import argparse, csv, glob, os, re, sys
from collections import defaultdict

GROUPS = {"001": "all", "031": "sed", "160": "el"}
INT = re.compile(r"\d+")
GS = re.compile(r"^(03|04|05|06|07|08|11|13)(01|02)$")
KNOWN = {2015: 47, 2018: 40, 2023: 40}   # contig grade+subject offsets (2024+: modern)

def probe_offset(path, sample=400000):
    """Find the contig grade+subject offset: the 4-char field position that looks
    like grade+subject on (nearly) every sampled group-001 SB row."""
    hits = defaultdict(int); n = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if ln[22:25] != "001" or ln[25:26] != "B": continue
            n += 1
            if n > sample: break
            for a in range(26, 70):
                if GS.match(ln[a:a+4]): hits[a] += 1
    if not hits: return None
    best = max(hits, key=lambda a: hits[a])
    return best if hits[best] >= 0.95 * min(n, sample) else None

def first_int(s):
    m = INT.search(s)
    return int(m.group()) if m else None

def parse_year(path, year, mode, off, out):
    """out[(cds,'all'|'sed'|'el')] = grade-11 CAASPP enrollment."""
    kept = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if mode == "modern":
                if ln[114:116] != "07": continue          # school-level records
                grp = ln[127:130]
                if grp not in GROUPS: continue
                if ln[130:132] != "11" or ln[125:127] != "01": continue
                cds = ln[0:7] + ln[47:54]; tail = ln[132:180]
            else:
                grp = ln[22:25]
                if grp not in GROUPS or ln[25:26] != "B": continue
                g = ln[off:off+4]
                if g[0:2] != "11" or g[2:4] != "01": continue
                cds = ln[0:14]; tail = ln[off+4:off+44]
                if cds[0:2] == "00" or cds[2:7] == "00000" or cds[7:14] == "0000000": continue
            enr = first_int(tail)
            if enr is None: continue
            out[(cds, GROUPS[grp])] = enr; kept += 1
    return kept

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--caaspp-dir", default="CAASPP Data")
    ap.add_argument("--out", default="data/components/school_group_context.csv")
    a = ap.parse_args()
    files = {}
    for fp in sorted(glob.glob(os.path.join(a.caaspp_dir, "sb_ca20??_all_ascii*txt"))):
        m = re.search(r"sb_ca(20\d\d)_all_ascii", os.path.basename(fp))
        if not m: continue
        yr = int(m.group(1))
        if "math" in os.path.basename(fp): continue        # 2025 math-only file
        files[yr] = fp
    rows = []
    for yr, fp in sorted(files.items()):
        mode = "modern" if yr >= 2024 else "contig"
        off = None
        if mode == "contig":
            off = KNOWN.get(yr) or probe_offset(fp)
            if off is None:
                sys.stderr.write(f"{yr}: could not locate grade field — skipped\n"); continue
        out = {}
        kept = parse_year(fp, yr, mode, off, out)
        schools = sorted({cds for (cds, g) in out if g == "all"})
        n_sed = n_el = 0
        for cds in schools:
            allc = out.get((cds, "all"))
            if not allc: continue
            sed = out.get((cds, "sed"), 0)      # absent group row -> zero students
            el  = out.get((cds, "el"), 0)
            sed_pct = round(100.0 * min(sed, allc) / allc, 1)
            el_pct  = round(100.0 * min(el, allc) / allc, 1)
            n_sed += sed is not None; n_el += el is not None
            rows.append([cds, yr, allc, sed, sed_pct, el, el_pct])
        sys.stderr.write(f"{yr}: mode={mode} off={off} rows_kept={kept} schools={len(schools)}\n")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cds14", "year", "enr11", "sed_n", "sed_pct", "el_n", "el_pct"])
        w.writerows(rows)
    sys.stderr.write(f"wrote {len(rows)} rows -> {a.out}\n")

if __name__ == "__main__":
    main()
