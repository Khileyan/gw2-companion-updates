# PowerShell 5.1, Windows-only regression test for the RC9 candidate launcher.
# Does not execute launcher startup, account API calls or tunnel processes.
param([Parameter(Mandatory=$true)][string]$Launcher)
Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $Launcher -PathType Leaf)){throw "Launcher not found: $Launcher"}
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($Launcher,[ref]$tokens,[ref]$errors)
if($errors.Count){throw "PowerShell syntax errors: $($errors[0].Message)"}
$funcs=@($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Set-Status'},$true))
if($funcs.Count -ne 1){throw "Expected exactly one Set-Status function"}
$source=$funcs[0].Extent.Text
if($source -match '\$script:TrayIcon\.Icon\s*=|Make-StatusIcon'){throw 'Unsafe icon replacement found'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$label=New-Object Windows.Forms.Label
$button=New-Object Windows.Forms.Button
$tray=New-Object Windows.Forms.NotifyIcon
try {
 $tray.Icon=[Drawing.SystemIcons]::Application
 $tray.Visible=$false
 $tray.Text='GW2 Companion'
 $icon=$tray.Icon
 $lblStatus=$label
 $btnToggle=$button
 $script:TrayIcon=$tray
 $script:Desired=$false
 $script:StatusText=''
 . ([scriptblock]::Create($source))
 $n=0
 foreach($iteration in 1..5){
  foreach($phase in @('idle','local','tunnel','connected','degraded','retry','error')){
   $message="Teststatus $iteration/$phase"
   Set-Status $phase $message
   if($label.Text -ne $message){throw "Label mismatch: $phase"}
   if($tray.Text -ne "GW2 Companion: $phase"){throw "Tooltip mismatch: $phase"}
   if(-not [object]::ReferenceEquals($icon,$tray.Icon)){throw "Icon replaced: $phase"}
   if(-not $button.Enabled){throw "Button disabled: $phase"}
   $n++
  }
 }
 $script:TrayIcon=$null
 Set-Status 'idle' 'No tray icon'
 if($label.Text -ne 'No tray icon'){throw 'Null tray test failed'}
 Write-Host "PASS: $n transitions; unchanged icon; null-tray fallback"
} finally {
 $script:TrayIcon=$null
 $tray.Dispose()
 $button.Dispose()
 $label.Dispose()
}
