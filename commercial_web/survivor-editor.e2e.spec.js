import {test,expect} from '@playwright/test'
import {createServer} from 'vite'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
const ROOT=path.dirname(fileURLToPath(import.meta.url))
let vite,local

test.beforeAll(async()=>{
 vite=await createServer({root:ROOT,logLevel:'error',server:{host:'127.0.0.1',port:0,strictPort:false}})
 await vite.listen()
 local='http://127.0.0.1:'+vite.httpServer.address().port+'/review_harness_survivor/index.html'
})
test.afterAll(async()=>{await vite?.close()})

async function ownerPage(page,{canManage=false,simulateReadbackMismatch=false,serverAckUnverified=false}={}){
 const writes=[]
 let persistedPicks=[]
 await page.route('**/api/survivor/**',async route=>{
  const u=new URL(route.request().url())
  // Every request must target the temporary local QA Vite host, NEVER production.
  expect(u.origin).toBe(new URL(local).origin)
  const name=u.pathname
  let response={status:404,body:{status:'UNMOCKED_QA_REQUEST_BLOCKED'}}
  if(name==='/api/survivor/pool-manager' && route.request().method()==='GET')response={status:200,body:{can_manage:canManage}}
  else if(name==='/api/survivor/save-picks' && route.request().method()==='POST'){
   const body=route.request().postDataJSON()
   expect(body.entry_name).toBe('SYNTHETIC QA 01')
   writes.push({path:name,method:'POST',body})
   persistedPicks=[...body.teams]
   response={status:200,body:serverAckUnverified
     ?{status:'SAVED_NOT_SUBMITTED',teams:body.teams,pool_submitted:false}
     :{status:'PERSISTED_IN_ZENITH_NOT_EXTERNAL_POOL',verified_disk_readback:true,
       entry_name:body.entry_name,week:body.week,teams:body.teams,
       pick_status:'SAVED_NOT_SUBMITTED',required_picks:1,
       pool_submitted:false,external_organizer_submission_verified:false,
       saved_at_utc:'2099-10-10T21:30:00.000Z'}}
  }else if(name==='/api/survivor/state' && route.request().method()==='GET'){
   response={status:200,body:{status:'READY',entry_linked:true,
     active_entry:'SYNTHETIC QA 01',entry_status:'ALIVE',pool_current_week:5,
     current_pick_status:'SAVED_NOT_SUBMITTED',required_picks:1,
     current_picks:simulateReadbackMismatch?[]:persistedPicks}}
  }else if(name==='/api/survivor/pool/preview' && route.request().method()==='POST'){
   const body=route.request().postDataJSON()
   expect(['QA_OFFICIAL.csv','QA_WEEK5.pdf']).toContain(body.filename)
   expect(body.base64.length).toBeGreaterThan(8)
   writes.push({path:name,method:'POST',preview:true,source_format:body.filename.endsWith('.pdf')?'PDF':'CSV'})
   response={status:200,body:{status:'PREVIEW_READY',preview_token:'SYNTHETIC_PREVIEW_ONLY',
     entry_count:4,pick_rows:7,max_week:5,source_format:body.filename.endsWith('.pdf')?'PDF':'CSV',
     duplicate_ticket_instances:1,examples:[{entry_name:'SYNTHETIC QA 01',pick_count:1}],
     linked_entry_preview:body.filename.endsWith('.pdf')?[{
       entry_name:'SYNTHETIC QA 01',exact_match:true,additional_same_name_tickets_review:1,
       current_week_picks:['Houston Texans'],weekly_picks:[{week:5,pick_number:1,team:'Houston Texans'}],
     }]:[],
   }}
  }else if(name==='/api/survivor/pool/confirm' && route.request().method()==='POST'){
   const body=route.request().postDataJSON()
   expect(body.preview_token).toBe('SYNTHETIC_PREVIEW_ONLY')
   writes.push({path:name,method:'POST',confirm:true})
   response={status:200,body:{status:'IMPORTED',entry_count:4,weekly_pick_rows:7,personal_entry_state_preserved:true}}
  }
  await route.fulfill({status:response.status,contentType:'application/json',body:JSON.stringify(response.body)})
 })
 await page.goto(local,{waitUntil:'networkidle'})
 await page.getByText('SYNTHETIC OWNER QA · ZERO REAL ACCOUNT ACCESS OR WRITES').waitFor()
 return writes
}

