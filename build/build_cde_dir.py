# =============================================================================
#  build_cde_dir.py  -  Build the CDE school directory (CDS -> name + county).
# =============================================================================
#  PART OF: the CEEB<->CDS crosswalk build.  See README.md
#
#  WHAT IT DOES
#    Harvests school names from the A-G files and several CUPC workbooks to make
#    a deduplicated directory keyed by the 14-digit CDS code, with a normalized
#    name (for fuzzy matching) and county. This is the lookup table the
#    crosswalk matches UC (CEEB) schools against.
#
#  *** RUN FROM:  the project root  ***
#  HOW TO RUN     python build_scripts_documented/build_cde_dir.py
#
#  INPUTS   A-G Data/acgr25.txt, acgr24.txt, acgr17.txt
#           Headcounts/cupc*-912.xls*   (the "School-CALPADS UPC Data (9-12)" sheet)
#  OUTPUTS  build_outputs/cde_directory.csv
#           columns: cds14, norm_name, raw_name, county
#
#  GOTCHAS / NOTES
#    - norm_name is aggressively normalized (uppercased, MT->MOUNT etc.,
#      stopwords like HIGH / SCHOOL removed) for matching - not for display.
#    - Requires openpyxl AND xlrd.
# =============================================================================

import csv,re,glob,sys
ABBR=[(r'\bMT\b','MOUNT'),(r'\bST\b','SAINT'),(r'\bJR\b','JUNIOR'),(r'\bSR\b','')]
STOP=re.compile(r'\b(SENIOR|HIGH|SCHOOL|HS|THE|OF|AND|FOR|AT)\b')
def norm(s):
    s=(s or "").upper().replace("&"," AND ").replace("/"," ").replace("-"," ").replace(".","")
    s=re.sub(r'[^A-Z0-9 ]',' ',s)
    for a,b in ABBR: s=re.sub(a,b,s)
    s=STOP.sub(' ',s); return re.sub(r'\s+',' ',s).strip()
D={}  # cds -> (norm,raw,county)
def add(cds,name,county):
    if not cds or len(cds)!=14 or cds[7:14]=="0000000": return
    nn=norm(name)
    if not nn: return
    if cds not in D or (not D[cds][2] and county): D[cds]=(nn,name,county)
for fn in ["acgr25.txt","acgr24.txt","acgr17.txt"]:
    for row in csv.DictReader(open(f"A-G Data/{fn}",encoding="latin-1",newline=""),delimiter="\t"):
        if row.get("AggregateLevel")=="S":
            add(row["CountyCode"].zfill(2)+row["DistrictCode"].zfill(5)+row["SchoolCode"].zfill(7),row.get("SchoolName"),row.get("CountyName"))
import openpyxl,xlrd
def cupc_rows(fp):
    if fp.lower().endswith(".xls"):
        b=xlrd.open_workbook(fp); s=b.sheet_by_name("School-CALPADS UPC Data (9-12)")
        for i in range(s.nrows): yield [s.cell_value(i,c) for c in range(s.ncols)]
    else:
        wb=openpyxl.load_workbook(fp,read_only=True,data_only=True); ws=wb["School-CALPADS UPC Data (9-12)"]
        for r in ws.iter_rows(values_only=True): yield list(r)
for fp in sorted(glob.glob("Headcounts/cupc*-912.xls*")):
    idx=None
    for row in cupc_rows(fp):
        low=[str(c).lower().replace("\n"," ") for c in row]
        if idx is None:
            if any("county" in c and "code" in c for c in low) and any("school name" in c for c in low):
                idx={'C':[j for j,c in enumerate(low) if "county" in c and "code" in c][0],
                     'D':[j for j,c in enumerate(low) if "district" in c and "code" in c][0],
                     'S':[j for j,c in enumerate(low) if "school" in c and "code" in c][0],
                     'N':[j for j,c in enumerate(low) if "school name" in c][0],
                     'CN':[j for j,c in enumerate(low) if "county name" in c][0]}
            continue
        sc=row[idx['S']]
        if sc in (None,""): continue
        add(str(row[idx['C']]).split('.')[0].zfill(2)+str(row[idx['D']]).split('.')[0].zfill(5)+str(sc).split('.')[0].zfill(7),row[idx['N']],row[idx['CN']])
    sys.stderr.write(f"after {fp}: {len(D)} cds\n")
with open("build_outputs/cde_directory.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["cds14","norm_name","raw_name","county"])
    for cds,(nn,raw,cty) in D.items(): w.writerow([cds,nn,raw,cty])
print("cde_directory.csv cds=",len(D))
