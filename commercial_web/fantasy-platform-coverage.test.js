import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fantasyProviderStatus } from './sleeper_fantasy.js'

const ui = readFileSync(new URL('./src/FantasyPlatformConnections.jsx',import.meta.url),'utf8')

test('ESPN, Yahoo, CBS and Sleeper all display with truthful sync status',()=>{
  assert.deepEqual(fantasyProviderStatus.map(x=>x.id),['sleeper','yahoo','espn','cbs'])
  assert.equal(fantasyProviderStatus.find(x=>x.id==='cbs')?.status,'PRIVATE_SIGN_IN_NOT_CONFIGURED')
  assert.equal(fantasyProviderStatus.find(x=>x.id==='yahoo')?.status,'OAUTH_NOT_CONFIGURED')
  assert.equal(fantasyProviderStatus.find(x=>x.id==='espn')?.status,'PRIVATE_SIGN_IN_NOT_CONFIGURED')
  assert.equal(fantasyProviderStatus.find(x=>x.id==='sleeper')?.status,'PUBLIC_READ_ONLY')
  assert.match(ui,/name: 'CBS Sports Fantasy'/)
  assert.match(ui,/CBS private-league sign-in and roster sync are not active/)
})

test('links to independently verified free tools never claim to sync with Sports Zenith',()=>{
  assert.match(ui,/https:\/\/www\.footballguys\.com\/rate-my-team/)
  assert.match(ui,/https:\/\/www\.fantasypros\.com\/nfl\/myplaybook\//)
  assert.match(ui,/CBS availability under that free path is not confirmed/)
  assert.match(ui,/Offers one free synced NFL team/)
  assert.match(ui,/Using them does not connect their rosters to Sports Zenith/)
  assert.match(ui,/Never enter ESPN, Yahoo, CBS or Sleeper passwords or session cookies/)
})

test('external CBS site is official, with no direct login claim',()=>{
  const cbs=fantasyProviderStatus.find(x=>x.id==='cbs')
  assert.equal(cbs.external_url,'https://www.cbssports.com/fantasy/football/')
  assert.match(ui,/https:\/\/www\.cbssports\.com\/fantasy\/football\//)
  assert.doesNotMatch(ui,/CBS OAuth active|CBS connected|CBS roster sync active/i)
})
