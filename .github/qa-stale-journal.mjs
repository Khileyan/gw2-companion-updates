// Fail-closed inspection and explicitly approved archival of a leftover fixed update journal.
// Archival is NOT confirmation of update health and never deletes the rollback backup.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {withExclusiveUpdateLock} from './exclusive-update-lock.mjs';
import {verifyLauncherSession} from './launcher-process-identity.mjs';

const V=/^\d+\.\d+\.\d+(?:-[a-z0-9.]+)?$/i;
const PARTS=['app','launcher','assets','projects','bootstrap'];
const read=file=>JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
const exists=file=>fs.existsSync(file);
function safeRegular(file){try{return fs.lstatSync(file).isFile();}catch{return false;}}
function safeDirectory(file){try{return fs.lstatSync(file).isDirectory();}catch{return false;}}
function noSymlinkAncestors(file,stop){
 const base=path.resolve(stop),target=path.resolve(file);
 if(target!==base&&!target.startsWith(base+path.sep))return false;
 let p=base;
 if(!safeDirectory(p))return false;
 for(const part of path.relative(base,target).split(path.sep).filter(Boolean)){
  p=path.join(p,part);
  try{if(fs.lstatSync(p).isSymbolicLink())return false;}catch{return false;}
 }
 return true;
}
function reason(code){return {safe_to_archive:false,reason:code};}
export function inspectStaleJournal(root,{now=Date.now(),minAgeMs=120000,verifySession=verifyLauncherSession}={}){
  const base=path.resolve(root),u=path.join(base,'updater'),j=path.join(u,'fixed-transaction.json');
  if(!exists(j))return reason('no_journal');
  if(!safeDirectory(base)||!safeDirectory(u)||!safeRegular(j)||!noSymlinkAncestors(j,base))
   return reason('unsafe_journal_path');
  let t;
  try{t=read(j);}catch{return reason('unreadable_journal');}
  if(t.schema!==1||t.layout!=='fixed-v1'||!V.test(t.from??'')||!V.test(t.to??'')||t.phase!=='starting'||
     typeof t.backup!=='string'||!path.resolve(t.backup).startsWith(u+path.sep)||
     !path.basename(t.backup).startsWith('fixed-rollback-'))return reason('unknown_transaction');
  if(!Number.isSafeInteger(t.at)||!Number.isSafeInteger(now)||!Number.isSafeInteger(minAgeMs)||
     minAgeMs<120000||now<t.at||now-t.at<minAgeMs)return reason('transaction_too_recent');
  for(const name of ['update.lock','transaction.json','shutdown.request']){
    if(exists(path.join(u,name)))return reason('update_in_progress_or_locked');
  }
  const session=path.join(u,'launcher-session.json');
  if(!exists(session)||!safeRegular(session))return reason('launcher_state_unverified');
  let launcherSession;
  try{launcherSession=read(session);}catch{return reason('unreadable_launcher_session');}
  const identity=verifySession(launcherSession);
  if(identity==='launcher_still_running')return reason('launcher_still_running');
  if(identity!=='process_exited')return reason('launcher_identity_unverified');
  let installed,marker,prior;
  try{
    if(!safeRegular(path.join(base,'app','package.json'))||
       !noSymlinkAncestors(path.join(base,'app','package.json'),base)||
       !safeRegular(path.join(base,'app-version.json'))||
       !noSymlinkAncestors(path.join(base,'app-version.json'),base)||
       !safeDirectory(t.backup)||!noSymlinkAncestors(t.backup,base)||
       !safeRegular(path.join(t.backup,'app','package.json'))||
       !noSymlinkAncestors(path.join(t.backup,'app','package.json'),base))
       return reason('unsafe_version_or_backup_path');
    installed=read(path.join(base,'app','package.json')).version;
    marker=read(path.join(base,'app-version.json')).version;
    prior=read(path.join(t.backup,'app','package.json')).version;
  }catch{return reason('version_evidence_missing');}
  if(installed!==t.to||marker!==t.to||prior!==t.from)return reason('version_mismatch');
  if(!exists(t.backup)||fs.lstatSync(t.backup).isSymbolicLink())return reason('invalid_backup');
  for(const name of PARTS){
    const part=path.join(t.backup,name);
    if(!exists(part)||fs.lstatSync(part).isSymbolicLink()||!fs.lstatSync(part).isDirectory())return reason('incomplete_backup');
  }
  // A stale PID file cannot prove the updater has exited. Without a secure
  // process identity and exclusive coordination, do NOT offer journal archival.
  return {safe_to_archive:false,reason:'requires_offline_verified_reconciliation',
    installed_version:installed,from:t.from,to:t.to};
}
export function archiveStaleJournal(root,{approved=false,now=Date.now(),minAgeMs=120000,isAlive=pidAlive}={}){
  if(approved!==true)throw Error('Explicit local approval required');
  return withExclusiveUpdateLock(root,({assertOwned})=>{
    // Lock is shared with the production updater. Never archive without owning it.
    // Inspection remains fail-closed until validated process identity exists.
    const status=inspectStaleJournal(root,{now,minAgeMs,verifySession});
    if(!status.safe_to_archive)throw Error('Archive refused: '+status.reason);
    assertOwned();
    const updater=path.join(path.resolve(root),'updater');
    const target='fixed-transaction.archived-'+new Date(now).toISOString().replace(/[^0-9]/g,'')+'-'+crypto.randomBytes(4).toString('hex')+'.json';
    fs.renameSync(path.join(updater,'fixed-transaction.json'),path.join(updater,target));
    return {archived:true,archive_name:target,backup_preserved:true,installed_version:status.installed_version};
  });
}
