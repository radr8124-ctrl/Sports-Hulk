import { test, expect } from '@playwright/test'
const base = process.env.ZENITH_WORKSPACE_URL || 'http://127.0.0.1:8510/'
async function fits(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
}

for (const width of [320,390,430]) {
  test('DFS shortcut, reload, history and dashboard return at ' + width, async ({ page }) => {
    await page.setViewportSize({ width, height:844 })
    await page.goto(base + '#dashboards')
    await page.getByRole('button',{name:'Build a DFS lineup'}).click()
    await expect(page).toHaveURL(/#fantasy\/dfs$/)
    const dfs = page.getByRole('button',{name:'DFS Lineup Lab',exact:true})
    await expect(dfs).toHaveAttribute('aria-pressed','true')
    await fits(page)
    await page.reload()
    await expect(dfs).toHaveAttribute('aria-pressed','true')
    await page.getByRole('button',{name:'Season-Long',exact:true}).click()
    await expect(page).toHaveURL(/#fantasy$/)
    await expect(dfs).toHaveAttribute('aria-pressed','false')
    await page.goBack()
    await expect(dfs).toHaveAttribute('aria-pressed','true')
    await page.getByRole('navigation',{name:'Mobile primary navigation'}).getByRole('button',{name:'Fantasy',exact:true}).click()
    await expect(dfs).toHaveAttribute('aria-pressed','false')
    await page.getByRole('navigation',{name:'Dashboard workspace'}).getByRole('button',{name:'All dashboards'}).click()
    await expect(page.getByRole('heading',{name:'Choose your dashboard.'})).toBeVisible()
    await page.getByRole('button',{name:'Explore player props'}).click()
    await expect(page).toHaveURL(/#props$/)
    await fits(page)
  })
}

test('betting jump controls preserve the route and move keyboard focus', async ({ page }) => {
  await page.setViewportSize({width:390,height:844})
  await page.goto(base + '#best-bets')
  const jump = page.getByRole('navigation',{name:'Betting dashboard sections'})
  await jump.getByRole('button',{name:'Research watchlist',exact:true}).click()
  await expect(page.locator('#bet-watchlist')).toBeFocused()
  await expect(page).toHaveURL(/#best-bets$/)
  await jump.getByRole('button',{name:'Compare prices',exact:true}).click()
  await expect(page.locator('#bet-prices')).toBeFocused()
  await fits(page)
})

test('every primary research dashboard has a working return to the hub', async ({ page }) => {
  for (const hash of ['scores','best-bets','fantasy','survivor','prediction-markets','brain-record']) {
    await page.goto(base + '#' + hash)
    const toolbar = page.getByRole('navigation',{name:'Dashboard workspace'})
    await expect(toolbar).toBeVisible()
    await toolbar.getByRole('button',{name:'All dashboards'}).click()
    await expect(page).toHaveURL(/#dashboards$/)
  }
})
