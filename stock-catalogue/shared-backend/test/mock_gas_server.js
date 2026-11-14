// Runs the real Code.gs with stand-ins for Google's SpreadsheetApp / ContentService / LockService.
const fs = require('fs'), vm = require('vm'), http = require('http');
const [,, CODE, PORT] = process.argv;
function Sheet() {
  const rows = []; let frozen = 0;
  const width = () => rows.reduce((m, r) => Math.max(m, r.length), 0);
  const check = (v) => { if (typeof v === 'string' && v.length > 50000) throw new Error('Your input contains more than the maximum of 50000 characters in a single cell.'); };
  return {
    rows, appendRow(a) { a.forEach(check); rows.push(a.slice()); },
    getDataRange() { const w = width(); return { getValues: () => rows.map((r) => { const c = r.slice(); while (c.length < w) c.push(''); return c; }) }; },
    getRange(r, c, nr, nc) { return { setNumberFormat() { return this; }, setFontWeight() { return this; }, setValues(v) { v.forEach((row, i) => { const R = r - 1 + i; while (rows.length <= R) rows.push([]); row.forEach((x, j) => { check(x); rows[R][c - 1 + j] = x; }); }); } }; },
    getLastRow: () => rows.length, getLastColumn: () => width(), deleteRow(r) { rows.splice(r - 1, 1); }, setFrozenRows(n) { frozen = n; },
    clearContents() { rows.length = 0; }, protect: () => ({ setWarningOnly() {} }),
  };
}
const sheets = {};
const ctx = {
  SpreadsheetApp: { getActiveSpreadsheet: () => ({ getSheetByName: (n) => sheets[n] || null, insertSheet: (n) => (sheets[n] = Sheet()) }) },
  ContentService: { MimeType: { JSON: 'json' }, createTextOutput: (s) => ({ s, setMimeType() { return this; } }) },
  LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
  JSON, Date, Number, String, Math, Object, console,
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(CODE, 'utf8').replace("const PASSCODE = 'CHANGE-ME'", "const PASSCODE = 'test-pass'"), ctx);
http.createServer((req, res) => {
  const cors = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json' };
  if (req.url.startsWith('/__view')) { res.writeHead(200, cors); const v = sheets['Articles (read-only)']; res.end(JSON.stringify(v ? v.rows : null)); return; }
  if (req.url.startsWith('/__sheet')) { res.writeHead(200, cors); res.end(JSON.stringify(sheets.data ? sheets.data.rows.map((r) => r.map((c) => (typeof c === 'string' ? c.length : c))) : [])); return; }
  let body = ''; req.on('data', (d) => (body += d)); req.on('end', () => {
    try {
      const u = new URL(req.url, 'http://x');
      const out = req.method === 'POST' ? vm.runInContext('doPost', ctx)({ postData: { contents: body } })
        : vm.runInContext('doGet', ctx)({ parameter: Object.fromEntries(u.searchParams) });
      res.writeHead(200, cors); res.end(out.s);
    } catch (e) { res.writeHead(500, cors); res.end(JSON.stringify({ ok: false, error: e.message })); }
  });
}).listen(PORT, () => console.log('mock apps script on', PORT));
