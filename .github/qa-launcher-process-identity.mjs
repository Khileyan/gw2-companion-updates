// Read-only launcher process identity check (PID + OS creation time + image).
// Never authorizes an update-journal deletion or automatic rollback on its own.
import {spawnSync} from 'node:child_process';
const ISO=/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z$/;
const NAMES=new Set(['powershell.exe','pwsh.exe']);
export function compareLauncherIdentity(session,observed){
 if(session?.schema!==2||!Number.isSafeInteger(session?.pid)||session.pid<=0||
    typeof session.started_at_utc!=='string'||!ISO.test(session.started_at_utc)||
    !Number.isFinite(Date.parse(session.started_at_utc)))return 'unverifiable_legacy_session';
 if(observed?.kind==='not_found')return 'process_exited';
 if(observed?.kind!=='observed'||observed.pid!==session.pid)
   return 'process_identity_unverified';
 if(typeof observed.started_at_utc!=='string'||!ISO.test(observed.started_at_utc)||
    typeof observed.image!=='string'||!NAMES.has(observed.image.toLowerCase()))
   return 'process_identity_unverified';
 const delta=Math.abs(Date.parse(session.started_at_utc)-Date.parse(observed.started_at_utc));
 if(!Number.isFinite(delta)||delta>500)return 'pid_reused_or_identity_mismatch';
 return 'launcher_still_running';
}
export function observeWindowsProcess(pid){
 if(process.platform!=='win32'||!Number.isSafeInteger(pid)||pid<1)return {kind:'unavailable'};
 // PID is validated numeric and interpolated only into a constant, noninteractive command.
 const script=`$ErrorActionPreference='Stop';try{
  $p=Get-Process -Id ${pid} -ErrorAction Stop
  $out=[ordered]@{kind='observed';pid=$p.Id;started_at_utc=$p.StartTime.ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture);image=$p.ProcessName+'.exe'}
  $out | ConvertTo-Json -Compress
 }catch [Microsoft.PowerShell.Commands.ProcessCommandException]{
  @{kind='not_found'} | ConvertTo-Json -Compress
 }catch{
  @{kind='unavailable'} | ConvertTo-Json -Compress
 }`;
 const r=spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-Command',script],{
  windowsHide:true,encoding:'utf8',timeout:3500,maxBuffer:4096
 });
 if(r.error||r.status!==0)return {kind:'unavailable'};
 try{return JSON.parse(r.stdout.trim());}catch{return {kind:'unavailable'};}
}
export function verifyLauncherSession(session,{observe=observeWindowsProcess}={}){
 if(session?.schema!==2)return 'unverifiable_legacy_session';
 return compareLauncherIdentity(session,observe(session.pid));
}
