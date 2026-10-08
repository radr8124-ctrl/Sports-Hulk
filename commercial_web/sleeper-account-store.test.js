import test from 'node:test'
import assert from 'node:assert/strict'
import { sleeperLeaguePayload, sleeperRosterPayload, saveSleeperFantasyTeam } from './sleeper_account_store.js'

const team = {
  user_id:'12345',username:'example',league_id:'123456789',league_name:'Championship',
  season:2026,roster_id:'7',team_name:'Home Team',
  roster:['Josh Allen','James Cook'],starters:['Josh Allen'],bench:['James Cook'],
  scoring:{preset:'half_ppr',reception_points:.5},roster_settings:{starting_slots:{qb:1},bench_slots:1},
}

function fakeClient({failOn=null}={}) {
  const tables={fantasy_leagues:[],fantasy_rosters:[]}
  const ops=[]
  let nextId=1
  class Query {
    constructor(table){this.table=table;this.filters=[];this.action='select';this.columns='*';this.body=null}
    select(cols){this.columns=cols; if (this.action==='delete' || this.action==='update') return this; if(this.action!=='insert')this.action='select'; return this}
    eq(k,v){this.filters.push([k,v]);return this}
    limit(){return this}
    insert(data){this.action='insert';this.body={...data};return this}
    update(data){this.action='update';this.body={...data};return this}
    delete(){this.action='delete';return this}
    async go(){
      const suffix=this.table+':'+this.action
      ops.push(suffix)
      if(failOn===suffix)return {data:null,error:{message:'TEST-ERROR'}}
      const list=tables[this.table]
      if (this.action==='insert') {
        const record={id:'new-id-'+nextId++,...this.body}
        list.push(record);return {data:[record],error:null}
      }
      const matches=row=>this.filters.every(([k,v])=>row[k]===v)
      if(this.action==='select')return {data:list.filter(matches),error:null}
      if(this.action==='update'){
        for(const row of list.filter(matches))Object.assign(row,this.body)
        return {data:[],error:null}
      }
      if(this.action==='delete'){
        for(let i=list.length-1;i>=0;i--)if(matches(list[i]))list.splice(i,1)
        return {data:[],error:null}
      }
      return {data:[],error:null}
    }
    then(resolve,reject){return this.go().then(resolve,reject)}
  }
  return {client:{database:{from:name=>new Query(name)}},tables,ops}
}

test('read-only import provenance never claims authenticated Sleeper ownership',()=>{
  const league=sleeperLeaguePayload('a',team,{},{})
  assert.equal(league.platform,'sleeper')
  assert.equal(league.provider_league_id,'123456789')
  assert.equal(league.provenance.provider_identity_verified,false)
  assert.equal(league.sync_status,'PUBLIC_READ_ONLY')
  assert.equal(league.owner_id,'a')
  assert.equal(sleeperRosterPayload(team,'league-uuid').provider_team_id,'sleeper-7')
})

test('existing provider link for different Sleeper user must not be overwritten',()=>{
  assert.throws(()=>sleeperLeaguePayload('me',team,{provenance:{sleeper_user_id:'67890'}}),/different Sleeper username/)
})

test('new Sleeper import creates only scoped league and roster, not manual records',async()=>{
  const {client,tables}=fakeClient()
  tables.fantasy_leagues.push({id:'manual-1',owner_id:'me',platform:'manual',provider_league_id:null,league_name:'My Team'})
  const a=await saveSleeperFantasyTeam(client,'me',team)
  assert.equal(a.status,'LINKED_PUBLIC_READ_ONLY')
  assert.equal(a.identity_verified,false)
  assert.equal(a.roster_count,2)
  assert.equal(tables.fantasy_leagues.length,2)
  assert.equal(tables.fantasy_leagues[0].league_name,'My Team')
  assert.equal(tables.fantasy_rosters.length,1)
  assert.equal(tables.fantasy_rosters[0].team_name,'Home Team')
  assert.deepEqual(tables.fantasy_rosters[0].roster,['Josh Allen','James Cook'])
})

test('repeating same Sleeper import updates its league and roster without duplicates',async()=>{
  const {client,tables}=fakeClient()
  const first=await saveSleeperFantasyTeam(client,'me',team)
  const second=await saveSleeperFantasyTeam(client,'me',{...team,team_name:'New Name'})
  assert.equal(first.league_id,second.league_id)
  assert.equal(first.roster_id,second.roster_id)
  assert.equal(tables.fantasy_leagues.length,1)
  assert.equal(tables.fantasy_rosters.length,1)
  assert.equal(tables.fantasy_rosters[0].team_name,'New Name')
})

test('other Sports Zenith users remain isolated even with same Sleeper league id',async()=>{
  const {client,tables}=fakeClient()
  const a=await saveSleeperFantasyTeam(client,'user-a',team)
  const b=await saveSleeperFantasyTeam(client,'user-b',team)
  assert.notEqual(a.league_id,b.league_id)
  assert.equal(tables.fantasy_leagues.length,2)
  assert.equal(tables.fantasy_leagues[0].owner_id,'user-a')
  assert.equal(tables.fantasy_leagues[1].owner_id,'user-b')
})

test('failed roster write rolls back newly created league',async()=>{
  const {client,tables,ops}=fakeClient({failOn:'fantasy_rosters:insert'})
  await assert.rejects(saveSleeperFantasyTeam(client,'me',team),/roster could not be saved/)
  assert.equal(tables.fantasy_leagues.length,0)
  assert.ok(ops.includes('fantasy_leagues:delete'))
})

test('unauthenticated account cannot use private account store',async()=>{
  const {client,tables}=fakeClient()
  await assert.rejects(saveSleeperFantasyTeam(client,'',team),/Sign in/)
  assert.equal(tables.fantasy_leagues.length,0)
})
