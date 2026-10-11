import {test,expect} from '@playwright/test'
const URL=process.env.ZENITH_ACCOUNT_QA_URL||'http://127.0.0.1:8510/'
for(const width of [320,390,1280])test(`Home account sign-up CTA reuses existing OTP securely at width ${width}`,async({page})=>{
 await page.setViewportSize({width,height:844})
 await page.goto(URL,{waitUntil:'domcontentloaded'})
 const hero=page.getByRole('region',{name:'Sports Zenith game-day command center'})
 const section=hero.locator('[aria-label="Join Sports Zenith"]')
 await expect(section).toBeVisible()
 await expect(section.getByRole('button',{name:'Sign in to Sports Zenith'})).toContainText('Create Account / Sign In')
 await section.getByRole('button',{name:'Sign in to Sports Zenith'}).click()
 await expect(page.getByRole('dialog',{name:/Sign in to continue/})).toBeVisible()
 await expect(page.getByLabel('Email address')).toBeVisible()
 await page.getByRole('button',{name:'Close sign in'}).click()
 await expect(page.getByRole('dialog',{name:/Sign in to continue/})).toHaveCount(0)
 const metrics=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth-innerWidth,scoresTop:document.querySelector('section[aria-label="Game Day scores and schedule"] article')?.getBoundingClientRect().top}))
 expect(metrics.overflow).toBeLessThanOrEqual(1)
 if(width===320)expect(metrics.scoresTop).toBeLessThan(850)
})
