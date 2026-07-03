#!/usr/bin/env python3
"""Parse UG Outcomes 'Grad. rates by GPA groups' crosstabs into tidy CSVs.

Source: outcomes data/data/raw/outcomes/ug_outcomes_gpa_groups_full
Grain: cohort 2010-2021 x campus (All + 9) x group_selection (Pell/first-gen/
ethnicity), sheets 'a. HS GPAs' (freshman entrants) and 'b. Transfer GPA';
'*Overall' variants (no subgroup split) exist for cohorts 2019-2020 only.

The crosstabs give graduate COUNTS by timing per subgroup x GPA band. Bands
are terciles of the SYSTEMWIDE enrollee GPA distribution per cohort and entry
type: the published band boundaries are identical across campus selections
(verified), so campuses draw unevenly from the three bands.

Timing windows differ by entry type; we store them uniformly as first /
second / third window:
  freshman (a. HS GPAs):   first = within 4 yrs, second = 5th yr only, third = 6th yr only
  transfer (b. Transfer GPA): first = within 2 yrs, second = 3rd yr only, third = 4th yr only

'Avg. UC Deg (...)' rows are the band-level RATES (mean of the 0/1 completion
indicator). In freshman sheets Tableau renders them integer-rounded (0/1) --
useless, dropped. In transfer sheets they are percent-formatted and usable;
we keep any Avg value carrying a '%' sign as r_first/r_second/r_third.
Freshman rates per band therefore remain unidentified (no denominators);
shares of graduates by timing are identified for both entry types.

Outputs:
  gpa_band_counts.csv  entry,campus,cohort,group_type,subgroup,band,band_lo,band_hi,
                       c_first,c_second,c_third,r_first_pct,r_second_pct,r_third_pct
  gpa_cutpoints.csv    entry,campus,cohort,q_lo,q1_hi,q2_hi,q_hi  (band boundaries)
"""
import argparse, csv, os, re, json
from collections import defaultdict

SUB = {
    'Pell Recipient': ('pell_status', 'pell'), 'Non-Pell Recipient': ('pell_status', 'non_pell'),
    'Non-Pell Recipeint': ('pell_status', 'non_pell'),
    'First-generation': ('first_gen_status', 'first_gen'),
    'Not first-generation': ('first_gen_status', 'not_first_gen'),
    'African American': ('ethnicity', 'black'), 'American Indian': ('ethnicity', 'aian'),
    'Asian': ('ethnicity', 'asian'), 'Pacific Islander': ('ethnicity', 'pacific_islander'),
    'Hispanic/Latinx': ('ethnicity', 'hispanic_latino'), 'Hispanic/ Latinx': ('ethnicity', 'hispanic_latino'),
    'Chicano/Latino': ('ethnicity', 'hispanic_latino'),
    'White': ('ethnicity', 'white'), 'International': ('ethnicity', 'international'),
    'Dom. Unknown': ('ethnicity', 'unknown'), 'Domestic Unknown': ('ethnicity', 'unknown'),
    'Overall': ('overall', 'overall'), 'All': ('overall', 'overall'),
}

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

