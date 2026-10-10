import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

// Original source-time Friday replay is immutable; never read live hourly files.
const base = file => JSON.parse(readFileSync(new URL('./test_fixtures/zenith_frozen_20261009/'+file,import.meta.url),'utf8'))
const survivor = base('survivor_v2_current.json')
const score = base('nfl_scores.json')
// Test-only historical replay: source archive has original Oct 9 capture,
// current Saturday collector correctly has zero fresh fixtures. Replay those
// actual dated archive prices ONLY with a frozen Friday clock; live UI never
// rewrites archived quotes as current offers.
const storedReference = base('nfl_research_book_refs.json')
const reference = {...storedReference, fixtures:storedReference.archived_snapshot.fixtures}

async function openReview(page, instant, mobile=false, refsData=reference) {
  if (mobile) await page.setViewportSize({width:390,height:844})
  await page.addInitScript(clock => {
    Date.now = () => clock
  }, Date.parse(instant))
  for(const [file,payload] of [
    ['survivor_v2_current.json',survivor],
    ['nfl_scores.json',score],
    ['nfl_research_book_refs.json',refsData],
  ]) {
    await page.route('**/'+file+'*',route=>route.fulfill({
      status:200,contentType:'application/json',body:JSON.stringify(payload),
    }))
  }
  await page.goto('http://127.0.0.1:8510/#survivor',{waitUntil:'domcontentloaded'})
  await page.getByRole('heading',{name:/Survivor market review/i}).waitFor()
  return page.locator('section[aria-label="Survivor weekly sportsbook review"]')
}

test('Friday source-fresh survivor research shows 13 matched games, one-pick rule, no private identity',async({page})=>{
  const section=await openReview(page,'2026-10-09T21:50:00Z')
  await expect(section.getByText(/13 source-matched options/)).toBeVisible()
  await expect(section.getByText(/Week 6 needs TWO unused teams/)).toBeVisible()
  await expect(section.getByText(/Pool deadline: Saturday 6 PM ET/)).toBeVisible()
  await expect(section.getByText(/ARCHIVED FRIDAY PREVIEW ONLY/)).toHaveCount(0)
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
})
test('Saturday morning expired quotes remain visibly historical, never current',async({page})=>{
  const section=await openReview(page,'2026-10-10T14:00:00Z',true)
  await expect(section.getByText(/0 current · 13 archived comparisons/)).toBeVisible()
  await expect(section.getByText(/ARCHIVED FRIDAY PREVIEW ONLY/)).toBeVisible()
  await expect(section.getByText('EXPIRED / NOT LIVE')).toHaveCount(13)
  await expect(section.getByText(/not a confirmed executable offer or guaranteed winner/).first()).toBeHidden()
  const size=await page.evaluate(()=>({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}))
  expect(size.scroll).toBeLessThanOrEqual(size.client+1)
})
test('a past-kickoff game cannot reappear via Friday archive time travel',async({page})=>{
  const section=await openReview(page,'2026-10-11T14:00:00Z')
  await expect(section.getByText(/0 current · 12 archived comparisons/)).toBeVisible()
  await expect(section.getByText('Jacksonville Jaguars',{exact:true})).toHaveCount(0)
  await expect(section.getByText(/ARCHIVED FRIDAY PREVIEW ONLY/)).toBeVisible()
})


test('hourly refresh with ZERO current prices still preserves clearly expired snapshot on Saturday',async({page})=>{
  const overnight={
    ...reference,
    generated_at:'2026-10-10T06:52:00Z',
    fixtures:[],
    paired_quote_games:0,
    paired_market_counts:{},
  }
  const section=await openReview(page,'2026-10-10T14:00:00Z',true,overnight)
  await expect(section.getByText(/0 current · 13 archived comparisons/)).toBeVisible()
  await expect(section.getByText(/ARCHIVED FRIDAY PREVIEW ONLY/)).toBeVisible()
  await expect(section.getByText('EXPIRED / NOT LIVE')).toHaveCount(13)
  await expect(section.getByText('Jacksonville Jaguars',{exact:true}).first()).toBeVisible()
  const dims=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth}))
  expect(dims.scroll).toBeLessThanOrEqual(dims.client+1)
})

test('corrupt provenance SHA disables archived preview, not relabeled live',async({page})=>{
  const overnight={
    ...reference,
    generated_at:'2026-10-10T06:52:00Z',
    fixtures:[],
    paired_quote_games:0,
    archived_snapshot:{...reference.archived_snapshot,original_archive_sha256:'CONFLICT_WITH_ORIGINAL'},
  }
  const section=await openReview(page,'2026-10-10T14:00:00Z',false,overnight)
  await expect(section.getByText(/0 source-matched options/)).toBeVisible()
  await expect(section.getByText(/ARCHIVED FRIDAY PREVIEW ONLY/)).toHaveCount(0)
  await expect(section.getByText(/No source-fresh Week 5 market reference/)).toBeVisible()
})
