import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_PREDICTION_URL||'http://127.0.0.1:8510/'
for(const width of [320,390,430]){
 test('cross-market scan with expanded evidence at '+width+'px',async({page})=>{
  await page.setViewportSize({width,height:844})
  await page.goto(BASE+'#prediction-markets',{waitUntil:'domcontentloaded'})
  const card=page.locator('[data-cross-market-scan]')
  await expect(card.getByRole('heading',{name:'Cross-market price scanner · NFL'})).toBeVisible()
  await expect(card).toContainText('No orders or paper fills created.')
  await expect(page.locator('[data-prediction-clv]')).toContainText('0 verified entries')
  await expect(page.locator('[data-prediction-clv]')).toContainText('Cost-adjusted CLV: not measured')
  await expect(page.locator('[data-prediction-clv]')).toContainText('positive CLV alone does not prove profitable ROI')
  await card.locator('summary').click()
  await expect(card).toContainText('Conditional net profit:')
  await expect(card).toContainText('settlement rules not equivalent')
  await expect(card).toContainText('no positive net gap')
  await expect(card).toContainText('0 positive after documented fees.')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 })
}
