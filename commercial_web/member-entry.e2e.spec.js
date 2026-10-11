import { test, expect } from '@playwright/test'

const base = process.env.ZENITH_ENTRY_URL || 'http://127.0.0.1:8510/'
const fits = async page => expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth)).toBe(true)

for (const width of [320, 390, 430, 1440]) {
  test('entry and dashboards fit at ' + width, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(base + '#signin')
    await expect(page.getByRole('heading', { name: 'Sign in to continue' })).toBeVisible()
    await expect(page.getByRole('navigation', { name: 'Mobile primary navigation' })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: /Know the game/ })).toBeVisible()
    await expect(page.getByText(/profitability is still being validated/)).toBeVisible()
    await fits(page)
    await page.getByRole('button', { name: 'Explore the dashboards' }).click()
    await expect(page).toHaveURL(/#dashboards$/)
    await expect(page.getByRole('heading', { name: 'Choose your dashboard.' })).toBeVisible()
    await expect(page.locator('.member-dashboard-card')).toHaveCount(6)
    await fits(page)
    await page.getByRole('button', { name: 'Compare markets' }).click()
    await expect(page).toHaveURL(/#prediction-markets$/)
    await expect(page.getByRole('heading', { name: 'Prediction Markets', exact: true })).toBeVisible()
    await page.goBack()
    await expect(page.getByRole('heading', { name: 'Choose your dashboard.' })).toBeVisible()
  })
}

test('standalone sign in handles email, bad code, resend and back without sending email', async ({ page }) => {
  let sent = 0
  await page.route('**/api/auth/email/send-otp', route => {
    sent++
    return route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify({ success:true }) })
  })
  await page.route('**/api/auth/sessions', route => route.fulfill({ status:400, contentType:'application/json', body:JSON.stringify({ error:'INVALID_OTP', message:'That code has expired. Request another code.' }) }))
  await page.goto(base + '#signin')
  await page.getByLabel('Email address').fill('browser-test@example.com')
  await page.getByRole('button', { name:'Continue', exact:true }).click()
  await expect(page.getByRole('heading', { name:'Check your email' })).toBeVisible()
  expect(sent).toBe(1)
  await page.getByLabel('Verification code').fill('12abc3456')
  await expect(page.getByLabel('Verification code')).toHaveValue('123456')
  await page.getByRole('button', { name:'Verify & continue' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await page.getByRole('button', { name:'Send a new code' }).click()
  expect(sent).toBe(2)
  await expect(page.getByLabel('Verification code')).toHaveValue('')
  await page.getByRole('button', { name:'Back', exact:true }).click()
  await expect(page.getByLabel('Email address')).toHaveValue('browser-test@example.com')
  await page.screenshot({ path:'/tmp/zenith-entry-desktop.png', fullPage:true })
})

test('homepage still fits and opens public introduction', async ({ page }) => {
  await page.setViewportSize({ width:390, height:844 })
  await page.goto(base)
  await fits(page)
  await page.getByRole('button', { name:'Meet Sports Zenith' }).click()
  await expect(page).toHaveURL(/#signin$/)
  await expect(page.getByLabel('Email address')).toBeVisible()
  await page.screenshot({ path:'/tmp/zenith-entry-mobile.png', fullPage:true })
})


test('verified sign in opens member dashboards with a simulated provider session', async ({ page }) => {
  const user = { id:'entry-browser-test', email:'browser-test@example.com', profile:{name:'Test Member'} }
  const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url')
  const accessToken = encode({alg:'none',typ:'JWT'}) + '.' + encode({sub:user.id,exp:Math.floor(Date.now()/1000)+3600}) + '.test'
  await page.route('**/api/auth/refresh', route => route.fulfill({status:401,contentType:'application/json',body:JSON.stringify({message:'No test session'})}))
  await page.route('**/api/auth/email/send-otp', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({success:true})}))
  await page.route('**/api/auth/sessions', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({user,accessToken})}))
  await page.route('**/api/account/**', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({})}))
  await page.goto(base + '#signin')
  await page.getByLabel('Email address').fill(user.email)
  await page.getByRole('button',{name:'Continue',exact:true}).click()
  await page.getByLabel('Verification code').fill('123456')
  await page.getByRole('button',{name:'Verify & continue'}).click()
  await expect(page).toHaveURL(/#dashboards$/)
  await expect(page.getByRole('heading',{name:'Welcome back. Make your next call.'})).toBeVisible()
  await expect(page.getByRole('button',{name:'Sign in / create account'})).toHaveCount(0)
})
