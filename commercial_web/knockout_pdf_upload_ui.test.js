import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const source=name=>readFileSync(new URL('./'+name,import.meta.url),'utf8')
const app=source('src/App.jsx')
const panel=app.slice(app.indexOf('function SurvivorCommercialPanel() {'),app.indexOf('function ',app.indexOf('function SurvivorCommercialPanel() {')+1))
const ui=source('src/SurvivorPoolImport.jsx')
const server=source('server.js')

test('Knockout Pool PDF button is near the top but actual upload stays after private pick editor',()=>{
 const clock=panel.indexOf('aria-label="Survivor entry deadline"')
 const shortcut=panel.indexOf('aria-label="Knockout Pool PDF quick access"')
 const history=panel.indexOf('aria-label="Survivor history status and refresh"')
 const editor=panel.indexOf('<SurvivorPickEditor')
 const importer=panel.indexOf('<SurvivorPoolImport')
 assert.ok(clock>0 && shortcut>clock && history>shortcut && editor>history && importer>editor)
 assert.equal((panel.match(/<SurvivorPoolImport/g)||[]).length,1)
 assert.match(panel.slice(clock,editor),/saved\.pool_manager_enabled === true/)
 assert.match(panel.slice(shortcut,history),/details\.open=true/)
 assert.match(panel.slice(shortcut,history),/getElementById\('knockout-pdf-upload'\)/)
})

test('only the authorized linked account sees PDF quick action, never anonymous public browsers',()=>{
 const route=server.slice(server.indexOf("url.pathname==='/api/survivor/state'"),server.indexOf("url.pathname==='/api/ask/evaluation-summary'"))
 assert.match(route,/if\(!user\) return json\(res,401/)
 assert.match(route,/pool_manager_enabled:poolManagerPermitted\(user\)/)
 assert.match(panel,/isSignedIn && saved\.pool_manager_enabled === true/)
 assert.match(ui,/if \(!allowed\) return null/)
 assert.match(ui,/api\/survivor\/pool-manager/)
})

test('manager-only PDF upload is collapsed by default and requires full preview and affirmative confirmation',()=>{
 assert.match(ui,/id="knockout-pdf-upload"/)
 assert.match(ui,/<details ref=\{detailsRef\}/)
 assert.match(ui,/Upload weekly PDF/)
 assert.match(ui,/accept="\.pdf,application\/pdf,\.xlsx,\.csv"/)
 assert.match(ui,/Preview pool file/)
 assert.match(ui,/Confirm pool import/)
 assert.match(ui,/preview\.preview_token/)
 assert.match(ui,/disabled=\{!confirmed \|\| working\}/)
 assert.match(ui,/setConfirmed\(false\)/)
 assert.match(ui,/linked_entry_preview/)
 assert.match(ui,/additional_same_name_tickets_review/)
})

test('browser never proposes recording the owner team based on a PDF preview alone',()=>{
 assert.doesNotMatch(ui,/\/api\/survivor\/save-picks/)
 assert.doesNotMatch(ui,/autoConfirm|autoSubmit|approveBet/)
 const preview=server.slice(server.indexOf("url.pathname==='/api/survivor/pool/preview'"),server.indexOf("url.pathname==='/api/survivor/pool/confirm'"))
 assert.match(preview,/poolManagerPermitted\(user\)/)
 assert.match(preview,/linkedSurvivorEntries\(req,user.id\)/)
 assert.match(preview,/focus_entry_names:ownerEntries/)
 assert.doesNotMatch(preview,/body\.focus_entry_names|body\.entry_name/)
})
