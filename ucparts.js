/* ucparts.js — on-demand loading of the generated data parts.
 *
 * Each page ships a small core data file (window.UCDATA, UCCTX, TRENDS_DATA, UCDENIED) and
 * fetches the rest in parts as the controls call for them: a campus, a graduation series,
 * a mode of the trends page, one school's history. Parts are plain scripts, inserted as
 * <script> tags, so the pages keep working from file:// and need no fetch() or JSON files.
 *
 * A part file registers itself as
 *     (window.UCPARTS_DATA = window.UCPARTS_DATA || {})["site:campus_0"] = {...};
 * and is loaded with UCPARTS.load("data_parts/campus_0.js", "site:campus_0").
 *
 * Numeric columns inside parts are packed strings ("78,73,,65": an empty field is null; a
 * column always has at least one cell, so "" is one null),
 * which is what keeps the files small; UCPARTS.unpack() turns one back into an array.
 * Values are written with the shortest decimal that round-trips, so unpack(x) reads the same
 * IEEE double JSON would have.
 */
(function () {
  'use strict';
  var P = window.UCPARTS = window.UCPARTS || {};
  var registry = window.UCPARTS_DATA = window.UCPARTS_DATA || {};
  var pending = {};       // key -> Promise (in flight)
  var inflight = 0;
  var waiters = [];

  function settle() { var w = waiters; waiters = []; w.forEach(function (f) { f(); }); }

  /* Load the part at `url` that registers under `key`. Resolves with its value; a part is
   * fetched once, later calls reuse it. Relative URLs resolve against the page. */
  P.load = function (url, key) {
    if (Object.prototype.hasOwnProperty.call(registry, key)) return Promise.resolve(registry[key]);
    if (pending[key]) return pending[key];
    inflight++;
    pending[key] = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = url; s.async = true;
      function done(err) {
        delete pending[key]; inflight--;
        if (s.parentNode) s.parentNode.removeChild(s);
        if (err) reject(err); else resolve(registry[key]);
        settle();
      }
      s.onload = function () {
        if (Object.prototype.hasOwnProperty.call(registry, key)) done(null);
        else done(new Error('data part ' + url + ' did not register "' + key + '"'));
      };
      s.onerror = function () { done(new Error('could not load data part ' + url)); };
      document.head.appendChild(s);
    });
    return pending[key];
  };
  /* Load several parts; resolves when all are present. */
  P.loadAll = function (pairs) { return Promise.all(pairs.map(function (p) { return P.load(p[0], p[1]); })); };
  P.has = function (key) { return Object.prototype.hasOwnProperty.call(registry, key); };
  P.get = function (key) { return registry[key]; };
  P.inflight = function () { return inflight; };

  /* Resolves once no part is in flight and nothing a completed load started is still in flight
   * (the check waits one task so a render that follows a load can ask for more). Used by the
   * headless tests to know when a page is settled. */
  P.whenIdle = function () {
    return new Promise(function (resolve) {
      (function check() {
        if (inflight > 0) { waiters.push(check); return; }
        setTimeout(function () { if (inflight > 0) waiters.push(check); else resolve(); }, 0);
      })();
    });
  };

  /* "78,73,,65" -> [78, 73, null, 65]. A column always has at least one cell ("" is [null]). */
  P.unpack = function (s) {
    if (s == null) return [];
    var parts = s.split(','), out = new Array(parts.length);
    for (var i = 0; i < parts.length; i++) out[i] = parts[i] === '' ? null : +parts[i];
    return out;
  };
  /* An array of packed column strings -> array of row arrays. */
  P.rows = function (cols) {
    var c = cols.map(P.unpack), n = c.length ? c[0].length : 0, out = new Array(n);
    for (var i = 0; i < n; i++) { var r = new Array(c.length); for (var j = 0; j < c.length; j++) r[j] = c[j][i]; out[i] = r; }
    return out;
  };

  /* The main explorer's panel. D.panel["ci|ceeb"] rows keep the layout index.html and
   * context/index.html read: [year,A,D,E,C,Gc,H,ela,math,upp,Gp,agpa,dgpa,egpa,Gr]. The
   * school part carries the school-year covariates once (they do not vary by campus) and a
   * campus part carries that campus's funnel counts and GPAs; this joins them. Returns true
   * when the campus is in place. The rows for a campus are created once. */
  P.sitePanel = function (D, ci) {
    var S = registry['site:schools'], C = registry['site:campus_' + ci];
    if (!S || !C) return false;
    if (!S.__byCeeb) {
      var idx = {};
      for (var i = 0; i < S.ceebs.length; i++) {
        var cols = S.data[i].map(P.unpack), m = {};
        for (var k = 0; k < cols[0].length; k++) {
          var row = new Array(cols.length - 1);
          for (var j = 1; j < cols.length; j++) row[j - 1] = cols[j][k];
          m[cols[0][k]] = row;          // year -> [C,Gc,H,ela,math,upp,Gp,Gr]
        }
        idx[S.ceebs[i]] = m;
      }
      S.__byCeeb = idx;
    }
    if (C.__installed) return true;
    var NONE = [null, null, null, null, null, null, null, null];
    for (var s = 0; s < C.ceebs.length; s++) {
      var ceeb = C.ceebs[s], f = C.data[s].map(P.unpack), cov = S.__byCeeb[ceeb] || {}, rows = [];
      for (var y = 0; y < f[0].length; y++) {
        var yr = f[0][y], c = cov[yr] || NONE;
        rows.push([yr, f[1][y], f[2][y], f[3][y], c[0], c[1], c[2], c[3], c[4], c[5], c[6], f[4][y], f[5][y], f[6][y], c[7]]);
      }
      D.panel[ci + '|' + ceeb] = rows;
    }
    C.__installed = true;
    return true;
  };
})();
