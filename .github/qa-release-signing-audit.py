#!/usr/bin/env python3
"""Read-only inventory of existing release signing and publishing contract.
Never print secret values, credentials or runtime account data."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
files=['app/publish-release.mjs','app/update-signature.mjs','app/updater.mjs','app/check-release.mjs','app/install-verified.mjs','tools/build-release.py']
key=re.compile(r'\b(sign|verify|publish|signature|manifest|preview|release|privateKey|publicKey|KEY|process\.env|github\.com)\b',re.I)
for rel in files:
 p=root/rel
 if not p.exists():
  print('PUBLISH-CONTRACT missing',rel);continue
 lines=p.read_text(encoding='utf-8-sig').splitlines()
 print('PUBLISH-CONTRACT file',rel,'lines',len(lines))
 for i,line in enumerate(lines,1):
  if key.search(line) and not re.search(r'[A-Za-z0-9+/]{60,}|secret.*=|token.*=',line,re.I):
   print('PUBLISH-CONTRACT',rel,i,line[:210])