BAND_RE = re.compile(r'([\d.]+)\s*[-–]\s*<?\s*([\d.]+)')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=r'C:\Users\harth\svetlana\outcomes data')
    ap.add_argument('--out', default=r'C:\Users\harth\svetlana\Svetlana\uc-merit-admissions\data\trends')
    a = ap.parse_args()
    base = os.path.join(a.corpus, 'data', 'raw', 'outcomes', 'ug_outcomes_gpa_groups_full')
    man = list(csv.DictReader(open(os.path.join(base, 'manifest.csv'), encoding='utf-8')))
    out_rows, cut_rows, fails = [], {}, []
    for m in man:
        if m['status'] != 'downloaded':
            continue
        sheet = m['sheet_name']
        entry = 'FR' if sheet.startswith('a.') else 'TR'
        rel = m['file_path'].split('ug_outcomes_gpa_groups_full\\')[-1].replace('\\', '/')
        path = os.path.join(base, rel)
        try:
            tab = cells(read_text(path, m.get('encoding_guess')))
        except Exception as e:
            fails.append((rel, str(e)))
            continue
        if len(tab) < 3:
            continue
        overall = 'Overall' in sheet
        # Overall sheets share the two-header layout (subgroup row is 'Overall').
        subs_row, bands_row = tab[0], tab[1]
        body = tab[2:]
        colmeta = {}
        band_count = defaultdict(int)
        for j in range(1, len(bands_row)):
            lbl = bands_row[j].strip()
            mm = BAND_RE.search(lbl)
            if not mm:
                continue
            sub_lbl = (subs_row[j].strip() if subs_row and j < len(subs_row) and subs_row[j].strip()
                       else 'Overall')
            band_count[sub_lbl] += 1
            colmeta[j] = (sub_lbl, band_count[sub_lbl], float(mm.group(1)), float(mm.group(2)))
        COUNT_SLOT = {'UC (4yr)': 0, 'UC Deg (4yr)': 0, 'UC Deg (5yr only)': 1,
                      'UC Deg (6yr only)': 2,
                      'UC Deg (2yr)': 0, 'UC Deg (3yr only)': 1, 'UC Deg (4yr only)': 2}
        RATE_SLOT = {'Avg. UC Deg (2yr)': 0, 'Avg. UC Deg (3yr only)': 1,
                     'Avg. UC Deg (4yr only)': 2, 'Avg. UC Deg (4yr)': 0,
                     'Avg. UC Deg (4yr) (copy)': 0, 'Avg. UC Deg (5yr only)': 1,
                     'Avg. UC Deg (6yr only)': 2}
        counts = defaultdict(lambda: [None]*6)
        for row in body:
            lbl = row[0].strip()
            if lbl.startswith('Avg'):
                slot = RATE_SLOT.get(lbl)
                if slot is None:
                    continue
                for j, meta in colmeta.items():
                    if j < len(row) and row[j].strip().endswith('%'):
                        v = num(row[j])
                        if v is not None:
                            counts[meta][3 + slot] = round(v)
                continue
            slot = COUNT_SLOT.get(lbl)
            if slot is None:
                continue
            for j, meta in colmeta.items():
                if j < len(row):
                    v = num(row[j])
                    if v is not None:
                        counts[meta][slot] = int(v)
        campus, cohort, gsel = m['campus'], int(m['cohort_year']), m['group_selection']
        bounds = set()
        for (sub_lbl, band, lo, hi), vals in counts.items():
            if sub_lbl not in SUB:
                fails.append((rel, 'unmapped subgroup %r' % sub_lbl))
                continue
            gtype, sub = SUB[sub_lbl]
            if overall:
                gtype, sub = 'overall', 'overall'
            out_rows.append([entry, campus, cohort, gtype, sub, band, lo, hi] +
                            [v if v is not None else '' for v in vals])
            bounds.add((band, lo, hi))
        if bounds:
            b = sorted(bounds)
            if len({x[0] for x in b}) == 3 and len(b) == 3:
                cut_rows[(entry, campus, cohort)] = [b[0][1], b[0][2], b[1][2], b[2][2]]
    seen, final = set(), []
    for r in out_rows:
        k = tuple(r[:6])
        if k in seen:
            continue
        seen.add(k)
        final.append(r)
    final.sort(key=lambda r: (r[0], r[1], r[2], r[3], r[4], r[5]))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'gpa_band_counts.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['entry', 'campus', 'cohort', 'group_type', 'subgroup', 'band',
                    'band_lo', 'band_hi', 'c_first', 'c_second', 'c_third',
                    'r_first_pct', 'r_second_pct', 'r_third_pct'])
        w.writerows(final)
    with open(os.path.join(a.out, 'gpa_cutpoints.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['entry', 'campus', 'cohort', 'q_lo', 'q1_hi', 'q2_hi', 'q_hi'])
        for (e, c, y), b in sorted(cut_rows.items()):
            w.writerow([e, c, y] + b)
    qa = {'rows': len(final), 'cutpoint_states': len(cut_rows), 'fails': fails[:20],
          'n_fails': len(fails)}
    with open(os.path.join(a.out, 'gpa_groups_qa.json'), 'w') as fh:
        json.dump(qa, fh, indent=1)
    print('rows', len(final), 'cutpoints', len(cut_rows), 'fails', len(fails))
    ex = [r for r in final if r[:5] == ['FR', 'All', 2010, 'pell_status', 'pell']]
    print('example All-2010 pell:', ex)

if __name__ == '__main__':
    main()
