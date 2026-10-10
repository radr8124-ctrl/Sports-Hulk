import {test,expect} from '@playwright/test'

const URL='http://127.0.0.1:8510/'
async function homepage(page,width=390){
 await page.setViewportSize({width,height:844})
 await page.goto(URL,{waitUntil:'domcontentloaded'})
 await expect(page.getByRole('region',{name:'Home decision overview'})).toBeVisible()
}

test('entire Home uses navy surfaces: decisions, news, Fantasy, Survivor, Brain and learning',async({page})=>{
 await homepage(page)
 const state=await page.evaluate(()=>{
  const computed=selector=>{
   const e=document.querySelector(selector)
   if(!e)throw new Error('Missing actual Home section: '+selector)
   const style=getComputedStyle(e)
   return {background:style.backgroundColor,gradient:style.backgroundImage,
    text:style.color}
  }
  return {
   page:computed('#root > div'),
   html:computed('html'),
   firstDecision:computed('section[aria-label="Home decision overview"] button.min-w-\\[270px\\]'),
   heading:computed('section[aria-label="Home decision overview"] h2'),
   news:computed(document.querySelector('section[aria-label="Home sports news"] > div:nth-child(2) button')
    ?'section[aria-label="Home sports news"] > div:nth-child(2) button'
    :'section[aria-label="Home sports news"] > div:nth-child(2)'),
   newsHeading:computed('section[aria-label="Home sports news"] h2'),
   survivor:computed('section[aria-label="Home Fantasy Survivor and Brain Record"] button:first-child'),
   fantasy:computed('section[aria-label="Home Fantasy Survivor and Brain Record"] button:nth-child(2)'),
   brain:computed('section[aria-label="Home Fantasy Survivor and Brain Record"] button:nth-child(3)'),
   learning:computed('section[aria-label="Home learning loop"] > div:last-child'),
   footer:computed('footer'),
   overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
  }
 })
 expect(state.page.background).toBe('rgb(6, 21, 37)')
 expect(state.html.background).toBe('rgb(6, 21, 37)')
 expect(state.footer.background).toBe('rgb(7, 27, 47)')
 for(const key of ['firstDecision','survivor','fantasy','brain','learning']){
  expect(state[key].gradient,key+' gradient').toContain('gradient(')
  expect(state[key].text,key+' readable foreground').toBe('rgb(255, 255, 255)')
 }
 expect(state.news.gradient.includes('gradient(')||state.news.background==='rgb(14, 39, 64)').toBe(true)
 expect(['rgb(255, 255, 255)','rgb(203, 213, 225)']).toContain(state.news.text)
 expect(state.heading.text).toBe('rgb(255, 255, 255)')
 expect(state.newsHeading.text).toBe('rgb(255, 255, 255)')
 expect(state.overflow).toBeLessThanOrEqual(1)
})

test('all Home decision cards and news remain functional and visibly dark on desktop',async({page})=>{
 await homepage(page,1280)
 const overview=page.getByRole('region',{name:'Home decision overview'})
 const actions=overview.locator('button.min-w-\\[270px\\]')
 await expect(actions).toHaveCount(5)
 await expect(actions.filter({hasText:'Best Bets'})).toBeVisible()
 const news=page.getByRole('region',{name:'Home sports news'})
 await expect(news.getByRole('heading',{name:'What changed that could matter'})).toBeVisible()
 const cards=news.locator('button.min-w-\\[285px\\]')
 if(await cards.count()>0){
  const textColors=await cards.first().evaluate(e=>({
   background:getComputedStyle(e).backgroundImage,
   color:getComputedStyle(e.querySelector('.line-clamp-3')).color,
  }))
  expect(textColors.background).toContain('gradient(')
  expect(textColors.color).toBe('rgb(255, 255, 255)')
 }
 await overview.getByRole('button',{name:/Best Bets/}).click()
 await expect(page).toHaveURL(/#best-bets/)
 await expect(page.getByRole('heading',{name:'Best Bets',exact:true})).toBeVisible()
 expect(await page.evaluate(()=>getComputedStyle(document.querySelector('#root > div')).backgroundColor))
  .toBe('rgb(241, 245, 250)')
})

test('Survivor/Fantasy and Brain remain readable while original private state stays protected',async({page})=>{
 await homepage(page)
 const personal=page.getByRole('region',{name:'Home Fantasy Survivor and Brain Record'})
 await expect(personal.getByText('Survivor',{exact:true})).toBeVisible()
 await expect(personal.getByText('Fantasy + DFS',{exact:true})).toBeVisible()
 await expect(personal.getByText('Brain Record',{exact:true})).toBeVisible()
 await expect(personal.getByRole('button',{name:/Open Survivor/})).toBeVisible()
 const body=await page.locator('body').innerText()
 expect(body.includes('ANNIE G 01')).toBe(false)
 await personal.getByRole('button',{name:/Open Survivor/}).click()
 await expect(page).toHaveURL(/#survivor/)
 expect(await page.evaluate(()=>getComputedStyle(document.querySelector('#root > div')).backgroundColor))
  .toBe('rgb(241, 245, 250)')
 await expect(page.getByRole('heading',{name:'Survivor',exact:true})).toBeVisible()
})

test('source-health accordion and footer do not return to white in lower Home',async({page})=>{
 await homepage(page)
 const details=page.locator('details').filter({hasText:'Source connections and system status'}).first()
 await details.locator('summary').click()
 await expect(details).toHaveAttribute('open','')
 const style=await details.evaluate(el=>{
  const cards=el.querySelectorAll('div.min-w-\\[185px\\]')
  return {
   details:getComputedStyle(el).backgroundColor,
   cardCount:cards.length,
   cards:[...cards].map(card=>getComputedStyle(card).backgroundColor),
  }
 })
 expect(style.details).toBe('rgb(10, 32, 54)')
 expect(style.cardCount).toBe(4)
 expect(style.cards.every(x=>x==='rgb(16, 40, 64)')).toBe(true)
 await expect(page.getByText(/A green collector is not proof/i)).toBeVisible()
 const footer=await page.locator('footer').evaluate(x=>getComputedStyle(x).backgroundColor)
 expect(footer).toBe('rgb(7, 27, 47)')
})

test('Other routes deliberately retain light evidence reading pages after revisiting Home',async({page})=>{
 await homepage(page,1280)
 for(const [hash,heading] of [['#best-bets','Best Bets'],['#fantasy',null],['#brain-record','How good is the brain?']]){
  await page.goto(URL+hash,{waitUntil:'domcontentloaded'})
  await expect(page.getByRole('main')).toBeVisible()
  if(heading)await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible()
  expect(await page.evaluate(()=>getComputedStyle(document.querySelector('#root > div')).backgroundColor))
   .toBe('rgb(241, 245, 250)')
  expect(await page.evaluate(()=>getComputedStyle(document.documentElement).backgroundColor))
   .toBe('rgb(248, 250, 252)')
 }
})
