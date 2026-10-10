// Private, versioned sidecar. Never lives under a web-served/static Git path.
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { randomBytes, createHash } from 'node:crypto'
import path from 'node:path'
const digest=bytes=>createHash('sha256').update(bytes).digest('hex')
export const DALLAS_PRIVATE_DIR='/home/ubuntu/sports-zenith-private/survivor_thursday'
const FILENAME='week5_dallas_report.json'

export async function loadDallasSnapshot(dir=DALLAS_PRIVATE_DIR) {
  let raw
  try { raw=await readFile(path.join(dir,FILENAME),'utf8') }
  catch(error){if(error?.code==='ENOENT')return null;throw error}
  const value=JSON.parse(raw)
  if(value?.kind!=='THURSDAY_DALLAS_USER_REPORTED_EVIDENCE' ||
    value?.version!==1 || !Array.isArray(value.rows) ||
    value.counts?.uploaded!==value.rows.length ||
    !/^[a-f0-9]{64}$/i.test(value.report_sha256||'') ||
    typeof value.source_text!=='string' || digest(Buffer.from(value.source_text))!==value.report_sha256){
    throw Error('Stored private Thursday report is invalid; preserve and review it before any update.')
  }
  return value
}

export async function saveDallasSnapshot(snapshot,dir=DALLAS_PRIVATE_DIR) {
  if(snapshot?.kind!=='THURSDAY_DALLAS_USER_REPORTED_EVIDENCE' ||
    snapshot?.version!==1 || !Array.isArray(snapshot.rows) ||
    snapshot.rows.length!==snapshot.counts?.uploaded ||
    !/^[a-f0-9]{64}$/i.test(snapshot.report_sha256||'') ||
    typeof snapshot.source_text!=='string' || digest(Buffer.from(snapshot.source_text))!==snapshot.report_sha256){
    throw Error('Refusing to write an invalid private report.')
  }
  await mkdir(dir,{recursive:true,mode:0o700})
  const prior=await loadDallasSnapshot(dir) // corrupt prior state must fail closed
  if(prior?.report_sha256===snapshot.report_sha256 && prior?.source_name===snapshot.source_name){
    return {status:'ALREADY_SAVED',snapshot:prior}
  }
  const encoded=JSON.stringify(snapshot,null,2)+'\n'
  const tmp=path.join(dir,'.report-'+randomBytes(12).toString('hex')+'.tmp')
  const destination=path.join(dir,FILENAME)
  if(prior){
    await mkdir(path.join(dir,'revisions'),{recursive:true,mode:0o700})
    const before=await readFile(destination)
    const archive=path.join(dir,'revisions',`${Date.now()}_${digest(before).slice(0,20)}.json`)
    await writeFile(archive,before,{flag:'wx',mode:0o600})
    if(digest(await readFile(archive))!==digest(before))throw Error('Report revision backup verification failed.')
  }
  await writeFile(tmp,encoded,{flag:'wx',mode:0o600})
  if(digest(await readFile(tmp))!==digest(Buffer.from(encoded)))throw Error('Private Thursday temporary write verification failed.')
  await rename(tmp,destination)
  const persisted=await loadDallasSnapshot(dir)
  if(persisted.report_sha256!==snapshot.report_sha256 ||
    persisted.source_name!==snapshot.source_name || persisted.rows.length!==snapshot.rows.length){
    throw Error('Private Thursday source readback failed.')
  }
  return {status:'SAVED_REPORTED_ONLY',snapshot:persisted}
}
