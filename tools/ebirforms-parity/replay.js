// node replay.js <form.html> <prefix> <ledger.json> [extra-steps.json]
// Replays Ledger's own export into eBIRForms' form: marks every radio and checkbox Ledger
// set, picks every dropdown, types every amount the form leaves open (twice over, so
// fields a first pass opens get their value), then compares every amount and saves the
// file eBIRForms would write.
const { chromium } = require('playwright');
const { SHIM } = require('./load.js');
const fs = require('fs');
(async () => {
  const [file, prefix, ledgerFile, extraFile] = process.argv.slice(2);
  const led = JSON.parse(fs.readFileSync(ledgerFile, 'utf8')).export;
  const extra = extraFile ? JSON.parse(fs.readFileSync(extraFile, 'utf8')) : { before: [], after: [], skip: [] };
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] }); const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.addInitScript(`window.__EBIR_APP__ = ${JSON.stringify((process.env.EBIR_APP || '/tmp/ebir/app').replace(/\/?$/, '/'))};`);
  await p.addInitScript(SHIM);
  await p.goto('file://' + file, { waitUntil: 'load' });
  await p.waitForTimeout(900);
  const run = async (steps) => { for (const [id, val, kind] of steps) {
    if (kind === 'wait') { await p.waitForTimeout(Number(val) || 400); continue; }
    await p.evaluate(([pre, fid, v, k]) => {
      if (k === 'call') { try { eval(v); } catch (e) { (window.__alerts = window.__alerts || []).push('CALL ' + v + ': ' + e.message); } return; }
      const el = document.getElementById(pre + fid) || document.getElementById(fid);
      if (!el) return;
      if (k === 'click') { if (!el.checked) el.click(); return; }
      el.value = v; for (const ev of ['keyup', 'change', 'blur']) el.dispatchEvent(new Event(ev, { bubbles: false }));
    }, [prefix, id, val, kind || 'set']); } };
  await run(extra.before || []);
  const isAmt = v => process.env.WHOLE ? /^\(?-?[\d,]*\d(\.\d\d)?\)?$/.test(v) && !/^0\d/.test(v) : /^-?[\d,]+\.\d\d$/.test(v);
  const keys = Object.keys(led);
  // 1. radios and checkboxes Ledger marked, dropdowns Ledger picked
  for (const k of keys) {
    if ((extra.skip || []).includes(k)) continue;
    await p.evaluate(([pre, fid, v, whole]) => {
      const el = document.getElementById(pre + fid) || document.getElementById(fid);
      if (el && el.disabled && v === 'true') (window.__alerts = window.__alerts || []).push('DISABLED-MARK ' + fid);
      if (!el || el.disabled) return;
      if ((el.type === 'radio' || el.type === 'checkbox') && v === 'true' && !el.checked) el.click();
      if (el.tagName === 'SELECT' && el.value !== ((x)=>{try{return decodeURIComponent(x)}catch(e){return x}})(v)) { el.value = ((x)=>{try{return decodeURIComponent(x)}catch(e){return x}})(v); el.dispatchEvent(new Event('change')); }
      if (el.type === 'text' && !el.readOnly && !(whole ? /^\(?-?[\d,]*\d(\.\d\d)?\)?$/.test(v) && !/^0\d/.test(v) : /^-?[\d,]+\.\d\d$/.test(v)) && v !== '' && el.value !== ((x)=>{try{return decodeURIComponent(x)}catch(e){return x}})(v)) { el.value = ((x)=>{try{return decodeURIComponent(x)}catch(e){return x}})(v); for (const ev of ['keyup', 'change', 'blur']) el.dispatchEvent(new Event(ev, { bubbles: false })); }
    }, [prefix, k, led[k], !!process.env.WHOLE]);
  }
  if (process.env.WATCH) console.error('after step 1:', await p.evaluate((ids) => ids.map(i => { const e = document.getElementById(i); return i + '=' + (e ? (e.type === 'radio' || e.type === 'checkbox' ? e.checked : e.value) : 'none'); }).join(' '), process.env.WATCH.split(',')));
  await run(extra.mid || []);
  // 2. every open amount (and plain typed number), twice
  const typed = new Set();
  for (let pass = 0; pass < 2; pass++) for (const k of keys) {
    if ((extra.skip || []).includes(k) || !isAmt(led[k])) continue;
    const did = await p.evaluate(([pre, fid, v]) => {
      const el = document.getElementById(pre + fid) || document.getElementById(fid);
      if (!el || el.disabled || el.readOnly || el.type !== 'text') return false;
      el.focus && el.focus(); el.value = v; for (const ev of ['keyup', 'change', 'blur']) el.dispatchEvent(new Event(ev, { bubbles: false }));
      return true;
    }, [prefix, k, led[k]]);
    if (did) typed.add(k);
  }
  if (process.env.WATCH) console.error('after step 2:', await p.evaluate((ids) => ids.map(i => { const e = document.getElementById(i); return i + '=' + (e ? (e.type === 'radio' || e.type === 'checkbox' ? e.checked : e.value) : 'none'); }).join(' '), process.env.WATCH.split(',')));
  await run(extra.after || []);
  await p.waitForTimeout(400);
  const amountKeys = keys.filter(k => isAmt(led[k]));
  const got = await p.evaluate(([pre, ids]) => Object.fromEntries(ids.map(i => { const el = document.getElementById(pre + i) || document.getElementById(i); return [i, el ? el.value : null]; })), [prefix, amountKeys]);
  const norm = v => { if (v == null) return null; let t = String(v).replace(/[,$\s]/g, ''); const neg = /^\(.*\)$/.test(t); t = t.replace(/[()]/g, ''); const n = Number(t || 0); return (neg ? -n : n).toFixed(2); };
  const diffs = [], missing = []; let same = 0;
  for (const k of amountKeys) { if (got[k] === null) { missing.push(k); continue; } if (norm(got[k]) === norm(led[k])) same++; else diffs.push([k, 'ledger ' + led[k], 'eBIRForms ' + got[k], typed.has(k) ? 'typed' : 'computed']); }
  const saved = await p.evaluate(() => { const f = document.getElementById('frmMain') || document.forms[0]; if (!f) return null; const out = [];
    for (const e of f.elements) { if (e.type == 'button' || e.type == 'hidden' || e.type == 'undefined' || !e.id) continue;
      if (e.type == 'text' || e.type == 'select-one') out.push([e.id, escape(e.value)]);
      if (e.type == 'radio' || e.type == 'checkbox') out.push([e.id, String(e.checked)]); } return out; });
  fs.writeFileSync(ledgerFile.replace('.json', '.ebir.json'), JSON.stringify(got, null, 1));
  fs.writeFileSync(ledgerFile.replace('.json', '.saved.json'), JSON.stringify(saved));
  fs.writeFileSync(ledgerFile.replace('.json', '.typed.json'), JSON.stringify([...typed]));
  console.log(JSON.stringify({ compared: same + diffs.length, same, typed: typed.size, diffs, not_on_form: missing, alerts: await p.evaluate(() => (window.__alerts || []).slice(0, 12)), errors: errs.slice(0, 5) }, null, 1));
  await b.close();
})();
