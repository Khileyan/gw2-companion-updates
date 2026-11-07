# Windows PowerShell 5.1 GUI regression against the exact RC9 candidate.
param([Parameter(Mandatory=$true)][string]$Launcher)
Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
if(-not(Test-Path -LiteralPath $Launcher -PathType Leaf)){throw 'Missing launcher'}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Launcher,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Invalid PowerShell syntax'}
$functions=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Set-Status'},$true))
if($functions.Count -ne 1){throw 'Expected one Set-Status'}
$source=$functions[0].Extent.Text
if($source -match '\$script:TrayIcon\.Icon\s*=|Make-StatusIcon'){throw 'Dynamic icon replacement still present'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$lblStatus=New-Object Windows.Forms.Label
$btnToggle=New-Object Windows.Forms.Button
$tray=New-Object Windows.Forms.NotifyIcon
try {
 $tray.Icon=[Drawing.SystemIcons]::Application
 $tray.Visible=$false
 $tray.Text='GW2 Companion'
 $initial=$tray.Icon
 $script:TrayIcon=$tray
 $script:Desired=$false
 $script:StatusText=''
 . ([scriptblock]::Create($source))
 $n=0
 foreach($iteration in 1..5){
  foreach($phase in @('idle','local','tunnel','connected','degraded','retry','error')){
   $message="Teststatus $iteration/$phase"
   Set-Status $phase $message
   if($lblStatus.Text -ne $message){throw "Incorrect status label: $phase"}
   if($tray.Text -ne "GW2 Companion: $phase"){throw "Incorrect tooltip: $phase"}
   if(-not [object]::ReferenceEquals($initial,$tray.Icon)){throw "Icon changed: $phase"}
   if(-not $btnToggle.Enabled){throw "Button disabled: $phase"}
   $n++
  }
 }
 $script:TrayIcon=$null
 Set-Status 'idle' 'No tray instance'
 if($lblStatus.Text -ne 'No tray instance'){throw 'Null tray case failed'}
 Write-Host "PASS: $n transitions and null tray fallback"
}finally{
 $script:TrayIcon=$null
 $tray.Dispose()
 $btnToggle.Dispose()
 $lblStatus.Dispose()
}
