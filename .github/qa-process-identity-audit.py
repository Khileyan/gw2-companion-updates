#!/usr/bin/env python3
"""Read-only code review probe: verify real launcher session/identity producers.
Emits only matching SOURCE lines in the public reconstructed candidate.
No host data, credentials, settings or user filesystem contents are read.
"""
from pathlib import Path
import re,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
patterns=[re.compile(x,re.I) for x in ('launcher-session\\.json','StartTime','Get-CimInstance','process\\.kill','\\$PID','session_token','creation_time','ProcessStart')]
paths=[root/'launcher/GW2-Companion.ps1',root/'bootstrap/Start-Managed.ps1',root/'bootstrap/fixed-update.mjs']
for file in paths:
 print('IDENTITY-AUDIT FILE',file.relative_to(root))
 if not file.exists():continue
 lines=file.read_text(encoding='utf-8-sig').splitlines()
 matches=[(i,line) for i,line in enumerate(lines,1) if any(p.search(line) for p in patterns)]
 print('IDENTITY-AUDIT MATCHES',len(matches))
 for i,line in matches[:22]:
  # Snippets from reviewed SOURCE only, no runtime account data.
  print('IDENTITY-AUDIT SOURCE',str(i),line[:240])
