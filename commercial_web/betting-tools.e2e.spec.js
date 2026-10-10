import {test,expect} from '@playwright/test'

const pageUrl='http://127.0.0.1:8510/#tools'
const tools=p=>p.getByRole('region',{name:'Zenith betting math tools'})
const calc=p=>p.getByRole('region',{name:'Calculation result'})
const select=p=>p.getByRole('group',{name:'Choose betting calculation'})

async function open(page,width=390) {
 await page.setViewportSize({width,height:844})
 await page.goto(pageUrl,{waitUntil:'domcontentloaded'})
 await expect(tools(page).getByRole('heading',{name:'Know the price. See the math.'})).toBeVisible()
}

test('iPhone tools tab loads directly, shows priced example, no horizontal page movement',async({page})=>{
 await open(page)
 await expect(calc(page).getByText('52.38%')).toBeVisible()
 await expect(calc(page).getByText('$9.09')).toBeVisible()
 await expect(calc(page).getByText('10/11')).toBeVisible()
 await expect(tools(page).getByText('No bets placed')).toBeVisible()
 const screen=await page.evaluate(()=>({
  y:scrollY,overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
 }))
 expect(screen.y).toBeLessThanOrEqual(2)
 expect(screen.overflow).toBeLessThanOrEqual(1)
})

test('Converter formats can be switched, and manual stake changes the example payout',async({page})=>{
 await open(page)
 await page.getByRole('combobox',{name:'Input odds format'}).selectOption('fractional')
 await page.getByRole('textbox',{name:'Quoted odds'}).fill('5/2')
 await page.getByRole('spinbutton',{name:'Example stake ($)'}).fill('100')
 await expect(calc(page).getByText('3.5000')).toBeVisible()
 await expect(calc(page).getByText('28.57%')).toBeVisible()
 await expect(calc(page).getByText('$250.00')).toBeVisible()
 await expect(calc(page).getByText('$350.00')).toBeVisible()
 await page.getByRole('combobox',{name:'Input odds format'}).selectOption('probability')
 await page.getByRole('textbox',{name:'Quoted odds'}).fill('40')
 await expect(calc(page).getByText('2.5000')).toBeVisible()
 await expect(calc(page).getByText('+150')).toBeVisible()
})

test('Hold-vig tool computes book margin and no-vig prices for exact opposing outcomes',async({page})=>{
 await open(page)
 await select(page).getByRole('button',{name:'Hold & no-vig'}).click()
 await expect(calc(page).getByText('4.76%',{exact:true})).toBeVisible()
 await expect(calc(page).getByText('50.00%')).toHaveCount(2)
 await expect(calc(page).getByText('Fair odds +100')).toHaveCount(2)
 await tools(page).getByRole('button',{name:'-200 / +170'}).click()
 await expect(calc(page).getByText('3.70%',{exact:true})).toBeVisible()
 await expect(calc(page).getByText(/market estimates, not proven true probabilities/i)).toBeVisible()
})

test('EV-Kelly results show honest manual model disclaimer and never create a suggested stake',async({page})=>{
 await open(page)
 await select(page).getByRole('button',{name:'EV & Kelly'}).click()
 await expect(calc(page).getByText('5.00%',{exact:true})).toBeVisible()
 await expect(calc(page).getByText('5.50%')).toBeVisible()
 await expect(calc(page).getByText('$13.75')).toBeVisible()
 await expect(calc(page).getByText(/Actual recommended exposure remains 0 units/)).toBeVisible()
 await page.getByRole('spinbutton',{name:'Your independent probability (%)'}).fill('50')
 await expect(calc(page).getByText('$0.00')).toBeVisible()
 const text=await calc(page).innerText()
 expect(text).toContain('-4.55%')
 expect(text).not.toContain('Approved PLAY')
})

test('Hedge scenario shows actual net both outcomes and warns if theoretical hedge loses',async({page})=>{
 await open(page)
 await select(page).getByRole('button',{name:'Hedge'}).click()
 await expect(calc(page).getByText('$180.00')).toBeVisible()
 await expect(calc(page).getByText('$20.00')).toHaveCount(2)
 await page.getByRole('textbox',{name:'Original American odds'}).fill('-110')
 await page.getByRole('textbox',{name:'Opposing American odds'}).fill('-110')
 await expect(calc(page).getByText('$100.00')).toBeVisible()
 await expect(calc(page).getByText(/locked-in loss/)).toBeVisible()
 await expect(calc(page).getByText(/No hedge has been placed/)).toBeVisible()
})

test('Parlay illustration supports mixed American, decimal and fractional leg formats but recommends nothing',async({page})=>{
 await open(page)
 await select(page).getByRole('button',{name:'Parlay payout'}).click()
 await expect(calc(page).getByText('$36.45')).toBeVisible()
 await expect(calc(page).getByText('$26.45')).toBeVisible()
 await expect(calc(page).getByText(/No parlay is recommended or generated/)).toBeVisible()
 await page.getByRole('combobox',{name:'Leg 2 format'}).selectOption('decimal')
 await page.getByRole('textbox',{name:'Leg 2 odds'}).fill('1.91')
 await page.getByRole('button',{name:'Add another example leg'}).click()
 await page.getByRole('combobox',{name:'Leg 3 format'}).selectOption('fractional')
 await page.getByRole('textbox',{name:'Leg 3 odds'}).fill('5/2')
 await expect(calc(page).getByText('3',{exact:true})).toBeVisible()
 await expect(calc(page).getByText(/\$127\.6/)).toBeVisible()
 await page.getByRole('button',{name:'Remove leg 3'}).click()
 await expect(page.getByRole('textbox',{name:'Leg 3 odds'})).toHaveCount(0)
 await page.getByRole('textbox',{name:'Leg 1 odds'}).fill('5')
 await expect(calc(page).getByRole('alert')).toBeVisible()
 await expect(calc(page).getByText(/American odds must be a whole price/)).toBeVisible()
})

test('Tools reachable from current Bets nav and desktop retains clean width',async({page})=>{
 await page.setViewportSize({width:1280,height:820})
 await page.goto('http://127.0.0.1:8510/#best-bets',{waitUntil:'domcontentloaded'})
 await page.getByRole('button',{name:'Tools',exact:true}).click()
 await expect(page).toHaveURL(/#tools/)
 await expect(tools(page).getByRole('heading',{name:'Know the price. See the math.'})).toBeVisible()
 const w=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
 expect(w).toBeLessThanOrEqual(1)
})
