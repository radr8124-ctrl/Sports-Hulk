import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {resolveWeekPickRule} from './survivor_rules.js'

// The user must see the real, authenticated pick editor before lengthy data
// panels; never mistake saved-in-Zenith for external pool submission.
const app=readFileSync(new URL('./src/App.jsx',import.meta.url),'utf8')
const survivor=app.slice(app.indexOf('function SurvivorCommercialPanel() {'),
  app.indexOf('function ',app.indexOf('function SurvivorCommercialPanel() {')+1))

test('Survivor places deadline and private pick editor ahead of every research/import panel',()=>{
 const clock=survivor.indexOf('aria-label="Survivor entry deadline"')
 const pick=survivor.indexOf('<SurvivorPickEditor')
 const research=survivor.indexOf('<SurvivorMarketReview')
 const importer=survivor.indexOf('<SurvivorPoolImport')
 assert(clock>0&&pick>clock&&research>pick&&importer>pick)
 assert.equal((survivor.match(/<SurvivorPickEditor/g)||[]).length,1)
 assert.match(survivor.slice(clock,pick),/EXTERNAL POOL/)
})

test('private save component stays behind entry-linking authentication',()=>{
 const opening=survivor.slice(survivor.indexOf('Survivor entry deadline'),survivor.indexOf('<SurvivorPickEditor'))
 assert.match(opening,/hasEntry && \(/)
 assert.match(survivor,/entryName=\{saved\.active_entry\}/)
 assert.match(survivor,/usedTeams=\{usedTeams\}/)
 assert.match(survivor,/currentPicks=\{currentPicks\}/)
 assert.match(survivor,/getAccessToken=\{getAccessToken\}/)
 assert.match(survivor,/onSaved=\{\(\) => setLinkRefresh\(/)
})

test('original 2026 pool rules confirm Week 5 one pick without new pool sheet',()=>{
 const r=resolveWeekPickRule(5,{
  required_picks:null,rule_status:'AWAITING_OFFICIAL_POOL_SHEET',official_pool_sheet_confirmed:false,
 })
 assert.equal(r.required_picks,1)
 assert.equal(r.rule_confirmed,true)
 assert.equal(r.rule_status,'CONFIRMED_FROM_2026_ORIGINAL_RULES')
 const week6=resolveWeekPickRule(6,{})
 assert.equal(week6.required_picks,2)
 assert.equal(week6.rule_confirmed,true)
})

test('conflicting imported weekly requirement must fail closed',()=>{
 const r=resolveWeekPickRule(5,{
  required_picks:2,official_pool_sheet_confirmed:true,
  rule_status:'CONFIRMED_FROM_IMPORTED_POOL_HEADER',
 })
 assert.equal(r.rule_confirmed,false)
 assert.equal(r.required_picks,null)
 assert.equal(r.rule_status,'RULE_SOURCE_CONFLICT_REVIEW_REQUIRED')
})
