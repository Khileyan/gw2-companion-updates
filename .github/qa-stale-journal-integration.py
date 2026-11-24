#!/usr/bin/env python3
"""Fail-closed integration of stale-journal diagnostics into the fixed updater CLI.

This patch is intended for reconstructed and verified RC10 source only.
No automatic archival takes place during a normal update.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
p=root/'bootstrap/fixed-update.mjs'
s=p.read_text(encoding='utf-8-sig')
def once(old,new):
 global s
 if s.count(old)!=1:raise SystemExit('RC10 QA integration guard failed: '+repr(old[:80]))
 s=s.replace(old,new)
once("import {requestProgressHostLaunch} from './update-host.mjs';",
     "import {requestProgressHostLaunch} from './update-host.mjs';\nimport {inspectStaleJournal,archiveStaleJournal} from './stale-journal.mjs';")
once(" if(action==='recover')return recoverFixed(root);",
""" if(action==='inspect-stale')return inspectStaleJournal(root);
 if(action==='archive-stale'){
  if(!process.argv.includes('--approve'))throw Error('Explicit LOCAL user approval required.');
  return archiveStaleJournal(root,{approved:true});
 }
 if(action==='recover')return recoverFixed(root);""")
once("Usage: node fixed-update.mjs update PID --approve --progress-host | recover | rollback VERSION --approve",
     "Usage: node fixed-update.mjs update PID --approve --progress-host | inspect-stale | archive-stale --approve | recover | rollback VERSION --approve")
p.write_text(s,encoding='utf-8')
print('RC10 QA stale journal read-only inspector and consent-gated archive wired')
