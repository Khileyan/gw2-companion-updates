// Fail-closed inspection and explicitly approved archival of a leftover fixed update journal.
// Archival is NOT confirmation of update health and never deletes the rollback backup.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const V=/^\d+\.\d+\.\d+(?:-[a-z0-9.]+)?$/i;
const PARTS=['app','launcher','assets','projects','bootstrap'];
const read=file=>JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
const exists=file=>fs.existsSync(file);
function pidAlive(pid){
  if(!Number.isSafeInteger(pid)||pid<1)return false;
  try{process.kill(pid,0);return true;}catch(e){return e.code==='EPERM';}
}
function reason(code){return {safe_to_archive:false,reason:code};}
export function inspectStaleJournal(root,{now=Date.now(),minAgeMs=120000,isAlive=pidAlive}={}){
  const base=path.resolve(root),u=path.join(base,'updater'),j=path.join(u,'fixed-transaction.json');
  if(!exists(j))return reason('no_journal');
  let t;
  try{t=read(j);}catch{return reason('unreadable_journal');}
  if(t.schema!==1||t.layout!=='fixed-v1'||!V.test(t.from??'')||!V.test(t.to??'')||t.phase!=='starting'||
     typeof t.backup!=='string'||!path.resolve(t.backup).startsWith(u+path.sep)||
     !path.basename(t.backup).startsWith('fixed-rollback-'))return reason('unknown_transaction');
  if(!Number.isSafeInteger(t.at)||now-t.at<minAgeMs)return reason('transaction_too_recent');
  for(const name of ['update.lock','transaction.json','shutdown.request']){
    if(exists(path.join(u,name)))return reason('update_in_progress_or_locked');
  }
  const session=path.join(u,'launcher-session.json');
  if(!exists(session))return reason('launcher_state_unverified');
  if(exists(session)){
    let pid;
    try{pid=read(session).pid;}catch{return reason('unreadable_launcher_session');}
    if(!Number.isSafeInteger(pid))return reason('unknown_launcher_session');
    if(isAlive(pid))return reason('launcher_still_running');
  }
  let installed,marker,prior;
  try{
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
  return {safe_to_archive:true,reason:'completed_version_with_stale_journal',installed_version:installed,from:t.from,to:t.to};
}
export function archiveStaleJournal(root,{approved=false,now=Date.now(),minAgeMs=120000,isAlive=pidAlive}={}){
  if(approved!==true)throw Error('Explicit local approval required');
  const status=inspectStaleJournal(root,{now,minAgeMs,isAlive});
  if(!status.safe_to_archive)throw Error('Archive refused: '+status.reason);
  const updater=path.join(path.resolve(root),'updater');
  const target='fixed-transaction.archived-'+new Date(now).toISOString().replace(/[^0-9]/g,'')+'-'+crypto.randomBytes(4).toString('hex')+'.json';
  // Rename, never unlink; the backup directory is deliberately retained.
  fs.renameSync(path.join(updater,'fixed-transaction.json'),path.join(updater,target));
  return {archived:true,archive_name:target,backup_preserved:true,installed_version:status.installed_version};
}
