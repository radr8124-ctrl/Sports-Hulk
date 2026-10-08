import test from 'node:test'
import assert from 'node:assert/strict'
import { survivorPersonalScoreCards } from './survivor_pick_scores.js'

function fixture() {
  return {
    current_week: 4,
    current_picks: [],
    week_5: { picks: [], entry_result: 'OPEN' },
    week_4: { picks: [{
      team: 'Minnesota Vikings', result: 'WIN',
      game_status: 'FINAL: Miami Dolphins 10 - Minnesota Vikings 15',
    }], entry_result: 'WIN' },
    week_3: { picks: [
      { team: 'Kansas City Chiefs', result: 'WIN', game_status: 'FINAL: Kansas City Chiefs 22 - Buffalo Bills 14' },
      { team: 'Buffalo Bills', result: 'WIN', game_status: 'FINAL: Buffalo Bills 14 - Kansas City Chiefs 22' },
    ], entry_result: 'WIN' },
  }
}

test('the actual Week 4 Vikings record is shown as saved SURVIVED, without changing Week 5', () => {
  const state = fixture()
  const previous = JSON.stringify(state)
  const cards = survivorPersonalScoreCards(state, 5, null, {at: Date.parse('2026-10-08T00:00:00Z')})
  assert.equal(cards.length, 3)
  assert.deepEqual(cards.map(v => v.week), [4,3,3])
  assert.deepEqual(cards.map(v => v.pick_number), [1,1,2])
  assert.equal(cards[0].team, 'Minnesota Vikings')
  assert.equal(cards[0].pool_result, 'SURVIVED')
  assert.equal(cards[0].game_state, 'FINAL_SAVED_RESULT')
  assert.equal(cards[0].score_line, 'Miami Dolphins 10 - Minnesota Vikings 15')
  assert.equal(cards[0].game_clock, 'FINAL')
  assert.equal(cards[0].source, 'SAVED_ENTRY_GRADE')
  assert.equal(JSON.stringify(state), previous)
})

test('multiple live Week 5 picks show their own scores; lead is not settled result', () => {
  const e = fixture()
  e.current_week=5
  e.current_picks=['Tampa Bay Buccaneers', 'Dallas Cowboys']
  e.week_5.picks = [
    {team: 'Tampa Bay Buccaneers', result:'PENDING'},
    {team: 'Dallas Cowboys', result:'PENDING'},
  ]
  const scores = {games:[{
    away:'Tampa Bay Buccaneers', home:'Dallas Cowboys',
    away_score:'20', home_score:'14', state:'in', live:true, final:false,
    status:'4th 10:32', start_time:'2026-10-09T00:15Z',
  }]}
  const cards = survivorPersonalScoreCards(e,5,scores,{at:Date.parse('2026-10-09T01:05Z')})
  assert.equal(cards[0].game_state,'LIVE_AHEAD')
  assert.equal(cards[1].game_state,'LIVE_BEHIND')
  assert.equal(cards[0].pool_result,'PENDING')
  assert.equal(cards[1].pool_result,'PENDING')
  assert.equal(cards[0].opponent,'Dallas Cowboys')
  assert.equal(cards[1].opponent,'Tampa Bay Buccaneers')
  assert.match(cards[0].score_line,/20.*14/)
  assert.equal(cards[0].game_clock,'4th 10:32')
})

test('a final public game does not falsely mark pool outcome as submitted or survived', () => {
  const e=fixture(); e.current_week=5; e.week_5.picks=[{team:'Dallas Cowboys',result:'PENDING'}]
  const scores={games:[{away:'Tampa Bay Buccaneers',home:'Dallas Cowboys',away_score:'20',home_score:'27',final:true,state:'post',status:'Final',start_time:'2026-10-09T00:15Z'}]}
  const [card]=survivorPersonalScoreCards(e,5,scores,{at:Date.parse('2026-10-09T03:15Z')})
  assert.equal(card.game_state,'FINAL_UNSETTLED_POOL')
  assert.equal(card.pool_result,'PENDING')
  assert.equal(card.pool_submitted,false)
})

test('wrong-week matchup cannot become this week live score', () => {
  const e=fixture(); e.current_week=5; e.week_5.picks=[{team:'Minnesota Vikings',result:'PENDING'}]
  const scores={games:[{away:'Minnesota Vikings',home:'Miami Dolphins',away_score:'15',home_score:'10',live:true,state:'in',status:'3rd',start_time:'2026-09-20T15:00Z'}]}
  const [card]=survivorPersonalScoreCards(e,5,scores,{at:Date.parse('2026-10-08T00:00Z')})
  assert.equal(card.game_state,'SCORE_WAITING')
  assert.equal(card.score_line,null)
  assert.equal(card.pool_result,'PENDING')
})

test('week rollover does not reuse historical current_picks in a new pool week', () => {
  const e=fixture();e.current_week=4;e.current_picks=['Minnesota Vikings']
  assert.equal(survivorPersonalScoreCards(e,5,{}, {at:0})[0].week,4)
})

test('latest pool week always wins, duplicate team across weeks is tracked separately', () => {
  const e=fixture();e.current_week=5;e.week_5.picks=[{team:'Minnesota Vikings',result:'PENDING'}]
  const cards=survivorPersonalScoreCards(e,5,{}, {at:0})
  assert.equal(cards[0].week,5)
  assert.equal(cards[0].pool_result,'PENDING')
  assert.equal(cards[1].week,4)
  assert.equal(cards[1].pool_result,'SURVIVED')
})

test('invalid or non-linked entries cannot generate a private scorecard', () => {
  assert.deepEqual(survivorPersonalScoreCards(null,5,{}),[])
  assert.deepEqual(survivorPersonalScoreCards({},0,{}),[])
  assert.deepEqual(survivorPersonalScoreCards({},5,{}),[])
})

test('upcoming NFL score never claims a score or a pool submission', () => {
  const e=fixture();e.current_week=5;e.week_5.picks=[{team:'Tampa Bay Buccaneers',result:'PENDING'}]
  const scores={next_games:[{away:'Tampa Bay Buccaneers',home:'Dallas Cowboys',away_score:'0',home_score:'0',final:false,live:false,state:'pre',status:'10/8 8:15 PM',start_time:'2026-10-09T00:15Z'}]}
  const [card]=survivorPersonalScoreCards(e,5,scores,{at:Date.parse('2026-10-08T02:00Z')})
  assert.equal(card.game_state,'UPCOMING')
  assert.equal(card.pool_result,'PENDING')
  assert.equal(card.pool_submitted,false)
  assert.equal(card.game_clock,'10/8 8:15 PM')
})
