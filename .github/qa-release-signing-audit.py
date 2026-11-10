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

print('PUBLISH-CONTRACT safe owner-path context')
p=root/'app/publish-release.mjs'
for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
 if 24<=i<=38 or 47<=i<=54:
  if re.search(r'[A-Za-z0-9+/]{80,}|secret.*=|token.*=',line,re.I):continue
  print('PUBLISH-PATH',i,line[:240])

for rel, intervals in [('app/publish-release.mjs',[(1,24),(38,47)]),('tools/build-release.py',[(1,57)])]:
 p=root/rel
 print('PUBLISH-SOURCE-BOUNDS',rel)
 for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
  if not any(a<=i<=b for a,b in intervals):continue
  if re.search(r'[A-Za-z0-9+/]{80,}|secret.*=|token.*=',line,re.I):continue
  print('PUBLISH-SOURCE',rel,i,line[:240])

for rel in ['bootstrap/check-release.mjs','app/check-release.mjs','app/updater.mjs']:
 p=root/rel
 if not p.exists():continue
 print('CHECK-DETAIL',rel,'lines',len(p.read_text(encoding='utf-8-sig').splitlines()))
 for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
  if rel.endswith('updater.mjs') and not (1<=i<=43):continue
  if re.search(r'[A-Za-z0-9+/]{80,}|secret.*=|token.*=',line,re.I):continue
  print('CHECK-CODE',rel,i,line[:240])

p=root/'bootstrap/fixed-core.mjs'
print('SLOT-DETAIL bootstrap/fixed-core.mjs')
for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
 if i>150:break
 if re.search(r'[A-Za-z0-9+/]{80,}|secret.*=|token.*=',line,re.I):continue
 print('SLOT-CODE',i,line[:240])

for rel in ['bootstrap/Update-Progress.ps1','bootstrap/Start-Managed.ps1','launcher/GW2-Companion.ps1','bootstrap/fixed-core.mjs']:
 p=root/rel
 if not p.exists():continue
 print('FAILURE-DIAG',rel)
 lines=p.read_text(encoding='utf-8-sig').splitlines()
 ranges=[]
 if rel.endswith('GW2-Companion.ps1'):
  ranges=[(i-6,i+18) for i,line in enumerate(lines,1) if '$btnUpdate.add_Click' in line or 'Update-Progress.ps1' in line or 'LastUpdate' in line]
 elif rel.endswith('fixed-core.mjs'):ranges=[(1,min(160,len(lines)))]
 else:ranges=[(1,min(150,len(lines)))]
 indices=set(i for a,b in ranges for i in range(max(1,a),min(len(lines),b)+1))
 for i in sorted(indices):
  line=lines[i-1]
  if re.search(r'[A-Za-z0-9+/]{80,}|secret.*=|token.*=',line,re.I):continue
  print('FAILURE-CODE',rel,i,line[:260])

for rel in ['bootstrap/fixed-update.mjs','bootstrap/Update-Progress.ps1','launcher/GW2-Companion.ps1']:
 p=root/rel
 lines=p.read_text(encoding='utf-8-sig').splitlines()
 print('ABORT-DIAG',rel,len(lines))
 needles=['update_aborted','not-activated','LauncherPid','progressProcess','ExitRequested','Quit-Application','Kill','update.lock','writeStatus','status.json']
 ranges=[]
 for i,line in enumerate(lines,1):
  if any(t in line for t in needles):
   ranges.append((max(1,i-5),min(len(lines),i+6)))
 selected=set(i for a,b in ranges for i in range(a,b+1))
 for i in sorted(selected):
  line=lines[i-1]
  if re.search(r'[A-Za-z0-9+/]{80,}|secret.*=|token.*=',line,re.I):continue
  print('ABORT-CODE',rel,i,line[:260])

for rel, interval in [('bootstrap/fixed-update.mjs',(1,140)),('bootstrap/Update-Progress.ps1',(149,220)),('launcher/GW2-Companion.ps1',(574,610))]:
 p=root/rel
 print('FLOW-DETAIL',rel)
 for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
  if not(interval[0]<=i<=interval[1]):continue
  if re.search(r'[A-Za-z0-9+/]{80,}|secret.*=|token.*=',line,re.I):continue
  print('FLOW-CODE',rel,i,line[:250])

for rel, ranges in [('bootstrap/Update-Progress.ps1',[(1,20),(169,190)]),('bootstrap/fixed-update.mjs',[(180,198)]),('launcher/GW2-Companion.ps1',[(526,565)])]:
 p=root/rel
 print('PATCH-INPUT',rel)
 for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
  if not any(a<=i<=b for a,b in ranges):continue
  print('PATCH-LINE',rel,i,line[:420])
