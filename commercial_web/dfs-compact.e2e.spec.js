import {test,expect} from '@playwright/test'
const base=process.env.ZENITH_DFS_COMPACT_URL || 'http://127.0.0.1:8510/'
async function pool(page) {
  await page.route('**/ask_context.json*',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
    generated_at:new Date().toISOString(),
    datasets:{dfs:['DRAFTKINGS','FANDUEL'].map(platform=>({sport:'NFL',platform,player:'UI Test Quarterback',position:'QB',salary:6000,projected_fantasy_points:20,availability_status:'ACTIVE'}))}
  })}))
}
for(const width of [320,390,430,820]) {
  test('DFS platform controls fit above mobile navigation at '+width,async({page})=>{
    await page.setViewportSize({width,height:844})
    await pool(page)
    await page.goto(base+'#fantasy/dfs')
    await expect(page.getByRole('heading',{name:'Fantasy · DFS'})).toBeVisible()
    const platform=page.getByRole('button',{name:'DraftKings',exact:true})
    await expect(platform).toBeVisible()
    const bounds=await platform.boundingBox()
    const nav=await page.getByRole('navigation',{name:'Mobile primary navigation'}).boundingBox()
    expect(bounds.y+bounds.height).toBeLessThan(nav.y)
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
    await expect(platform).toHaveAttribute('aria-pressed','true')
    await page.getByRole('button',{name:'FanDuel',exact:true}).click()
    await expect(platform).toHaveAttribute('aria-pressed','false')
    await expect(page.getByRole('button',{name:'FanDuel',exact:true})).toHaveAttribute('aria-pressed','true')
  })
}
test('build precedes optional customization and retains platform, mode and ownership guards',async({page})=>{
  await page.setViewportSize({width:390,height:844})
  await pool(page)
  let request
  await page.route('**/api/dfs/optimize',route=>{
    request=route.request().postDataJSON()
    return route.fulfill({status:422,contentType:'application/json',body:JSON.stringify({status:'ERROR',error:'Test player pool cannot form a legal lineup.'})})
  })
  await page.goto(base+'#fantasy/dfs')
  await page.getByRole('button',{name:'FanDuel',exact:true}).click()
  const cash=page.getByRole('button',{name:/^Cash Safe/})
  await cash.click()
  await expect(cash).toHaveAttribute('aria-pressed','true')
  await expect(page.getByRole('button',{name:/^Contrarian Leverage|^Contrarian/})).toBeDisabled()
  const build=page.getByRole('button',{name:'BUILD BEST LINEUP',exact:true})
  const customize=page.getByRole('button',{name:/Customize players/})
  const buildPosition=await build.boundingBox(), optionalPosition=await customize.boundingBox()
  expect(buildPosition.y).toBeLessThan(optionalPosition.y)
  await build.click()
  await expect(page.getByText('Test player pool cannot form a legal lineup.',{exact:true})).toBeVisible()
  expect(request).toEqual({platform:'FANDUEL',mode:'CASH_SAFE',locked_keys:[],excluded_keys:[],alternatives:4})
})
