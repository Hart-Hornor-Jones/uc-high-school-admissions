# =============================================================================
#  diag.py  -  Tiny CAASPP "modern"-layout probe (debugging helper).
# =============================================================================
#  PART OF: the CAASPP parsing step.  See README.md
#
#  WHAT IT DOES
#    Counts how many grade-11 ELA "All" records parse cleanly vs fail under the
#    "modern" CAASPP byte offsets, and prints a few failing records so you can
#    spot a layout mismatch. Use it when adding a new CAASPP year before wiring
#    it into parse_caaspp_year.py.
#
#  *** RUN FROM:  the project root (or anywhere)  ***
#  HOW TO RUN
#    python build_scripts_documented/diag.py < "CAASPP Data/sb_ca2024_all_ascii_v1.txt"
#
#  INPUTS   a CAASPP file on STDIN
#  OUTPUTS  none (prints a total/valid/fail count + sample failing records)
#
#  GOTCHAS / NOTES
#    - Hard-wired to the MODERN offsets. For older "contig" years it will report
#      everything as failing - that is expected; this is a modern-layout probe.
# =============================================================================

import sys,re
MEAN=re.compile(r'(\d{4}\.\d)(?!\d)');PCT2=re.compile(r'\d+\.\d{2}\b')
tot=valid=fail=0; samp=[]
for ln in sys.stdin:
    if ln[114:116]!="07" or ln[130:132]!="11" or ln[125:127]!="01" or ln[127:130]!="001": continue
    tot+=1; tail=ln[132:]; m=MEAN.search(tail)
    v=[float(x.group()) for x in PCT2.finditer(tail[m.end():])] if m else []
    if m and len(v)>=5 and abs(v[0]+v[1]-v[2])<=0.06 and 99<=v[2]+v[3]+v[4]<=101: valid+=1
    else:
        fail+=1
        if len(samp)<6: samp.append(ln.rstrip("\n"))
print(f"rectype07 g11 ELA All: total={tot} valid={valid} fail={fail}")
for s in samp: print("FAIL[114:225]:",repr(s[114:225]))
