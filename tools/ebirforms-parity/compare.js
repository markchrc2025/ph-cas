// node compare.js <form.html> <prefix> <steps.json> <ledger.json>
// Types the steps into eBIRForms' own form (null value = the Ledger's exported value for that id),
// then compares every amount the Ledger exports with what eBIRForms computed for the same field.
const { chromium } = require('playwright');
const { SHIM } = require('./load.js');
const fs = require('fs');
(async () => {
  const [file, prefix, stepsFile, ledgerFile] = process.argv.slice(2);
  const steps = JSON.parse(fs.readFileSync(stepsFile, 'utf8'));
  const led = JSON.parse(fs.readFileSync(ledgerFile, 'utf8')).export || {};
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] }); const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.addInitScript(`window.__EBIR_APP__ = ${JSON.stringify((process.env.EBIR_APP || '/tmp/ebir/app').replace(/\/?$/, '/'))};`);
  await p.addInitScript(SHIM);
  await p.goto('file://' + file, { waitUntil: 'load' });
  await p.waitForTimeout(800);
  for (let [id, val, kind] of steps) {
    if (kind === 'wait') { await p.waitForTimeout(Number(val) || 400); continue; }
    if (val === null) val = led[id];
    await p.evaluate(([fid, v, k]) => {
      if (k === 'call') { try { eval(v); } catch (e) { (window.__alerts = window.__alerts || []).push('CALL ' + v + ': ' + e.message); } return; }
      const el = document.getElementById(fid) || document.getElementById(fid.split(':').pop());
      if (!el) { (window.__alerts = window.__alerts || []).push('NO FIELD ' + fid); return; }
      if (k === 'click') { if (!el.checked) el.click(); return; }
      else if (k === 'call') { eval(v); return; }
      else if (k === 'select') { el.value = v; }
      else { if (el.disabled) { (window.__alerts = window.__alerts || []).push('DISABLED ' + fid + ' (wanted ' + v + ')'); return; } el.focus && el.focus(); el.value = v; }
      for (const ev of ['keyup', 'change', 'blur']) el.dispatchEvent(new Event(ev, { bubbles: false }));
    }, [prefix + id, val, kind || 'set']);
  }
  await p.waitForTimeout(400);
  const amountKeys = Object.keys(led).filter(k => /^-?[\d,]+\.\d\d$/.test(led[k]));
  const got = await p.evaluate(([pre, ids]) => Object.fromEntries(ids.map(i => { const el = document.getElementById(pre + i) || document.getElementById(i); return [i, el ? el.value : null]; })), [prefix, amountKeys]);
  const norm = v => v == null ? null : Number(String(v).replace(/,/g, '') || 0).toFixed(2);
  const diffs = [], same = [], missing = [];
  for (const k of amountKeys) {
    if (got[k] === null) { missing.push(k); continue; }
    (norm(got[k]) === norm(led[k]) ? same : diffs).push(k);
  }
  console.log(JSON.stringify({ compared: same.length + diffs.length, same: same.length, diffs: diffs.map(k => [k, 'ledger ' + led[k], 'eBIRForms ' + got[k]]), not_on_form: missing, alerts: await p.evaluate(() => (window.__alerts || []).slice(0, 10)), errors: errs.slice(0, 5) }, null, 1));
  fs.writeFileSync(ledgerFile.replace('.json', '.ebir.json'), JSON.stringify(got, null, 1));
  const saved = await p.evaluate(() => { const f = document.getElementById('frmMain'); if (!f) return null; const out = [];
    for (const e of f.elements) { if (e.type == 'button' || e.type == 'hidden' || e.type == 'undefined' || !e.id) continue;
      if (e.type == 'text' || e.type == 'select-one') out.push([e.id, escape(e.value)]);
      if (e.type == 'radio' || e.type == 'checkbox') out.push([e.id, String(e.checked)]); } return out; });
  fs.writeFileSync(ledgerFile.replace('.json', '.saved.json'), JSON.stringify(saved));
  await b.close();
})();
