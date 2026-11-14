const { chromium } = require('playwright'); const fs = require('fs');
const FILE = process.argv[2], SP = process.argv[3], API = 'http://127.0.0.1:8765/exec';
(async () => {
  const b = await chromium.launch(); const errs = [];
  const person = async (name) => {
    const ctx = await b.newContext({ acceptDownloads: true, viewport: { width: 1280, height: 900 } });
    await ctx.route(/^https?:\/\/(?!127\.0\.0\.1)/, r => r.abort());
    const p = await ctx.newPage(); p.on('pageerror', e => errs.push(name + ': ' + e.message));
    await p.goto('file://' + FILE); await p.waitForSelector('#connectForm');
    return p;
  };
  const connect = async (p, key, name) => { await p.fill('#cx_url', API); await p.fill('#cx_key', key); await p.fill('#cx_by', name); await p.click('#connectForm button[type=submit]'); await p.waitForTimeout(400); };
  const A = await person('A');
  await connect(A, 'wrong', 'Devarsh');
  console.log('wrong passcode message:', await A.textContent('#connectForm .flag'));
  await connect(A, 'test-pass', 'Devarsh');
  await A.click('button[data-act="seedRemote"]'); await A.waitForSelector('button.cat');
  const add = async (p, size, thk, kgm) => { await p.click('button.cat:has-text("Square Hollow")'); await p.fill('#add_size', size); await p.fill('#add_thickness_mm', thk); await p.fill('#add_weight_kg_m', kgm); await p.click('button[data-act="addRow"]'); await p.waitForTimeout(600); };
  await add(A, '44x44', '2.0', '2.55');
  console.log('A status after add:', await A.textContent('#status'));
  const B = await person('B'); await connect(B, 'test-pass', 'Nitin'); await B.waitForSelector('button.cat');
  await B.click('button.cat:has-text("Square Hollow")');
  console.log('B sees A\'s new article:', await B.$eval('table', t => t.innerHTML.includes('SHS-44X44-2.0')));
  await add(B, '46x46', '2.5', '3.30');
  await A.click('#tabs button[data-view="versions"]'); await A.click('button[data-act="syncNow"]'); await A.waitForTimeout(500);
  await A.click('#tabs button[data-view="articles"]'); await A.click('button.cat:has-text("Square Hollow")');
  console.log('A sees B\'s new article after sync:', await A.$eval('table', t => t.innerHTML.includes('SHS-46X46-2.5')));
  // simultaneous edit of the same category -> conflict handled, nothing silently lost
  await B.fill('#add_size', '48x48'); await B.fill('#add_thickness_mm', '2.0');
  await A.fill('#add_size', '49x49'); await A.fill('#add_thickness_mm', '2.0');
  await A.click('button[data-act="addRow"]'); await A.waitForTimeout(500);
  await B.click('button[data-act="addRow"]'); await B.waitForTimeout(700);
  console.log('B conflict notice:', ((await B.textContent('#main')).match(/changed this at the same time[^.]*/) || ['none'])[0]);
  // A exports version 1; B downloads it from the shared list
  await A.click('#exportBtn');
  const [d] = await Promise.all([A.waitForEvent('download'), A.click('button[data-act="exportVersion"]')]); await d.saveAs(SP + '/shared_v1_A.pdf');
  await B.click('#tabs button[data-view="versions"]'); await B.click('button[data-act="syncNow"]'); await B.waitForTimeout(500);
  console.log('B sees versions:', await B.$$eval('.ver', v => v.length));
  const [d2] = await Promise.all([B.waitForEvent('download'), B.click('button[data-act="dlVer"]')]); await d2.saveAs(SP + '/shared_v1_B.pdf');
  // reconnects automatically after reopening
  await B.reload(); await B.waitForSelector('button.cat');
  console.log('B reopened without re-entering passcode:', true);
  console.log('page errors:', errs.length ? errs : 'none');
  await b.close();
})();
