import test from 'node:test'
import assert from 'node:assert/strict'
import {verifiedEspnPlayerTables} from './verified_player_boxscore.js'

const game = (state='post') => ({
  header: {
    id:'401898395',
    competitions:[{
      status:{type:{state,completed:state==='post'}},
      competitors:[
        {team:{id:'10',displayName:'Houston Rockets',abbreviation:'HOU'}},
        {team:{id:'6',displayName:'Dallas Mavericks',abbreviation:'DAL'}},
      ],
    }],
  },
  boxscore:{
    players:[
      {team:{id:'10'},statistics:[{name:'players',labels:['MIN','PTS','AST'],athletes:[
        {athlete:{id:'3202',displayName:'Kevin Durant',position:{abbreviation:'F'}},stats:['23','15','2'],starter:true},
        {athlete:{id:'44',displayName:'Injured player'},stats:['0','0','0'],didNotPlay:true},
      ]}]},
      {team:{id:'6'},statistics:[{name:'players',labels:['MIN','PTS','AST'],athletes:[
        {athlete:{id:'120',displayName:'Test Maverick'},stats:['35','21','4'],starter:true},
      ]}]},
    ],
  },
})
test('source-verified ESPN final has exact event, 2 teams and actual stat rows',()=>{
  const r=verifiedEspnPlayerTables(game(),'NBA','401898395')
  assert.equal(r.player_source_status,'VERIFIED_PLAYER_STATS')
  assert.equal(r.official_game_state,'FINAL')
  assert.equal(r.player_stat_rows,2)
  assert.equal(r.player_dnp_count,1)
  assert.deepEqual(r.player_tables[0].groups[0].labels,['MIN','PTS','AST'])
  assert.equal(r.player_tables[0].groups[0].players[0].name,'Kevin Durant')
  assert.equal(r.player_tables[1].team,'Dallas Mavericks')
  assert.equal(JSON.stringify(r).includes('Injured player'),false)
})
test('pregame roster cannot be mislabeled as recorded player stats',()=>{
  const r=verifiedEspnPlayerTables(game('pre'),'NBA','401898395')
  assert.equal(r.player_source_status,'PREGAME_NO_PLAYER_STATS')
  assert.equal(r.player_stat_rows,0)
  assert.deepEqual(r.player_tables,[])
})
test('in-progress match may show legitimately reported player stats as LIVE',()=>{
  const r=verifiedEspnPlayerTables(game('in'),'NBA','401898395')
  assert.equal(r.official_game_state,'LIVE')
  assert.equal(r.player_stat_rows,2)
})
test('contradictory final game state fails closed',()=>{
  const g=game('post');g.header.competitions[0].status.type.completed=false
  assert.equal(verifiedEspnPlayerTables(g,'NBA','401898395').player_source_status,'GAME_STATE_UNVERIFIED')
})
test('refuses other ESPN events and team IDs, including mixed games',()=>{
  assert.throws(()=>verifiedEspnPlayerTables(game(),'NBA','401898396'),/identity/)
  const g=game();g.boxscore.players[0].team.id='999'
  assert.throws(()=>verifiedEspnPlayerTables(g,'NBA','401898395'),/competitors/)
  const q=game();q.header.competitions[0].competitors[1].team.id='10'
  assert.throws(()=>verifiedEspnPlayerTables(q,'NBA','401898395'),/conflict/)
  const duplicate=game();duplicate.boxscore.players[1].team.id='10'
  assert.throws(()=>verifiedEspnPlayerTables(duplicate,'NBA','401898395'),/competitors/)
})
test('missing or misaligned stats do not create fabricated zero lines',()=>{
  const g=game()
  g.boxscore.players[0].statistics[0].athletes[0].stats=['23','15']
  const r=verifiedEspnPlayerTables(g,'NBA','401898395')
  assert.equal(r.player_stat_rows,1)
  assert.equal(r.player_rows_omitted,1)
  assert.equal(r.player_dnp_count,1)
})
test('unknown status and empty NHL box score show no player proof',()=>{
  const g=game();g.header.competitions[0].status.type.state='error'
  assert.equal(verifiedEspnPlayerTables(g,'NHL','401898395').player_source_status,'GAME_STATE_UNVERIFIED')
  const h=game();h.boxscore.players=[]
  assert.equal(verifiedEspnPlayerTables(h,'NHL','401898395').player_source_status,'NO_VERIFIED_PLAYER_STATS')
})
test('NHL goalies and college football roles remain distinct sourced categories',()=>{
  const h=game()
  h.boxscore.players[0].statistics.push({name:'goalies',labels:['MIN','GA'],athletes:[
    {athlete:{id:'8950',displayName:'Goalie Example'},stats:['58','1']},
  ]})
  const nhl=verifiedEspnPlayerTables(h,'NHL','401898395')
  assert.equal(nhl.player_stat_rows,3)
  assert.equal(nhl.player_tables[0].groups[1].category,'goalies')
  const cfb=game()
  cfb.boxscore.players[0].statistics[0].name='passing'
  assert.equal(verifiedEspnPlayerTables(cfb,'CFB','401898395').player_tables[0].groups[0].category,'passing')
})
