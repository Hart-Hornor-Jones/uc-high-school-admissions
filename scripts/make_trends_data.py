#!/usr/bin/env python3
"""Bundle data/trends/*.csv into trends/data_trends.js (window.TRENDS_DATA).

Everything the page shows is precomputed here; the page ships no raw data
beyond these aggregates. Values are already display-rounded by the parsers.
"""
import csv, json, os, sys, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(REPO, 'data', 'trends')

def rd(name):
    with open(os.path.join(D, name), newline='') as fh:
        return list(csv.DictReader(fh))

def fnum(v):
    if v is None or v == '':
        return None
    x = float(v)
    return int(x) if x == int(x) else x

out = {}

# ---- systemwide (UC IC) ----
sys_series = {}
for r in rd('sys_rates.csv'):
    key = '|'.join([r['level'], r['slice'], r['eth'], r['pell'], r['fg']])
    m = sys_series.setdefault(key, {})
    m.setdefault(r['measure'], []).append([int(r['cohort']), fnum(r['value']), fnum(r['n'])])
for k in sys_series:
    for meas in sys_series[k]:
        sys_series[k][meas].sort()

# synthesize all-ethnicity Pell / first-gen aggregates from the cross slices.
# Rate cells are graduate(or retained) share x cohort N, so the N-weighted mean
# over the full ethnicity partition equals the true combined rate (cells are
# published to 0.1pp; aggregation error is negligible). Only rate measures with
# per-cell Ns are aggregated; TTD/GPA means are left to the ethnicity view.
RATE_MEASURES = {'ret1','grad2','grad3','grad4','grad5','grad6','grad5p','grad7p'}
def synth(level, slice_, field_vals, out_key_tail):
    eths = ['aian','asian_pi','black','hispanic_latino','international','unknown','white']
    for fv in field_vals:
        agg = {}
        complete = {}
        for e in eths:
            k = '|'.join([level, slice_, e] + fv)
            src = sys_series.get(k)
            if not src:
                continue
            for meas, arr in src.items():
                if meas not in RATE_MEASURES:
                    continue
                for yr, v, n in arr:
                    if v is None or not n:
                        continue
                    g, den, cnt = agg.get((meas, yr), (0.0, 0, 0))
                    agg[(meas, yr)] = (g + v * n / 100.0, den + n, cnt + 1)
        out_series = {}
        for (meas, yr), (g, den, cnt) in agg.items():
            if den < 1 or cnt < 5:   # require most ethnicities present
                continue
            out_series.setdefault(meas, []).append([yr, round(100.0 * g / den, 1), den])
        for meas in out_series:
            out_series[meas].sort()
        if out_series:
            sys_series['|'.join([level, 'agg'] + out_key_tail(fv))] = out_series

for level in ('FR', 'TR'):
    synth(level, 'eth_x_pell', [['pell', 'all'], ['non_pell', 'all']],
          lambda fv: ['all', fv[0], 'all'])
    synth(level, 'eth_x_fg', [['all', 'first_gen'], ['all', 'not_first_gen']],
          lambda fv: ['all', 'all', fv[1]])

out['sys'] = sys_series

# ---- federal campus panel ----
panel, stats = {}, {}
for r in rd('fed_campus_panel.csv'):
    yr = int(r['year'])
    if r['group'] == '__campus__':
        stats.setdefault(r['campus'], []).append(
            [yr, fnum(r['ret_ft4_pct']), fnum(r['pctpell']), fnum(r['ftftpctpell']), fnum(r['ugds'])])
    else:
        if r['c150_pct'] == '' and r['d150'] == '':
            continue
        panel.setdefault(r['campus'] + '|' + r['group'], []).append(
            [yr, fnum(r['c150_pct']), fnum(r['d150'])])
for d in (panel, stats):
    for k in d:
        d[k].sort()
money = {}
for r in rd('fed_money.csv'):
    money.setdefault(r['campus'], {})[r['metric'] + '|' + r['subgroup']] = \
        [fnum(r['value']), fnum(r['n'])]
