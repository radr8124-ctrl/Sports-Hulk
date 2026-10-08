import test from 'node:test'
import assert from 'node:assert/strict'
import {
  validateSleeperUsername, validateSleeperLeagueId, lookupSleeperLeagues,
  mapSleeperScoring, resolveSleeperRoster, fetchSleeperRosterByLeague,
  fantasyProviderStatus, resetSleeperPlayerCacheForTests,
} from './sleeper_fantasy.js'
import { resetCircuitBreakersForTests } from './resilient_fetch.js'

function mockFetch(routes) {
  const urls = []
  const fetchImpl = async url => {
    const path = String(url).replace('https://api.sleeper.app/v1','')
    urls.push(path)
    const entry = routes[path]
    return {
      ok: entry !== undefined,
      status: entry !== undefined ? 200 : 404,
      json: async () => entry,
    }
  }
  return {fetchImpl,urls}
}

const routes = {
  '/user/exampleuser': { user_id: '123456789', username: 'exampleuser', email: 'private@example.com' },
  '/user/123456789/leagues/nfl/2026': [
    {league_id:'890123456789',name:'Home Championship',status:'in_season',total_rosters:12,season:'2026',roster_positions:['QB','RB','WR']},
    {league_id:'987654321000',name:'Other League',status:'pre_draft',total_rosters:10,season:'2026'},
  ],
  '/league/890123456789': {league_id:'890123456789',scoring_settings:{rec:0.5},
    roster_positions:['QB','RB','RB','WR','WR','TE','FLEX','SUPER_FLEX','DEF','BN','BN','IR']},
  '/league/890123456789/rosters': [
    {roster_id:1,owner_id:'other_user',players:['101']},
    {roster_id:7,owner_id:'123456789',metadata:{team_name:'My Fantasy Stars'},
      players:['101','202','BUF'],starters:['101','BUF']},
  ],
  '/players/nfl': {
    '101':{full_name:'Josh Allen',position:'QB'},
    '202':{full_name:'James Cook',position:'RB'},
  },
}

test('Sleeper connection is read-only and other platforms are marked unavailable', () => {
  assert.equal(fantasyProviderStatus.find(x=>x.id==='sleeper').status,'PUBLIC_READ_ONLY')
  assert.equal(fantasyProviderStatus.find(x=>x.id==='yahoo').status,'OAUTH_NOT_CONFIGURED')
  assert.equal(fantasyProviderStatus.find(x=>x.id==='espn').status,'PRIVATE_SIGN_IN_NOT_CONFIGURED')
})

test('username and league validation rejects URL injection and secret-like strings', () => {
  for (const name of ['',null,'a','../user/admin','hello@x','abc/def','secret:name','a'.repeat(41)]) {
    assert.throws(()=>validateSleeperUsername(name))
  }
  assert.equal(validateSleeperUsername('  My.NFL-2026  '),'My.NFL-2026')
  for (const id of ['123/rosters','../../','/','xyz','123?key=me']) {
    assert.throws(()=>validateSleeperLeagueId(id))
  }
})

test('public league preview minimizes profile fields and never exposes user email', async () => {
  resetCircuitBreakersForTests()
  const m = mockFetch(routes)
  const v = await lookupSleeperLeagues('exampleuser',{season:2026,fetchImpl:m.fetchImpl})
  assert.equal(v.status,'READY')
  assert.equal(v.access,'SLEEPER_PUBLIC_READ_ONLY_NO_IDENTITY_VERIFICATION')
  assert.equal(v.leagues.length,2)
  assert.equal(v.leagues[0].name,'Home Championship')
  assert.equal(v.user.user_id,'123456789')
  assert.ok(!JSON.stringify(v).includes('private@example.com'))
  assert.deepEqual(m.urls,['/user/exampleuser','/user/123456789/leagues/nfl/2026'])
})

