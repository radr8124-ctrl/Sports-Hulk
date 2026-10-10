import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtemp,readFile,readdir,writeFile,rm} from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import {createHash} from 'node:crypto'
import {loadDallasSnapshot,saveDallasSnapshot} from './survivor_thursday_store.js'
const snapshot=(name,source)=>({
 version:1,kind:'THURSDAY_DALLAS_USER_REPORTED_EVIDENCE',
 report_sha256:createHash('sha256').update(source).digest('hex'),source_text:source,counts:{uploaded:1},source_name:name,
 rows:[{entry_name:'PRIVATE NAME 01',match_status:'NOT_IN_PREVIOUS_SHEET'}],
})

test('private write is readback verified, idempotent, versioned and preserves previous rows',async()=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'zenith-dallas-'))
 try{
  assert.equal(await loadDallasSnapshot(dir),null)
  const a=await saveDallasSnapshot(snapshot('source A','PRIVATE NAME 01'),dir)
  assert.equal(a.status,'SAVED_REPORTED_ONLY')
  const b=await saveDallasSnapshot(snapshot('source A','PRIVATE NAME 01'),dir)
  assert.equal(b.status,'ALREADY_SAVED')
  const c=await saveDallasSnapshot(snapshot('source B','PRIVATE NAME 02'),dir)
  assert.equal(c.status,'SAVED_REPORTED_ONLY')
  assert.equal((await loadDallasSnapshot(dir)).source_name,'source B')
  const revisions=await readdir(path.join(dir,'revisions'))
  assert.equal(revisions.length,1)
  const prev=JSON.parse(await readFile(path.join(dir,'revisions',revisions[0]),'utf8'))
  assert.equal(prev.source_name,'source A')
 }finally{await rm(dir,{recursive:true,force:true})}
})

test('corrupt existing report cannot be silently replaced',async()=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'zenith-dallas-'))
 try{
  await writeFile(path.join(dir,'week5_dallas_report.json'),'broken data')
  await assert.rejects(()=>saveDallasSnapshot(snapshot('replacement','PRIVATE NAME 03'),dir))
  assert.equal(await readFile(path.join(dir,'week5_dallas_report.json'),'utf8'),'broken data')
 }finally{await rm(dir,{recursive:true,force:true})}
})
