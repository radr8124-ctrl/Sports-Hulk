import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'

const report=JSON.parse(readFileSync(new URL('./public/zenith_learning_review.json',import.meta.url),'utf8'))

async function open(page,source=report,width=390){
  await page.setViewportSize({width,height:844})
  await page.route('**/zenith_learning_review.json*',r=>r.fulfill({
    status:200,contentType:'application/json',body:JSON.stringify(source),
  }))
  await page.goto('http://127.0.0.1:8510/#brain-record',{waitUntil:'domcontentloaded'})
  return page.getByRole('region',{name:'How Zenith learns from mistakes'})
}

test('Brain Record preserves 3 rejected error corrections and original bookmaker comparison',async({page})=>{
  const section=await open(page)
  const disclosure=section.getByText('Corrections tested: 3 · rejected: 3',{exact:true})
  await expect(disclosure).toBeVisible()
  await disclosure.click()
  await expect(section.getByText('Original NFL model',{exact:true})).toBeVisible()
  await expect(section.getByText('Use original bookmaker no-vig when either team has fewer than three previous same-season games')).toBeVisible()
  await expect(section.getByText('Use original bookmaker favorite when experimental model reverses it')).toBeVisible()
  await expect(section.getByText('Apply both unverified-market safeguards together')).toBeVisible()
  await expect(section.getByText('REJECTED',{exact:true})).toHaveCount(4)
  await expect(section.getByText(/original bookmaker no-vig/).first()).toBeVisible()
  await expect(section.getByText(/No live weights changed/)).toBeVisible()
  await expect(section.getByText(/2022–2025/)).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
})

test('Learning panel refuses to display forged approved weights or source-less trials',async({page})=>{
  const bad=structuredClone(report)
  bad.error_correction_trial_registry.model_weights_changed=true
  const section=await open(page,bad)
  await expect(section.getByText(/Historical correction evidence is not verified yet/)).toBeVisible()
  await expect(section.getByText(/Corrections tested: 3/)).toHaveCount(0)
})

test('Desktop and mobile sections keep original official learning record intact',async({page})=>{
  const section=await open(page,report,1280)
  await expect(section.getByRole('heading',{name:'How Zenith learns from mistakes'})).toBeVisible()
  await expect(section.getByText('Corrections tested: 3 · rejected: 3',{exact:true})).toBeVisible()
  await expect(section.getByText('Chiefs 30 — Raiders 27')).toBeVisible()
  await expect(page.getByRole('heading',{name:'How good is the brain?'})).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
})