test('unknown username fails without inventing any linked league',async()=>{
  resetCircuitBreakersForTests()
  const m=mockFetch({'/user/nonexistent':null})
  await assert.rejects(lookupSleeperLeagues('nonexistent',{season:2026,fetchImpl:m.fetchImpl}),/not found/)
})

test('correct season and actual roster owner are validated before import',async()=>{
  resetCircuitBreakersForTests()
  resetSleeperPlayerCacheForTests()
  const m=mockFetch(routes)
  const v=await fetchSleeperRosterByLeague({username:'exampleuser',league_id:'890123456789',season:2026},{fetchImpl:m.fetchImpl,now:1700000000000})
  assert.equal(v.roster_id,'7')
  assert.equal(v.team_name,'My Fantasy Stars')
  assert.equal(v.scoring.preset,'half_ppr')
  assert.equal(v.roster_settings.bench_slots,2)
  assert.equal(v.roster_settings.ir_slots,1)
  assert.equal(v.roster_settings.starting_slots.superflex,1)
  assert.equal(v.roster_settings.starting_slots.dst,1)
  assert.deepEqual(v.roster,['Josh Allen','James Cook','Buffalo Bills D/ST'])
  assert.deepEqual(v.starters,['Josh Allen','Buffalo Bills D/ST'])
  assert.deepEqual(v.bench,['James Cook'])
  assert.equal(v.access,'SLEEPER_PUBLIC_READ_ONLY_NO_IDENTITY_VERIFICATION')
  assert.equal(m.urls.filter(x=>x==='/players/nfl').length,1)
  const second=await fetchSleeperRosterByLeague({username:'exampleuser',league_id:'890123456789',season:2026},{fetchImpl:m.fetchImpl,now:1700000005000})
  assert.equal(second.roster.length,3)
  assert.equal(m.urls.filter(x=>x==='/players/nfl').length,1)
})

test('does not import a league outside this public username',async()=>{
  resetCircuitBreakersForTests()
  const m=mockFetch(routes)
  await assert.rejects(fetchSleeperRosterByLeague({username:'exampleuser',league_id:'999999999999',season:2026},{fetchImpl:m.fetchImpl}),/not listed/)
  assert.equal(m.urls.filter(x=>x.includes('/rosters')).length,0)
})

test('does not import another roster owner even when league is public',async()=>{
  resetCircuitBreakersForTests()
  const m=mockFetch({...routes,'/league/890123456789/rosters':[
    {roster_id:5,owner_id:'other_user',players:['101']}
  ]})
  await assert.rejects(fetchSleeperRosterByLeague({username:'exampleuser',league_id:'890123456789',season:2026},{fetchImpl:m.fetchImpl}),/No owned roster/)
  assert.equal(m.urls.includes('/players/nfl'),false)
})

test('fails closed if any non-placeholder roster player is unresolved',async()=>{
  resetCircuitBreakersForTests();resetSleeperPlayerCacheForTests()
  const m=mockFetch({...routes,'/league/890123456789/rosters':[
    {roster_id:7,owner_id:'123456789',players:['101','unknown'],starters:['101']}
  ]})
  await assert.rejects(fetchSleeperRosterByLeague({username:'exampleuser',league_id:'890123456789',season:2026},{fetchImpl:m.fetchImpl,now:1800000000000}),/player names are incomplete/)
})

test('league scoring with unknown point-per-reception stays unknown',()=>{
  assert.equal(mapSleeperScoring({}).scoring.preset,null)
  assert.equal(mapSleeperScoring({scoring_settings:{rec:1}}).scoring.preset,'ppr')
  assert.equal(mapSleeperScoring({scoring_settings:{rec:0}}).scoring.preset,'standard')
  assert.deepEqual(resolveSleeperRoster({players:['0','BUF','101'],starters:['BUF']},{101:{full_name:'J. Allen'}}).roster,['Buffalo Bills D/ST','J. Allen'])
})
