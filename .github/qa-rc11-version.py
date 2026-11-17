#!/usr/bin/env python3
"""Non-publishing RC11 version overlay. Fail closed on unexpected RC10 source."""
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('rc11-source')
base='5.9.0-rc.10';target='5.9.0-rc.11'
files=('app/package.json','app-version.json','app/engine.mjs','tools/build-release.py')
for rel in files:
 p=root/rel
 s=p.read_text(encoding='utf-8-sig')
 if base not in s or target in s:raise SystemExit('RC11 version marker guard failed: '+rel)
 p.write_text(s.replace(base,target),encoding='utf-8')
pub=root/'app/publish-release.mjs'
s=pub.read_text(encoding='utf-8-sig')
old='RC10: Separate Versionspruefung, verbesserte Aktualitaets- und Sicherheitskontrollen.'
new='RC11: Update-Sperren und sichere Wiederherstellung, Windows-Prozessidentitaet.'
if s.count(old)!=1:raise SystemExit('RC11 release notes layout unknown; not modifying')
pub.write_text(s.replace(old,new),encoding='utf-8')
print('Non-publishing RC11 candidate version overlay applied')
