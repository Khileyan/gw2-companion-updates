// Fail-closed mutual exclusion using the update.lock path shared with fixed-update.mjs.
// A stale lock is never removed automatically.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export class UpdateLockBusyError extends Error {
 constructor(){super('Update operation active or lock state unknown');this.code='UPDATE_LOCK_BUSY';}
}
export function acquireExclusiveUpdateLock(root,{now=Date.now,kind='fixed-update'}={}){
 if(!['fixed-update','stale-journal-review'].includes(kind))throw Error('Invalid lock operation');
 const base=path.resolve(root), updater=path.join(base,'updater');
 if(!fs.lstatSync(base).isDirectory()||!fs.lstatSync(updater).isDirectory())throw Error('Unsafe update root');
 const lockFile=path.join(updater,'update.lock'),token=crypto.randomBytes(32).toString('hex');
 let fd;
 try{fd=fs.openSync(lockFile,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL,0o600);}
 catch(e){if(e.code==='EEXIST')throw new UpdateLockBusyError();throw e;}
 try{
  fs.writeFileSync(fd,JSON.stringify({schema:1,pid:process.pid,token,created_at:now(),kind})+'\n');
  fs.fsyncSync(fd);
 }catch(e){try{fs.closeSync(fd)}catch{}throw e;}
 fs.closeSync(fd);
 const assertOwned=()=>{
  const st=fs.lstatSync(lockFile);
  if(!st.isFile()||st.isSymbolicLink())throw Error('Exclusive lock changed');
  const current=JSON.parse(fs.readFileSync(lockFile,'utf8'));
  if(current.token!==token||current.pid!==process.pid||current.kind!==kind)
   throw Error('Exclusive lock ownership lost');
 };
 const release=()=>{assertOwned();fs.unlinkSync(lockFile);};
 return {assertOwned,release};
}
export function withExclusiveUpdateLock(root,operation,{now=Date.now}={}){
 if(typeof operation!=='function')throw TypeError('Callback required');
 const {assertOwned,release}=acquireExclusiveUpdateLock(root,{now,kind:'stale-journal-review'});
 let result,operationError;
 try{
  assertOwned();result=operation({assertOwned});
  if(result&&typeof result.then==='function')throw Error('Async callback is not supported');
  assertOwned();
 }catch(e){operationError=e;}
 try{release()}catch(e){if(!operationError)operationError=e;}
 if(operationError)throw operationError;
 return result;
}
