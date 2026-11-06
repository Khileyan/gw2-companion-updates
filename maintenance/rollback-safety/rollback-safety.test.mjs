import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {activateFixed,finishFixed,recoverFixed,currentApp,isCommittedFixed,loadJSON, COMPONENTS} from '../bootstrap/fixed-core.mjs';
const V1='5.9.0-rc.7', V2='5.9.0-rc.8';
function populate(root,ver){
  for(const k of COMPONENTS){const p=path.join(root,k);fs.mkdirSync(p,{recursive:true});fs.writeFileSync(path.join(p,'release-marker'),ver);}
  fs.writeFileSync(path.join(root,'app','package.json'),JSON.stringify({version:ver,install_layout:'fixed-v1'}));
  fs.writeFileSync(path.join(root,'app','server.mjs'),'//test');
  fs.writeFileSync(path.join(root,'launcher','GW2-Companion.ps1'),'#test');
  fs.writeFileSync(path.join(root,'app','tool-manifest.json'),JSON.stringify({count:33,names:Array.from({length:33},(_,i)=>'t'+i)}));
}
function fixture(){
 const base=fs.mkdtempSync(path.join(os.tmpdir(),'gw2-rollback-safety-'));
 const root=path.join(base,'install'),candidate=path.join(base,'candidate');
 fs.mkdirSync(root,{recursive:true});fs.mkdirSync(candidate,{recursive:true});
 populate(root,V1);populate(candidate,V2);fs.writeFileSync(path.join(root,'app-version.json'),JSON.stringify({version:V1}));
 return {root,candidate,cleanup(){fs.rmSync(base,{recursive:true,force:true})}};
}
test('successful activation completes and removes backup without blocking restart',()=>{
 const f=fixture();try{
  activateFixed(f.root,f.candidate,V1,V2);
  const result=finishFixed(f.root);
  assert.equal(result.active,V2);assert.equal(result.cleanup_pending,false);
  assert.equal(currentApp(f.root).version,V2);
  assert.equal(fs.existsSync(path.join(f.root,'updater','fixed-transaction.json')),false);
  assert.equal(recoverFixed(f.root).recovered,false);
 }finally{f.cleanup()}
});
test('blocked backup removal is nonfatal; no rollback of connected candidate',()=>{
 const f=fixture();try{
  const txn=activateFixed(f.root,f.candidate,V1,V2);
  const remove=(target,opts)=>{if(target===txn.backup){const e=new Error('locked');e.code='EPERM';throw e;}return fs.rmSync(target,opts)};
  const result=finishFixed(f.root,{remove});
  assert.equal(result.cleanup_pending,true);
  assert.equal(currentApp(f.root).version,V2);
  assert.equal(fs.existsSync(txn.backup),true);
  assert.equal(fs.existsSync(path.join(f.root,'updater','fixed-transaction.json')),false);
  assert.equal(loadJSON(path.join(f.root,'updater','cleanup-pending.json')).version,V2);
 }finally{f.cleanup()}
});
test('blocked journal deletion retains a verified committed journal, not a false recovery',()=>{
 const f=fixture();try{
  const txn=activateFixed(f.root,f.candidate,V1,V2);
  const journal=path.join(f.root,'updater','fixed-transaction.json');
  const remove=(target,opts)=>{if(target===journal){const e=new Error('locked');e.code='EPERM';throw e;}return fs.rmSync(target,opts)};
  const result=finishFixed(f.root,{remove});
  assert.equal(result.cleanup_pending,true);
  assert.equal(isCommittedFixed(f.root),true);
  assert.equal(currentApp(f.root).version,V2);
  assert.equal(recoverFixed(f.root,{minAgeMs:0}).committed,true);
  assert.equal(currentApp(f.root).version,V2);
 }finally{f.cleanup()}
});
test('uncommitted interrupted transaction is not incorrectly treated as completed',()=>{
 const f=fixture();try{
  activateFixed(f.root,f.candidate,V1,V2);
  assert.equal(isCommittedFixed(f.root),false);
  const result=recoverFixed(f.root,{minAgeMs:0});
  assert.equal(result.restored,V1);
  assert.equal(currentApp(f.root).version,V1);
 }finally{f.cleanup()}
});
test('committed journal with mismatched last-good is rejected rather than silently accepted',()=>{
 const f=fixture();try{
  activateFixed(f.root,f.candidate,V1,V2);
  const txn=loadJSON(path.join(f.root,'updater','fixed-transaction.json'));
  fs.writeFileSync(path.join(f.root,'updater','fixed-transaction.json'),JSON.stringify({...txn,phase:'committed'}));
  assert.equal(isCommittedFixed(f.root),false);
  assert.throws(()=>recoverFixed(f.root,{minAgeMs:0}),/manual review/);
  assert.equal(currentApp(f.root).version,V2);
 }finally{f.cleanup()}
});

test('transient Windows EPERM retry preserves recovery semantics and eventually succeeds',async()=>{
 const {retryRestoreFixed}=await import('../bootstrap/fixed-update.mjs');
 let calls=0, waits=0;
 const result=await retryRestoreFixed('unused',{attempts:4,sleep:async()=>{waits++},restore:()=>{
  calls++;if(calls<3)throw Object.assign(new Error('lock'),{code:'EPERM'});return {restored:V1};
 }});
 assert.equal(result.restored,V1);assert.equal(calls,3);assert.equal(waits,2);
});
test('non-lock restoration error fails closed without retrying',async()=>{
 const {retryRestoreFixed}=await import('../bootstrap/fixed-update.mjs');
 let calls=0;
 await assert.rejects(retryRestoreFixed('unused',{restore:()=>{calls++;throw Object.assign(new Error('bad metadata'),{code:'EINVAL'})},sleep:async()=>{}}),/bad metadata/);
 assert.equal(calls,1);
});