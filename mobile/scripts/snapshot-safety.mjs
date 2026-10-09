/* Never ship mutable sports-data JSON snapshots inside a signed native binary.
   Website snapshots are served live by the common HTTPS API instead. */
import {readdirSync, statSync, unlinkSync} from 'node:fs'
import {join,relative,resolve} from 'node:path'

export function stripNativeRuntimeSnapshots(webDir) {
  const root=resolve(webDir)
  const removed=[]
  const walk = dir => {
    for (const item of readdirSync(dir,{withFileTypes:true})) {
      const path=join(dir,item.name)
      if (item.isSymbolicLink()) throw new Error('Native web bundle cannot contain symlinks')
      if (item.isDirectory()) {walk(path);continue}
      if (!item.isFile()) continue
      const rel=relative(root,path).replaceAll('\\','/')
      if (!rel.endsWith('.json') || rel==='manifest.json') continue
      unlinkSync(path)
      removed.push(rel)
    }
  }
  walk(root)
  return removed.sort()
}

export function assertNoNativeSnapshotJSON(webDir) {
  const root=resolve(webDir)
  const forbidden=[]
  const walk=dir=>{
    for(const item of readdirSync(dir,{withFileTypes:true})) {
      const path=join(dir,item.name)
      if(item.isSymbolicLink())throw new Error('Native web bundle contains untrusted symlink')
      if(item.isDirectory()) {walk(path);continue}
      const rel=relative(root,path).replaceAll('\\','/')
      if(item.isFile()&&rel.endsWith('.json')&&rel!=='manifest.json')forbidden.push(rel)
    }
  }
  walk(root)
  if(forbidden.length)throw new Error('Native bundle embeds runtime sports-data JSON: '+forbidden.join(', '))
  return true
}
