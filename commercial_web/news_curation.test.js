import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {gunzipSync} from 'node:zlib'
import {createHash} from 'node:crypto'
import {
  NEWS_SPORTS,NEWS_CATEGORIES,curateSportsNews,newsCategory,
  selectHomeTopStories,filterSportsNews,groupSportsNews,
} from './news_curation.js'

const feed=JSON.parse(gunzipSync(readFileSync(new URL('../reports/SPORTS_ZENITH_NEWS_SOURCE_FIXTURE_20261010.json.gz',import.meta.url))).toString('utf8'))
const NOW=Date.parse(feed.generated_at)+3*60_000
const curated=curateSportsNews(feed,NOW)
test('immutable original news capture retains its exact source and archived compression checksums',()=>{
 const archive=readFileSync(new URL('../reports/SPORTS_ZENITH_NEWS_SOURCE_FIXTURE_20261010.json.gz',import.meta.url))
 const original=gunzipSync(archive)
 assert.equal(createHash('sha256').update(original).digest('hex'),
  '11eb3bb010a3055e0403a574471dfc81c7546814bba539dd973f70ef271831a1')
 assert.equal(createHash('sha256').update(archive).digest('hex'),
  '6a6b80f8f78b960079b8e8003e159455bb3ca1ab10a9521a523f8b457d7f888d')
 assert.equal(JSON.parse(original).news_events.length,661)
})

const makeRow=(id,title,options={})=>({
  event_node_id:'NEWS:'+id,event_source_type:'NEWS',
  sport:'NFL',event_type:'NEWS',title,detail:'Description of '+title,
  source:'ESPN',source_tier:'EXTERNAL_NEWS',
  source_url:'https://www.espn.com/nfl/story/'+id,
  published_or_effective_at:new Date(NOW-30*60_000).toISOString(),
  ...options,
})
const data=rows=>({generated_at:new Date(NOW-3*60_000).toISOString(),news_events:rows})

