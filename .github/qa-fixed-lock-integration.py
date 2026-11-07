#!/usr/bin/env python3
"""Integrate token-owned exclusive lock with the async fixed updater (non-publishing)."""
from pathlib import Path
import sys
p=(Path(sys.argv[1]) if len(sys.argv)>1 else Path('source'))/'bootstrap/fixed-update.mjs'
s=p.read_text(encoding='utf-8-sig')
import_anchor="import {requestProgressHostLaunch} from './update-host.mjs';"
if s.count(import_anchor)!=1:raise SystemExit('Unknown fixed updater import layout')
s=s.replace(import_anchor,import_anchor+"\nimport {acquireExclusiveUpdateLock} from './exclusive-update-lock.mjs';")
start=s.find("function lock(root){")
end=s.find("\n\nexport async function performFixedUpdate",start)
if start<0 or end<0 or s.count("function lock(root){")!=1:
 raise SystemExit('Unknown fixed updater lock layout')
old=s[start:end]
if "flag:'wx'" not in old or "fs.rmSync(f,{force:true})" not in old:
 raise SystemExit('Refusing to replace unrecognized lock implementation')
s=s[:start]+"""function lock(root){
 // The existing fixed-update path already coordinates through updater/update.lock.
 // Never remove a lock whose random owner token changed mid-flight.
 return acquireExclusiveUpdateLock(root,{kind:'fixed-update'}).release;
}"""+s[end:]
p.write_text(s,encoding='utf-8')
print('QA exclusive owner lock integrated into fixed async updater')
