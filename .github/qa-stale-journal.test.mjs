import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// Historical incident fixture. This test suite does not modify a real installation.
// Do not mistake a green static guard test for a verified automatic repair.
const update = fs.readFileSync(new URL('../bootstrap/fixed-update.mjs',import.meta.url),'utf8');
const gui = fs.readFileSync(new URL('../launcher/GW2-Companion.ps1',import.meta.url),'utf8');

function fixture(overrides={}) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'gw2-qa-journal-'));
  const updater=path.join(root,'updater');
  const backup=path.join(updater,'fixed-rollback-synthetic');
  fs.mkdirSync(backup,{recursive:true});
  fs.mkdirSync(path.join(root,'app'),{recursive:true});
  fs.writeFileSync(path.join(root,'app','package.json'), JSON.stringify({version:'5.9.0-rc.9'}));
  const journal={schema:1,layout:'fixed-v1',from:'5.9.0-rc.8.2',to:'5.9.0-rc.9',backup,at:1794057341979,phase:'starting',...overrides};
  fs.writeFileSync(path.join(updater,'fixed-transaction.json'), JSON.stringify(journal));
  fs.writeFileSync(path.join(updater,'status.json'),JSON.stringify({state:'failed',phase:'not-activated',error_code:'update_aborted'}));
  return {root,updater,backup,journal};
}

test('real incident fixture: installed RC9, unfinished RC8.2 to RC9 journal, no update lock',t=>{
  const f=fixture();
  t.after(()=>fs.rmSync(f.root,{recursive:true,force:true}));
  assert.equal(JSON.parse(fs.readFileSync(path.join(f.root,'app','package.json'))).version,f.journal.to);
  assert.equal(JSON.parse(fs.readFileSync(path.join(f.updater,'fixed-transaction.json'))).phase,'starting');
  assert.ok(fs.existsSync(f.backup));
  assert.equal(fs.existsSync(path.join(f.updater,'update.lock')),false);
  assert.equal(fs.existsSync(path.join(f.updater,'transaction.json')),false);
  assert.equal(JSON.parse(fs.readFileSync(path.join(f.updater,'status.json'))).error_code,'update_aborted');
});

test('existing installer retains incomplete journal rather than silently deleting it',()=>{
  assert.match(update,/if\(fs\.existsSync\(p\.journal\)\)throw Error/);
  assert.doesNotMatch(update,/fs\.rmSync\(p\.journal,\{force:true\}\)/);
});

test('status display and actual backup safety are distinct from verified signed manifests',()=>{
  assert.match(gui,/fixed-transaction\.json/);
  assert.match(gui,/Letztes Update fehlgeschlagen/);
  assert.match(gui,/check-status\.json/);
});

test.todo('LIVE REGRESSION: previous-version installed journal at starting is classified as stale only after full process, backup, and version safety checks');
test.todo('LIVE REGRESSION: previous incomplete journal is reconciled safely; missing backup, mismatched target, active updater and update.lock remain blocked');
test.todo('LIVE REGRESSION: status failed from a historical update is distinguished from failed current installation in the GUI');
test.todo('LIVE REGRESSION: interrupted updater retry preserves rollback backup and produces reason-coded diagnostics');
