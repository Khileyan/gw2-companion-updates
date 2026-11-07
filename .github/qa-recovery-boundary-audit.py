#!/usr/bin/env python3
"""Inspect fixed updater ownership boundaries without exposing runtime credentials."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
p=root/'bootstrap/fixed-update.mjs'
lines=p.read_text(encoding='utf-8-sig').splitlines()
pattern=re.compile(r'recoverFixed|rollbackFixed|retryRestoreFixed|function lock\(|release\(|unlock\(|fs\.(rmSync|renameSync|writeFileSync)|action===|performFixedUpdate|finally\s*\{',re.I)
indexes=[i for i,line in enumerate(lines) if pattern.search(line)]
selected=set()
for i in indexes:
 selected.update(range(max(0,i-2),min(len(lines),i+4)))
print('AUDIT total-lines:',len(lines))
for i in sorted(selected):
 line=lines[i]
 if any(z in line.lower() for z in ('authorization','token=','key=','secret=')):continue
 print(f'AUDIT {i+1:04d}: {line[:450]}')
