# Windows-only standalone GUI visibility and startup handshake smoke test.
# This script DOES NOT launch or modify Guild Wars 2 Account Companion or its updater.
# Requires Windows PowerShell 5.1, no administrator rights.
[CmdletBinding()]
param(
    [switch]$Child,
    [string]$Nonce='',
    [string]$ReadyFile=''
)
$ErrorActionPreference='Stop'
if($Child){
    if($Nonce -cnotmatch '^[0-9a-f]{32}$'){throw 'Invalid test nonce'}
    $testRoot=Join-Path ([IO.Path]::GetTempPath()) 'GW2-RC12-UI-SMOKE'
    $resolved=[IO.Path]::GetFullPath($ReadyFile)
    $expected=Join-Path $testRoot ('ready-'+$Nonce+'.json')
    if($resolved -cne $expected){throw 'Unexpected smoke receipt destination'}
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [Windows.Forms.Application]::EnableVisualStyles()
    $form=New-Object Windows.Forms.Form
    $form.Text='GW2 Companion RC12 - reiner Fenster-Test'
    $form.Size=New-Object Drawing.Size(510,240)
    $form.StartPosition='CenterScreen'
    $form.FormBorderStyle='FixedDialog'
    $form.MaximizeBox=$false
    $form.Font=New-Object Drawing.Font('Segoe UI',10)
    $title=New-Object Windows.Forms.Label
    $title.Text='Sichtbarkeit des Fortschrittsfensters'
    $title.Location=New-Object Drawing.Point(20,24)
    $title.Size=New-Object Drawing.Size(455,28)
    [void]$form.Controls.Add($title)
    $desc=New-Object Windows.Forms.Label
    $desc.Text='Nur ein Anzeige- und Handshake-Test. Kein Download, kein Update, kein Neustart.'
    $desc.Location=New-Object Drawing.Point(20,58)
    $desc.Size=New-Object Drawing.Size(455,45)
    [void]$form.Controls.Add($desc)
    $bar=New-Object Windows.Forms.ProgressBar
    $bar.Location=New-Object Drawing.Point(20,117)
    $bar.Size=New-Object Drawing.Size(455,20)
    $bar.Value=100
    [void]$form.Controls.Add($bar)
    $close=New-Object Windows.Forms.Button
    $close.Text='Testfenster schliessen'
    $close.Location=New-Object Drawing.Point(286,151)
    $close.Size=New-Object Drawing.Size(190,31)
    $close.Add_Click({$form.Close()})
    [void]$form.Controls.Add($close)
    $form.Add_Shown({
        # Exactly the same PID+nonce write/rename handshake contract as RC12's host.
        $temp=$ReadyFile+'.tmp'
        try{
            $receipt=[ordered]@{schema=1;nonce=$Nonce;pid=$PID;at=[datetime]::UtcNow.ToString('o')}
            [IO.File]::WriteAllText($temp,($receipt|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
            Move-Item -LiteralPath $temp -Destination $ReadyFile
        }finally{Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue}
        $form.Activate()
    })
    try{[Windows.Forms.Application]::Run($form)}finally{$form.Dispose()}
    return
}
if($Nonce -or $ReadyFile){throw 'Only smoke child may supply nonce or ready file'}
if([Threading.Thread]::CurrentThread.ApartmentState -ne 'STA'){
    Write-Host 'PowerShell wird fuer diesen Fenster-Test im STA-Modus neu gestartet.'
}
$testRoot=Join-Path ([IO.Path]::GetTempPath()) 'GW2-RC12-UI-SMOKE'
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$id=[guid]::NewGuid().ToString('N')
$ready=Join-Path $testRoot ('ready-'+$id+'.json')
$exe=Join-Path $PSHOME 'powershell.exe'
$arguments='-NoProfile -STA -ExecutionPolicy Bypass -File "'+$PSCommandPath+'" -Child -Nonce '+$id+' -ReadyFile "'+$ready+'"'
$proc=$null
try{
    $proc=Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Normal -PassThru
    if($null -eq $proc -or $proc.Id -lt 1){throw 'Testfenster-Prozess konnte nicht gestartet werden.'}
    $confirmed=$false
    for($i=0;$i -lt 80;$i++){
        $proc.Refresh()
        if($proc.HasExited){break}
        if(Test-Path -LiteralPath $ready -PathType Leaf){
            try{
                $receipt=Get-Content -LiteralPath $ready -Raw | ConvertFrom-Json
                if($receipt.schema -eq 1 -and [string]$receipt.nonce -ceq $id -and [int]$receipt.pid -eq $proc.Id){
                    $confirmed=$true;break
                }
            }catch{}
        }
        Start-Sleep -Milliseconds 125
    }
    if(-not $confirmed){
        Write-Host 'FEHLER: Das separate Fenster hat seinen Start nicht bestaetigt.' -ForegroundColor Red
        try{if(-not $proc.HasExited){$proc.Kill()}}catch{}
        exit 1
    }
    Write-Host 'HANDSHAKE OK: Separater PowerShell-Fensterprozess bestaetigt.' -ForegroundColor Green
    Write-Host 'Pruefe, ob das GW2 RC12 Testfenster mit Ladebalken sichtbar ist. Schliessen ueber seinen Button.'
    # The GUI stays open while we return; never block or terminate an acknowledged child.
}finally{
    Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue
    if($null -ne $proc){try{$proc.Dispose()}catch{}}
}
