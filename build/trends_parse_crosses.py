#!/usr/bin/env python3
"""Parse UC IC systemwide graduation-rate crosses (crosses_v2) into a tidy long CSV.

Source: outcomes data/data/raw/outcomes/ug_outcomes_graduation_rates_systemwide_crosses_v2
Output: data/trends/sys_rates.csv  (long)
  level  FR|TR
  slice  all|eth|eth_x_pell|eth_x_fg
  eth,pell,fg  canonical subgroup keys ('all' when not split)
  cohort  entering cohort year (int)
  measure ret1|grad2..grad7p|grad6_nonuc|ttd_mean|gradgpa_mean
  value   percent 0-100 for rates; years for ttd; GPA for gradgpa
  n       cohort size where the sheet provides one ('' otherwise)

Quirks handled: tab-delimited despite .csv; utf-8 or utf-16 (manifest
encoding_guess, with fallback); blank = missing, never zero; thousands
separators; trailing normalized 'Cohort size' column in TR rates; transposed
sheets (TTD, 6 yrs with Non UC Deg, Grad GPA); Grad GPA weighted mean over
time-to-degree buckets using per-bucket cohort sizes.

Run (sandbox):
  python3 trends_parse_crosses.py --corpus "/…/outcomes data" --out "/…/repo/data/trends"
Windows default paths match Hart's layout.
"""
import argparse, csv, io, os, re, sys, json
from collections import defaultdict

ETH = {
    'All': 'all', 'African American': 'black', 'American Indian': 'aian',
    'Asian/Pac Isl': 'asian_pi', 'Dom. Unknown': 'unknown',
    'Hispanic/Latinx': 'hispanic_latino', 'Hispanic/ Latinx': 'hispanic_latino',
    'International': 'international', 'White': 'white',
}
PELL = {'All': 'all', 'Pell Recipient': 'pell', 'Non-Pell Recipient': 'non_pell',
        'Non-Pell Recipeint': 'non_pell'}
FG = {'All': 'all', 'First-generation': 'first_gen', 'Not first-generation': 'not_first_gen'}
SLICE = {'all_demographics': 'all', 'ethnicity': 'eth',
         'ethnicity_x_pell': 'eth_x_pell', 'ethnicity_x_first_generation': 'eth_x_fg'}

def read_text(path, enc_guess):
    for enc in ([enc_guess, 'utf-16', 'utf-8-sig'] if enc_guess else ['utf-8', 'utf-16']):
        try:
            with open(path, encoding=enc) as f:
                t = f.read()
            if '\t' in t or t.strip() == '':
                return t
        except (UnicodeError, LookupError):
            continue
    raise IOError('cannot decode %s' % path)

def cells(text):
    return [r.split('\t') for r in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            if r.strip('\t ').strip()]

def num(s):
    s = (s or '').strip().replace(',', '').rstrip('%')
    if s in ('', '-'):
        return None
    try:
        return float(s)
    except ValueError:
        return None

def parse_rates(tab, level):
    """FR rates / TR rates: rows = cohorts, cols = Cohort Size + horizons."""
    hdr = tab[0]
    colmap = {}
    for j, h in enumerate(hdr):
        h = h.strip()
        if h == 'Cohort Size':
            colmap[j] = '__n__'
        elif h == '1st yr':
            colmap[j] = 'ret1'
        elif re.fullmatch(r'(\d)\+? ?yrs', h):
            colmap[j] = 'grad' + re.match(r'(\d)', h).group(1)
        elif re.fullmatch(r'(\d)\+ ?yrs', h.replace(' ', '')):
            colmap[j] = 'grad' + h[0] + 'p'
    # explicit + variants ('7+yrs', '5+ yrs')
    for j, h in enumerate(hdr):
        h = h.strip().replace(' ', '')
        if h == '7+yrs':
            colmap[j] = 'grad7p'
        elif h == '5+yrs':
            colmap[j] = 'grad5p'
        elif h == 'Cohortsize':   # trailing normalized col in TR rates
            colmap.pop(j, None)
    out = []
    for row in tab[1:]:
        yr = num(row[0])
        if yr is None or not (1990 < yr < 2030):
            continue
        n = None
        vals = {}
        for j, key in colmap.items():
            if j >= len(row):
                continue
            v = num(row[j])
            if key == '__n__':
                n = v
            elif v is not None:
                vals[key] = v
        for k, v in vals.items():
            out.append((int(yr), k, v, int(n) if n is not None else ''))
    return out

def parse_transposed_rate(tab, rowlabel_contains, measure):
    """6 yrs with Non UC Deg: years across columns; take the labelled row."""
    hdr = tab[0]
    years = {j: int(num(h)) for j, h in enumerate(hdr) if num(h) and 1990 < num(h) < 2030}
    out = []
    for row in tab[1:]:
        if rowlabel_contains.lower() in row[0].strip().lower():
            for j, yr in years.items():
                if j < len(row):
                    v = num(row[j])
                    if v is not None:
                        out.append((yr, measure, v, ''))
            break
    return out

def parse_ttd(tab, level):
    """TTD: rows = Freshman/Transfer, years across columns."""
    want = 'Freshman' if level == 'FR' else 'Transfer'
    hdr = tab[0]
    years = {j: int(num(h)) for j, h in enumerate(hdr) if num(h) and 1990 < num(h) < 2030}
    out = []
    for row in tab[1:]:
        if row[0].strip() == want:
            for j, yr in years.items():
                if j < len(row):
                    v = num(row[j])
                    if v is not None:
                        out.append((yr, 'ttd_mean', v, ''))
    return out