test('owner-facing Week 5 editor excludes all five burned teams, saves only to synthetic mock, displays external pool warning',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 const writes=await ownerPage(page)
 const editor=page.getByRole('region',{name:'Save this week Survivor picks'})
 await expect(editor).toBeVisible()
 await expect(page.locator('[data-survivor-cover-status="DECISION_OPEN"]')).toBeVisible()
 await expect(page.locator('[data-survivor-cover-metric="saved"]')).toContainText('0 / 1')
 await expect(page.locator('[data-survivor-cover-metric="used"]')).toContainText('5')
 await expect(page.locator('[data-survivor-cover-metric="qualified"]')).toContainText('0')
 const picker=editor.getByRole('combobox',{name:'Choose an unused NFL team'})
 const options=await picker.locator('option').allTextContents()
 for(const burned of ['Los Angeles Chargers','San Francisco 49ers','Kansas City Chiefs','Buffalo Bills','Minnesota Vikings']){
  expect(options).not.toContain(burned)
 }
 await picker.selectOption('Jacksonville Jaguars')
 await editor.getByRole('button',{name:'Add',exact:true}).click()
 await expect(editor.getByText('1 / 1 pick(s)')).toBeVisible()
 await expect(editor.getByRole('status').filter({hasText:'DRAFT ONLY'})).toBeVisible()
 await expect(editor.getByRole('button',{name:'Add',exact:true})).toBeDisabled()
 await editor.getByRole('button',{name:'Save picks'}).click()
 await expect(editor.getByRole('status').filter({hasText:'Saved and verified'})).toContainText('Your external pool has NOT been submitted')
 expect(writes).toHaveLength(1)
 expect(writes[0].body.teams).toEqual(['Jacksonville Jaguars'])
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
 await expect(page.getByRole('region',{name:'My Survivor pick score'}).getByText('SURVIVED',{exact:true})).toBeVisible()
})

test('false 200 from a save cannot claim success without a verified on-disk receipt',async({page})=>{
 const writes=await ownerPage(page,{serverAckUnverified:true})
 const editor=page.getByRole('region',{name:'Save this week Survivor picks'})
 await editor.getByRole('combobox',{name:'Choose an unused NFL team'}).selectOption('Houston Texans')
 await editor.getByRole('button',{name:'Add',exact:true}).click()
 await expect(editor.getByText('DRAFT ONLY', {exact:false})).toBeVisible()
 await editor.getByRole('button',{name:'Save picks'}).click()
 await expect(editor).toContainText('Save could not be verified in Zenith')
 await expect(editor).not.toContainText('Saved and verified in Sports Zenith')
 await expect(editor.getByRole('button',{name:'Save picks'})).toBeDisabled()
 expect(writes).toHaveLength(1)
})

test('post receipt with mismatched private GET cannot claim Texans was actually saved',async({page})=>{
 const writes=await ownerPage(page,{simulateReadbackMismatch:true})
 const editor=page.getByRole('region',{name:'Save this week Survivor picks'})
 await editor.getByRole('combobox',{name:'Choose an unused NFL team'}).selectOption('Houston Texans')
 await editor.getByRole('button',{name:'Add',exact:true}).click()
 await editor.getByRole('button',{name:'Save picks'}).click()
 await expect(editor).toContainText('private dashboard did not confirm it')
 await expect(editor).not.toContainText('Saved and verified in Sports Zenith')
 await expect(editor.getByRole('button',{name:'Save picks'})).toBeDisabled()
 expect(writes).toHaveLength(1)
})

