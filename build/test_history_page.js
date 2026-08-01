// jsdom behavioral suite for history/index.html
// usage: node test_history_page.js [path-to-history-dir]   (default: ../history or .)
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

let dir = process.argv[2];
if(!dir){
  dir = fs.existsSync(path.join(__dirname, 'index.html')) ? __dirname
      : path.join(__dirname, '..', 'history');
}
const html = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');
const dataJs = fs.readFileSync(path.join(dir, 'data_history.js'), 'utf8');
const D = JSON.parse(dataJs.slice(dataJs.indexOf('{'), dataJs.lastIndexOf('}') + 1));

let pass = 0, fail = 0;
function ok(cond, name){ if(cond){ pass++; console.log('  ok  ' + name); }
                         else { fail++; console.log('FAIL  ' + name); } }

const dom = new JSDOM(html, { runScripts: 'outside-only', url: 'https://example.org/history/' });
const { window } = dom;
const doc = window.document;
// inject data (script src does not resolve in jsdom), then re-run inline script
window.eval(dataJs);
const inline = [...doc.querySelectorAll('script')].map(s => s.textContent).filter(t => t.trim()).pop();
window.eval(inline);
const $ = id => doc.getElementById(id);
const txt = el => el.textContent;

// ---- 1. boot & anchor rendering
ok(!!window.HISTORY_DATA, 'data object loads');
ok(txt($('titleArc')) === 'Berkeley, 1999–2025', 'default campus is Berkeley');
ok($('tblArc').innerHTML.includes('+0.50 (440)'),
   'anchor: Berkeley 2016 college-bound r=+0.50 n=440 in the table (unchanged by re-alignment)');
ok($('tblArc').innerHTML.includes('2016'), 'table carries year rows');

// census points drawn, hollow for compressed instruments
const arcCircles = $('cArc').querySelectorAll('circle');
ok(arcCircles.length > 40, 'arc has plotted points (' + arcCircles.length + ')');
const hollow = [...arcCircles].filter(c => c.getAttribute('fill') === '#fff');
ok(hollow.length >= 2, 'hollow (compressed-instrument) census points present: ' + hollow.length);

// dashed splice segments exist
const dashed = [...$('cArc').querySelectorAll('line')].filter(l =>
  l.getAttribute('stroke-dasharray') === '4 4');
ok(dashed.length >= 2, 'dashed instrument-splice connections present: ' + dashed.length);

// summary line computed from data
ok(txt($('sumArc')).includes('+0.50') && txt($('sumArc')).includes('2016'),
   'Berkeley summary line carries computed peak');

// ---- cohort alignment
const cenB = D.arc['Berkeley'].census;
ok(cenB.every(p => p.length === 5), 'census points carry [class, r, n, source, spring]');
ok(cenB.every(p => (p[3] === 'cahsee' || p[3] === 's9') ? p[0] === p[4] + 2 : p[0] === p[4] + 1),
   'every census point is shifted from its test spring by its own cohort offset');
const cls = new Set(cenB.map(p => p[0]));
ok(!cls.has(2021) && !cls.has(2022), 'classes of 2021-22 absent (grade-11 springs cancelled/excluded)');
ok(cls.has(2020), 'class of 2020 HAS a census point (spring 2019) — was missing pre-realignment');
ok(cls.has(2014) && cls.has(2015), 'the 2014-15 census hole closes on the class timeline');
ok(!cls.has(2003), 'class of 2003 correctly absent (no grade-11 census instrument)');
ok(D.census_agreement.pairs > 100 && D.census_agreement.mean_abs_diff < 0.08,
   `two census instruments agree on the same class: mean |diff| ${D.census_agreement.mean_abs_diff} over ${D.census_agreement.pairs} pairs`);
ok(doc.getElementById('alignTable').innerHTML.includes('CAHSEE'), 'alignment table rendered in methods');
ok(txt($('agDiff')).length > 0 && txt($('agPairs')).length > 0, 'agreement figures injected from data');

// ---- 2. campus interaction
const chips = [...$('campusChips').children];
ok(chips.length === 10, '10 campus chips');
chips.find(c => c.textContent === 'San Diego').click();
ok(txt($('titleArc')) === 'San Diego, 1999–2025', 'chip click switches campus');
ok(txt($('sumArc')).length > 10, 'summary re-renders');
chips.find(c => c.textContent === 'Santa Barbara').click();
ok(txt($('sumArc')).includes('rulers genuinely disagree'), 'Santa Barbara divergence flag shown');
chips.find(c => c.textContent === 'Berkeley').click();

// ACT toggle
const actChip = [...$('lArc').querySelectorAll('button')].find(b => b.textContent.includes('ACT'));
const before = $('cArc').querySelectorAll('circle').length;
actChip.click();
const after = $('cArc').querySelectorAll('circle').length;
ok(after > before, 'ACT family toggles on (' + before + ' -> ' + after + ' points)');