def parse_gradgpa(tab, level):
    """Grad GPA: rows = ttd-bucket x person-type x metric; years across cols.
    Return cohort-level weighted mean GPA (weights = bucket cohort sizes)."""
    want = 'Freshman' if level == 'FR' else 'Transfer'
    hdr = tab[0]
    years = {j: int(num(h)) for j, h in enumerate(hdr) if num(h) and 1990 < num(h) < 2030}
    gpa = defaultdict(dict)   # bucket -> yr -> gpa
    siz = defaultdict(dict)   # bucket -> yr -> n
    for row in tab[1:]:
        if len(row) < 4:
            continue
        bucket, ptype, metric = row[0].strip(), row[1].strip(), row[2].strip()
        if ptype != want:
            continue
        for j, yr in years.items():
            if j >= len(row):
                continue
            v = num(row[j])
            if v is None:
                continue
            if 'Gpa' in metric or 'GPA' in metric:
                gpa[bucket][yr] = v
            elif 'Cohort' in metric:
                siz[bucket][yr] = v
    out = []
    allyrs = sorted({y for b in gpa.values() for y in b})
    for yr in allyrs:
        num_, den = 0.0, 0.0
        for b in gpa:
            g, n = gpa[b].get(yr), siz.get(b, {}).get(yr)
            if g is not None and n:
                num_ += g * n
                den += n
        if den > 0:
            out.append((yr, 'gradgpa_mean', round(num_ / den, 3), int(den)))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=r'C:\Users\harth\svetlana\outcomes data')
    ap.add_argument('--out', default=r'C:\Users\harth\svetlana\Svetlana\uc-merit-admissions\data\trends')
    a = ap.parse_args()
    base = os.path.join(a.corpus, 'data', 'raw', 'outcomes',
                        'ug_outcomes_graduation_rates_systemwide_crosses_v2')
    man = list(csv.DictReader(open(os.path.join(base, 'manifest.csv'), encoding='utf-8')))
    rows, fails = [], []
    for m in man:
        if m['status'] != 'downloaded':
            continue
        sheet = m['sheet_name']
        if sheet not in ('FR rates', 'TR rates', 'TTD', 'Grad GPA', '6 yrs with Non UC Deg'):
            continue
        level = 'FR' if m['applicant_level'] == 'Freshman' else 'TR'
        if sheet == 'FR rates' and level != 'FR':
            continue
        if sheet == 'TR rates' and level != 'TR':
            continue
        rel = m['file_path'].split('crosses_v2\\')[-1].replace('\\', '/')
        path = os.path.join(base, rel)
        try:
            tab = cells(read_text(path, m.get('encoding_guess')))
        except Exception as e:
            fails.append((rel, str(e)))
            continue
        if not tab:
            continue
        if sheet in ('FR rates', 'TR rates'):
            recs = parse_rates(tab, level)
        elif sheet == 'TTD':
            recs = parse_ttd(tab, level)
        elif sheet == 'Grad GPA':
            recs = parse_gradgpa(tab, level)
        else:
            recs = parse_transposed_rate(tab, 'non-UC degrees', 'grad6_nonuc') or \
                   parse_transposed_rate(tab, 'non uc degrees', 'grad6_nonuc') or \
                   parse_transposed_rate(tab, '6 yrs with', 'grad6_nonuc')
        sl = SLICE[m['slice_type']]
        eth = ETH.get(m['ethnicity'].strip(), None)
        pell = PELL.get(m['pell_grant'].strip(), None)
        fg = FG.get(m['first_generation'].strip(), None)
        if eth is None or pell is None or fg is None:
            fails.append((rel, 'unmapped label %r/%r/%r' %
                          (m['ethnicity'], m['pell_grant'], m['first_generation'])))
            continue
        for yr, meas, val, n in recs:
            rows.append([level, sl, eth, pell, fg, yr, meas, val, n])
    # dedupe (Grad GPA vs Grad GPA (2) may duplicate cells; keep first)
    seen, out = set(), []
    for r in rows:
        k = tuple(r[:7])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    out.sort(key=lambda r: (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'sys_rates.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['level', 'slice', 'eth', 'pell', 'fg', 'cohort', 'measure', 'value', 'n'])
        w.writerows(out)
    qa = {
        'rows': len(out), 'files_failed': fails,
        'anchor_2024_ret': [r for r in out if r[:7] == ['FR','all','all','all','all',2024,'ret1']],
        'anchor_2021_g4':  [r for r in out if r[:7] == ['FR','all','all','all','all',2021,'grad4']],
        'anchor_hisp_pell_2019_g6': [r for r in out if r[:6] == ['FR','eth_x_pell','hispanic_latino','pell','all',2019] and r[6]=='grad6'],
    }
    with open(os.path.join(a.out, 'sys_rates_qa.json'), 'w') as f:
        json.dump(qa, f, indent=1, default=str)
    print('rows', len(out), 'failed', len(fails))
    for k in ('anchor_2024_ret', 'anchor_2021_g4', 'anchor_hisp_pell_2019_g6'):
        print(k, qa[k])

if __name__ == '__main__':
    main()
