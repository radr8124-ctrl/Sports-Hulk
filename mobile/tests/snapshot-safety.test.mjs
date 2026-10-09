import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtempSync,writeFileSync,mkdirSync,readFileSync,existsSync,rmSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {stripNativeRuntimeSnapshots,assertNoNativeSnapshotJSON} from '../scripts/snapshot-safety.mjs'

test('native package strips website sports feeds but retains only static install manifest', () => {
  const base=mkdtempSync(join(tmpdir(),'zenith-native-snapshot-'))
  try {
    writeFileSync(join(base,'manifest.json'),JSON.stringify({name:'Sports Zenith'}))
    writeFileSync(join(base,'nfl_scores.json'),JSON.stringify({scores:[99]}))
    writeFileSync(join(base,'brain_performance.json'),JSON.stringify({stale:true}))
    writeFileSync(join(base,'index.html'),'<html>App shell</html>')
    mkdirSync(join(base,'data'))
    writeFileSync(join(base,'data','private_member_links.json'),'{"private":true}')
    const removed=stripNativeRuntimeSnapshots(base)
    assert.deepEqual(removed,['brain_performance.json','data/private_member_links.json','nfl_scores.json'])
    assert.equal(assertNoNativeSnapshotJSON(base),true)
    assert.equal(readFileSync(join(base,'manifest.json'),'utf8'),'{"name":"Sports Zenith"}')
    assert.equal(readFileSync(join(base,'index.html'),'utf8'),'<html>App shell</html>')
  } finally {rmSync(base,{recursive:true,force:true})}
})

test('native bundle audit refuses mutable packaged JSON rather than reporting false success', () => {
  const base=mkdtempSync(join(tmpdir(),'zenith-native-bundle-check-'))
  try {
    writeFileSync(join(base,'manifest.json'),'{}')
    writeFileSync(join(base,'mlb_scores.json'),'{"scores":[]}')
    assert.throws(()=>assertNoNativeSnapshotJSON(base),/runtime sports-data JSON/)
    stripNativeRuntimeSnapshots(base)
    assert.equal(assertNoNativeSnapshotJSON(base),true)
  } finally {rmSync(base,{recursive:true,force:true})}
})
