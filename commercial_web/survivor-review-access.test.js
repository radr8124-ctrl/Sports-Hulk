import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const app=readFileSync(new URL('./src/App.jsx',import.meta.url),'utf8')
const panel=app.slice(app.indexOf('function SurvivorCommercialPanel() {'),
 app.indexOf('function ',app.indexOf('function SurvivorCommercialPanel() {')+1))

test('public Survivor sign in/access is immediately after deadline, before research or week5 editor',()=>{
 const a=panel.indexOf('aria-label="Survivor entry deadline"')
 const b=panel.indexOf('aria-label="Survivor review access shortcut"')
 const c=panel.indexOf('<SurvivorPickEditor')
 const d=panel.indexOf('<SurvivorMarketReview')
 assert(a>0&&b>a&&c>b&&d>c)
 assert.match(panel.slice(b,c),/!isSignedIn/)
 assert.match(panel.slice(b,c),/AccountButton/)
 assert.match(panel.slice(a,b),/!hasEntry/)
 assert.match(panel.slice(b,c),/Refresh my entries/)
 assert.match(panel.slice(b,c),/appear automatically without a name or claim code/)
 assert.doesNotMatch(panel.slice(b,c),/Link my Survivor entry/)
 assert.doesNotMatch(panel.slice(b,c),/scrollIntoView/)
})

test('preassigned returning owners automatically load their entry; optional manual claim remains collapsed and protected',()=>{
 assert.match(panel,/id="survivor-link-entry"/)
 assert.match(panel,/Need to connect another entry\? Optional pool-manager claim/)
 assert.match(panel,/Manual entry connection \(optional\)/)
 assert.equal((panel.match(/<SurvivorPickEditor/g)||[]).length,1)
 assert.match(panel,/getAccessToken=\{getAccessToken\}/)
 assert.match(panel,/onClick=\{linkExistingEntry\}/)
 assert.match(panel,/single-use/)
 assert.match(panel,/saved.status==='PRIVATE_STATE_UNAVAILABLE'/)
})
