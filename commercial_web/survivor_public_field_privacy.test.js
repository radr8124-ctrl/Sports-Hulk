import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {buildSurvivorWeek5FieldWatch} from './survivor_week5_field_watch.js'
const original=readFileSync(new URL('../nfl_live/survivor_pool/derived/SURVIVOR_POOL_LEDGER.csv',import.meta.url),'utf8')
const meta=JSON.parse(readFileSync(new URL('../nfl_live/survivor_pool/derived/LATEST_OFFICIAL_POOL.json',import.meta.url),'utf8'))
const feed=JSON.parse(readFileSync(new URL('./public/nfl_scores.json',import.meta.url),'utf8'))
const server=readFileSync(new URL('./server.js',import.meta.url),'utf8')
test('anonymous aggregate recomputes the original whole field, without any personally identifiable entries',()=>{
 const result=buildSurvivorWeek5FieldWatch({csvText:original,meta,scoreboard:feed,at:Date.now()})
 assert.equal(result.status,'VERIFIED_OFFICIAL_FIELD')
 assert.equal(result.total_entries,333)
 assert.equal(result.marked_eliminated_before_sunday,148)
 assert.equal(result.owner,null)
 assert.equal(JSON.stringify(result).includes('ANNIE G 01'),false)
 assert.equal(result.teams.find(x=>x.team==='Houston Texans').entries,62)
})
test('public HTTP endpoint explicitly allowlists only aggregate fields and has no member lookup or mutable verbs',()=>{
 const start=server.indexOf("url.pathname==='/api/survivor/public-field-watch'")
 const end=server.indexOf("url.pathname==='/api/survivor/field-watch'",start)
 assert.ok(start>=0 && end>start)
 const route=server.slice(start,end)
 assert.match(route,/csvText:ledger,meta,scoreboard:scores/)
 assert.match(route,/buildSurvivorWeek5FieldWatch/)
 assert.match(route,/teams:report\.teams/)
 assert.doesNotMatch(route,/entry_name:|owner:report\.owner|current_picks:|email:|linkedSurvivorEntries|survivorUser|INSFORGE_ADMIN/)
 assert.doesNotMatch(route,/req\.method==='POST'|saveMemberLinks|process\('confirm'/)
})
