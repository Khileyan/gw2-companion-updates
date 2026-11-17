// Non-publishing RC11 ZIP validation that can run on both Linux and Windows.
// No signing keys or live installation paths are accessed.
import fs from 'node:fs';
import {inspectReleaseZip} from '../source/app/install-verified.mjs';
import {compareVersions} from '../source/app/updater.mjs';
const archive=process.argv[2];
if(!archive)throw Error('RC11 test artifact required');
if(compareVersions('5.9.0-rc.11','5.9.0-rc.10')!==1)throw Error('Invalid RC11 monotonic upgrade version');
const records=inspectReleaseZip(fs.readFileSync(archive),{version:'5.9.0-rc.11'}).records;
if(!records?.length)throw Error('RC11 archive empty');
const files=records.map(r=>r.parts.join('/'));
for(const component of [
 'bootstrap/exclusive-update-lock.mjs',
 'bootstrap/launcher-process-identity.mjs',
 'bootstrap/fixed-confirm.mjs',
 'bootstrap/stale-journal.mjs',
 'launcher/GW2-Companion.ps1',
 'app/package.json'
]){
 if(!files.some(x=>x.endsWith('/'+component)))throw Error('Missing critical RC11 component: '+component);
}
console.log('RC11 unsigned QA archive verified on this OS:',records.length,'entries');
