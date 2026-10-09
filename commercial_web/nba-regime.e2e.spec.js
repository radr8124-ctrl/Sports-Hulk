import { test, expect } from '@playwright/test'

const makeRow = (id, player, competition_regime) => ({
  lane: 'PROP', sport: 'NBA', event_id: `nba-${id}`, game_key: `2099-10-20|BOS|DET`,
  player, player_key: player.toLowerCase().replaceAll(' ', ''),
  competition_regime, competition_regime_source: competition_regime === 'UNKNOWN' ? '' : 'ESPN_SITE_SCOREBOARD_EXACT_GAME',
  market_subtype: 'PLAYER_TOTAL_POINTS', side: 'OVER', line: 20.5,
  american_odds: -110, data_quality_grade: 'B', data_quality_book_count: 2,
  shadow_decision: 'PASS_INSUFFICIENT_HISTORY',
  market_reference_probability_pct: 52.38, v2_probability_pct: 52.38,
  conservative_probability_pct: 42.38, conservative_edge_pct_points: -10,
})

async function openNbaResearch(page) {
  await page.route('**/prop_v2_current.json*', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({summary:{candidates:3,shadow_plays:0,shadow_monitors:0,passes:3},picks:[
      makeRow('1','Preseason Player','PRESEASON'),
      makeRow('2','Regular Player','REGULAR'),
      makeRow('3','Unknown Player','UNKNOWN'),
    ]}),
  }))
  await page.goto('http://127.0.0.1:8510/#props', {waitUntil:'domcontentloaded'})
  await page.getByRole('button', {name:'NBA', exact:true}).last().click()
  await expect(page.getByText(/NBA competition source:/)).toBeVisible()
}

test('NBA prop phase filters keep preseason separate on desktop', async ({page}) => {
  await openNbaResearch(page)
  await expect(page.getByText('Preseason Player',{exact:true})).toBeVisible()
  await expect(page.getByText('Regular Player',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Preseason',exact:true}).click()
  await expect(page.getByText('Preseason Player',{exact:true})).toBeVisible()
  await expect(page.getByText('Regular Player',{exact:true})).toHaveCount(0)
  await page.getByRole('button',{name:'Regular season',exact:true}).click()
  await expect(page.getByText('Regular Player',{exact:true})).toBeVisible()
  await expect(page.getByText('Preseason Player',{exact:true})).toHaveCount(0)
  await page.getByRole('button',{name:'Unverified',exact:true}).click()
  await expect(page.getByText('Unknown Player',{exact:true})).toBeVisible()
  await expect(page.getByText('Regular Player',{exact:true})).toHaveCount(0)
})

test('NBA competition controls remain accessible within phone width', async ({page}) => {
  await page.setViewportSize({width:390,height:844})
  await openNbaResearch(page)
  await page.getByRole('button',{name:'Preseason',exact:true}).click()
  await expect(page.getByText('Preseason Player',{exact:true})).toBeVisible()
  const dims=await page.evaluate(() => ({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}))
  expect(dims.scroll).toBeLessThanOrEqual(dims.client+1)
})
