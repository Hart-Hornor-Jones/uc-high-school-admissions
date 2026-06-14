# =============================================================================
#  parse_caaspp_year.py  -  Parse ONE year of CAASPP into grade-11 school %met.
# =============================================================================
#  PART OF: the UC Admissions x School-Merit panel build.  See README.md
#
#  WHAT IT DOES
#    Reads one CAASPP Smarter-Balanced research file (a large fixed-width text
#    file) ON STANDARD INPUT and writes grade-11 school-level "% met standard"
#    for ELA and Math. The %met column is located by ARITHMETIC (exceeded+met
#    = met&above; the three bands sum to ~100), so exact byte offsets of the
#    percent columns are never guessed.  This is the per-year parser that feeds
#    the panel (run it once per year).
#
#  *** RUN FROM:  the project root  ***
#
#  HOW TO RUN  (pipe the raw file in on stdin; args set the year + layout)
#    # 2024 & 2025 use the "modern" layout (no byte offsets needed):
#    python build_scripts_documented/parse_caaspp_year.py 2024 modern \
#        < "CAASPP Data/sb_ca2024_all_ascii_v1.txt"
#    python build_scripts_documented/parse_caaspp_year.py 2025 modern \
#        < "CAASPP Data/sb_ca2025_all_ascii_v1.txt"
#    # 2018 & 2023 use "contig" with the grade+subject field at bytes 40-44:
#    python build_scripts_documented/parse_caaspp_year.py 2018 contig 40 44 \
#        < "CAASPP Data/sb_ca2018_all_ascii_v3.txt"
#    python build_scripts_documented/parse_caaspp_year.py 2023 contig 40 44 \
#        < "CAASPP Data/sb_ca2023_all_ascii_v1.txt"
#    # 2015 uses "contig15" (integer percentages) with the field at bytes 47-51:
#    python build_scripts_documented/parse_caaspp_year.py 2015 contig15 47 51 \
#        < "CAASPP Data/sb_ca2015_all_ascii_v3.txt"
#
#  ARGUMENTS
#    argv[1] = year (e.g. 2024) - also names the output file
#    argv[2] = mode: "modern" (2024+), "contig" (2-decimal %), or
#                    "contig15" (integer %, 2015-style)
#    argv[3] argv[4] = byte offsets of the grade+subject field
#                      (contig / contig15 only; OMIT for modern)
#
#  INPUTS   the raw CAASPP file on STDIN
#           ("CAASPP Data/sb_caYYYY_all_ascii_*.txt")
#  OUTPUTS  Panel Build 2026-06-07/components/caaspp_{year}.csv
#           columns: cds14, year, ela_pct_met, math_pct_met,
#                    ela_mean, math_mean, ela_n, math_n
#
#  GOTCHAS / NOTES
#    - The grade-11 field OFFSET differs by year for the contig modes.
#      Confirmed: 2015 -> contig15 47 51 ; 2018 & 2023 -> contig 40 44 ;
#      2024 & 2025 -> modern. The other years already in components/
#      (2016, 2017, 2019, 2022) were produced the same way with their own
#      offsets. For a brand-new year, probe the layout with diag.py first.
#    - 2020 was cancelled (COVID); 2021 is EXCLUDED from the panel as
#      non-representative (a caaspp_2021.csv may still exist but merge skips it).
#    - The output folder Panel Build 2026-06-07/components/ must already exist.
# =============================================================================

import re,sys,csv
year=sys.argv[1]; mode=sys.argv[2]
ggss=(int(sys.argv[3]),int(sys.argv[4])) if mode.startswith("contig") else None
MEAN=re.compile(r'(\d{4}\.\d)(?!\d)')   # scale score NNNN.N
PCT2=re.compile(r'\d+\.\d{2}\b')        # two-decimal percentage
INT=re.compile(r'\d+')
def extract(tail, ints_mode):
    mm=MEAN.search(tail)
    if not mm: return None,None,None
    mean=float(mm.group(1))
    pre=tail[:mm.start()]; nums_pre=INT.findall(pre)
    N=int(nums_pre[-1]) if nums_pre else None
    s=tail[mm.end():]
    if ints_mode:
        vals=[int(x) for x in INT.findall(s)]
        if len(vals)<5: return None,mean,N
        a,b,c,d,e=vals[:5]
        if abs(a+b-c)<=1 and 99<=c+d+e<=101 and 0<=c<=100: return float(c),mean,N
        return None,mean,N
    else:
        vals=[float(x.group()) for x in PCT2.finditer(s)]
        if len(vals)<5: return None,mean,N
        a,b,c,d,e=vals[:5]
        if abs(a+b-c)<=0.06 and 99<=c+d+e<=101 and 0<=c<=100: return c,mean,N
        return None,mean,N
data={}; n_ela=n_math=n_fail=n_in=0
for ln in sys.stdin:
    n_in+=1
    if mode=="modern":
        if ln[114:116]!="07" or ln[130:132]!="11" or ln[127:130]!="001": continue
        subj=ln[125:127]
        if subj not in ("01","02"): continue
        cds=ln[0:7]+ln[47:54]; tail=ln[132:]
    else:
        if ln[22:25]!="001" or ln[25:26]!="B": continue
        a,b=ggss; g=ln[a:b]
        if g[0:2]!="11" or g[2:4] not in ("01","02"): continue
        subj=g[2:4]; cds=ln[0:14]
        if cds[0:2]=="00" or cds[2:7]=="00000" or cds[7:14]=="0000000": continue
        tail=ln[b:]
    pct,mean,N=extract(tail, mode=="contig15")
    if pct is None: n_fail+=1; continue
    d=data.setdefault((cds,year),{})
    if subj=="01": d["ela"]=pct; d["ela_mean"]=mean; d["ela_n"]=N; n_ela+=1
    else: d["math"]=pct; d["math_mean"]=mean; d["math_n"]=N; n_math+=1
with open(f"Panel Build 2026-06-07/components/caaspp_{year}.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["cds14","year","ela_pct_met","math_pct_met","ela_mean","math_mean","ela_n","math_n"])
    for (cds,yr),d in sorted(data.items()):
        w.writerow([cds,yr,d.get("ela"),d.get("math"),d.get("ela_mean"),d.get("math_mean"),d.get("ela_n"),d.get("math_n")])
sys.stderr.write(f"{year}: in={n_in} ELA={n_ela} Math={n_math} fails={n_fail} schools={len(data)}\n")
