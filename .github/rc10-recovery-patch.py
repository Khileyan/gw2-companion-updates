#!/usr/bin/env python3
"""Expose safe rollback reason codes without overwriting recovery journals."""
from pathlib import Path
import sys
p=(Path(sys.argv[1]) if len(sys.argv)>1 else Path('source'))/'bootstrap/fixed-update.mjs'
s=p.read_text(encoding='utf-8')
old="}catch{event(root,'recovery_required',{failure:'fixed_rollback_failed'});}"
new="""}catch(restoreError){
        // Retain the original transaction and backup for manual recovery.
        // Report only known OS error codes; never log paths or exception messages.
        const code=['EPERM','EACCES','EBUSY','ENOENT'].includes(restoreError?.code)?restoreError.code:'unclassified';
        event(root,'recovery_required',{failure:'fixed_rollback_failed',rollback_error_code:code});
      }"""
if s.count(old)!=1:raise SystemExit('Unexpected rollback error handler, refusing patch')
p.write_text(s.replace(old,new),encoding='utf-8')
print('RC10 bounded rollback diagnostics added')
