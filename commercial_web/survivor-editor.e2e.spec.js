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

async function ownerPage(page,{canManage=false}={}){
 const writes=[]
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
   response={status:200,body:{status:'SAVED_NOT_SUBMITTED',teams:body.teams,pool_submitted:false}}
  }else if(name==='/api/survivor/pool/preview' && route.request().method()==='POST'){
   const body=route.request().postDataJSON()
   expect(body.filename).toBe('QA_OFFICIAL.csv')
   expect(body.base64.length).toBeGreaterThan(8)
   writes.push({path:name,method:'POST',preview:true})
   response={status:200,body:{status:'PREVIEW_READY',preview_token:'SYNTHETIC_PREVIEW_ONLY',entry_count:4,pick_rows:7,max_week:5,duplicate_ticket_instances:1,examples:[{entry_name:'SYNTHETIC QA 01',pick_count:1}]}}
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
 await expect(editor.getByRole('button',{name:'Add',exact:true})).toBeDisabled()
 await editor.getByRole('button',{name:'Save picks'}).click()
 await expect(editor.getByRole('status')).toContainText('Your external pool has NOT been submitted')
 expect(writes).toHaveLength(1)
 expect(writes[0].body.teams).toEqual(['Jacksonville Jaguars'])
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
 await expect(page.getByRole('region',{name:'My Survivor pick score'}).getByText('SURVIVED',{exact:true})).toBeVisible()
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

test('regular linked owner cannot open manager import',async({page})=>{
 const writes=await ownerPage(page,{canManage:false})
 await expect(page.getByRole('region',{name:'Import full Survivor pool'})).toHaveCount(0)
 expect(writes).toHaveLength(0)
})
