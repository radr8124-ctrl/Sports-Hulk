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
 assert.match(panel.slice(b,c),/Link my Survivor entry/)
})

test('link entry shortcut points to existing, still server-secure one-time claim form, not a bypass',()=>{
 assert.match(panel,/id="survivor-link-entry"/)
 assert.match(panel,/scrollIntoView/)
 assert.equal((panel.match(/<SurvivorPickEditor/g)||[]).length,1)
 assert.match(panel,/getAccessToken=\{getAccessToken\}/)
 assert.match(panel,/onClick=\{linkExistingEntry\}/)
 assert.match(panel,/Connect another Survivor entry/)
 assert.match(panel,/single-use/)
})
