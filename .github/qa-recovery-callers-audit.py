#!/usr/bin/env python3
"""Fail CI when non-test production source directly invokes unguarded restore/recovery."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
names=('recoverFixed','restoreFixed','activateFixed','finishFixed','rollbackFromGitHub','recoverWithExclusiveLock')
for directory in ('app','bootstrap','launcher'):
 for file in sorted((root/directory).rglob('*')):
  if not file.is_file() or file.suffix not in ('.mjs','.js','.ps1','.cjs'):continue
  try:lines=file.read_text(encoding='utf-8-sig').splitlines()
  except UnicodeDecodeError:continue
  for idx,line in enumerate(lines,1):
   if any(re.search(r'\\b'+re.escape(term)+r'\\b',line) for term in names):
    print(f'CALLER {file.relative_to(root)}:{idx}: {line[:240]}')
print('CALLER AUDIT END')
