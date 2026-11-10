#!/usr/bin/env python3
"""Guard manual-rollback confirmation with the same exclusive update.lock."""
from pathlib import Path
import sys
p=(Path(sys.argv[1]) if len(sys.argv)>1 else Path('source'))/'bootstrap/fixed-confirm.mjs'
s=p.read_text(encoding='utf-8-sig')
anchor="import {fixedRoot,fixedPaths,loadJSON,finishFixed,currentApp} from './fixed-core.mjs';"
if s.count(anchor)!=1:raise SystemExit('Unknown confirm module imports')
s=s.replace(anchor,anchor+"\nimport {acquireExclusiveUpdateLock} from './exclusive-update-lock.mjs';")
old="if(j.manual_rollback_pending&&j.to===version)finishFixed(root);"
new="""if(j.manual_rollback_pending&&j.to===version){
   const owner=acquireExclusiveUpdateLock(root,{kind:'fixed-update'});
   try{
     owner.assertOwned();
     // Re-read the journal under lock: pre-lock state may have changed.
     const current=loadJSON(fixedPaths(root).journal);
     if(!current||!current.manual_rollback_pending||current.to!==version)
       throw Error('Rollback confirmation state changed during lock acquisition');
     owner.assertOwned();
     finishFixed(root);
   }finally{owner.release();}
  }"""
if s.count(old)!=1:raise SystemExit('Unknown manual rollback confirmation path')
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('QA: manual rollback confirmation now owns update.lock before finishFixed')