// ---- 3. minis
ok($('miniGrid').children.length === 10, '10 mini panels');
$('miniGrid').querySelector('[data-campus="Riverside"]').click();
ok(txt($('titleArc')) === 'Riverside, 1999–2025', 'mini click selects campus');
ok(txt($('gridNote')).includes('Riverside') && txt($('gridNote')).includes('never invert'),
   'grid note carries computed post-blind ordering');

// ---- 4. volume
ok(txt($('rsVol')).includes('2.96') && txt($('rsVol')).includes('1.98'),
   'volume era ratios 2.96 / 1.98 shown');
ok($('cVol').querySelectorAll('circle').length > 100, 'volume series plotted');

// ---- 5. AP
ok(txt($('titleAP')).includes('AP exams per 100 seniors'), 'AP default mode');
[...$('apMode').children].find(b => b.dataset.mode === 'pass').click();
ok(txt($('titleAP')).includes('scored 3 or higher'), 'AP mode toggle switches view');
ok(txt($('apN')).length > 0, 'AP fixed-panel size rendered: ' + txt($('apN')));

// ---- 6. wedge
ok(txt($('wMean')) === '76', 'wedge overall mean +76');
ok(txt($('wPos')) === '99.9%', 'wedge share positive 99.9%');
ok(txt($('wR')).includes('0.36') || txt($('wR')).includes('0.35'),
   'wedge x achievement correlation rendered: ' + txt($('wR')));

// ---- 7. drift
ok(txt($('dFlatShare')) === '70%', 'flat-yardstick share rising 70%');
ok(txt($('dFlatN')) === '301', 'flat-yardstick n=301');
ok(txt($('dFlatSlope')) === '+0.0067', 'flat-yardstick slope +0.0067');
ok(txt($('dApR')) === '+0.04', 'AP-drift r=+0.04');
ok($('cDriftA').querySelectorAll('circle').length === D.gpa_drift.n,
   'drift A plots all ' + D.gpa_drift.n + ' schools');
ok($('cDriftB').querySelectorAll('circle').length === D.ap_drift.n,
   'drift B plots all ' + D.ap_drift.n + ' schools');

// ---- 8. rulers
ok(txt($('rulPre')) === '.79', 'rulers pre-2015 mean .79');
ok($('cRulers').querySelectorAll('circle').length === D.rulers.census_x_collegebound.length,
   'rulers chart plots all census x college-bound years');

// ---- 9. data-consistency spot checks (page vs JSON twin)
const b = D.arc['Berkeley'];
ok(b.sat.find(p => p[0] === 2016)[1] === 0.4965, 'JSON twin: Berkeley 2016 = 0.4965');
const riv = D.campus_summary['Riverside'];
ok(riv.post_blind_mean > 0.4, 'JSON twin: Riverside post-blind mean stays strongly positive');
ok(D.rulers.pre_mean === 0.7942, 'JSON twin: rulers mean = .7942');

// ---- 10. house style
const bodyText = doc.body.textContent;
ok(!/merit/i.test(bodyText), 'no "merit" anywhere in rendered text');
for(const w of ['colour','grey','behaviour','centred','standardised','cancelled?']){}
ok(!/colour|behaviour|centred|standardised|analyse/.test(bodyText),
   'no British spellings in rendered text');
ok(bodyText.includes('understated, not inflated'), 'attenuation direction disclosed');
ok(bodyText.includes('percent_tested'), 'participation limit disclosed');
ok(bodyText.includes('Santa Barbara'), 'SB divergence disclosed');
ok(bodyText.includes('voluntary grade-9'), 'CAHSEE 2001 exclusion disclosed');
ok(/association is not attribution/.test(bodyText), 'non-causal framing present');
ok($('footer').textContent.includes('build_history_data.py'), 'footer names the builder');

// ---- 11. 2020 annotation
chips.find(c => c.textContent === 'San Diego').click();
const rings = [...$('cArc').querySelectorAll('circle')].filter(c =>
  c.getAttribute('fill') === 'none' && parseFloat(c.getAttribute('r')) > 5);
ok(rings.length >= 1, '2020 anomaly ring drawn on the arc: ' + rings.length);
ok(txt($('lArc')).includes('one-year step'), 'legend carries the 2020 key');
const mtext = $('methods').textContent;
ok(mtext.includes('one-year step, not part of the trend'), 'methods: 2020 bullet present');
ok(mtext.includes('35.0%') && mtext.includes('25.9%'), 'methods: 2020 quartile evidence stated');
ok(mtext.includes('field test'), 'methods: 2014 STAR/CAASPP instrument gap explained');
ok(mtext.includes('on the class timeline it closes'), 'methods: 2014 hole closing on class axis stated');
ok(mtext.includes('graduating class, not the testing year'), 'methods: cohort dating convention stated');
ok(doc.body.textContent.includes('graduating class'), 'axis named in page text');
chips.find(c => c.textContent === 'Berkeley').click();

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
