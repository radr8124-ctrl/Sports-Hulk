import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_PREDICTION_URL||'http://127.0.0.1:8510/'
for(const width of [320,390,430]){
 test('Elo benchmark evidence at '+width+'px',async({page})=>{
  await page.setViewportSize({width,height:844})
  await page.goto(BASE+'#prediction-markets',{waitUntil:'domcontentloaded'})
  await expect(page.getByRole('cell',{name:'Elo (scores only)',exact:true})).toBeVisible({timeout:5000})
  await page.getByText('Elo value diagnostic',{exact:true}).click()
  const detail=page.locator('[data-elo-diagnostic]')
  await expect(detail).toContainText('1115 retrospective selections')
  await expect(detail).toContainText('-13.3%')
  await expect(detail).toContainText('hypothetical 2% stake cost')
  await expect(detail).toContainText('not realized exchange ROI')
  await expect(detail).toContainText('Production model unchanged')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 })
}
