# Read-only acceptance gate for a future locally signed RC12 update.
# Does NOT launch an updater, kill processes, modify the Companion or access private keys.
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$PackageZip,
 [Parameter(Mandatory=$true)][string]$Checksums,
 [string]$InstallRoot=(Join-Path $env:LOCALAPPDATA 'GW2-Account-Companion')
)
$ErrorActionPreference='Stop'
$failed=0
function Check([string]$label,[bool]$ok) {
 if($ok){Write-Host ('PASS  '+$label) -ForegroundColor Green}
 else{$script:failed++;Write-Host ('STOP  '+$label) -ForegroundColor Yellow}
}
$version='5.9.0-rc.12'
$name="GW2-Account-Companion-v$version-All-in-One-Preview.zip"
Write-Host 'RC12 READ-ONLY MIGRATION PREFLIGHT - NO INSTALLATION'
$zip=(Resolve-Path -LiteralPath $PackageZip -ErrorAction Stop).Path
$sum=(Resolve-Path -LiteralPath $Checksums -ErrorAction Stop).Path
Check 'Canonical RC12 candidate filename' ((Split-Path -Leaf $zip) -ceq $name)
$lines=@(Get-Content -LiteralPath $sum)
$matches=@($lines|Where-Object {$_ -match '^[0-9a-fA-F]{64}\s+\*?GW2-Account-Companion-v5\.9\.0-rc\.12-All-in-One-Preview\.zip$'})
Check 'Exactly one SHA256 checksum record' ($matches.Count -eq 1)
if($matches.Count -eq 1){
 $expected=$matches[0].Substring(0,64).ToLowerInvariant()
 $actual=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
 Check 'Artifact SHA256 matches pinned handoff checksum' ($actual -ceq $expected)
}else{$failed++}
$root=[IO.Path]::GetFullPath($InstallRoot)
$updater=Join-Path $root 'updater'
Check 'Managed installation found' (Test-Path -LiteralPath (Join-Path $root 'app\package.json') -PathType Leaf)
Check 'No active fixed transaction journal' (-not(Test-Path -LiteralPath (Join-Path $updater 'fixed-transaction.json')))
Check 'No outstanding shutdown request' (-not(Test-Path -LiteralPath (Join-Path $updater 'shutdown.request')))
# Update lock names vary between revisions: neither silently delete nor override them.
$locks=@(Get-ChildItem -LiteralPath $updater -ErrorAction SilentlyContinue |
 Where-Object {$_.Name -match '^(update\.lock|exclusive-update-lock(?:\.json)?|fixed-update\.lock)$'})
Check 'No known update lock artifact' ($locks.Count -eq 0)
foreach($rel in @('config\update-source.json','config\publisher-public.pem','bootstrap\fixed-update.mjs','bootstrap\Start-Managed.ps1',
 'app\node_modules','shared\bin\tunnel-client.exe')){
 Check ('Installed prerequisite '+$rel) (Test-Path -LiteralPath (Join-Path $root $rel))
}
$installed=$null
try{
 $a=(Get-Content -LiteralPath (Join-Path $root 'app-version.json') -Raw|ConvertFrom-Json).version
 $b=(Get-Content -LiteralPath (Join-Path $root 'app\package.json') -Raw|ConvertFrom-Json).version
 $installed=[string]$b
 Check 'Active and application version agree, currently RC10' ($a -ceq '5.9.0-rc.10' -and $b -ceq '5.9.0-rc.10')
}catch{Check 'Active version markers are readable' $false}
try{
 $source=Get-Content -LiteralPath (Join-Path $root 'config\update-source.json') -Raw|ConvertFrom-Json
 Check 'Signed preview update source matches pinned GitHub feed' (
    $source.schema -eq 1 -and $source.channel -ceq 'preview' -and
    $source.manifest_url -ceq 'https://raw.githubusercontent.com/Khileyan/gw2-companion-updates/main/preview.json'
 )
}catch{Check 'Trusted signed preview feed readable' $false}
# Read ZIP structure in memory; no extraction, execution, installation or modification.
try{
 Add-Type -AssemblyName System.IO.Compression
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 $archive=[IO.Compression.ZipFile]::OpenRead($zip)
 try{
  $entries=@($archive.Entries)
  $packages=@($entries|Where-Object {$_.FullName -match '(^|/)app/package\.json$' -and $_.Length -gt 0})
  Check 'One packaged application version descriptor' ($packages.Count -eq 1)
  if($packages.Count -eq 1){
    $stream=$packages[0].Open()
    try{
      $reader=New-Object IO.StreamReader($stream)
      try{$candidate=$reader.ReadToEnd()|ConvertFrom-Json}
      finally{$reader.Dispose()}
    }finally{$stream.Dispose()}
    Check 'Candidate is RC12 and fixed-v1' ($candidate.version -ceq $version -and $candidate.install_layout -ceq 'fixed-v1')
    try{
      $current=Get-Content -LiteralPath (Join-Path $root 'app\package.json') -Raw|ConvertFrom-Json
      $deps=@($current.dependencies.PSObject.Properties|ForEach-Object {$_.Name+':'+$_.Value}|Sort-Object) -join '|'
      $nextdeps=@($candidate.dependencies.PSObject.Properties|ForEach-Object {$_.Name+':'+$_.Value}|Sort-Object) -join '|'
      $eng=@($current.engines.PSObject.Properties|ForEach-Object {$_.Name+':'+$_.Value}|Sort-Object) -join '|'
      $nexteng=@($candidate.engines.PSObject.Properties|ForEach-Object {$_.Name+':'+$_.Value}|Sort-Object) -join '|'
      Check 'No unreviewed runtime dependencies or engine changes' ($deps -ceq $nextdeps -and $eng -ceq $nexteng)
      Check 'Database schema unchanged' ($current.data_schema_version -eq $candidate.data_schema_version)
    }catch{Check 'Runtime compatibility metadata readable' $false}
  }
  foreach($rel in @('bootstrap/Update-Progress.ps1','bootstrap/fixed-update.mjs','launcher/GW2-Companion.ps1')){
    Check ('Required RC12 component '+$rel) (@($entries|Where-Object {$_.FullName.EndsWith('/'+$rel,[StringComparison]::OrdinalIgnoreCase)}).Count -eq 1)
  }
 }finally{$archive.Dispose()}
}catch{Check 'Candidate ZIP safely readable' $false}
# No process command-line values or user data are printed.
try{
 $nodes=@(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction Stop|
 Where-Object {$_.CommandLine -match 'fixed-update\.mjs\s+(update|rollback|recover)'})
 Check 'No active Node update/recovery helper' ($nodes.Count -eq 0)
}catch{Check 'Updater process state can be verified' $false}
if($failed -gt 0){
 Write-Host ("STOP: "+$failed+" condition(s) failed. Do not publish or install RC12.") -ForegroundColor Red
 exit 2
}
Write-Host 'PREFLIGHT PASS: No local installation was changed. This does NOT authorize installation or publication.' -ForegroundColor Green
$global:LASTEXITCODE=0
