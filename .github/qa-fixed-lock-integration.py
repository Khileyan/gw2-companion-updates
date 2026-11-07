#!/usr/bin/env python3
"""Narrow replacement: the legacy updater's lock function only, never helper routines."""
from pathlib import Path
import re,sys
p=(Path(sys.argv[1]) if len(sys.argv)>1 else Path('source'))/'bootstrap/fixed-update.mjs'
s=p.read_text(encoding='utf-8-sig')
anchor="import {requestProgressHostLaunch} from './update-host.mjs';"
if s.count(anchor)!=1:raise SystemExit('Unknown fixed updater import layout')
s=s.replace(anchor,anchor+"\nimport {acquireExclusiveUpdateLock} from './exclusive-update-lock.mjs';")
pattern=r"function lock\(root\)\{[^\n]*flag:'wx'[^\n]*return \(\)=>fs\.rmSync\(f,\{force:true\}\);\}"
replacement="""function lock(root){
 // Own update.lock with an exclusive random token across awaited update steps.
 // Never remove another process's replacement lock.
 return acquireExclusiveUpdateLock(root,{kind:'fixed-update'}).release;
}"""
if len(re.findall(pattern,s))!=1:raise SystemExit('Unknown original fixed updater lock; refusing patch')
s=re.sub(pattern,lambda _:replacement,s)
# Rollback and other helper functions remain byte-for-byte unchanged.
if 'retryRestoreFixed' not in s:raise SystemExit('Recovery helper lost: refusing patch')
p.write_text(s,encoding='utf-8')
print('QA fixed updater lock changed without removing existing recovery helpers')
