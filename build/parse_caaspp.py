#!/usr/bin/env python3
# =============================================================================
#  parse_caaspp.py  -  (EARLIER all-in-one CAASPP parser - reference only)
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.  See README.md
#
#  WHAT IT DOES
#    An earlier version of the CAASPP parser that loops over a FIXED set of
#    years (2015/2018/2023/2024/2025, defined in the YEARS dict below) and
#    writes ONE combined file. The actual panel is built from the per-year
#    files in components/ produced by parse_caaspp_year.py (which covers all
#    nine years 2015-2025). This file is kept because its YEARS dict is the
#    handy reference for each year's mode + byte offsets, and for spot-checks.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/parse_caaspp.py
#
#  INPUTS   CAASPP Data/sb_caYYYY_all_ascii_*.txt  (only the years in YEARS)
#  OUTPUTS  build_outputs/caaspp_grade11.csv  (combined; NOT used by the panel)
#
#  GOTCHAS / NOTES
#    - The panel uses Panel Build .../components/caaspp_YYYY.csv (per-year),
#      NOT this combined file. Prefer parse_caaspp_year.py for rebuilds.
#    - The detailed layout-decoding notes are in the docstring just below.
# =============================================================================

"""Parse CAASPP Smarter Balanced research files -> grade-11 school-level %Met&Above (ELA+Math).
Layouts decoded & arithmetic-validated against Berkeley High (CDS 01-61143-0131177).
%Standard Met and Above is the 3rd 'overall-block' percentage: %exceeded + %met = %met&above,
and %met&above + %nearly + %notmet = 100. We locate the block by that arithmetic, so the
exact byte offsets of the % columns never need to be guessed."""
import re, csv, os, sys
BASE="CAASPP Data"
YEARS={
 "2015":dict(path=f"{BASE}/sb_ca2015_all_ascii_v3.txt", mode="contig15", ggss=(47,51)),
 "2018":dict(path=f"{BASE}/sb_ca2018_all_ascii_v3.txt", mode="contig",   ggss=(40,44)),
 "2023":dict(path=f"{BASE}/sb_ca2023_all_ascii_v1.txt", mode="contig",   ggss=(40,44)),
 "2024":dict(path=f"{BASE}/sb_ca2024_all_ascii_v1.txt", mode="modern"),
 "2025":dict(path=f"{BASE}/sb_ca2025_all_ascii_v1.txt", mode="modern"),
}
PCT=re.compile(r'\d+\.\d{2}')
INT=re.compile(r'\d+')
def find_block_dec(tail):
    """tail with 2-decimal percentages: return (exc,met,metabove) for first valid overall block + mean,N if findable."""
    toks=[(m.start(),float(m.group())) for m in PCT.finditer(tail)]
    vals=[v for _,v in toks]
    for i in range(len(vals)-4):
        a,b,c,d,e=vals[i:i+5]
        if abs(a+b-c)<=0.05 and 99.0<=c+d+e<=101.0 and c<=100.0:
            return c
    return None
def find_block_int(tail):
    """tail with integer percentages (2015). Need a decimal mean to anchor, then 5 ints."""
    # tokens in order; ints that are plausible percents 0..100
    toks=tail.split()
    nums=[]
    for t in toks:
        if re.fullmatch(r'\d+', t): nums.append(int(t))
        elif re.fullmatch(r'\d+\.\d', t): nums.append(None)  # mean marker (1-decimal)
        # ignore others
    # find window of 5 consecutive ints (no None between) with arithmetic
    for i in range(len(nums)-4):
        w=nums[i:i+5]
        if any(x is None for x in w): continue
        a,b,c,d,e=w
        if a+b==c and 99<=c+d+e<=101 and c<=100:
            return float(c)
    return None

def mean_and_n(tail):
    m=re.search(r'(\d+)\s*(\d{3,4}\.\d)\b', tail)  # N then mean-scale (1 decimal)
    if m: return float(m.group(2)), int(m.group(1))
    mm=re.search(r'\d{3,4}\.\d\b', tail)
    return (float(mm.group()) if mm else None), None

def school_level_contig(cds):
    return cds[0:2]!="00" and cds[2:7]!="00000" and cds[7:14]!="0000000"

data={}  # (cds,year) -> dict
stats={}
for yr,cfg in YEARS.items():
    path=cfg["path"]; mode=cfg["mode"]
    n_lines=0; n_ela=0; n_math=0; n_fail=0
    with open(path, encoding="latin-1") as fh:
        for ln in fh:
            n_lines+=1
            if mode=="modern":
                if ln[114:116]!="07": continue
                if ln[130:132]!="11": continue
                subj=ln[125:127]
                if subj not in ("01","02"): continue
                if ln[127:130]!="001": continue
                cds=ln[0:7]+ln[47:54]
                tail=ln[132:]
                pct=find_block_dec(tail)
            else:
                # contiguous
                if ln[22:25]!="001": continue
                if ln[25:26]!="B": continue
                a,b=cfg["ggss"]; ggss=ln[a:b]
                if ggss[0:2]!="11": continue
                subj=ggss[2:4]
                if subj not in ("01","02"): continue
                cds=ln[0:14]
                if not school_level_contig(cds): continue
                tail=ln[b:]
                pct=find_block_int(tail) if mode=="contig15" else find_block_dec(tail)
            if pct is None:
                n_fail+=1; continue
            mn,N=mean_and_n(tail)
            key=(cds,yr)
            d=data.setdefault(key,{})
            if subj=="01":
                d["ela_pct_met"]=pct; d["ela_mean"]=mn; d["ela_n"]=N; n_ela+=1
            else:
                d["math_pct_met"]=pct; d["math_mean"]=mn; d["math_n"]=N; n_math+=1
    stats[yr]=(n_lines,n_ela,n_math,n_fail)
    print(f"{yr}: lines={n_lines:>9,}  ELA g11 schools={n_ela:>5}  Math={n_math:>5}  validation_fails={n_fail}")

# write
out="build_outputs/caaspp_grade11.csv"
with open(out,"w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["cds14","year","ela_pct_met","math_pct_met","ela_mean","math_mean","ela_n","math_n"])
    for (cds,yr),d in sorted(data.items()):
        w.writerow([cds,yr,d.get("ela_pct_met"),d.get("math_pct_met"),
                    d.get("ela_mean"),d.get("math_mean"),d.get("ela_n"),d.get("math_n")])
print("\nwrote",out,"rows=",len(data))

# spot checks
checks={"Berkeley High":"01611430131177","University High Irvine":"10621660114553"}
for name,cds in checks.items():
    print(f"\n{name} ({cds}):")
    for yr in YEARS:
        d=data.get((cds,yr))
        if d: print(f"  {yr}: ELA={d.get('ela_pct_met')}  Math={d.get('math_pct_met')}  (ela_n={d.get('ela_n')})")
