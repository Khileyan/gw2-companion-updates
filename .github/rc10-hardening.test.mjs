import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const gui=fs.readFileSync(new URL('../launcher/GW2-Companion.ps1',import.meta.url),'utf8');
const fixed=fs.readFileSync(new URL('../bootstrap/fixed-update.mjs',import.meta.url),'utf8');
test('RC10: no overlapping automatic and manual update checks',()=>{
 assert.match(gui,/ManualCheckPending -and \(Get-Date\) -ge \$script:NextAutoUpdateCheck/);
 assert.match(gui,/ManualCheckProcess\.Dispose\(\)/);
 assert.match(gui,/ManualCheckProcess\.Kill\(\)/);
});
test('RC10: stale and unverifiable version badges cannot enable install',()=>{
 assert.match(gui,/\$fresh=\$checked -le \[datetime\]::UtcNow\.AddMinutes\(2\) -and \$checked -ge \[datetime\]::UtcNow\.AddHours\(-1\)/);
 assert.match(gui,/if\(\$fresh -and \$available\.verified -eq \$true/);
 assert.match(gui,/\$btnUpdate\.Enabled=\$false/);
 assert.match(gui,/updater\.mjs check /);
});
test('RC10: historical errors are not treated as active recovery without a journal',()=>{
 assert.match(gui,/historical_recovery_status/);
 assert.match(gui,/updater\\fixed-transaction\.json/);
 assert.match(gui,/if\(Test-Path -LiteralPath \$journal\)/);
});
test('RC10: child processes are disposed and diagnostics remain sanitized',()=>{
 assert.match(gui,/function Stop-Proc\(\$proc\)/);
 assert.match(gui,/\$proc\.Dispose\(\)/);
 assert.match(gui,/if\(\$raw -match '\^\[a-z_\]\{1,40\}\$'\)/);
 assert.match(gui,/Active transaction: /);
 assert.doesNotMatch(gui,/Log-Event 'UPDATE' \$\(\$_\.Exception\.Message/);
});
test('RC10: rollback errors are classified but journal is retained',()=>{
 assert.match(fixed,/rollback_error_code:code/);
 assert.match(fixed,/\['EPERM','EACCES','EBUSY','ENOENT'\]/);
 assert.match(fixed,/if\(fs\.existsSync\(p\.journal\)\)throw Error/);
 assert.doesNotMatch(fixed,/fs\.rmSync\(p\.journal,\{force:true\}\)/);
});
