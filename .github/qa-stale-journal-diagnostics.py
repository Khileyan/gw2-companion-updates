#!/usr/bin/env python3
"""Scoped RC10 QA error classification and actionable launcher warning."""
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('source')
def replace_once(p,old,new):
 s=p.read_text(encoding='utf-8-sig')
 if s.count(old)!=1:raise SystemExit('QA error classification guard failed: '+str(p))
 p.write_text(s.replace(old,new),encoding='utf-8')
replace_once(root/'bootstrap/fixed-update.mjs',
 "}else event(root,'failed',{phase:'not-activated',version:from??null,error_code:'update_aborted'});",
 """}else {
     const code=e?.message==='Pending fixed update transaction: review before another update.'
       ?'pending_fixed_transaction':'update_aborted';
     event(root,'failed',{phase:'not-activated',version:from??null,error_code:code});
   }""")
replace_once(root/'launcher/GW2-Companion.ps1',
 """                    }elseif($progress.state -eq 'failed'){
                        $lblHelp.Text='Letztes Update fehlgeschlagen; aktuelle Version unveraendert.'""",
 """                    }elseif($progress.state -eq 'failed'){
                        if([string]$progress.error_code -eq 'pending_fixed_transaction'){
                            $lblHelp.Text='Vorheriges Update nicht abgeschlossen. Bitte Diagnose und sichere Wiederherstellung pruefen.'
                            $btnUpdate.Enabled=$false
                        }else{
                            $lblHelp.Text='Letztes Update fehlgeschlagen; aktuelle Version unveraendert.'
                        }""")
print('Scoped pending transaction diagnostics and launcher warning added')
