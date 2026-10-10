import {test,expect} from '@playwright/test'
const eventId='401898395'
const game={event_id:eventId,league:'NBA',home:'Dallas Mavericks',home_abbr:'DAL',away:'Houston Rockets',away_abbr:'HOU',
 home_score:70,away_score:61,live:true,final:false,status:'3rd quarter',boxscore_available:true}
const score={games:[game],generated_at:'2026-10-10T08:30:00Z',status:'READY',counts:{games:1,live:1,final:0,upcoming:0}}
const readbox=points=>({status:'READY',league:'NBA',event_id:eventId,source:'ESPN',
 official_game_state:'LIVE',player_source_status:'VERIFIED_PLAYER_STATS',player_stat_rows:1,player_dnp_count:0,player_rows_omitted:0,
 generated_at:new Date('2026-10-10T08:30:00Z').toISOString(),
 teams:[{team:'Houston Rockets',abbreviation:'HOU',stats:[{label:'PTS',value:'61'}]}],leaders:[],
 player_tables:[{team_id:'10',team:'Houston Rockets',abbreviation:'HOU',groups:[{category:'Player stats',labels:['MIN','PTS'],players:[{id:'3202',name:'Kevin Durant',stats:['23',String(points)]}]}]}]})

test('live player boxscore refreshes without blanking source and keeps honest stale notice on failures',async({page})=>{
 await page.clock.install({time:new Date('2026-10-10T08:30:00Z')})
 await page.setViewportSize({width:390,height:844})
 let calls=0
 await page.route('**/nba_scores.json*',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(score)}))
 await page.route('**/api/boxscore?*',route=>{
   calls++
   if(calls===3) return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({status:'ERROR'})})
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(readbox(calls===1?15:25))})
 })
 await page.goto('http://127.0.0.1:8510/#scores',{waitUntil:'domcontentloaded'})
 await page.getByRole('button',{name:'NBA',exact:true}).click()
 await page.getByRole('button',{name:/Open Game Center/}).click()
 await page.getByRole('tab',{name:'Box Score',exact:true}).click()
 const panel=page.getByRole('region',{name:'Official player box scores'})
 await expect(panel.getByText('Kevin Durant')).toBeVisible()
 await expect(page.getByText(/refresh every 60 seconds while this tab is open/)).toBeVisible()
 const row=panel.getByRole('row',{name:/Kevin Durant/})
 await expect(row.getByRole('cell',{name:'15',exact:true})).toBeVisible()
 await page.clock.fastForward(60*1000)
 await expect(row.getByRole('cell',{name:'25',exact:true})).toBeVisible()
 await expect(row.getByRole('cell',{name:'15',exact:true})).toHaveCount(0)
 await page.clock.fastForward(60*1000)
 await expect(page.getByRole('alert')).toContainText('Latest live update unavailable')
 await expect(row.getByRole('cell',{name:'25',exact:true})).toBeVisible()
 expect(calls).toBe(3)
 await page.getByRole('tab',{name:'Odds',exact:true}).click()
 await page.clock.fastForward(60*1000)
 expect(calls).toBe(3)
})
