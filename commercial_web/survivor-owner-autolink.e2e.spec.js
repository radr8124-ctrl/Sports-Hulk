import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
const BASE=process.env.ZENITH_AUTO_OWNER_BASE||'http://127.0.0.1:8510/'

test('private Survivor and account summary refuse anonymous users, never reveal preassigned identity',async({request})=>{
 for(const url of ['/api/survivor/state','/api/account/summary']){
  const response=await request.get(new URL(url,BASE).href)
  expect(response.status()).toBe(401)
  const text=await response.text()
  expect(text).not.toContain('ANNIE G 01')
  expect(text).not.toContain('owner_entitlements')
  expect(text).not.toContain('email_sha256')
 }
 const response=await request.post(new URL('/api/survivor/link-entry',BASE).href,{
  data:{entry_name:'ANNIE G 01',claim_code:'MADE-UP-CODE'},
 })
 expect(response.status()).toBe(401)
 expect((await response.text()).includes('ANNIE G 01')).toBe(false)
})

test('sign-in experience never shows a public claim code or user pool data',async({page})=>{
 for(const width of [320,390,430,768]){
  await page.setViewportSize({width,height:844})
  const response=await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
  if(response)expect(response.status()).toBe(200)
  const region=page.getByRole('region',{name:'Survivor review access shortcut'})
  await expect(region.getByText('Sign in to see your entry',{exact:true})).toBeVisible()
  await expect(page.locator('#survivor-link-entry')).toHaveCount(0)
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
 }
})

test('server uses provider-verified account ID/email rather than a client-supplied claim to provision an entry',()=>{
 const root=new URL('./',import.meta.url)
 const server=readFileSync(new URL('./server.js',root),'utf8')
 const app=readFileSync(new URL('./src/App.jsx',root),'utf8')
 const domain=server.slice(server.indexOf('async function ensureVerifiedSurvivorOwner('),server.indexOf('async function linkedSurvivorEntries('))
 expect(domain).toContain('user.emailVerified!==true')
 expect(domain).toContain('secureAutoLinkReservedEntry')
 expect(domain).toContain('survivorOwnerAdminStore()')
 expect(domain).toContain('survivorEntryOwnedByOther')
 expect(domain).not.toContain('url.searchParams')
 expect(domain).not.toContain('body.claim_code')
 expect(server.slice(server.indexOf("url.pathname==='/api/account/summary'"),server.indexOf("url.pathname==='/api/fantasy/providers'"))).toContain('ensureVerifiedSurvivorOwner(user)')
 expect(server.slice(server.indexOf("url.pathname==='/api/survivor/state'"),server.indexOf("url.pathname==='/api/survivor/state'")+1300)).toContain('ensureVerifiedSurvivorOwner(user)')
 expect(server.slice(server.indexOf("url.pathname==='/api/survivor/link-entry'"),server.indexOf("url.pathname==='/api/survivor/pool-manager'"))).toContain('isReservedForDifferentAccount(entryName,user,ownerMap)')
 expect(app).toContain('appear automatically without a name or claim code')
 expect(app).toContain('<details id="survivor-link-entry"')
 expect(app).not.toContain("'Your passwordless account is authenticated. Use the exact entry name and one-time claim code")
})
