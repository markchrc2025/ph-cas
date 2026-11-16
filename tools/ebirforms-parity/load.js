const { chromium } = require('playwright');
const SHIM = `
(function(){
  var BASE='file://' + (window.__EBIR_APP__ || '/tmp/ebir/app/');
  function rd(path){ try { path=String(path).split(String.fromCharCode(92)).join('/'); if(path.indexOf('file:')!==0){ if(path.indexOf('./')===0) path=path.slice(2); path=BASE+path; } var x=new XMLHttpRequest(); x.open('GET',path,false); x.send(); return (x.status===0||x.status===200)&&x.responseText ? x.responseText : null; } catch(e){ return null; } }
  function fso(){ return { FileExists:(p)=>rd(p)!==null, FolderExists:()=>true, CreateFolder:()=>{}, OpenTextFile:(p)=>{ var t=rd(p)||''; return {ReadAll:()=>t,WriteLine:()=>{},Write:()=>{},Close:()=>{},AtEndOfStream:t.length===0,ReadLine:()=>''}; }, CreateTextFile:()=>({WriteLine:()=>{},Write:()=>{},Close:()=>{}}), GetFolder:()=>({Files:[] , SubFolders:[]}), DeleteFile:()=>{}, GetFile:()=>({}), GetAbsolutePathName:(p)=>p, BuildPath:(a,b)=>a+'\\\\'+b }; }
  window.ActiveXObject = function(n){ n=String(n).toLowerCase(); if(n.indexOf('scripting.filesystemobject')>=0) return fso(); if(n.indexOf('wscript.shell')>=0) return {Run:()=>0,ExpandEnvironmentStrings:(s)=>s,RegRead:()=>''}; if(n.indexOf('xmldom')>=0||n.indexOf('msxml')>=0){ return {async:false, loadXML:function(s){this._d=new DOMParser().parseFromString(s,'text/xml');return true;}, load:()=>false, selectNodes:()=>[], selectSingleNode:()=>null}; } return {}; };
  // mshta runs JScript 5.x, where Number#toLocaleString ignores its options and gives the
  // Windows number format with two decimals ("1,234.00"); Chromium would give "$1,234".
  Number.prototype.toLocaleString = function(){ var n=Number(this), neg=n<0, t=Math.abs(n).toFixed(2), i=t.split('.')[0], f=t.split('.')[1], o=''; while(i.length>3){ o=','+i.slice(-3)+o; i=i.slice(0,-3); } return (neg?'-':'')+i+o+'.'+f; };
  // JScript's Date#getYear gives the full year from 2000 on; Chromium gives year - 1900
  Date.prototype.getYear = function(){ var y = this.getFullYear(); return (y >= 1900 && y < 2000) ? y - 1900 : y; };
  window.alert = (m)=>{ (window.__alerts=window.__alerts||[]).push(String(m)); };
  window.confirm = (m)=>{ (window.__alerts=window.__alerts||[]).push('CONFIRM: '+m); return true; };
  window.msgbox = window.MsgBox = (m)=>{ (window.__alerts=window.__alerts||[]).push('MSGBOX: '+m); return 1; };
})();`;
module.exports = { SHIM };
if (require.main === module) {
 (async () => {
  const f = process.argv[2];
  const b = await chromium.launch(); const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message)); 
  await p.addInitScript(SHIM);
  await p.goto('file://' + f, { waitUntil: 'load' }).catch(e => errs.push('goto ' + e.message));
  await p.waitForTimeout(1500);
  console.log('title', await p.title());
  console.log('errors', JSON.stringify(errs.slice(0, 10)));
  console.log('alerts', JSON.stringify(await p.evaluate(() => window.__alerts || [])));
  await b.close();
 })();
}
