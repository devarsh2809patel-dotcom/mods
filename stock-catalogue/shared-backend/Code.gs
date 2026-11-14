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
      return out_({ ok: true, rev: rev });
    }
    if (req.action === 'delete') {
      if (cur) sh.deleteRow(cur.row);
      return out_({ ok: true });
    }
    return out_({ ok: false, error: 'bad_request' });
  } finally {
    lock.releaseLock();
  }
}
