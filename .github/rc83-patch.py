#!/usr/bin/env python3
"""Fail-closed patch of reviewed RC8.0 source to RC8.3 release candidate."""
from pathlib import Path
import sys

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
target='5.9.0-rc.8.3'
base='5.9.0-rc.8'

def change_exact(path,old,new):
    data=path.read_text(encoding='utf-8-sig')
    count=data.count(old)
    if count != 1:
        raise SystemExit(f'Expected one occurrence of {old!r} in {path}, found {count}')
    path.write_text(data.replace(old,new), encoding='utf-8')

# All versioned metadata must change together.
for rel in ('app/package.json','app-version.json','app/engine.mjs','tools/build-release.py'):
    p=root/rel
    data=p.read_text(encoding='utf-8-sig')
    if base not in data or target in data:
        raise SystemExit(f'Unexpected base version in {p}')
    p.write_text(data.replace(base,target), encoding='utf-8')

launcher=root/'launcher/GW2-Companion.ps1'
old=r'^\d+\.\d+\.\d+(?:-rc\.\d+)?$'
new=r'^\d+\.\d+\.\d+(?:-rc\.\d+(?:\.\d+)*)?$'
change_exact(launcher,old,new)

host=root/'bootstrap/Update-Progress.ps1'
s=host.read_text(encoding='utf-8-sig')
def once(a,b):
    global s
    n=s.count(a)
    if n != 1:
        raise SystemExit(f'Expected exactly one occurrence of {a[:80]!r} in progress host, found {n}')
    s=s.replace(a,b)
once('function Write-Receipt([string]$nonce,[string]$version,[int]$pid,[string]$errorCode',
     'function Write-Receipt([string]$nonce,[string]$version,[int]$launcherProcessId,[string]$errorCode')
once('$obj.pid=$pid','$obj.pid=$launcherProcessId')
once('    if($success){$progress.Value=100}else{$progress.Value=0}',
     '    if($success){$progress.Value=100;$script:doneAt=Get-Date}else{$progress.Value=0}')
once("""        if($script:terminal -and $script:confirmedPid -gt 0 -and -not (Get-Process -Id $script:confirmedPid -ErrorAction SilentlyContinue)){
            $script:confirmedPid=0
            Set-Phase 'Neuer Companion beendet' 'Der Start war zunaechst erfolgreich, aber das Fenster ist wieder verschwunden.' $null""",
     """        if($script:terminal -and $script:confirmedPid -gt 0 -and -not (Get-Process -Id $script:confirmedPid -ErrorAction SilentlyContinue)){
            $script:doneAt=$null
            $script:confirmedPid=0
            Set-Phase 'Neuer Companion beendet' 'Der Start war zunaechst erfolgreich, aber das Fenster ist wieder verschwunden.' $null""")
once("""        if(-not $script:terminal -and $null -ne $script:jobProcess){""",
     """        if($script:terminal -and $null -ne $script:doneAt -and ((Get-Date)-$script:doneAt).TotalSeconds -ge 3){$form.Close();return}
        if(-not $script:terminal -and $null -ne $script:jobProcess){""")
once('try{[Windows.Forms.Application]::Run($form)}finally{$timer.Stop();$timer.Dispose();$form.Dispose()}',
     'try{[Windows.Forms.Application]::Run($form)}finally{$timer.Stop();$timer.Dispose();if($null -ne $script:jobProcess){$script:jobProcess.Dispose()};$form.Dispose()}')
host.write_text(s,encoding='utf-8')

core=root/'bootstrap/fixed-core.mjs'
s=core.read_text(encoding='utf-8')
start=s.index('export function atomicJSON(file,value){')
end=s.index('export function loadJSON(file)',start)
if s.count('export function atomicJSON(file,value){')!=1 or end<=start:
    raise SystemExit('Unexpected fixed-core.mjs atomicJSON source layout')
replacement=r"""export function atomicJSON(file,value){
 fs.mkdirSync(path.dirname(file),{recursive:true});
 const tmp=file+'.'+process.pid+'.'+crypto.randomBytes(8).toString('hex')+'.tmp';
 const pause=new Int32Array(new SharedArrayBuffer(4));
 try{
  fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n',{flag:'wx',mode:0o600});
  for(let attempt=0;attempt<10;attempt++){
   try{fs.renameSync(tmp,file);return;}
   catch(e){
    if(!['EPERM','EACCES','EBUSY'].includes(e.code)||attempt===9)throw e;
    Atomics.wait(pause,0,0,50*(attempt+1));
   }
  }
 }finally{
  try{fs.rmSync(tmp,{force:true})}
  catch(e){if(!['EPERM','EACCES','EBUSY'].includes(e.code))throw e;}
 }
}
"""
core.write_text(s[:start]+replacement+s[end:],encoding='utf-8')

# Maintain ordering semantics of inherited version-specific tests:
# current RC8 -> RC8.3; synthetic next RC9 -> RC8.4.
for p in (root/'tests').glob('*.test.mjs'):
    s=p.read_text(encoding='utf-8')
    s=s.replace('5.9.0-rc.9','__RC83_FUTURE__')
    s=s.replace(r'5\.9\.0-rc\.9','__RC83_FUTURE_ESC__')
    s=s.replace('5.9.0-rc.8',target)
    s=s.replace(r'5\.9\.0-rc\.8',r'5\.9\.0-rc\.8\.3')
    s=s.replace('__RC83_FUTURE__','5.9.0-rc.8.4')
    s=s.replace('__RC83_FUTURE_ESC__',r'5\.9\.0-rc\.8\.4')
    p.write_text(s,encoding='utf-8')

assert target in (root/'app-version.json').read_text()
assert new in launcher.read_text()
assert '$script:doneAt=$null' in host.read_text()
print('RC8.3 candidate patched fail-closed:',target)