test('an eliminated entry is read-only and zero mocked pick writes occur',async({page})=>{
 const writes=await ownerPage(page)
 await page.getByRole('button',{name:'Switch test entry activity'}).click()
 const editor=page.getByRole('region',{name:'Save this week Survivor picks'})
 await expect(page.locator('[data-survivor-cover-status="NOT_ACTIVE"]')).toBeVisible()
 await expect(editor.getByRole('combobox',{name:'Choose an unused NFL team'})).toHaveCount(0)
 await expect(editor.getByRole('button',{name:'Save picks'})).toHaveCount(0)
 await expect(editor.getByText(/Only an active Survivor entry may save picks/)).toBeVisible()
 expect(writes).toHaveLength(0)
})

test('manager-only official pool preview and confirm are separate, never touch a real server',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 const writes=await ownerPage(page,{canManage:true})
 const section=page.getByRole('region',{name:'Import full Survivor pool'})
 await expect(section).toBeVisible()
 await section.locator('summary').click()
 await section.getByRole('button',{name:'Preview pool file'}).isDisabled()
 await section.getByLabel('Choose official pool file').setInputFiles({name:'QA_OFFICIAL.csv',mimeType:'text/csv',buffer:Buffer.from('entry_name,week,team\nSYNTHETIC QA 01,5,Jacksonville Jaguars\n')})
 await section.getByRole('button',{name:'Preview pool file'}).click()
 await expect(section.getByText('Duplicate tickets')).toBeVisible()
 await expect(section.getByText('4',{exact:true}).first()).toBeVisible()
 await expect(section.getByRole('button',{name:'Confirm pool import'})).toBeDisabled()
 expect(writes).toHaveLength(1)
 await section.getByText(/I reviewed the preview and authorize/).click()
 await section.getByRole('button',{name:'Confirm pool import'}).click()
 await expect(section.getByRole('status')).toContainText('Your existing personal entry history was preserved')
 expect(writes.map(item=>item.path)).toEqual(['/api/survivor/pool/preview','/api/survivor/pool/confirm'])
})

test('Knockout Pool PDF is easy to open and preview the exact owner ticket; never auto-imports',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 const writes=await ownerPage(page,{canManage:true})
 const section=page.getByRole('region',{name:'Import full Survivor pool'})
 await expect(section.getByText('Upload weekly PDF')).toBeVisible()
 await expect(section.locator('details')).not.toHaveAttribute('open','')
 await section.locator('summary').click()
 await section.getByLabel('Choose official pool file').setInputFiles({
  name:'QA_WEEK5.pdf',mimeType:'application/pdf',
  buffer:Buffer.from('%PDF-1.4\nSynthetic QA fixture only; backend parsing is tested separately.\n'),
 })
 await expect(section.getByText(/Selected: QA_WEEK5.pdf/)).toBeVisible()
 await section.getByRole('button',{name:'Preview pool file'}).click()
 await expect(section.getByText('Found your entry: SYNTHETIC QA 01')).toBeVisible()
 await expect(section.getByText('Week 5: Houston Texans')).toBeVisible()
 await expect(section).toContainText('1 more same-name ticket')
 await expect(section.getByRole('button',{name:'Confirm pool import'})).toBeDisabled()
 expect(writes.map(r=>r.path)).toEqual(['/api/survivor/pool/preview'])
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
 await section.screenshot({path:'/tmp/zenith_knockout_pdf_owner_preview_390_20261010.png'})
})

test('regular linked owner cannot open manager import',async({page})=>{
 const writes=await ownerPage(page,{canManage:false})
 await expect(page.getByRole('region',{name:'Import full Survivor pool'})).toHaveCount(0)
 expect(writes).toHaveLength(0)
})
