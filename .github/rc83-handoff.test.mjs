import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {requestProgressHostLaunch} from '../bootstrap/update-host.mjs';

const VERSION = '5.9.0-rc.8.3';
function fixture(t) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'gw2-rc83-handoff-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  return root;
}
function deliver({root,nonce,version,readiness,receipt},state='connected',pid=123456) {
  fs.mkdirSync(path.dirname(receipt),{recursive:true});
  fs.writeFileSync(receipt,JSON.stringify({schema:1,nonce,version,pid}));
  fs.writeFileSync(readiness,JSON.stringify({version,pid,state}));
}
test('verified handoff: independent launcher acknowledge + connected health marker',async t=>{
  const root=fixture(t);
  const result=await requestProgressHostLaunch(root,VERSION,'starting',{
    pollMs:5,ackTimeoutMs:1000,readyTimeoutMs:1000,stableMs:25,
    isAlive:pid=>pid===123456,
    onRequest:req=>deliver(req)
  });
  assert.equal(result.pid,123456);
  assert.equal(result.last_marker,'connected');
});
test('rollback handoff: independent launcher reconnects previous version',async t=>{
  const root=fixture(t);
  const result=await requestProgressHostLaunch(root,'5.9.0-rc.8.2','rollback_starting',{
    pollMs:5,ackTimeoutMs:1000,readyTimeoutMs:1000,stableMs:25,
    isAlive:pid=>pid===123456,
    onRequest:req=>deliver(req)
  });
  assert.equal(result.last_marker,'connected');
});
test('premature launcher exit is reported and not treated as success',async t=>{
  const root=fixture(t);
  await assert.rejects(
    requestProgressHostLaunch(root,VERSION,'starting',{
      pollMs:5,ackTimeoutMs:1000,readyTimeoutMs:200,stableMs:25,
      isAlive:()=>false,onRequest:req=>deliver(req)
    }),
    /launcher_exited_before_connected/
  );
});
test('fatal readiness is reported and launcher is terminated',async t=>{
  const root=fixture(t);
  const stopped=[];
  await assert.rejects(
    requestProgressHostLaunch(root,VERSION,'starting',{
      pollMs:5,ackTimeoutMs:1000,readyTimeoutMs:200,stableMs:25,
      isAlive:()=>true,terminate:pid=>stopped.push(pid),
      onRequest:req=>deliver(req,'fatal')
    }),
    /launcher_reported_fatal/
  );
  assert.deepEqual(stopped,[123456]);
});
test('missing host acknowledgement times out without reporting success',async t=>{
  const root=fixture(t);
  await assert.rejects(
    requestProgressHostLaunch(root,VERSION,'starting',{
      pollMs:5,ackTimeoutMs:40,readyTimeoutMs:200,stableMs:25,
      isAlive:()=>true
    }),
    /launch_host_timeout/
  );
});
