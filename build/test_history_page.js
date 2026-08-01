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
   'anchor: Berkeley 2016 college-bound r=+0.50 n=440 in the table');
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

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
