/**
 * Stock Catalogue Studio: shared database in a Google Sheet.
 *
 * Paste this whole file into Extensions > Apps Script of an empty Google Sheet.
 * Change PASSCODE below, then Deploy > New deployment > Web app
 * (Execute as: Me, Who has access: Anyone). See SETUP.md.
 *
 * Every article list, company and saved version is one row in the "data" sheet.
 * Do not edit the "data" sheet by hand: use the Studio page. The sheet's own
 * version history (File > Version history) is an extra backup.
 */
const PASSCODE = 'CHANGE-ME';   // the team passcode everyone types once in the Studio
const SHEET = 'data';
const CHUNK = 40000;            // a cell holds max 50,000 characters; long data spreads over more cells
const KINDS = ['companies', 'sections', 'versions'];

function out_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function sheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET);
  if (!sh) {
    sh = ss.insertSheet(SHEET);
    sh.appendRow(['kind', 'id', 'rev', 'updatedAt', 'updatedBy', 'data (do not edit by hand)']);
    sh.setFrozenRows(1);
  }
  return sh;
}

/** All stored documents, with their sheet row numbers. */
function rows_(sh) {
  const values = sh.getDataRange().getValues();
  const list = [];
  for (let i = 1; i < values.length; i++) {
    const r = values[i];
    if (!r[0]) continue;
    let json = '';
    for (let c = 5; c < r.length; c++) {
      const part = String(r[c] || '');
      if (part) json += part.slice(1);           // every part starts with "j" so Sheets never reads it as a formula
    }
    list.push({ row: i + 1, kind: String(r[0]), id: String(r[1]), rev: Number(r[2]) || 0,
      updatedAt: Number(r[3]) || 0, updatedBy: String(r[4] || ''), json: json });
  }
  return list;
}

function find_(list, kind, id) {
  for (let i = 0; i < list.length; i++) if (list[i].kind === kind && list[i].id === id) return list[i];
  return null;
}

function put_(sh, row, kind, id, rev, by, json) {
  const vals = [kind, id, rev, Date.now(), String(by || '').slice(0, 60)];
  for (let i = 0; i < json.length; i += CHUNK) vals.push('j' + json.slice(i, i + CHUNK));
  const width = Math.max(sh.getLastColumn(), vals.length);
  while (vals.length < width) vals.push('');
  sh.getRange(row, 1, 1, width).setValues([vals]);
}

/** Version lists leave out the large data snapshot; it is fetched when needed. */
function pub_(d, full) {
  let body = JSON.parse(d.json || '{}');
  if (!full && d.kind === 'versions' && body.snapshot) {
    body = Object.assign({}, body);
    delete body.snapshot;
    body.hasSnapshot = true;
  }
  return { kind: d.kind, id: d.id, rev: d.rev, updatedAt: d.updatedAt, updatedBy: d.updatedBy, body: body };
}

/* ---------- readable view: one article per row ---------- */
const VIEW = 'Articles (read-only)';
const FIXED = [['size', 'Size (mm)'], ['nominal_bore', 'Nominal bore'], ['od_mm', 'OD (mm)'], ['thickness_mm', 'Thick (mm)'],
  ['pipe_class', 'Class'], ['weight_kg_m', 'Kg/m'], ['weight_kg_pc', 'Kg/pc']];

function rebuildView_(list) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sh = ss.getSheetByName(VIEW);
    if (!sh) { sh = ss.insertSheet(VIEW, 0); sh.setFrozenRows(1); sh.protect().setWarningOnly(true); }
    const names = {};
    list.forEach(function (d) { if (d.kind === 'companies') { try { names[d.id] = JSON.parse(d.json).name; } catch (e) { names[d.id] = d.id; } } });
    const keys = FIXED.map(function (f) { return f[0]; });
    const secs = list.filter(function (d) { return d.kind === 'sections'; })
      .map(function (d) { return JSON.parse(d.json); })
      .sort(function (a, b) { return String(a.company).localeCompare(String(b.company)) || (a.order || 0) - (b.order || 0); });
    const out = [['Company', 'Category', 'Article code'].concat(FIXED.map(function (f) { return f[1]; })).concat(['Other fields'])];
    secs.forEach(function (s) {
      (s.rows || []).forEach(function (r) {
        const c = r.cells || {};
        const other = (s.columns || []).filter(function (col) { return keys.indexOf(col.key) < 0 && c[col.key]; })
          .map(function (col) { return col.label + ': ' + c[col.key]; }).join('; ');
        out.push([names[s.company] || s.company, s.title, r.code].concat(keys.map(function (k) { return c[k] === undefined ? '' : String(c[k]); })).concat([other]));
      });
    });
    sh.clearContents();
    const range = sh.getRange(1, 1, out.length, out[0].length);
    range.setNumberFormat('@');                 // keep values exactly as typed (2.00 stays 2.00)
    range.setValues(out);
    sh.getRange(1, 1, 1, out[0].length).setFontWeight('bold');
  } catch (err) {
    console.error('Articles view not updated: ' + err);   // never block a save because of the view
  }
}

/** Run this once from the editor (select it, press Run) to build the Articles tab straight away. */
function refreshArticlesSheet() { rebuildView_(rows_(sheet_())); }

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.key !== PASSCODE) return out_({ ok: false, error: 'bad_key' });
  const list = rows_(sheet_());
  if (p.action === 'get') {
    const d = find_(list, p.kind, String(p.id));
    return out_(d ? { ok: true, doc: pub_(d, true) } : { ok: false, error: 'not_found' });
  }
  return out_({ ok: true, now: Date.now(), docs: list.map(function (d) { return pub_(d, false); }) });
}

function doPost(e) {
  let req;
  try { req = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false, error: 'bad_request' }); }
  if (req.key !== PASSCODE) return out_({ ok: false, error: 'bad_key' });
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sh = sheet_();
    const list = rows_(sh);
    if (req.action === 'seed') {
      if (list.length) return out_({ ok: false, error: 'not_empty' });
      (req.docs || []).forEach(function (d) {
        if (KINDS.indexOf(d.kind) < 0 || !d.id) return;
        sh.appendRow([d.kind]);
        put_(sh, sh.getLastRow(), d.kind, String(d.id), 1, req.by, JSON.stringify(d.body));
      });
      rebuildView_(rows_(sh));
      return out_({ ok: true });
    }
    if (KINDS.indexOf(req.kind) < 0 || !req.id) return out_({ ok: false, error: 'bad_request' });
    const cur = find_(list, req.kind, String(req.id));
    if (req.action === 'save') {
      // someone else saved this since you loaded it: send theirs back instead of overwriting
      if (cur && Number(req.rev) !== cur.rev) return out_({ ok: false, error: 'conflict', doc: pub_(cur, true) });
      const rev = cur ? cur.rev + 1 : 1;
      let row = cur ? cur.row : 0;
      if (!row) { sh.appendRow([req.kind]); row = sh.getLastRow(); }
      put_(sh, row, req.kind, String(req.id), rev, req.by, JSON.stringify(req.body));
      if (req.kind !== 'versions') rebuildView_(rows_(sh));
      return out_({ ok: true, rev: rev });
    }
    if (req.action === 'delete') {
      if (cur) sh.deleteRow(cur.row);
      if (req.kind !== 'versions') rebuildView_(rows_(sh));
      return out_({ ok: true });
    }
    return out_({ ok: false, error: 'bad_request' });
  } finally {
    lock.releaseLock();
  }
}
