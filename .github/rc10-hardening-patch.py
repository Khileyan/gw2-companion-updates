#!/usr/bin/env python3
"""RC10 fail-closed launcher hardening, preserving all active transaction journals."""
from pathlib import Path
import sys
p=(Path(sys.argv[1]) if len(sys.argv)>1 else Path('source'))/'launcher/GW2-Companion.ps1'
s=p.read_text(encoding='utf-8-sig')
def once(a,b):
 global s
 if s.count(a)!=1:raise SystemExit('Unexpected source layout: '+repr(a[:70]))
 s=s.replace(a,b)
once("function Stop-Proc($proc){if(Running $proc){try{$proc.Kill();[void]$proc.WaitForExit(2000)}catch{}}}",
"""function Stop-Proc($proc){
    if($null -eq $proc){return}
    try{if(Running $proc){try{$proc.Kill();[void]$proc.WaitForExit(2000)}catch{}}}
    finally{try{$proc.Dispose()}catch{}}
}""")
once("    $script:ExitRequested=$true;Stop-Connection\n",
"""    $script:ExitRequested=$true;Stop-Connection
    if($null -ne $script:ManualCheckProcess){
        try{if(-not $script:ManualCheckProcess.HasExited){$script:ManualCheckProcess.Kill()}}catch{}
        try{$script:ManualCheckProcess.Dispose()}catch{}
        $script:ManualCheckProcess=$null
    }
""")
once("        if($script:ManagedRoot -and (Get-Date) -ge $script:NextAutoUpdateCheck){",
     "        if($script:ManagedRoot -and -not $script:ManualCheckPending -and (Get-Date) -ge $script:NextAutoUpdateCheck){")
once("                    if($available.verified -eq $true -and [string]$available.version -match '^\\d+\\.\\d+\\.\\d+(?:-[a-z0-9.]+)?$' -and (Is-NewerRelease ([string]$available.version) $script:CompanionVersion)){",
"""                    $fresh=$false
                    try{
                        $checked=[datetime]::Parse([string]$available.checked_at).ToUniversalTime()
                        $fresh=$checked -le [datetime]::UtcNow.AddMinutes(2) -and $checked -ge [datetime]::UtcNow.AddHours(-1)
                    }catch{}
                    if($fresh -and $available.verified -eq $true -and [string]$available.version -match '^\\d+\\.\\d+\\.\\d+(?:-[a-z0-9.]+)?$' -and (Is-NewerRelease ([string]$available.version) $script:CompanionVersion)){""")
once("                    }elseif($progress.state -eq 'failed'){\n                        $lblHelp.Text='Letztes Update fehlgeschlagen; aktuelle Version unveraendert.'",
"""                    }elseif($progress.state -eq 'failed'){
                        $lblHelp.Text='Letztes Update fehlgeschlagen; aktuelle Version unveraendert.'
                    }elseif($progress.state -eq 'recovery_required'){
                        $journal=Join-Path $script:ManagedRoot 'updater\\fixed-transaction.json'
                        if(Test-Path -LiteralPath $journal){
                            $lblHelp.Text='Aktive Update-Wiederherstellung erforderlich. Bitte Diagnoseprotokoll pruefen.'
                            $btnUpdate.Enabled=$false
                        }
                        # No live journal: historical state, not an active failure.
""")
once("        # No account data, no keys.\n        [Windows.Forms.MessageBox]::Show($m,'Diagnose','OK','Information')",
"""        if($script:ManagedRoot){
            $statusFile=Join-Path $script:ManagedRoot 'updater\status.json'
            $journalFile=Join-Path $script:ManagedRoot 'updater\\fixed-transaction.json'
            $active=Test-Path -LiteralPath $journalFile
            $updateState='none'
            if(Test-Path -LiteralPath $statusFile){
                try{
                    $json=Get-Content -LiteralPath $statusFile -Raw -Encoding UTF8|ConvertFrom-Json
                    $raw=[string]$json.state
                    if($raw -match '^[a-z_]{1,40}$'){$updateState=$raw}else{$updateState='invalid'}
                }catch{$updateState='unreadable'}
            }
            if($updateState -eq 'recovery_required' -and -not $active){$updateState='historical_recovery_status'}
            $m+=' | Update-Version: '+$script:CompanionVersion+' | Status: '+$updateState+' | Active transaction: '+$active
        }
        # No account data, no keys.
        [Windows.Forms.MessageBox]::Show($m,'Diagnose','OK','Information')""")
p.write_text(s,encoding='utf-8')
print('RC10 launcher hardening applied')
