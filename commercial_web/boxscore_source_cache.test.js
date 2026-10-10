import test from 'node:test'
import assert from 'node:assert/strict'
import {createBoxscoreSourceCache} from './boxscore_source_cache.js'

const result = (league,eventId,stage='FINAL') => ({
  status:'READY',league,event_id:eventId,official_game_state:stage,
  player_source_status:'VERIFIED_PLAYER_STATS',player_tables:[{team:'Test',groups:[]}],
  generated_at:'2026-10-10T08:10:00Z',
})

test('simultaneous readers share one official source call for same event',async()=>{
  let calls=0,now=100
  const cache=createBoxscoreSourceCache(async (league,event)=>{
    calls++
    await Promise.resolve()
    return result(league,event)
  },{now:()=>now})
  const three=await Promise.all([...Array(3)].map(()=>cache.get('NBA','401898395')))
  assert.equal(calls,1)
  assert.deepEqual(three,[three[0],three[0],three[0]])
  assert.equal(cache.size(),1)
})

test('Final data is reused for at most five minutes with original source time',async()=>{
  let calls=0,now=0
  const cache=createBoxscoreSourceCache(async (league,event)=>{calls++;return result(league,event)},{now:()=>now})
  const a=await cache.get('NBA','401898395')
  now=299999
  const b=await cache.get('NBA','401898395')
  assert.equal(calls,1)
  assert.equal(b.generated_at,a.generated_at)
  now=300000
  await cache.get('NBA','401898395')
  assert.equal(calls,2)
})

test('LIVE expires at 45 seconds; PREGAME expires at 2 minutes',async()=>{
  let now=0,calls=0
  const fetcher=async (league,event)=>{calls++;return result(league,event,event.endsWith('5')?'LIVE':'PREGAME')}
  const cache=createBoxscoreSourceCache(fetcher,{now:()=>now})
  await cache.get('NBA','401898395')
  await cache.get('NHL','401892464')
  assert.equal(calls,2)
  now=44000;await cache.get('NBA','401898395');await cache.get('NHL','401892464');assert.equal(calls,2)
  now=45000;await cache.get('NBA','401898395');assert.equal(calls,3)
  now=120000;await cache.get('NHL','401892464');assert.equal(calls,4)
})

test('source failures and invalid identity cannot become cached content',async()=>{
  let calls=0
  const cache=createBoxscoreSourceCache(async(league,event)=>{
    calls++
    if(calls===1)throw Error('ESPN unavailable')
    if(calls===2)return {...result(league,event),event_id:'99999999'}
    return result(league,event)
  })
  await assert.rejects(cache.get('NBA','401898395'),/ESPN/)
  await assert.rejects(cache.get('NBA','401898395'),/not verified/)
  assert.equal(cache.size(),0)
  const r=await cache.get('NBA','401898395')
  assert.equal(r.official_game_state,'FINAL')
  assert.equal(calls,3)
})

test('unsupported event IDs and sports are rejected before any upstream request',async()=>{
  let calls=0
  const cache=createBoxscoreSourceCache(async(...args)=>{calls++;return result(...args)})
  await assert.rejects(cache.get('NFL','401898395'),/Unsupported/)
  await assert.rejects(cache.get('NBA','../etc/passwd'),/Unsupported/)
  await assert.rejects(cache.get('NBA',''),/Unsupported/)
  assert.equal(calls,0)
})

test('cache is bounded to prevent growing indefinitely',async()=>{
  let index=0
  const cache=createBoxscoreSourceCache(async(league,event)=>result(league,event),{maxEntries:2})
  for(const id of ['401898395','401898396','401898397'])await cache.get('NBA',id)
  assert.equal(cache.size(),2)
})
