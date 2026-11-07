# Local owner-only RC11 publication. NEVER run against an unsigned/unverified source.
# The private Ed25519 key is read directly by the original release publisher,
# remains on this PC, and must NEVER be uploaded to ChatGPT/GitHub.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$PackageZip,
  [Parameter(Mandatory=$true)][string]$Checksums,
  [Parameter(Mandatory=$true)][string]$SigningKeyFile,
  [switch]$Publish
)
$ErrorActionPreference='Stop'
$version='5.9.0-rc.11'
$repo='Khileyan/gw2-companion-updates'
$name="GW2-Account-Companion-v$version-All-in-One-Preview.zip"
$zip=(Resolve-Path -LiteralPath $PackageZip).Path
$sum=(Resolve-Path -LiteralPath $Checksums).Path
$key=(Resolve-Path -LiteralPath $SigningKeyFile).Path
if((Split-Path -Leaf $zip) -cne $name){throw "Falscher Paketname. Erwartet: $name"}
if(-not (Get-Command node.exe -ErrorAction SilentlyContinue)){throw 'Node.js fehlt.'}
if(-not (Get-Command gh.exe -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) fehlt.'}
if(-not (Test-Path -LiteralPath $key -PathType Leaf)){throw 'Privater Signierschluessel nicht gefunden.'}
$line=Get-Content -LiteralPath $sum | Where-Object {$_ -match [regex]::Escape($name)+'$'} | Select-Object -First 1
if(-not $line -or $line -notmatch '^([0-9a-fA-F]{64})\s+'){throw 'Fehlende SHA256-Zeile fuer RC11.'}
$expected=$Matches[1].ToLowerInvariant()
$got=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if($got -cne $expected){throw 'SHA256-Pruefsumme stimmt nicht. Abbruch.'}
& gh auth status >$null 2>&1
if($LASTEXITCODE -ne 0){throw 'GitHub CLI nicht angemeldet. Zuerst gh auth login.'}
$repoName=& gh repo view $repo --json nameWithOwner --jq '.nameWithOwner'
if($LASTEXITCODE -ne 0 -or $repoName.Trim() -cne $repo){throw 'Zugriff auf das richtige GitHub-Repository fehlt.'}
& gh release view "v$version" --repo $repo --json tagName 2>$null | Out-Null
if($LASTEXITCODE -eq 0){throw 'RC11-Release existiert bereits. Nicht ueberschreiben!'}
Write-Host "Paketpruefung erfolgreich: $name" -ForegroundColor Green
Write-Host "SHA256: $got"
Write-Host 'Private Signierschluesseldatei verbleibt lokal.'
if(-not $Publish){
 Write-Host 'NUR VORPRUEFUNG. Fuer eine tatsaechliche Veroeffentlichung den Parameter -Publish verwenden.'
 return
}
$answer=Read-Host 'Zum Signieren UND Veroeffentlichen wortwoertlich PUBLISH RC11 eingeben'
if($answer -cne 'PUBLISH RC11'){throw 'Veroeffentlichung nicht bestaetigt.'}
$temp=Join-Path ([IO.Path]::GetTempPath()) ("GW2-RC11-signing-"+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
 Expand-Archive -LiteralPath $zip -DestinationPath $temp -Force
 $found=@(Get-ChildItem -LiteralPath $temp -File -Recurse -Filter publish-release.mjs)
 if($found.Count -ne 1){throw 'Release Publisher im Paket nicht eindeutig vorhanden.'}
 if((Split-Path -Leaf (Split-Path $found[0].FullName -Parent)) -cne 'app'){
   throw 'Publisher liegt ausserhalb des erwarteten app-Verzeichnisses.'
 }
 Push-Location $temp
 try { & node.exe $found[0].FullName $zip $key
   if($LASTEXITCODE -ne 0){throw 'Publisher fehlgeschlagen. GitHub Release und Preview-Manifest vor erneutem Versuch manuell pruefen!'}
 }finally{Pop-Location}
 Write-Host 'Publisher meldet Erfolg. RC11 signiert und veroeffentlicht.' -ForegroundColor Green
}finally{
 Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
