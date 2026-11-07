#!/usr/bin/env python3
"""Guarded, non-publishing RC9 -> RC10 stability candidate patch."""
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
base='5.9.0-rc.9'
target='5.9.0-rc.10'
def read(p):return p.read_text(encoding='utf-8-sig')
def write(p,s):p.write_text(s,encoding='utf-8')
for rel in ('app/package.json','app-version.json','app/engine.mjs','tools/build-release.py'):
 p=root/rel;s=read(p)
 if base not in s or target in s:raise SystemExit('Unexpected base version in '+rel)
 write(p,s.replace(base,target))
p=root/'launcher/GW2-Companion.ps1'
s=read(p)
def once(old,new):
 global s
 if s.count(old)!=1:raise SystemExit('RC10 layout guard failed: '+repr(old[:65]))
 s=s.replace(old,new)
once("$btnLog=MakeButton 'Diagnoseprotokoll oeffnen' 23 608 305\n$btnUpdate=MakeButton 'Auf Update pruefen / Aktualisieren' 340 608 303",
"""$btnLog=MakeButton 'Diagnoseprotokoll oeffnen' 23 608 196
$btnCheck=MakeButton 'Nach Updates suchen' 231 608 202
$btnUpdate=MakeButton 'Update installieren' 445 608 198
$btnUpdate.Enabled=$false""")
once("$script:LastAnnouncedUpdate='' ","""$script:LastAnnouncedUpdate=''
$script:ManualCheckProcess=$null
$script:ManualCheckStarted=[datetime]::MinValue
$script:ManualCheckPending=$false """)
handler=r"""# Read-only discovery: a separate button and local consent are required to install.
$btnCheck.add_Click({
    if($script:ManualCheckPending){return}
    if([string]::IsNullOrWhiteSpace($script:ManagedRoot)){
        [Windows.Forms.MessageBox]::Show('Zuerst die verwaltete Installation einrichten.','Versionspruefung')|Out-Null;return
    }
    $checkFile=Join-Path $script:ManagedRoot 'bootstrap\check-release.mjs'
    if(-not(Test-Path -LiteralPath $checkFile)){
        [Windows.Forms.MessageBox]::Show('Die signierte Versionspruefung fehlt.','Versionspruefung')|Out-Null;return
    }
    try{
        $node=Get-Command node.exe -ErrorAction Stop
        $script:ManualCheckStarted=[datetime]::UtcNow
        $script:ManualCheckProcess=Start-Process -FilePath $node.Source -ArgumentList @(('"'+$checkFile+'"')) -WorkingDirectory $script:ManagedRoot -WindowStyle Hidden -PassThru
        if($null -eq $script:ManualCheckProcess){throw 'Versionspruefung konnte nicht gestartet werden.'}
        $script:ManualCheckPending=$true
        $btnCheck.Enabled=$false
        $btnUpdate.Enabled=$false
        $lblHelp.Text='Signiertes Update wird geprueft. Es wird nichts installiert.'
        Log-Event 'UPDATE' 'Manuelle signierte Versionspruefung gestartet.'
    }catch{
        $script:ManualCheckPending=$false
        $btnCheck.Enabled=$true
        $lblHelp.Text='Versionspruefung konnte nicht gestartet werden.'
        Log-Event 'UPDATE' 'Manuelle Versionspruefung fehlgeschlagen.'
    }
})
"""
once('$btnUpdate.add_Click({',handler+'$btnUpdate.add_Click({')
poll=r"""        if($script:ManualCheckPending){
            $finished=$false;$exitCode=-1
            try{
                $script:ManualCheckProcess.Refresh()
                if($script:ManualCheckProcess.HasExited){
                    $finished=$true;$exitCode=$script:ManualCheckProcess.ExitCode
                }elseif(([datetime]::UtcNow-$script:ManualCheckStarted).TotalSeconds -gt 30){
                    try{$script:ManualCheckProcess.Kill()}catch{}
                    $finished=$true
                }
            }catch{$finished=$true}
            if($finished){
                try{$script:ManualCheckProcess.Dispose()}catch{}
                $script:ManualCheckProcess=$null
                $script:ManualCheckPending=$false
                $btnCheck.Enabled=$true
                $btnUpdate.Enabled=$false
                if($exitCode -ne 0){
                    $lblHelp.Text='Versionspruefung fehlgeschlagen. Bestehende Installation unveraendert.'
                    Log-Event 'UPDATE' 'Manuelle Versionspruefung lieferte keinen gueltigen Status.'
                }else{
                    $checkStatusFile=Join-Path $script:ManagedRoot 'updater\check-status.json'
                    $availableFile=Join-Path $script:ManagedRoot 'updater\available.json'
                    try{
                        $check=Get-Content -LiteralPath $checkStatusFile -Raw -Encoding UTF8 | ConvertFrom-Json
                        $verifiedAt=[datetime]::Parse([string]$check.checked_at).ToUniversalTime()
                        if(-not $check.verified -or $verifiedAt -lt $script:ManualCheckStarted.AddSeconds(-2)){
                            throw 'Veraltete oder nicht verifizierte Pruefung.'
                        }
                        if($check.update_available -eq $true){
                            $available=Get-Content -LiteralPath $availableFile -Raw -Encoding UTF8 | ConvertFrom-Json
                            if($available.verified -ne $true -or -not(Is-NewerRelease ([string]$available.version) $script:CompanionVersion)){
                                throw 'Kein verifiziertes neueres Release.'
                            }
                            $btnUpdate.Enabled=$true
                            $script:LastAnnouncedUpdate=''
                            $lblHelp.Text='Signiertes Update '+[string]$available.version+' verfuegbar.'
                        }else{
                            $script:LastAnnouncedUpdate=''
                            $btnUpdate.Text='Update installieren'
                            $lblHelp.Text='Keine neue Version verfuegbar.'
                        }
                    }catch{
                        $lblHelp.Text='Die Versionspruefung konnte nicht sicher ausgewertet werden.'
                        Log-Event 'UPDATE' 'Manuelle Versionspruefung ohne gueltiges Ergebnis.'
                    }
                }
            }
        }
"""
once("        if($script:ManagedRoot -and (Get-Date) -ge $script:NextAutoUpdateCheck){",poll+"        if($script:ManagedRoot -and (Get-Date) -ge $script:NextAutoUpdateCheck){")
once("                            $btnUpdate.Text='Update verfuegbar: '+[string]$available.version",
     "                            $btnUpdate.Text='Update verfuegbar: '+[string]$available.version\n                            if(-not $script:ManualCheckPending){$btnUpdate.Enabled=$true}")
once("                $btnUpdate.Text='Auf Update pruefen / Aktualisieren'",
     "                $btnUpdate.Text='Update installieren'\n                $btnUpdate.Enabled=$false")
if 'updater.mjs check ' not in s or 'Update-Progress.ps1' not in s:
 raise SystemExit('Signed live installer verification no longer present')
write(p,s)
# Adjust inherited version-specific tests, without changing production routes.
for p in (root/'tests').glob('*.test.mjs'):
 s=read(p)
 s=s.replace('5.9.0-rc.9.1','__FUTURE_RC__')
 s=s.replace(base,target).replace('__FUTURE_RC__','5.9.0-rc.10.1')
 write(p,s)
publisher=root/'app/publish-release.mjs'
s=read(publisher)
old='RC9: Windows-Tray-Startfehler behoben; Verbindung und Statuswechsel stabilisiert; signiertes Update.'
new='RC10: Separate Versionspruefung, verbesserte Aktualitaets- und Sicherheitskontrollen.'
if s.count(old)!=1:raise SystemExit('Unknown publisher release notes')
write(publisher,s.replace(old,new))
print('RC10 read-only update check candidate patched')
