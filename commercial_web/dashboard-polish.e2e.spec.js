import { test, expect } from '@playwright/test'
const base=process.env.ZENITH_POLISH_URL || 'http://127.0.0.1:8510/'

for (const width of [320,390,430,820,1280]) {
  test('Ref access avoids mobile overlap and keeps page context at '+width,async({page})=>{
    await page.setViewportSize({width,height:900})
    await page.goto(base+'#best-bets')
    const launcher=page.getByRole('button',{name:'Open the Ref sports assistant'})
    if(width<1024) await expect(launcher).toBeHidden()
    else await expect(launcher).toBeVisible()
    await page.getByRole('navigation',{name:'Dashboard workspace'}).getByRole('button',{name:'Ask The Ref'}).click()
    const dialog=page.getByRole('dialog',{name:'Ask the Ref on this page'})
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Reviewing: Best Bets')).toBeVisible()
    await expect(page).toHaveURL(/#best-bets$/)
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
    await dialog.getByRole('button',{name:'Close the Ref chat'}).click()
    await expect(dialog).toBeHidden()
  })
}

test('DFS builder appears before expandable strategy record',async({page})=>{
  await page.setViewportSize({width:390,height:844})
  await page.goto(base+'#fantasy/dfs')
  const builder=page.getByRole('heading',{name:'Let the brain build the lineup.'})
  await expect(builder).toBeVisible()
  const proof=page.locator('[data-dfs-proof]')
  await expect(proof).not.toHaveAttribute('open','')
  await expect(page.getByText('Projection + correlation',{exact:true})).toBeHidden()
  expect(await builder.evaluate(el=>!!(el.compareDocumentPosition(document.querySelector('[data-dfs-proof]'))&Node.DOCUMENT_POSITION_FOLLOWING))).toBe(true)
  await proof.locator('summary').click()
  await expect(page.getByText('Projection + correlation',{exact:true})).toBeVisible()
  await expect(proof.getByText('Ownership required',{exact:true})).toBeVisible()
  await page.screenshot({path:'/tmp/zenith-dfs-polish.png'})
})

test('fantasy proof stays available without expanding before player research',async({page})=>{
  await page.goto(base+'#fantasy')
  await page.getByRole('button',{name:'Start / Sit',exact:true}).click()
  const proof=page.locator('[data-fantasy-proof]')
  await expect(proof.locator('summary')).toBeVisible()
  await expect(page.getByRole('heading',{name:'Five fantasy lanes are being tested'})).toBeHidden()
  await proof.locator('summary').click()
  await expect(page.getByRole('heading',{name:'Five fantasy lanes are being tested'})).toBeVisible()
  await expect(proof.getByText('NO AUTO-PROMOTION')).toBeVisible()
})
