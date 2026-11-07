import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const root=process.env.RC12_SOURCE||'rc12-source';
const read=p=>fs.readFileSync(path.join(root,p),'utf8');

test('RC12: independently visible progress host with one-use verified readiness receipt',()=>{
 const gui=read('launcher/GW2-Companion.ps1');
 const host=read('bootstrap/Update-Progress.ps1');
 assert.match(gui,/\$progressProcess=Start-Process[^\n]+-WindowStyle Normal -PassThru/);
 assert.doesNotMatch(gui,/\$progressProcess=Start-Process[^\n]+-WindowStyle Hidden/);
 assert.match(gui,/progress-ready-/);
 assert.match(gui,/if\(-not \$acknowledged\)/);
 assert.match(gui,/if\(\$receipt.schema -eq 1 -and \[string\]\$receipt.nonce -ceq \$nonce -and \[int\]\$receipt.pid -eq \$progressProcess.Id\)/);
 assert.match(gui,/if\(-not \$progressProcess.HasExited\)\{\$progressProcess.Kill\(\)\}/);
 assert.match(host,/if\(\$ReadyNonce -cnotmatch '\^\[0-9a-f\]\{32\}\$'\)/);
 assert.match(host,/\$form.Add_Shown\(\{/);
 assert.match(host,/progress-ready-/);
 const handoff=gui.indexOf("$progressProcess=Start-Process");
 const ack=gui.indexOf("if(-not $acknowledged)");
 assert.ok(ack>handoff);
 const child=host.split('$form.Add_Shown({')[1];
 assert.ok(child.indexOf('Move-Item -LiteralPath $tmpReady -Destination $readyPath')<child.indexOf('$script:jobProcess=[Diagnostics.Process]::Start($startInfo)'));
});
test('RC12: pre-activation failure reason captured without leaking exception details',()=>{
 const updater=read('bootstrap/fixed-update.mjs');
 for(const state of ['preflight','trusted_source','manifest_check','download','verification','staged','launcher_shutdown']) assert.ok(updater.includes("'"+state+"'"));
 assert.match(updater,/failure_stage:failureStage/);
 assert.match(updater,/error_code:code,failure_stage:failureStage/);
 assert.doesNotMatch(updater,/failure_stage:e\.message/);
});
test('RC12: package version increased and source is consistent',()=>{
 assert.equal(JSON.parse(read('app/package.json')).version,'5.9.0-rc.12');
 assert.equal(JSON.parse(read('app-version.json')).version,'5.9.0-rc.12');
 assert.match(read('app/engine.mjs'),/5\.9\.0-rc\.12/);
});
