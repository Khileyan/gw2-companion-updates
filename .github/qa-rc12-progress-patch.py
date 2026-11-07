#!/usr/bin/env python3
"""RC12 candidate: visible, acknowledged update progress host, plus safe failure stages.
Never modify signed RC11 artifacts. Apply to reviewed RC11 *source* only."""
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('rc12-source')
def patch(rel,replacements):
 p=root/rel
 s=p.read_text(encoding='utf-8-sig')
 for old,new in replacements:
  if s.count(old)!=1:
   raise SystemExit('RC12 guarded replacement mismatch '+rel+' '+repr(old[:90])+' count='+str(s.count(old)))
  s=s.replace(old,new,1)
 p.write_text(s,encoding='utf-8')

# The progress form is a separate window; it must not inherit a hidden window style.
# A unique readiness receipt means we never shut down a healthy RC10 if the host
# does not actually initialize (script error, blocked UI, launch failure).
patch('launcher/GW2-Companion.ps1',[
 ("""        $pidValue=[string]$PID
        $args='-NoProfile -STA -ExecutionPolicy Bypass -File "'+$progressHost+'" -LauncherPid '+$pidValue
        $progressProcess=Start-Process -FilePath 'powershell.exe' -ArgumentList $args -WorkingDirectory $script:ManagedRoot -WindowStyle Hidden -PassThru
        if($null -eq $progressProcess -or $progressProcess.Id -lt 1){throw 'Update-Fortschrittsfenster konnte nicht gestartet werden.'}
        Log-Event 'UPDATE' ('Freigegebenes Update auf '+$u.version+' gestartet.')""",
  """        $pidValue=[string]$PID
        $nonce=[guid]::NewGuid().ToString('N')
        $ready=Join-Path $script:ManagedRoot ('updater\\progress-ready-'+$nonce+'.json')
        $args='-NoProfile -STA -ExecutionPolicy Bypass -File "'+$progressHost+'" -LauncherPid '+$pidValue+' -ReadyNonce '+$nonce
        $progressProcess=$null
        try{
            # No hidden window: this is the standalone user-facing progress UI.
            $progressProcess=Start-Process -FilePath 'powershell.exe' -ArgumentList $args -WorkingDirectory $script:ManagedRoot -WindowStyle Normal -PassThru
            if($null -eq $progressProcess -or $progressProcess.Id -lt 1){throw 'Update-Fortschrittsfenster konnte nicht gestartet werden.'}
            $acknowledged=$false
            for($n=0;$n -lt 80;$n++){
                $progressProcess.Refresh()
                if($progressProcess.HasExited){break}
                if(Test-Path -LiteralPath $ready -PathType Leaf){
                    try{
                        $receipt=Get-Content -LiteralPath $ready -Raw -Encoding UTF8|ConvertFrom-Json
                        if($receipt.schema -eq 1 -and [string]$receipt.nonce -ceq $nonce -and [int]$receipt.pid -eq $progressProcess.Id){
                            $acknowledged=$true;break
                        }
                    }catch{}
                }
                Start-Sleep -Milliseconds 125
            }
            if(-not $acknowledged){
                # Only stop the *specific child we just spawned* if it never acknowledged startup.
                try{if(-not $progressProcess.HasExited){$progressProcess.Kill()}}catch{}
                throw 'Update-Fortschrittsfenster hat seinen Start nicht bestaetigt. RC10 bleibt aktiv.'
            }
        }finally{
            Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue
            if($null -ne $progressProcess){try{$progressProcess.Dispose()}catch{}}
        }
        Log-Event 'UPDATE' ('Freigegebenes Update auf '+$u.version+' gestartet.')""")
])
patch('bootstrap/Update-Progress.ps1',[
 ("param([Parameter(Mandatory=$true)][int]$LauncherPid)",
  "param([Parameter(Mandatory=$true)][int]$LauncherPid,[Parameter(Mandatory=$true)][string]$ReadyNonce)"),
 ("if($LauncherPid -lt 1){throw 'Ungueltige Launcher-Prozess-ID.'}",
  """if($LauncherPid -lt 1){throw 'Ungueltige Launcher-Prozess-ID.'}
if($ReadyNonce -cnotmatch '^[0-9a-f]{32}$'){throw 'Ungueltiger Fortschritts-Handshake.'}"""),
 ("""$form.Add_Shown({
    try{
        $startInfo=New-Object Diagnostics.ProcessStartInfo""",
  """$form.Add_Shown({
    try{
        # Publish a fresh acknowledgment ONLY after the form has been shown.
        # The launcher waits for this before allowing any shutdown request.
        $readyPath=Join-Path $updater ('progress-ready-'+$ReadyNonce+'.json')
        $tmpReady=$readyPath+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
        try{
            $receipt=[ordered]@{schema=1;nonce=$ReadyNonce;pid=$PID;at=[datetime]::UtcNow.ToString('o')}
            [IO.File]::WriteAllText($tmpReady,($receipt|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
            Move-Item -LiteralPath $tmpReady -Destination $readyPath
        }finally{Remove-Item -LiteralPath $tmpReady -Force -ErrorAction SilentlyContinue}
        $startInfo=New-Object Diagnostics.ProcessStartInfo""")
])
# The old status collapsed every pre-activation problem into update_aborted.
# Preserve compatibility while recording a non-sensitive enumerated phase.
patch('bootstrap/fixed-update.mjs',[
 ("const p=fixedPaths(root),unlock=lock(root);let stage=null,activated=false,connected=false,from,to,downloaded=null,newProcess=null;",
  "const p=fixedPaths(root),unlock=lock(root);let stage=null,activated=false,connected=false,from,to,downloaded=null,newProcess=null;let failureStage='preflight';"),
 ("   const source=loadJSON(path.join(p.config,'update-source.json'));",
  "   failureStage='trusted_source';\n   const source=loadJSON(path.join(p.config,'update-source.json'));"),
 ("   event(root,'checking');",
  "   failureStage='manifest_check';\n   event(root,'checking');"),
 ("   stage=stagingArea(root);event(root,'downloading',{version:to,downloaded:0,total:m.bytes});",
  "   failureStage='download';\n   stage=stagingArea(root);event(root,'downloading',{version:to,downloaded:0,total:m.bytes});"),
 ("   downloaded=zip;event(root,'verifying',{version:to});",
  "   failureStage='verification';\n   downloaded=zip;event(root,'verifying',{version:to});"),
 ("   event(root,'staged',{version:to});",
  "   failureStage='staged';\n   event(root,'staged',{version:to});"),
 ("   event(root,'waiting_for_launcher',{version:to});",
  "   failureStage='launcher_shutdown';\n   event(root,'waiting_for_launcher',{version:to});"),
 ("      event(root,'failed',{phase:'not-activated',version:from??null,error_code:code});",
  "      event(root,'failed',{phase:'not-activated',version:from??null,error_code:code,failure_stage:failureStage});")
])
for rel in ('app/package.json','app-version.json','app/engine.mjs','tools/build-release.py'):
 p=root/rel
 s=p.read_text(encoding='utf-8-sig')
 if '5.9.0-rc.11' not in s or '5.9.0-rc.12' in s:raise SystemExit('RC12 version guard failed '+rel)
 p.write_text(s.replace('5.9.0-rc.11','5.9.0-rc.12'),encoding='utf-8')
p=root/'app/publish-release.mjs'
s=p.read_text(encoding='utf-8-sig')
old='RC11: Update-Sperren und sichere Wiederherstellung, Windows-Prozessidentitaet.'
if s.count(old)!=1:raise SystemExit('RC12 publisher notes guard failed')
p.write_text(s.replace(old,'RC12: Sichtbarer Update-Fortschritt, Start-Handshake und feinerer Abbruchstatus.'),encoding='utf-8')
print('RC12 visible and acknowledged progress host candidate patch applied')
