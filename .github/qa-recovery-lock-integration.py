#!/usr/bin/env python3
"""Make CLI recovery share the same exclusive update lock as update and rollback."""
from pathlib import Path
import sys
p=(Path(sys.argv[1]) if len(sys.argv)>1 else Path('source'))/'bootstrap/fixed-update.mjs'
s=p.read_text(encoding='utf-8-sig')
old=" if(action==='recover')return recoverFixed(root);"
new=" if(action==='recover')return recoverWithExclusiveLock(root);"
if s.count(old)!=1:raise SystemExit('Unknown CLI recovery entry: no mutation')
s=s.replace(old,new)
identity_import="import {verifyLauncherSession} from './launcher-process-identity.mjs';"
lock_import="import {acquireExclusiveUpdateLock} from './exclusive-update-lock.mjs';"
if s.count(lock_import)!=1:raise SystemExit('Missing shared lock import')
s=s.replace(lock_import,lock_import+"\\n"+identity_import)
anchor='export async function performFixedUpdate(root,'
if s.count(anchor)!=1:raise SystemExit('Unknown update source: no mutation')
addition="""// Recovery must never race a normal update or manual rollback.
export function recoverWithExclusiveLock(root,{recover=recoverFixed,verifySession=verifyLauncherSession}={}){
 const owner=acquireExclusiveUpdateLock(root,{kind:'fixed-update'});
 try{
  owner.assertOwned();
  const paths=fixedPaths(root);
  // A recovery may move live application directories. Refuse unless the previous
  // launcher has a verifiably exited Windows process identity.
  if(fs.existsSync(paths.journal)){
   if(!fs.lstatSync(paths.journal).isFile())throw Error('Unsafe recovery journal');
   const sessionPath=path.join(paths.updater,'launcher-session.json');
   let session;
   try{
    if(!fs.lstatSync(sessionPath).isFile())throw Error('Unsafe session file');
    session=JSON.parse(fs.readFileSync(sessionPath,'utf8').replace(/^\\uFEFF/,''));
   }catch{throw Error('Recovery blocked: launcher identity unavailable');}
   const identity=verifySession(session);
   if(identity!=='process_exited')throw Error('Recovery blocked: launcher exit not verified ('+identity+')');
  }
  owner.assertOwned();
  const result=recover(root);
  if(result && typeof result.then==='function')throw Error('Async recovery is not supported');
  owner.assertOwned();
  return result;
 }finally{owner.release();}
}
"""
s=s.replace(anchor,addition+'\n'+anchor)
p.write_text(s,encoding='utf-8')
print('QA: CLI recovery now uses shared exclusive update.lock')
