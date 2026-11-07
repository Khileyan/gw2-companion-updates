#!/usr/bin/env python3
"""Fail-closed patch of SHA-pinned released RC8.3 to RC9."""
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
base='5.9.0-rc.8.3'
target='5.9.0-rc.9'
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')
for rel in ('app/package.json','app-version.json','app/engine.mjs','tools/build-release.py'):
 p=root/rel
 s=read(p)
 if base not in s or target in s: raise SystemExit('Unexpected base version: '+rel)
 write(p,s.replace(base,target))
p=root/'launcher/GW2-Companion.ps1'
s=read(p)
start=s.find('function Make-StatusIcon(')
end=s.find('function Set-Status(',start)
if start<0 or end<=start or s.count('function Make-StatusIcon(')!=1 or s.count('function Set-Status(')!=1:
 raise SystemExit('Unexpected TrayIcon function layout')
if 'GetHicon()' not in s[start:end] or 'DestroyIcon' not in s[start:end]:
 raise SystemExit('Unexpected icon handle lifecycle')
s=s[:start]+'''# Keep the verified brand/fallback icon during connection status changes.
# Replacing NotifyIcon.Icon crashed the Windows PowerShell 5.1 launcher.
'''+s[end:]
old="""        $icon=Make-StatusIcon $color;$old=$script:TrayIcon.Icon
        $script:TrayIcon.Icon=$icon
        if($null -ne $old){$old.Dispose()}
        $script:TrayIcon.Text='GW2 Companion: '+$phase"""
new="""        # Cosmetic tray updates must not abort startup or health checks.
        try {
            $tooltip='GW2 Companion: '+[string]$phase
            if($tooltip.Length -gt 63){$tooltip=$tooltip.Substring(0,63)}
            $script:TrayIcon.Text=$tooltip
        } catch {
            try {Log-Event 'HEALTH' 'Tray-Statustext konnte nicht aktualisiert werden.'} catch {}
        }"""
if s.count(old)!=1: raise SystemExit('Unexpected Set-Status icon replacement layout')
s=s.replace(old,new)
if 'Make-StatusIcon' in s or '$script:TrayIcon.Icon=$icon' in s:
 raise SystemExit('Unsafe TrayIcon dynamic replacement remains')
write(p,s)
# Preserve synthetic version ordering in inherited regression fixtures.
for p in (root/'tests').glob('*.test.mjs'):
 s=read(p)
 s=s.replace('5.9.0-rc.8.4','__FUTURE__').replace(r'5\.9\.0-rc\.8\.4','__FUTURE_ESC__')
 s=s.replace(base,target).replace(r'5\.9\.0-rc\.8\.3',r'5\.9\.0-rc\.9')
 s=s.replace('__FUTURE__','5.9.0-rc.9.1').replace('__FUTURE_ESC__',r'5\.9\.0-rc\.9\.1')
 write(p,s)
# Release notes shown to the user by the signed publisher (not an RC8 carry-over).
publisher=root/'app/publish-release.mjs'
pub=read(publisher)
old_note="RC8: versionsgenaue Titelleiste, Doppelstart-Erkennung und automatische Update-Benachrichtigung; signierte Release-Veroeffentlichung."
new_note="RC9: Windows-Tray-Startfehler behoben; Verbindung und Statuswechsel stabilisiert; signiertes Update."
if pub.count(old_note)!=1:raise SystemExit('Unexpected publisher release-note source')
write(publisher,pub.replace(old_note,new_note))
# The old icon asset test asserted per-transition bitmap drawing, which was
# deliberately removed to prevent the confirmed Windows NotifyIcon crash.
# Preserve verification that the packaged ICO is still loaded on startup.
icon_test=root/'tests/icon-assets.test.mjs'
it=read(icon_test)
lines=it.splitlines(keepends=True)
hits=[i for i,line in enumerate(lines) if 'DrawImage' in line and 'assert.match' in line]
if len(hits)!=1:raise SystemExit('Unknown icon assets regression layout')
import re
m=re.search(r'assert\\.match\\(\\s*([A-Za-z_$][A-Za-z0-9_$]*)\\s*,',lines[hits[0]])
if not m:raise SystemExit('Unknown icon test assertion operand')
var=m.group(1)
lines[hits[0]]=('  assert.match('+var+r', /\\$tray\\.Icon=\\$script:BrandIcon/);'+'\\n')
it=''.join(lines)
if 'DrawImage' in it and 'assert.match' in it:
 raise SystemExit('Obsolete icon assertion still present')
write(icon_test,it)
if target not in read(root/'app-version.json'):raise SystemExit('Patch did not update version')
print('RC9 narrow GUI tray fix applied')
