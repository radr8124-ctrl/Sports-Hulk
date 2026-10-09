import { test, expect } from '@playwright/test'

function fixture(stale = false) {
  const now = Date.now()
  const kickoff = new Date(now + 48 * 3600 * 1000).toISOString()
  const updated = new Date(now - (stale ? 30 : 2) * 3600 * 1000).toISOString()
  const captured = new Date(now - (stale ? 29 : 1.8) * 3600 * 1000).toISOString()
  const common = {
    book: 'fanduel', source_event_id: 'archive-event-1',
    source_updated_at: updated, source_captured_at: captured,
    quote_type: 'TWO_SIDED_ARCHIVED_RESEARCH_SNAPSHOT',
    is_executable_current_offer: false, is_verified_main_line: false,
    is_approved_bet: false,
  }
  return {
    game: {
      event_id: 'espn-source-1', start_time: kickoff,
      away_abbr: 'PHI', home_abbr: 'JAC', state: 'pre', final: false,
    },
    payload: {
      status: 'RESEARCH_ONLY', original_source: 'SPORTWIZZARD_ARCHIVED_SAME_BOOK_TWO_SIDED_RESEARCH',
      book_prices_live_or_executable_verified: false, betting_decision_created: false,
      model_advantage_proven: false, fixtures: [{
        official_espn_event_id: 'espn-source-1', source_event_id: 'archive-event-1',
        official_start: kickoff, approved_play: false, away: 'PHI', home: 'JAX',
        markets: {
          MONEYLINE: {...common, market:'MONEYLINE', line:null, away_price:310, home_price:-390},
          SPREAD: {...common, market:'SPREAD', line:7.5, away_line:7.5, home_line:-7.5, away_price:-110, home_price:-110},
          TOTAL: {...common, market:'TOTAL', line:41.5, over_price:-115, under_price:-105},
        },
      }],
    },
  }
}
async function openMarket(page, stale=false) {
  const {game,payload} = fixture(stale)
  await page.route('**/nfl_scores.json*', route => route.fulfill({
    status:200, contentType:'application/json', body:JSON.stringify({next_games:[game]}),
  }))
  await page.route('**/nfl_research_book_refs.json*', route => route.fulfill({
    status:200, contentType:'application/json', body:JSON.stringify(payload),
  }))
  await page.route('**/betting_v2_all_markets_current.json*', route => route.fulfill({
    status:200, contentType:'application/json', body:JSON.stringify({summary:{candidates:0},picks:[]}),
  }))
  await page.goto('http://127.0.0.1:8510/#best-bets',{waitUntil:'domcontentloaded'})
  await page.getByRole('button',{name:'NFL',exact:true}).first().click()
  await expect(page.getByText(/NFL primary market source failed freshness checks/i)).toBeVisible()
}

test('NFL shows official-fixture matched research quotes but no betting picks', async ({page}) => {
  await openMarket(page)
  await expect(page.getByText(/1 of 1 games with source-matched research quotes/)).toBeVisible()
  await expect(page.getByText('Research quote', {exact:true})).toBeVisible()
  await page.getByText('View dated sportsbook references').click()
  await expect(page.getByText('PHI +310 · JAC -390')).toBeVisible()
  await expect(page.getByText('Over 41.5 (-115) · Under 41.5 (-105)')).toBeVisible()
  await expect(page.getByText(/Neither primary\/main lines nor current executable offers are verified/i)).toBeVisible()
  await expect(page.getByText('0 verified plays · research only')).toBeVisible()
})
test('stale NFL archive quote disappears automatically, remains not recommended', async ({page}) => {
  await openMarket(page,true)
  await expect(page.getByText(/0 of 1 games with source-matched research quotes/)).toBeVisible()
  await expect(page.getByText('Quote unavailable')).toBeVisible()
  await expect(page.getByText('View dated sportsbook references')).toHaveCount(0)
})
test('research odds remain readable on iPhone width, totals filter retains source',async ({page})=>{
  await page.setViewportSize({width:390,height:844})
  await openMarket(page)
  await page.getByRole('button',{name:'Totals',exact:true}).click()
  await expect(page.getByText('Research quote', {exact:true})).toBeVisible()
  await page.getByText('View dated sportsbook references').click()
  await expect(page.getByText('Over 41.5 (-115) · Under 41.5 (-105)')).toBeVisible()
  await expect(page.getByText('PHI +310 · JAC -390')).toHaveCount(0)
  const width=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}))
  expect(width.scroll).toBeLessThanOrEqual(width.viewport+1)
})