test('news feed contains linked source articles in all six ESPN league verticals',()=>{
 assert.equal(curated.status,'READY')
 assert.equal(curated.rawNewsRows,180)
 assert.ok(curated.stories.length>=140)
 assert.deepEqual(groupSportsNews(curated.stories).map(r=>r.sport),NEWS_SPORTS)
 assert.deepEqual([...new Set(curated.stories.map(x=>x.sport))].sort(),[...NEWS_SPORTS].sort())
 assert(curated.stories.every(x=>/^https?:\/\//.test(x.url)))
 assert(curated.stories.every(x=>x.attributedNotVerifiedFact))
 assert.equal(curated.originalOddsOrBettingModelInputsCreated,false)
 assert(curated.stories.every(x=>x.publishedMs<=NOW+5*60_000))
})

test('all distinct ESPN game recaps preserved, including path-equal different game IDs',()=>{
 const rows=curated.stories.filter(x=>x.category==='RECAP')
 assert.ok(rows.length>=10)
 const matchup=rows.filter(x=>x.url.includes('/nhl/recap?'))
 assert.ok(matchup.length>=4)
 assert.equal(new Set(matchup.map(x=>x.url)).size,matchup.length)
 const two=curateSportsNews(data([
  makeRow('recap-a','Team A comes back late to win',{source_url:'http://www.espn.com/ncf/recap?gameId=4011',event_type:'RECAP'}),
  makeRow('recap-b','Team B wins another game',{source_url:'http://www.espn.com/ncf/recap?gameId=4012',event_type:'RECAP'}),
 ]),NOW)
 assert.equal(two.stories.length,2)
})

test('injury signs are based on actual article context not unreliable provider tag alone',()=>{
 assert.equal(newsCategory({event_type:'NEWS',title:'Washington QB exits game, set for X-rays'}),'INJURY')
 assert.equal(newsCategory({event_type:'NEWS',title:'Rangers goalie helped off ice'}),'INJURY')
 assert.equal(newsCategory({event_type:'INJURY',title:'Chris Doering dives into Week 6 matchups',detail:'Experts preview key SEC conference games'}),'NEWS')
 assert.equal(newsCategory({event_type:'INJURY',title:'Jordan Mason expected to return Week 7',detail:'Mason on IR after ankle surgery'}),'INJURY')
 assert.equal(newsCategory({event_type:'RECAP',title:'Jets win 5-1'}),'RECAP')
 assert.equal(newsCategory({event_type:'FANTASY',title:'Fantasy football rankings'}),'FANTASY')
 assert.equal(newsCategory({event_type:'NEWS',title:'Starting pitcher announced for ALCS'}),'LINEUP')
})

test('home uses at most four recent headlines from different sports and visibly different story types',()=>{
 const top=selectHomeTopStories(curated.stories,NOW)
 assert.equal(top.length,4)
 assert.equal(new Set(top.map(x=>x.id)).size,4)
 assert.equal(new Set(top.map(x=>x.sport)).size,4)
 assert(top.some(x=>x.category==='INJURY'))
 assert(top.some(x=>x.category==='RECAP'))
 assert(top.every(x=>NOW-x.publishedMs<=48*3600_000))
 const none=selectHomeTopStories(curated.stories,NOW+30*86400000)
 assert.equal(none.length,0)
})

test('search category and league filter examine the ENTIRE original article collection',()=>{
 const nfl=filterSportsNews(curated.stories,{sport:'NFL'})
 assert.ok(nfl.length>=20)
 assert(nfl.every(x=>x.sport==='NFL'))
 const recaps=filterSportsNews(curated.stories,{category:'RECAP'})
 assert.ok(recaps.length>=10)
 assert(recaps.every(x=>x.category==='RECAP'))
 const name=filterSportsNews(curated.stories,{search:'Shesterkin'})
 assert.ok(name.length>=1)
 assert(name.every(x=>(x.title+' '+x.summary).toLowerCase().includes('shesterkin')))
 const date=filterSportsNews(curated.stories,{sort:'LATEST'})
 assert(date[0].publishedMs>=date[1].publishedMs)
 assert.equal(groupSportsNews(curated.stories).reduce((n,x)=>n+x.stories.length,0),curated.stories.length)
 assert(NEWS_CATEGORIES.some(x=>x.label==='Injuries'))
 assert(NEWS_CATEGORIES.some(x=>x.label==='Recaps'))
})

test('nonarticle facts, highlight videos, ad headlines, unsafe links and duplicate source reports never enter the linked article hub',()=>{
 const common=makeRow('one','Verified lineups confirmed for tonight')
 const examples=[
   common,
   {...common,event_node_id:'FACT:duplicate',event_source_type:'FACT',title:'Something else'},
   {...common,event_node_id:'NEWS:duplicate-copy'},
   makeRow('video','Bulls vs Lakers: Game Highlights'),
   makeRow('promo','Exclusive sportsbook promo code with bonus bets!'),
   makeRow('unsafe','Article with javascript URI',{source_url:'javascript:alert(1)'}),
   makeRow('missing','Article without any valid original source',{source_url:null}),
 ]
 const output=curateSportsNews(data(examples),NOW)
 assert.equal(output.status,'READY')
 assert.equal(output.stories.length,1)
 assert.equal(output.stories[0].title,common.title)
 assert.equal(output.excludedRows,5)
})

test('distinct missing/failed/stale versus verified-empty sources are NOT called no bets',()=>{
 assert.equal(curateSportsNews(null,NOW).status,'DATA_SOURCE_FAILURE')
 assert.equal(curateSportsNews({},NOW).status,'DATA_SOURCE_FAILURE')
 assert.equal(curateSportsNews({generated_at:new Date(NOW).toISOString()},NOW).status,'DATA_SOURCE_FAILURE')
 assert.equal(curateSportsNews({generated_at:new Date(NOW+1000000).toISOString(),news_events:[]},NOW).status,'DATA_SOURCE_FAILURE')
 assert.equal(curateSportsNews({generated_at:new Date(NOW-7*3600000).toISOString(),news_events:[makeRow('new','Real sourced article')]},NOW).status,'SOURCE_STALE')
 assert.equal(curateSportsNews(data([]),NOW).status,'NO_QUALIFIED_ARTICLES')
})

test('article source timestamps and model truth are never rewritten by the newsroom',()=>{
 const before=JSON.stringify(feed)
 const rows=curateSportsNews(feed,NOW)
 assert.equal(before,JSON.stringify(feed))
 for(const row of rows.stories){
  assert.equal(typeof row.publishedAt,'string')
  assert(row.url.includes('espn.com')||row.source==='ESPN')
  assert.equal(row.attributedNotVerifiedFact,true)
 }
})
