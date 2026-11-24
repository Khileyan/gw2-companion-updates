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
 // Keep a callable release interface for the old updater, with explicit
 // ownership assertions available directly before each filesystem mutation.
 const owner=acquireExclusiveUpdateLock(root,{kind:'fixed-update'});
 const unlock=()=>owner.release();
 unlock.assertOwned=()=>owner.assertOwned();
 return unlock;
}"""
if len(re.findall(pattern,s))!=1:raise SystemExit('Unknown original fixed updater lock; refusing patch')
s=re.sub(pattern,lambda _:replacement,s)
def guarded(old,new):
 global s
 if s.count(old)!=1:raise SystemExit('Unsafe/unexpected update mutation boundary: '+repr(old))
 s=s.replace(old,new)
guarded("activateFixed(root,candidate,from,to);activated=true;",
        "unlock.assertOwned();activateFixed(root,candidate,from,to);activated=true;")
guarded("const done=finishFixed(root);activated=false;",
        "unlock.assertOwned();const done=finishFixed(root);activated=false;")
guarded("try{const restored=await retryRestoreFixed(root);activated=false;",
        "try{const restored=await retryRestoreFixed(root,{restore:(r)=>{unlock.assertOwned();return restoreFixed(r);}});activated=false;")
guarded("activateFixed(root,candidate,current,m.version);",
        "unlock.assertOwned();activateFixed(root,candidate,current,m.version);")
guarded("if(fs.existsSync(p.journal))try{restoreFixed(root);}catch{}",
        "if(fs.existsSync(p.journal))try{unlock.assertOwned();restoreFixed(root);}catch{}")
# Rollback and other helper functions remain byte-for-byte unchanged.
if 'retryRestoreFixed' not in s:raise SystemExit('Recovery helper lost: refusing patch')
p.write_text(s,encoding='utf-8')
print('QA fixed updater lock changed without removing existing recovery helpers')