fg = {}
for r in rd('fed_firstgen_curves.csv'):
    fg.setdefault(r['campus'] + '|' + r['group'], {}).setdefault(r['outcome'], []).append(
        [int(r['years_after_entry']), fnum(r['rate_pct']), fnum(r['cohort_n'])])
for k in fg:
    for oc in fg[k]:
        fg[k][oc].sort()
out['fed'] = {'panel': panel, 'stats': stats, 'money': money, 'fg': fg}

# ---- high schools ----
names, series = {}, {}
for r in rd('hs_names.csv'):
    names[r['ceeb']] = [r['name'], r['city'], r['county']]
for r in rd('hs_series.csv'):
    series.setdefault(r['campus'], {}).setdefault(r['ceeb'], []).append(
        [int(r['entry_year']), fnum(r['cohort_n']), fnum(r['ret1_pct']),
         fnum(r['grad4_pct']), fnum(r['grad5_pct']), fnum(r['grad6_pct'])])
for c in series:
    for s in series[c]:
        series[c][s].sort()
out['hs'] = {'names': names, 'series': series}

# ---- community colleges ----
cnames, cseries = {}, {}
for r in rd('ccc_names.csv'):
    cnames[r['ccc_id']] = [r['name'], r['county']]
for r in rd('ccc_series.csv'):
    cseries.setdefault(r['campus'], {}).setdefault(r['ccc_id'], []).append(
        [int(r['entry_year']), fnum(r['cohort_n']), fnum(r['ret1_pct']),
         fnum(r['grad2_pct']), fnum(r['grad3_pct']), fnum(r['grad4_pct'])])
for c in cseries:
    for s in cseries[c]:
        cseries[c][s].sort()
out['ccc'] = {'names': cnames, 'series': cseries}

# ---- GPA bands ----
gcounts, gcuts = {}, {}
for r in rd('gpa_band_counts.csv'):
    key = '|'.join([r['entry'], r['campus'], r['group_type'], r['subgroup']])
    gcounts.setdefault(key, []).append(
        [int(r['cohort']), int(r['band']), fnum(r['band_lo']), fnum(r['band_hi']),
         fnum(r['c_first']), fnum(r['c_second']), fnum(r['c_third']),
         fnum(r['r_first_pct']), fnum(r['r_second_pct']), fnum(r['r_third_pct'])])
for k in gcounts:
    gcounts[k].sort()
for r in rd('gpa_cutpoints.csv'):
    gcuts.setdefault(r['entry'] + '|' + r['campus'], []).append(
        [int(r['cohort']), fnum(r['q_lo']), fnum(r['q1_hi']), fnum(r['q2_hi']), fnum(r['q_hi'])])
for k in gcuts:
    gcuts[k].sort()
out['gpa'] = {'counts': gcounts, 'cuts': gcuts}

# ---- majors ----
titles, mseries = {}, {}
for r in rd('majors_cip2.csv'):
    titles[r['cip2']] = r['cip2_title']
    mseries.setdefault(r['campus'] + '|' + r['cip2'], []).append(
        [int(r['year']), fnum(r['total']), fnum(r['urm'])])
for k in mseries:
    mseries[k].sort()
out['majors'] = {'titles': titles, 'series': mseries}

out['meta'] = {
    'built': datetime.date.today().isoformat(),
    'counts': {k: (len(v) if isinstance(v, dict) else None) for k, v in out.items()},
    'sources': {
        'uc_ic': 'UC Information Center UG Outcomes & Admissions-by-source-school dashboards (harvested June 2026)',
        'scorecard': 'College Scorecard institution files, June 10 2026 vintage',
        'ipeds': 'IPEDS Completions C2012-C2024 (provisional 2023-24)',
    },
}

js = 'window.TRENDS_DATA = ' + json.dumps(out, separators=(',', ':'), ensure_ascii=False) + ';\n'
dst = os.path.join(REPO, 'trends', 'data_trends.js')
os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, 'w', encoding='utf-8') as fh:
    fh.write(js)
print('wrote', dst, len(js), 'bytes')
for k, v in out.items():
    if isinstance(v, dict):
        print(' ', k, {kk: len(vv) if isinstance(vv, (dict, list)) else '' for kk, vv in list(v.items())[:6] if isinstance(vv, (dict, list))})
