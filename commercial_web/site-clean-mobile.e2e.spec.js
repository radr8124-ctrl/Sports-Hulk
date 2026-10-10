import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

const fixture = file => JSON.parse(readFileSync(new URL('./public/' + file, import.meta.url), 'utf8'))
const survivor = fixture('survivor_v2_current.json')
const scores = fixture('nfl_scores.json')
const reference = fixture('nfl_research_book_refs.json')
const friday = Date.parse('2026-10-09T21:50:00Z')
const base = 'http://127.0.0.1:8510/'

async function mobile(page) {
  await page.setViewportSize({ width: 390, height: 844 })
}

function noOverflow(page) {
  return page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
    height: document.body.scrollHeight,
  }))
}

test('Home uses one readable hero with actionable navigation, not a wall of metric tiles', async ({ page }) => {
  await mobile(page)
  await page.goto(base + '#home', { waitUntil: 'domcontentloaded' })
  const hero = page.getByRole('heading', { name: /The game.*The smarter call/s })
  await expect(hero).toBeVisible()
  const dimensions = await noOverflow(page)
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.viewport + 1)
  expect(await hero.evaluate(el => el.getBoundingClientRect().width)).toBeGreaterThan(255)
  const desk=page.getByRole('region',{name:'Sports Zenith game-day command center'})
  await expect(desk.getByRole('button',{name:/Explore Bets/})).toBeVisible()
  await expect(desk.getByRole('button',{name:/Ask The Ref/})).toBeVisible()
  await expect(page.getByRole('region',{name:'Game Day scores and schedule'}).getByRole('heading',{name:'Scores & matchups'})).toBeVisible()
})

test('Survivor first look fits title and top market option on an iPhone, full history stays one tap away', async ({ page }) => {
  await mobile(page)
  await page.addInitScript(clock => { Date.now = () => clock }, friday)
  for (const [name, data] of [
    ['survivor_v2_current.json', survivor],
    ['nfl_scores.json', scores],
    ['nfl_research_book_refs.json', reference],
  ]) {
    await page.route('**/' + name + '*', route => route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify(data),
    }))
  }
  await page.goto(base + '#survivor', { waitUntil: 'domcontentloaded' })
  const review = page.getByRole('region', { name: 'Survivor weekly sportsbook review' })
  await expect(review.getByText(/13 source-matched options/)).toBeVisible()
  const header = page.getByRole('heading', { name: 'Survivor', exact: true })
  await expect(header).toBeVisible()
  expect(await header.evaluate(el => el.getBoundingClientRect().width)).toBeGreaterThan(250)
  const first = review.locator('article').first()
  await expect(first.getByText('Jacksonville Jaguars', { exact: true })).toBeVisible()
  expect(await first.evaluate(el => el.getBoundingClientRect().top + window.scrollY)).toBeLessThan(900)
  const expanded = page.locator('details').filter({
    has: page.getByText('Full Survivor research board', { exact: true }),
  }).first()
  await expect(expanded).toBeVisible()
  expect(await expanded.evaluate(el => el.open)).toBe(false)
  const collapsed = await noOverflow(page)
  expect(collapsed.scroll).toBeLessThanOrEqual(collapsed.viewport + 1)
  expect(collapsed.height).toBeLessThan(4000)
  await expanded.locator('summary').click()
  expect(await expanded.evaluate(el => el.open)).toBe(true)
  await expect(expanded.getByRole('heading', { name: 'Survivor decision board' })).toBeVisible()
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
})

test('Bets shows concise safety status with source explanation on demand', async ({ page }) => {
  await mobile(page)
  await page.goto(base + '#best-bets', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'NFL', exact: true }).first().click()
  const status = page.getByRole('region', { name: 'Best Bets source proof and game intelligence' })
  await expect(status.getByText(/NFL primary market source failed freshness checks/)).toBeVisible()
  await expect(status.getByText('Why this market is blocked')).toBeVisible()
  const details = status.locator('details').filter({ hasText: 'View source verification details' }).first()
  expect(await details.evaluate(el => el.open)).toBe(false)
  await details.locator('summary').click()
  expect(await details.evaluate(el => el.open)).toBe(true)
  await expect(details.getByText(/older prices and point spreads are excluded/i)).toBeVisible()
  const size = await noOverflow(page)
  expect(size.scroll).toBeLessThanOrEqual(size.viewport + 1)
  await expect(page.getByText(/0 verified plays · research only/)).toBeVisible()
})
