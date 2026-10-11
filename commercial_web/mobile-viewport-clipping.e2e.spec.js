import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_MOBILE_CLIP_URL||'http://127.0.0.1:8510/'
for (const width of [320, 360, 390, 430]) {
test(`mobile page keeps its roots stationary and carousels scrollable at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:844})
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 await page.locator('.zenith-signal-rail').waitFor()
 await page.locator('[data-scorecard-scroll]').waitFor()
 const rect=await page.evaluate(()=>{
  const rail=document.querySelector('.zenith-signal-rail')
  const deck=document.querySelector('[data-scorecard-scroll]')
  const nav=document.querySelector('[aria-label="Mobile primary navigation"]')
  const root=document.getElementById('root')
  for(const parent of [document.documentElement,document.body,root])parent.scrollLeft=135
  const x=[document.documentElement.scrollLeft,document.body.scrollLeft,root.scrollLeft]
  rail.scrollLeft=175
  const signalMoved=rail.scrollLeft>0
  if(deck)deck.scrollLeft=deck.scrollWidth
  return {rootScroll:x,signalMoved,deckMoved:deck&&deck.scrollWidth>deck.clientWidth+3?deck.scrollLeft>0:true,overflowX:getComputedStyle(document.documentElement).overflowX,
   pageWidth:document.documentElement.scrollWidth,viewport:window.innerWidth,navLeft:nav.getBoundingClientRect().left,navRight:nav.getBoundingClientRect().right}
 })
 expect(rect.overflowX).toBe('clip')
 expect(rect.rootScroll).toEqual([0,0,0])
 expect(rect.signalMoved).toBe(true)
 const deck=page.locator('[data-scorecard-scroll]')
 if(await deck.count()) {
  const scrollable=await deck.evaluate(el=>el.scrollWidth>el.clientWidth+3)
  if(scrollable) await deck.evaluate(el=>{el.scrollLeft=el.scrollWidth})
  if(scrollable) await expect.poll(()=>deck.evaluate(el=>el.scrollLeft)).toBeGreaterThan(0)
 }
 const vertical=await page.evaluate(()=>{ window.scrollTo(0,350); return window.scrollY })
 expect(vertical).toBeGreaterThan(0)
 // Actual source feeds may show one score tile; independent scorecard tests cover multi-game swipes.
 expect(rect.pageWidth).toBeLessThanOrEqual(rect.viewport+1)
 expect(rect.navLeft).toBe(0)
 expect(rect.navRight).toBe(width)
})
}
