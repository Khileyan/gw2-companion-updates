import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {recoverWithExclusiveLock} from '../bootstrap/fixed-update.mjs';
import {acquireExclusiveUpdateLock,UpdateLockBusyError} from '../bootstrap/exclusive-update-lock.mjs';
function setup(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'gw2-recovery-lock-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 fs.mkdirSync(path.join(root,'updater'));
 return root;
}
const journal=r=>path.join(r,'updater','fixed-transaction.json');
const session=r=>path.join(r,'updater','launcher-session.json');
const exitedRecord={schema:2,pid:12345,started_at_utc:'2026-11-07T14:28:22.123Z',version:'5.9.0-rc.10'};
test('recovery cannot operate while normal update owns exclusive lock',t=>{
 const r=setup(t),owner=acquireExclusiveUpdateLock(r,{kind:'fixed-update'});
 fs.writeFileSync(journal(r),'keep');
 let called=false;
 try{
  assert.throws(()=>recoverWithExclusiveLock(r,{recover:()=>{called=true}}),UpdateLockBusyError);
  assert.equal(called,false);
  assert.equal(fs.readFileSync(journal(r),'utf8'),'keep');
 }finally{owner.release();}
});
test('normal update or rollback cannot acquire lock during recovery',t=>{
 const r=setup(t);
 let result;
 result=recoverWithExclusiveLock(r,{recover:()=>{
   assert.throws(()=>acquireExclusiveUpdateLock(r,{kind:'fixed-update'}),UpdateLockBusyError);
   return {recovered:true};
 }});
 assert.deepEqual(result,{recovered:true});
 assert.equal(fs.existsSync(path.join(r,'updater','update.lock')),false);
});
test('failed recovery preserves journal and releases only owned lock',t=>{
 const r=setup(t);fs.writeFileSync(journal(r),'KEEP');
 fs.writeFileSync(session(r),JSON.stringify(exitedRecord));
 assert.throws(()=>recoverWithExclusiveLock(r,{
  verifySession:()=> 'process_exited',
  recover:()=>{throw Error('synthetic EPERM')}
 }),/synthetic EPERM/);
 assert.equal(fs.readFileSync(journal(r),'utf8'),'KEEP');
 assert.equal(fs.existsSync(path.join(r,'updater','update.lock')),false);
});
test('tampered lock cannot be deleted even during failed recovery',t=>{
 const r=setup(t),lf=path.join(r,'updater','update.lock');
 assert.throws(()=>recoverWithExclusiveLock(r,{recover:()=>{
  fs.writeFileSync(lf,JSON.stringify({pid:999,token:'forged',kind:'fixed-update'}));
  throw Error('synthetic error');
 }}),/synthetic error|ownership lost/);
 assert.ok(fs.existsSync(lf));
});
test('CLI recovery routes through exclusive lock, not raw fixed core recovery',()=>{
 const text=fs.readFileSync(new URL('../bootstrap/fixed-update.mjs',import.meta.url),'utf8');
 assert.match(text,/if\(action==='recover'\)return recoverWithExclusiveLock\(root\)/);
 assert.doesNotMatch(text,/if\(action==='recover'\)return recoverFixed\(root\)/);
});
test('synchronous-only recovery refuses escaped asynchronous mutations',t=>{
 const r=setup(t);
 assert.throws(()=>recoverWithExclusiveLock(r,{recover:()=>Promise.resolve()}),/Async recovery is not supported/);
 assert.equal(fs.existsSync(path.join(r,'updater','update.lock')),false);
});

test('live launcher denies recovery before any file mutation',t=>{
 const r=setup(t);fs.writeFileSync(journal(r),'keep');
 fs.writeFileSync(session(r),JSON.stringify(exitedRecord));
 let called=false;
 assert.throws(()=>recoverWithExclusiveLock(r,{
  verifySession:()=> 'launcher_still_running',recover:()=>{called=true;}
 }),/launcher exit not verified/);
 assert.equal(called,false);
 assert.equal(fs.readFileSync(journal(r),'utf8'),'keep');
});
test('missing launcher session denies recovery and preserves journal',t=>{
 const r=setup(t);fs.writeFileSync(journal(r),'keep');
 assert.throws(()=>recoverWithExclusiveLock(r,{recover:()=>{throw Error('should not execute')}}),/identity unavailable/);
 assert.equal(fs.readFileSync(journal(r),'utf8'),'keep');
});
test('legacy PID-only session cannot authorize recovery',t=>{
 const r=setup(t);fs.writeFileSync(journal(r),'keep');
 fs.writeFileSync(session(r),JSON.stringify({pid:12345,version:'5.9.0-rc.10'}));
 assert.throws(()=>recoverWithExclusiveLock(r,{recover:()=>{throw Error('should not execute')}}),/launcher exit not verified/);
});
test('verified exited process authorizes recovery only under exclusive lock',t=>{
 const r=setup(t);fs.writeFileSync(journal(r),'keep');
 fs.writeFileSync(session(r),JSON.stringify(exitedRecord));
 const out=recoverWithExclusiveLock(r,{
  verifySession:()=> 'process_exited',
  recover:()=>{assert.ok(fs.existsSync(path.join(r,'updater','update.lock')));return {safe:true}}
 });
 assert.deepEqual(out,{safe:true});
 assert.equal(fs.readFileSync(journal(r),'utf8'),'keep');
});
