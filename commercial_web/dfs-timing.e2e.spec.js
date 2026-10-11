import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
const base=process.env.ZENITH_DFS_TIMING_URL || 'http://127.0.0.1:8510/'
const receipt=JSON.parse(readFileSync(new URL('../reports/SPORTS_ZENITH_DFS_BUILD_VALIDATION_20261011.json',import.meta.url),'utf8'))
const saved=receipt.builds.find(row=>row.platform==='DRAFTKINGS').response
for(const [width,status,message] of [
  [320,'GAME_TIMES_UNVERIFIED','Game times are missing or unverified'],
  [390,'SLATE_STARTED','This slate had already started'],
  [430,'PREGAME_TIMES_OBSERVED','Contest entry availability and late-swap rules are not verified'],
]) {
  test('paper result states timing accurately at '+width,async({page})=>{
    await page.setViewportSize({width,height:844})
    await page.route('**/ask_context.json*',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({datasets:{dfs:[{sport:'NFL',platform:'DRAFTKINGS',player:'UI Test',salary:6000,projected_fantasy_points:20}]}})}))
    await page.route('**/api/dfs/optimize',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...saved,timing_evidence:{...saved.timing_evidence,status}})}))
    await page.goto(base+'#fantasy/dfs')
    await page.getByRole('button',{name:'BUILD BEST LINEUP',exact:true}).click()
    await expect(page.getByRole('heading',{name:'Best Overall lineup',exact:true})).toBeVisible()
    await expect(page.locator('[data-dfs-timing]')).toContainText(message)
    await expect(page.getByText('PAPER BUILD · DRAFTKINGS',{exact:true})).toBeVisible()
    await expect(page.getByText('LEGAL BUILD · DRAFTKINGS',{exact:true})).toHaveCount(0)
    await expect(page.locator('[data-dfs-timing]')).toContainText('Timing checked')
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  })
}
