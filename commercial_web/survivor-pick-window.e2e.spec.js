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
async function openSynthetic(page,width=390){
 const writes=[]
 await page.setViewportSize({width,height:844})
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url())
  expect(url.origin).toBe(new URL(local).origin)
  if(url.pathname==='/api/survivor/save-picks')writes.push(route.request().postDataJSON())
  const res=url.pathname==='/api/survivor/pool-manager'?{status:200,can_manage:false}:{status:401,message:'TEST_LOCAL_API_DENIED'}
  await route.fulfill({status:url.pathname==='/api/survivor/pool-manager'?200:401,contentType:'application/json',body:JSON.stringify(res)})
 })
 const response=await page.goto(local,{waitUntil:'domcontentloaded'})
 expect(response.status()).toBe(200)
 return writes
}

test('real owner-alive record with a passed verified deadline cannot offer an unsaved team',async({page})=>{
 const writes=await openSynthetic(page)
 const editor=page.getByRole('region',{name:'Save this week Survivor picks'})
 await expect(editor.getByRole('combobox',{name:'Choose an unused NFL team'})).toBeVisible()
 await page.getByRole('button',{name:'Toggle synthetic pool deadline'}).click()
 await expect(editor.getByText('DEADLINE PASSED',{exact:true})).toBeVisible()
 await expect(editor.locator('[data-survivor-pick-lock]')).toContainText('This entry is read-only')
 await expect(editor.getByRole('combobox',{name:'Choose an unused NFL team'})).toHaveCount(0)
 await expect(editor.getByRole('button',{name:'Save picks'})).toHaveCount(0)
 await expect(editor.getByRole('button',{name:'Add',exact:true})).toHaveCount(0)
 await editor.screenshot({path:'/tmp/zenith_survivor_closed_editor_390_20261010.png'})
 await expect(page.getByRole('region',{name:'My Survivor past picks'}).locator('[data-past-pick]')).toHaveCount(5)
 expect(writes).toHaveLength(0)
})

test('verified schedule limits pick options; burned teams and other-week matchups absent',async({page})=>{
 const writes=await openSynthetic(page)
 const editor=page.getByRole('region',{name:'Save this week Survivor picks'})
 const pick=editor.getByRole('combobox',{name:'Choose an unused NFL team'})
 const available=await pick.locator('option').allTextContents()
 assertNoUnverified(available)
 expect(available).toContain('Jacksonville Jaguars')
 expect(available).toContain('Houston Texans')
 expect(available).toContain('Cincinnati Bengals')
 expect(available).not.toContain('Los Angeles Chargers')
 expect(available).not.toContain('Buffalo Bills')
 expect(available).not.toContain('Seattle Seahawks')
 expect(writes).toHaveLength(0)
})
const assertNoUnverified=entries=>expect(entries).toEqual([
 'Choose an unused team','Cincinnati Bengals','Houston Texans','Jacksonville Jaguars',
])

test('a closed synthetic pool still shows older scores and zero current picks at 320px iPhone',async({page})=>{
 const writes=await openSynthetic(page,320)
 await page.getByRole('button',{name:'Toggle synthetic pool deadline'}).click()
 const editor=page.getByRole('region',{name:'Save this week Survivor picks'})
 await expect(editor.getByText('0 / 1 pick(s)')).toBeVisible()
 await expect(editor.locator('[data-survivor-pick-lock]')).toBeVisible()
 const history=page.getByRole('region',{name:'My Survivor past picks'})
 await expect(history).toContainText('Week 5: No pick saved in Zenith')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
 expect(writes).toHaveLength(0)
})

test('anonymous production Survivor never exposes the private window, picks, or saved team history',async({request,page})=>{
 const response=await request.get('https://sportszenith.com/api/survivor/state')
 expect(response.status()).toBe(401)
 expect((await response.text()).includes('editable_team_cutoffs')).toBe(false)
 await page.goto('https://sportszenith.com/#survivor',{waitUntil:'domcontentloaded'})
 await expect(page.getByRole('region',{name:'Save this week Survivor picks'})).toHaveCount(0)
 await expect(page.getByRole('region',{name:'My Survivor past picks'})).toHaveCount(0)
 expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
})
