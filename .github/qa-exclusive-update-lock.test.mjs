import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {withExclusiveUpdateLock,acquireExclusiveUpdateLock,UpdateLockBusyError} from '../bootstrap/exclusive-update-lock.mjs';
function create(t){const r=fs.mkdtempSync(path.join(os.tmpdir(),'gw2-lock-'));t.after(()=>fs.rmSync(r,{recursive:true,force:true}));fs.mkdirSync(path.join(r,'updater'));return r;}
const lock=r=>path.join(r,'updater','update.lock');
test('exclusive lock blocks nested racing acquisition and cleans owned lock',t=>{
 const r=create(t);let ran=false;const n=withExclusiveUpdateLock(r,()=>{
  assert.ok(fs.existsSync(lock(r)));assert.throws(()=>withExclusiveUpdateLock(r,()=>{ran=true}),UpdateLockBusyError);return 123;
 });assert.equal(n,123);assert.equal(ran,false);assert.equal(fs.existsSync(lock(r)),false);
});
test('stale lock is never automatically reclaimed',t=>{
 const r=create(t);fs.writeFileSync(lock(r),JSON.stringify({pid:9999999,created_at:1}));
 assert.throws(()=>withExclusiveUpdateLock(r,()=>{}),UpdateLockBusyError);assert.ok(fs.existsSync(lock(r)));
});
test('throwing callback releases only owned lock',t=>{
 const r=create(t);assert.throws(()=>withExclusiveUpdateLock(r,()=>{throw Error('failed')}),/failed/);
 assert.equal(fs.existsSync(lock(r)),false);
});
test('lock replacement cannot be deleted by prior holder',t=>{
 const r=create(t);assert.throws(()=>withExclusiveUpdateLock(r,()=>{
  fs.writeFileSync(lock(r),JSON.stringify({schema:1,pid:9999,token:'changed',kind:'stale-journal-review'}));
 }),/ownership lost/);assert.ok(fs.existsSync(lock(r)));
});
test('symlink updater directory refuses lock',t=>{
 const r=create(t),other=fs.mkdtempSync(path.join(os.tmpdir(),'gw2-lock-target-'));
 t.after(()=>fs.rmSync(other,{recursive:true,force:true}));fs.rmSync(path.join(r,'updater'),{recursive:true});
 try{fs.symlinkSync(other,path.join(r,'updater'),'dir');}catch(e){if(process.platform==='win32')return;throw e;}
 assert.throws(()=>withExclusiveUpdateLock(r,()=>{}),/Unsafe updater directory/);
});
test('second Node process observes held exclusive lock',t=>{
 const r=create(t),url=new URL('../bootstrap/exclusive-update-lock.mjs',import.meta.url).href;
 withExclusiveUpdateLock(r,()=>{
  const js=`import {withExclusiveUpdateLock} from ${JSON.stringify(url)};try{withExclusiveUpdateLock(process.argv[1],()=>{});process.exitCode=99}catch(e){if(e.code!=='UPDATE_LOCK_BUSY')process.exitCode=98;}`;
  const p=spawnSync(process.execPath,['--input-type=module','-e',js,r],{encoding:'utf8'});
  assert.equal(p.status,0,p.stderr);
 });
});

test('abrupt updater termination leaves a lock and blocks any subsequent repair',t=>{
 const r=create(t),url=new URL('../bootstrap/exclusive-update-lock.mjs',import.meta.url).href;
 const js=`import {withExclusiveUpdateLock} from ${JSON.stringify(url)};withExclusiveUpdateLock(process.argv[1],()=>{process.exit(67);});`;
 const p=spawnSync(process.execPath,['--input-type=module','-e',js,r],{encoding:'utf8'});
 assert.equal(p.status,67,p.stderr);
 assert.ok(fs.existsSync(lock(r)));
 assert.throws(()=>withExclusiveUpdateLock(r,()=>{}),UpdateLockBusyError);
});
test('asynchronous callback is rejected instead of silently dropping exclusive ownership',t=>{
 const r=create(t);
 assert.throws(()=>withExclusiveUpdateLock(r,()=>Promise.resolve()),/Async callback is not supported/);
 assert.equal(fs.existsSync(lock(r)),false);
});

test('existing fixed updater wx lock and reviewer lock are mutually exclusive',t=>{
 const r=create(t);
 fs.writeFileSync(lock(r),JSON.stringify({pid:5555,created:1}),{flag:'wx'});
 assert.throws(()=>withExclusiveUpdateLock(r,()=>{}),UpdateLockBusyError);
 fs.rmSync(lock(r));
 withExclusiveUpdateLock(r,()=>{
   assert.throws(()=>fs.writeFileSync(lock(r),JSON.stringify({pid:7777}),{flag:'wx'}),e=>e.code==='EEXIST');
 });
});

test('async fixed updater holds exclusive lock across awaited work',async t=>{
 const r=create(t);
 const owner=acquireExclusiveUpdateLock(r,{kind:'fixed-update'});
 try{
  await new Promise(resolve=>setImmediate(resolve));
  assert.throws(()=>acquireExclusiveUpdateLock(r,{kind:'stale-journal-review'}),UpdateLockBusyError);
  owner.assertOwned();
 }finally{owner.release();}
 assert.equal(fs.existsSync(lock(r)),false);
});
test('fixed updater cannot remove another process replacement lock',t=>{
 const r=create(t),owner=acquireExclusiveUpdateLock(r,{kind:'fixed-update'});
 const p=lock(r);
 fs.writeFileSync(p,JSON.stringify({schema:1,pid:555,token:'replacement',kind:'fixed-update'}));
 assert.throws(()=>owner.release(),/ownership lost/);
 assert.equal(fs.existsSync(p),true);
});
test('fixed updater uses token owner lock, not blind rmSync',()=>{
 const src=fs.readFileSync(new URL('../bootstrap/fixed-update.mjs',import.meta.url),'utf8');
 assert.match(src,/acquireExclusiveUpdateLock\(root,\{kind:'fixed-update'\}\)\.release/);
 assert.doesNotMatch(src,/function lock\(root\)\{const f=fixedPaths\(root\)\.lock/);
});
