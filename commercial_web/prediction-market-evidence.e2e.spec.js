import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_PREDICTION_URL||'http://127.0.0.1:8510/'
for(const width of [320,390,430]) {
 test(`matched NFL evidence at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:844})
  await page.goto(BASE+'#prediction-markets',{waitUntil:'domcontentloaded'})
  await expect(page.getByRole('heading',{name:'Prediction Markets',exact:true})).toBeVisible()
  await expect(page.getByText('NFL contract evidence · Kalshi')).toBeVisible()
  await expect(page.locator('article').first()).toContainText('RESEARCH ONLY')
  await page.getByRole('button',{name:/Polymarket \(/}).click()
  await expect(page.getByText('NFL contract evidence · Polymarket')).toBeVisible()
  await expect(page.locator('article').first()).toContainText('Displayed outcomes:')
  await expect(page.getByText('Postponement terms differ between providers.',{exact:false})).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.getByLabel('Search observed markets').fill('unlikely-team-no-match')
  await expect(page.getByText('No matching observations in this view.')).toBeVisible()
 })
}
