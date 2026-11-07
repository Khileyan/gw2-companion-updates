import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {inspectStaleJournal,archiveStaleJournal} from '../bootstrap/stale-journal.mjs';
const NOW=1794057500000;
function setup(t,opts={}){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'gw2-journal-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const u=path.join(root,'updater');fs.mkdirSync(u);
  const backup=path.join(u,'fixed-rollback-fixture');
  for(const dir of ['app','launcher','assets','projects','bootstrap'])fs.mkdirSync(path.join(backup,dir),{recursive:true});
  fs.mkdirSync(path.join(root,'app'));
  const save=(p,x)=>fs.writeFileSync(p,JSON.stringify(x));
  save(path.join(root,'app','package.json'),{version:opts.installed??'5.9.0-rc.9'});
  save(path.join(root,'app-version.json'),{version:opts.marker??'5.9.0-rc.9'});
  save(path.join(backup,'app','package.json'),{version:'5.9.0-rc.8.2'});
  save(path.join(u,'fixed-transaction.json'),{schema:1,layout:'fixed-v1',from:'5.9.0-rc.8.2',to:'5.9.0-rc.9',backup,at:opts.at??NOW-150000,phase:opts.phase??'starting'});
  return {root,u,backup,save};
}
test('read-only inspection identifies old RC8.2 to RC9 journal',t=>{
  const f=setup(t);const check=inspectStaleJournal(f.root,{now:NOW,isAlive:()=>false});
  assert.equal(check.safe_to_archive,true);assert.equal(check.to,'5.9.0-rc.9');
  assert.ok(fs.existsSync(path.join(f.u,'fixed-transaction.json')));
});
test('explicit consent required; retain backup and status after archival',t=>{
  const f=setup(t);f.save(path.join(f.u,'status.json'),{state:'failed'});
  assert.throws(()=>archiveStaleJournal(f.root,{now:NOW,isAlive:()=>false}),/Explicit local approval/);
  const out=archiveStaleJournal(f.root,{approved:true,now:NOW,isAlive:()=>false});
  assert.equal(out.archived,true);assert.ok(fs.existsSync(f.backup));
  assert.ok(fs.existsSync(path.join(f.u,out.archive_name)));
  assert.ok(!fs.existsSync(path.join(f.u,'fixed-transaction.json')));
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.u,'status.json'))),{state:'failed'});
});
for(const [name,mutate,expected] of [
  ['active update lock',({u})=>fs.writeFileSync(path.join(u,'update.lock'),''),'update_in_progress_or_locked'],
  ['other transaction',({u})=>fs.writeFileSync(path.join(u,'transaction.json'),''),'update_in_progress_or_locked'],
  ['pending shutdown',({u})=>fs.writeFileSync(path.join(u,'shutdown.request'),''),'update_in_progress_or_locked'],
  ['missing backup component',({backup})=>fs.rmSync(path.join(backup,'launcher'),{recursive:true}),'incomplete_backup'],
  ['version mismatch',({root,save})=>save(path.join(root,'app','package.json'),{version:'5.9.0-rc.8.2'}),'version_mismatch'],
  ['target marker mismatch',({root,save})=>save(path.join(root,'app-version.json'),{version:'5.9.0-rc.10'}),'version_mismatch'],
  ['too recent',({u,save})=>{const p=path.join(u,'fixed-transaction.json');const x=JSON.parse(fs.readFileSync(p));x.at=NOW-1000;save(p,x);},'transaction_too_recent'],
  ['unknown phase',({u,save})=>{const p=path.join(u,'fixed-transaction.json');const x=JSON.parse(fs.readFileSync(p));x.phase='moving';save(p,x);},'unknown_transaction'],
  ['invalid backup path',({u,save})=>{const p=path.join(u,'fixed-transaction.json');const x=JSON.parse(fs.readFileSync(p));x.backup='/not/under/updater';save(p,x);},'unknown_transaction']
])test('refuses '+name,t=>{
  const f=setup(t);mutate(f);
  assert.equal(inspectStaleJournal(f.root,{now:NOW,isAlive:()=>false}).reason,expected);
  assert.throws(()=>archiveStaleJournal(f.root,{approved:true,now:NOW,isAlive:()=>false}),/Archive refused/);
  assert.ok(fs.existsSync(path.join(f.u,'fixed-transaction.json')));
});
test('running launcher session vetoes archival',t=>{
  const f=setup(t);f.save(path.join(f.u,'launcher-session.json'),{pid:1234});
  assert.equal(inspectStaleJournal(f.root,{now:NOW,isAlive:()=>true}).reason,'launcher_still_running');
});

test('pending transaction has its own sanitized error code and a blocking GUI warning',()=>{
  const fixed=fs.readFileSync(new URL('../bootstrap/fixed-update.mjs',import.meta.url),'utf8');
  const gui=fs.readFileSync(new URL('../launcher/GW2-Companion.ps1',import.meta.url),'utf8');
  assert.match(fixed,/pending_fixed_transaction/);
  assert.match(gui,/\\$progress\\.error_code -eq 'pending_fixed_transaction'/);
  assert.match(gui,/Vorheriges Update nicht abgeschlossen/);
  assert.match(gui,/\\$btnUpdate\\.Enabled=\\$false/);
});
test('inspection and archival are separate CLI routes; archive requires local approval',()=>{
  const fixed=fs.readFileSync(new URL('../bootstrap/fixed-update.mjs',import.meta.url),'utf8');
  assert.match(fixed,/action==='inspect-stale'/);
  assert.match(fixed,/action==='archive-stale'/);
  assert.match(fixed,/if\\(!process\\.argv\\.includes\\('--approve'\\)\\)throw Error/);
});
