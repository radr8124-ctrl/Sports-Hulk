import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const app=readFileSync(new URL('./src/App.jsx',import.meta.url),'utf8')
const history=readFileSync(new URL('./src/SurvivorPastPicks.jsx',import.meta.url),'utf8')
const panel=app.slice(app.indexOf('function SurvivorCommercialPanel() {'),app.indexOf('function ',app.indexOf('function SurvivorCommercialPanel() {')+1))
const hook=app.slice(app.indexOf('function usePrivateSurvivorState('),app.indexOf('function humanize('))

test('history access and refresh appear directly below current-week warning for every signed-in visitor',()=>{
 const deadline=panel.indexOf('aria-label="Survivor entry deadline"')
 const access=panel.indexOf('aria-label="Survivor history status and refresh"')
 const previous=panel.indexOf('<SurvivorPastPicks')
 const editor=panel.indexOf('<SurvivorPickEditor')
 assert.ok(deadline>=0 && access>deadline && previous>access && editor>previous)
 assert.match(panel.slice(deadline,editor),/isSignedIn/)
 assert.match(panel.slice(deadline,editor),/setLinkRefresh\(value => value \+ 1\)/)
 assert.match(panel.slice(deadline,editor),/My Past Picks/)
 assert.match(panel.slice(deadline,editor),/View all/)
 assert.match(panel.slice(deadline,editor),/Refreshing/)
})

test('signed-in error states stay visible, not mistaken for no historical picks',()=>{
 assert.match(panel,/PRIVATE_STATE_UNAVAILABLE/)
 assert.match(panel,/Your past picks could not be loaded/)
 assert.match(panel,/HISTORY_UNAVAILABLE/)
 assert.match(panel,/No entry connected/)
 assert.match(panel,/historyLoadError/)
})

test('history is private and anchor is stable for iPhone direct navigation',()=>{
 assert.match(history,/id="my-survivor-past-picks"/)
 assert.match(history,/data-survivor-past-picks/)
 assert.match(panel,/getElementById\('my-survivor-past-picks'\)\?\.scrollIntoView/)
 assert.doesNotMatch(panel,/href="#my-survivor-past-picks"/)
 assert.match(panel,/hasEntry/)
 assert.doesNotMatch(panel,/window\.localStorage\.setItem\('survivor/)
})

test('returning Safari tab refreshes private history without saving or submitting a pick',()=>{
 assert.match(hook,/visibilitychange/)
 assert.match(hook,/pageshow/)
 assert.match(hook,/document\.visibilityState/)
 assert.match(hook,/window\.addEventListener/)
 assert.match(hook,/window\.removeEventListener/)
 assert.match(hook,/setData\(payload\)/)
 assert.match(hook,/previousLinkedIdentity/)
 assert.match(hook,/previousLinkedIdentity\.current !== privateIdentity/)
 assert.match(hook,/requestId === latestRequestId/)
 assert.doesNotMatch(hook,/\/api\/survivor\/save-picks/)
})
