import {test,expect} from '@playwright/test'

const games = {
  status:'READY',generated_at:'2026-10-10T07:55:00Z',
  counts:{games:1,live:0,final:1,upcoming:0},
  games:[{
    event_id:'401898395',league:'NBA',start_time:'2026-10-09T12:00Z',
    home:'Dallas Mavericks',home_abbr:'DAL',home_score:117,
    away:'Houston Rockets',away_abbr:'HOU',away_score:101,
    live:false,final:true,state:'post',status:'Final',source:'ESPN NBA',boxscore_available:true,
  }],
}
const box = {
  status:'READY',league:'NBA',event_id:'401898395',source:'ESPN',
  official_game_state:'FINAL',player_source_status:'VERIFIED_PLAYER_STATS',
  player_stat_rows:3,player_dnp_count:1,player_rows_omitted:0,
  teams:[{team:'Houston Rockets',abbreviation:'HOU',stats:[{label:'REB',value:'41'}]},
         {team:'Dallas Mavericks',abbreviation:'DAL',stats:[{label:'REB',value:'39'}]}],
  leaders:[],
  player_tables:[
    {team_id:'10',team:'Houston Rockets',abbreviation:'HOU',groups:[
      {category:'Player stats',labels:['MIN','PTS','AST'],players:[
        {id:'3202',name:'Kevin Durant',position:'F',starter:true,stats:['23','15','2']},
        {id:'3203',name:'Houston Teammate',position:'G',starter:true,stats:['30','14','5']},
      ]},
    ]},
    {team_id:'6',team:'Dallas Mavericks',abbreviation:'DAL',groups:[
      {category:'Player stats',labels:['MIN','PTS','AST'],players:[
        {id:'12345',name:'Dallas Player',position:'G',starter:true,stats:['31','17','4']},
      ]},
    ]},
  ],
}

for (const width of [390,1280]) {
  test(`verified player-by-player Game Center usable at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:844})
    await page.route('**/nba_scores.json*',route=>route.fulfill({
      status:200,contentType:'application/json',body:JSON.stringify(games),
    }))
    await page.route('**/api/boxscore?*',route=>route.fulfill({
      status:200,contentType:'application/json',body:JSON.stringify(box),
    }))
    await page.goto('http://127.0.0.1:8510/#scores',{waitUntil:'domcontentloaded'})
    await page.getByRole('button',{name:'NBA',exact:true}).click()
    await page.getByRole('button',{name:/Open Game Center/}).click()
    await page.getByRole('tab',{name:'Box Score',exact:true}).click()
    const playerPanel=page.getByRole('region',{name:'Official player box scores'})
    await expect(playerPanel.getByRole('heading',{name:'Player-by-player box score'})).toBeVisible()
    await expect(playerPanel.getByText('3 source-matched player-stat lines', {exact:false})).toBeVisible()
    await expect(playerPanel.getByText(/1 did-not-play roster rows excluded/)).toBeVisible()
    await expect(playerPanel.getByRole('columnheader',{name:'PTS'})).toBeVisible()
    await expect(playerPanel.getByText('Kevin Durant')).toBeVisible()
    await expect(playerPanel.getByText('Dallas Player')).toBeHidden()
    await playerPanel.getByText(/Dallas Mavericks · 1 stat lines/).click()
    await expect(playerPanel.getByText('Dallas Player')).toBeVisible()
    const bounds=await page.evaluate(()=>({
      doc:document.documentElement.scrollWidth,
      client:document.documentElement.clientWidth,
      regions:[...document.querySelectorAll('[role="region"]')].filter(e=>e.getAttribute('aria-label')?.includes('Player stats')).map(e=>({scroll:e.scrollWidth,client:e.clientWidth})),
    }))
    expect(bounds.doc).toBeLessThanOrEqual(bounds.client+1)
    expect(bounds.regions.length).toBeGreaterThan(0)
    expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
  })
}
