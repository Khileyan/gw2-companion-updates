import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const src=fs.readFileSync(new URL('../launcher/GW2-Companion.ps1',import.meta.url),'utf8');
test('RC10: separate manual check control from installation and require consent',()=>{
 assert.match(src,/\$btnCheck=MakeButton 'Nach Updates suchen'/);
 assert.match(src,/\$btnUpdate=MakeButton 'Update installieren'/);
 assert.match(src,/\$btnCheck\.add_Click\(\{/);
 assert.match(src,/\$btnUpdate\.add_Click\(\{/);
 const check=src.split('$btnCheck.add_Click({')[1].split('$btnUpdate.add_Click({')[0];
 assert.match(check,/bootstrap\\check-release\.mjs/);
 assert.doesNotMatch(check,/Update-Progress\.ps1/);
 assert.doesNotMatch(check,/updater\.mjs check /);
 const install=src.split('$btnUpdate.add_Click({')[1].split('$form.add_Resize')[0];
 assert.match(install,/updater\.mjs check /);
 assert.match(install,/DialogResult\]::Yes/);
 assert.match(install,/Update-Progress\.ps1/);
});
test('RC10: failed or stale manual checks never enable install',()=>{
 assert.match(src,/ManualCheckStarted/);
 assert.match(src,/ManualCheckPending/);
 assert.match(src,/if\(-not \$check\.verified -or \$verifiedAt -lt \$script:ManualCheckStarted\.AddSeconds\(-2\)\)/);
 assert.match(src,/if\(\$exitCode -ne 0\)/);
 assert.match(src,/\$btnUpdate\.Enabled=\$false/);
 assert.match(src,/if\(\$available\.verified -ne \$true -or -not\(Is-NewerRelease/);
});
test('RC10: branded tray icon and managed shutdown remain intact',()=>{
 assert.match(src,/\$tray\.Icon=\$script:BrandIcon/);
 assert.match(src,/reason -eq 'verified-update'/);
 assert.doesNotMatch(src,/function Make-StatusIcon/);
 assert.match(src,/function Quit-Application/);
});
