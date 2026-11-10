#!/usr/bin/env python3
"""RC11 QA: write process creation timestamp beside PID in Launcher session.
Do not change existing session lifetime or restart behaviour.
"""
from pathlib import Path
import sys
p=(Path(sys.argv[1]) if len(sys.argv)>1 else Path('source'))/'launcher/GW2-Companion.ps1'
s=p.read_text(encoding='utf-8-sig')
old="try{[ordered]@{pid=$PID;version=$script:CompanionVersion} | ConvertTo-Json | Set-Content -LiteralPath $script:ManagedSession -Encoding UTF8}catch{}"
new="""try{
        $self=Get-Process -Id $PID -ErrorAction Stop
        $started=$self.StartTime.ToUniversalTime().ToString('o',[Globalization.CultureInfo]::InvariantCulture)
        [ordered]@{schema=2;pid=$PID;version=$script:CompanionVersion;started_at_utc=$started} | ConvertTo-Json -Compress | Set-Content -LiteralPath $script:ManagedSession -Encoding UTF8
      }catch{}"""
if s.count(old)!=1:raise SystemExit('Unknown launcher-session writer layout; refuse patch')
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('QA launcher session includes Windows process start timestamp')
