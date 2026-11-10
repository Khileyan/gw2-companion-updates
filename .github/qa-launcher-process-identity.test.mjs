import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {compareLauncherIdentity,verifyLauncherSession,observeWindowsProcess} from '../bootstrap/launcher-process-identity.mjs';
const session={schema:2,pid:12345,version:'5.9.0-rc.10',started_at_utc:'2026-11-07T15:28:22.123Z'};
const observed={kind:'observed',pid:12345,image:'powershell.exe',started_at_utc:'2026-11-07T15:28:22.123Z'};
test('same PID and Windows creation time identifies current launcher',()=>{
 assert.equal(compareLauncherIdentity(session,observed),'launcher_still_running');
});
test('reused PID with different creation time never accepted',()=>{
 assert.equal(compareLauncherIdentity(session,{...observed,started_at_utc:'2026-11-07T15:29:22.123Z'}),'pid_reused_or_identity_mismatch');
});
test('different process image with same PID/time not accepted',()=>{
 assert.equal(compareLauncherIdentity(session,{...observed,image:'notepad.exe'}),'process_identity_unverified');
});
test('unknown process state fails closed',()=>{
 assert.equal(verifyLauncherSession(session,{observe:()=>({kind:'unavailable'})}),'process_identity_unverified');
});
test('confirmed process exit is not alone authorization to archive',()=>{
 assert.equal(compareLauncherIdentity(session,{kind:'not_found'}),'process_exited');
});
test('legacy session cannot prove a process identity',()=>{
 assert.equal(verifyLauncherSession({pid:12345,version:'5.9.0-rc.10'},{observe:()=>observed}),'unverifiable_legacy_session');
});
test('missing or malformed timestamp cannot prove identity',()=>{
 for(const value of ['not-a-date','2026-11-07T15:28:22Z','2026-11-07T15:28:22.123+01:00']){
  assert.equal(compareLauncherIdentity({...session,started_at_utc:value},observed),'unverifiable_legacy_session');
 }
});
test('invalid PID cannot reach OS process observer',()=>{
 assert.deepEqual(observeWindowsProcess(-1),{kind:'unavailable'});
});
test('verified launcher session source stores PID AND process start timestamp',()=>{
 const ps=fs.readFileSync(new URL('../launcher/GW2-Companion.ps1',import.meta.url),'utf8');
 assert.match(ps,/started_at_utc=\$started/);
 assert.match(ps,/schema=2;pid=\$PID/);
});

test('Windows: live OS observer returns PID and creation timestamp of this Node process',{skip:process.platform!=='win32'},()=>{
 const seen=observeWindowsProcess(process.pid);
 assert.equal(seen.kind,'observed',JSON.stringify(seen));
 assert.equal(seen.pid,process.pid);
 assert.match(seen.started_at_utc,/^\d{4}-/);
 assert.equal(seen.image.toLowerCase(),'node.exe');
});
