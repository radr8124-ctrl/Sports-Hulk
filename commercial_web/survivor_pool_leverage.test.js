import test from 'node:test'
import assert from 'node:assert/strict'
import { survivorHistoricalAvailability } from './survivor_pool_leverage.js'

const meta = {
  source_filename: 'WEEK #4 PICKS .pdf',
  source_sha256: 'a'.repeat(64),
  max_week_in_file: 4,
  parsed_entries: 4,
}
const fixture = `entry_name,status,used_teams,source_filename
"PERSON, ONE 01",ACTIVE_OR_UNCONFIRMED,"Jacksonville Jaguars | Cincinnati Bengals",WEEK #4 PICKS .pdf
"PERSON, ONE 01",ACTIVE_OR_UNCONFIRMED,"Jacksonville Jaguars | Houston Texans",WEEK #4 PICKS .pdf
PERSON TWO 03,ACTIVE_OR_UNCONFIRMED,Houston Texans,WEEK #4 PICKS .pdf
PERSON OUT 04,ELIMINATED,Jacksonville Jaguars,WEEK #4 PICKS .pdf
`
const input = {
  meta, csvText: fixture, currentWeek: 5,
  teamNames: ['Jacksonville Jaguars', 'Houston Texans', 'Cincinnati Bengals', 'Los Angeles Rams'],
}

test('verified previous sheet preserves duplicate entry instances but never exposes competitors', () => {
  const got = survivorHistoricalAvailability(input)
  assert.equal(got.status, 'HISTORICAL_PRIOR_WEEK_ONLY')
  assert.equal(got.source_week, 4)
  assert.equal(got.current_week, 5)
  assert.equal(got.sample_size, 3)
  assert.equal(got.excluded_eliminated_rows, 1)
  assert.deepEqual(got.teams, [
    {team:'Jacksonville Jaguars',used_count:2,not_previously_used_count:1,previously_used_share_pct:66.7},
    {team:'Houston Texans',used_count:2,not_previously_used_count:1,previously_used_share_pct:66.7},
    {team:'Cincinnati Bengals',used_count:1,not_previously_used_count:2,previously_used_share_pct:33.3},
    {team:'Los Angeles Rams',used_count:0,not_previously_used_count:3,previously_used_share_pct:0},
  ])
  assert.equal(JSON.stringify(got).includes('PERSON'), false)
  assert.equal(JSON.stringify(got).includes('entry_name'), false)
  assert.equal(JSON.stringify(got).includes('current_week_pick_share_pct'), false)
})

test('unrelated imported sheet metadata cannot be presented as verified usage', () => {
  const got = survivorHistoricalAvailability({
    ...input, meta:{...meta,source_filename:'OTHER WEEK #4.pdf'},
  })
  assert.equal(got.status, 'SOURCE_CONFLICT')
  assert.deepEqual(got.teams, [])
})

test('current/future sheets cannot be misused as PRIOR-week availability', () => {
  for (const currentWeek of [4,3]) {
    const got = survivorHistoricalAvailability({...input,currentWeek})
    assert.equal(got.status, 'PRIOR_WEEK_SNAPSHOT_REQUIRED')
    assert.equal(got.sample_size, null)
  }
})

test('missing source hash and CSV corruption fail closed', () => {
  assert.equal(survivorHistoricalAvailability({...input,meta:{...meta,source_sha256:''}}).status,'SOURCE_UNVERIFIED')
  assert.equal(survivorHistoricalAvailability({...input,csvText:fixture.replace('PERSON OUT 04,ELIMINATED,','"PERSON OUT 04,ELIMINATED,')}).status,'SOURCE_CONFLICT')
  assert.equal(survivorHistoricalAvailability({...input,meta:{...meta,parsed_entries:20}}).status,'SOURCE_CONFLICT')
})

test('malicious extra status or unavailable candidate team returns no fabricated figures', () => {
  const got = survivorHistoricalAvailability({...input,csvText:fixture.replace('PERSON TWO 03,ACTIVE_OR_UNCONFIRMED','PERSON TWO 03,ALIVE')})
  assert.equal(got.status,'SOURCE_CONFLICT')
  assert.equal(got.sample_size,null)
})
