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
$existing=& gh release list --repo $repo --json tagName --limit 100
if($LASTEXITCODE -ne 0){throw 'GitHub Release-Liste nicht lesbar. Abbruch.'}
$releaseList=@($existing | ConvertFrom-Json)
if(@($releaseList | Where-Object {$_.tagName -ceq "v$version"}).Count -gt 0){
 throw 'RC11-Release existiert bereits. Nicht ueberschreiben!'
}
Write-Host "Paketpruefung erfolgreich: $name" -ForegroundColor Green
Write-Host "SHA256: $got"
Write-Host 'Private Signierschluesseldatei verbleibt lokal.'
$temp=Join-Path ([IO.Path]::GetTempPath()) ("GW2-RC11-signing-"+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
 Expand-Archive -LiteralPath $zip -DestinationPath $temp -Force
 $found=@(Get-ChildItem -LiteralPath $temp -File -Recurse -Filter publish-release.mjs)
 if($found.Count -ne 1){throw 'Release Publisher im Paket nicht eindeutig vorhanden.'}
 if((Split-Path -Leaf (Split-Path $found[0].FullName -Parent)) -cne 'app'){
   throw 'Publisher liegt ausserhalb des erwarteten app-Verzeichnisses.'
 }
 # The canonical signed-release publisher intentionally requires the concise ZIP
 # basename GW2-Account-Companion-v<VERSION>.zip. Preserve the downloaded artifact
 # and its verified SHA-256; pass a byte-identical temporary copy to the publisher.
 $publisherZip=Join-Path $temp ("GW2-Account-Companion-v$version.zip")
 if(Test-Path -LiteralPath $publisherZip){throw 'Ziel fuer die Publisher-Kopie existiert bereits.'}
 Copy-Item -LiteralPath $zip -Destination $publisherZip -ErrorAction Stop
 $copyHash=(Get-FileHash -LiteralPath $publisherZip -Algorithm SHA256).Hash.ToLowerInvariant()
 if($copyHash -cne $got){throw 'Temporäre ZIP-Kopie weicht vom verifizierten Paket ab.'}
 # The reproducible release builder deliberately excludes root app-version.json.
 # The owner-only publisher uses it as a self-version marker; restore it in the
 # TEMPORARY workspace from the verified, packaged app/package.json, not in ZIP.
 $publisherRoot=Split-Path -Parent (Split-Path -Parent $found[0].FullName)
 $packageJson=Join-Path $publisherRoot 'app\package.json'
 if(-not (Test-Path -LiteralPath $packageJson -PathType Leaf)){
   throw 'Paket enthaelt keine app/package.json im erwarteten Versionsordner.'
 }
 $packageData=Get-Content -LiteralPath $packageJson -Raw | ConvertFrom-Json
 if($packageData.version -cne $version){
   throw 'Paketversion stimmt nicht mit dem RC11-Publisher ueberein.'
 }
 $markerPath=Join-Path $publisherRoot 'app-version.json'
 if(Test-Path -LiteralPath $markerPath){
   $existingMarker=Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
   if($existingMarker.version -cne $version){throw 'Abweichende app-version.json: Abbruch.'}
 }else{
   $markerJson=(@{version=$version} | ConvertTo-Json -Compress)
   [IO.File]::WriteAllText($markerPath,$markerJson,[Text.UTF8Encoding]::new($false))
 }
 # The original release publisher validates against its own *pinned* trust
 # configuration; never synthesize trust settings from the private key.
 $configRoot=Join-Path $env:LOCALAPPDATA 'GW2-Account-Companion\config'
 $embeddedConfig=Join-Path $publisherRoot 'config'
 if(-not (Test-Path -LiteralPath (Join-Path $embeddedConfig 'publisher-public.pem') -PathType Leaf)){
   foreach($required in @('publisher-public.pem','update-source.json')){
     if(-not (Test-Path -LiteralPath (Join-Path $configRoot $required) -PathType Leaf)){
       throw "Publisher-Vertrauenskonfiguration fehlt: $configRoot\$required. Keine Veroeffentlichung."
     }
   }
 }
 Write-Host 'Publisher-Arbeitsverzeichnis und Versionsdatei geprueft.' -ForegroundColor Green
 if(-not $Publish){
   Write-Host 'NUR VORPRUEFUNG. Keine Signierung oder Veroeffentlichung.'
   return
 }
 $answer=Read-Host 'Zum Signieren UND Veroeffentlichen wortwoertlich PUBLISH RC11 eingeben'
 if($answer -cne 'PUBLISH RC11'){throw 'Veroeffentlichung nicht bestaetigt.'}
 Push-Location $temp
 try { & node.exe $found[0].FullName $publisherZip $key
   if($LASTEXITCODE -ne 0){throw 'Publisher fehlgeschlagen. GitHub Release und Preview-Manifest vor erneutem Versuch manuell pruefen!'}
 }finally{Pop-Location}
 Write-Host 'Publisher meldet Erfolg. RC11 signiert und veroeffentlicht.' -ForegroundColor Green
}finally{
 Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
