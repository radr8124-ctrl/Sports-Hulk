import test from 'node:test'
import assert from 'node:assert/strict'
import { survivorCoverState } from './survivor_cover_state.js'

const privateEntry={
 signedIn:true,hasEntry:true,entryStatus:'ALIVE',poolWeek:5,
 usedTeams:['Los Angeles Chargers','San Francisco 49ers','Buffalo Bills','Kansas City Chiefs','Minnesota Vikings'],
 currentPicks:[],requiredPicks:1,ruleConfirmed:true,
 officialPoolWeek:4,recommendationStatus:'WAIT_FOR_FRESH_VERIFIED_MARKET_QUOTES',
 shadowRecommendation:[],
}

test('alive, undecided entry is explicitly NOT saved or submitted',()=>{
 const state=survivorCoverState(privateEntry)
 assert.equal(state.status,'DECISION_OPEN')
 assert.equal(state.label,'NOT YET CHOSEN')
 assert.equal(state.saved,'0 / 1')
 assert.equal(state.used,5)
 assert.equal(state.qualified,'0')
 assert.equal(state.official,'WEEK 4 ONLY')
 assert.match(state.proof,/not verified/i)
 assert.match(state.external,/not submit/i)
})

test('saved Zenith pick never becomes an external pool submission',()=>{
 const state=survivorCoverState({...privateEntry,currentPicks:['Jacksonville Jaguars']})
 assert.equal(state.status,'SAVED_ZENITH_ONLY')
 assert.equal(state.saved,'1 / 1')
 assert.match(state.label,/SAVED IN ZENITH/)
 assert.match(state.external,/not submit/i)
})

test('unauthenticated users receive zero private entry data, even if passed by accident',()=>{
 const state=survivorCoverState({...privateEntry,signedIn:false,hasEntry:false})
 assert.equal(state.status,'SIGN_IN_REQUIRED')
 assert.equal(state.saved,'—')
 assert.equal(state.used,'—')
 assert.equal(state.official,'SIGN IN')
 assert.equal(state.qualified,'—')
 assert.equal(state.label,'SIGN IN TO VIEW')
})

test('account without linked entry must not reveal private counts',()=>{
 const state=survivorCoverState({...privateEntry,hasEntry:false})
 assert.equal(state.status,'LINK_ENTRY')
 assert.equal(state.saved,'—')
 assert.equal(state.used,'—')
 assert.equal(state.official,'LINK ENTRY')
})

test('model picks only count when valid rule and proof gate are both verified',()=>{
 assert.equal(survivorCoverState({...privateEntry,shadowRecommendation:[{team:'Jacksonville Jaguars'}]}).qualified,'0')
 assert.equal(survivorCoverState({...privateEntry,ruleConfirmed:false,recommendationStatus:'SHADOW_RECOMMENDATION_READY',shadowRecommendation:[{team:'Jacksonville Jaguars'}]}).qualified,'0')
 assert.equal(survivorCoverState({...privateEntry,recommendationStatus:'SHADOW_RECOMMENDATION_READY',shadowRecommendation:[{team:'Jacksonville Jaguars'}]}).qualified,'1')
})

test('official field does not become current week from historical sheet or user-reported losses',()=>{
 assert.equal(survivorCoverState({...privateEntry,officialPoolWeek:4}).official,'WEEK 4 ONLY')
 assert.equal(survivorCoverState({...privateEntry,officialPoolWeek:5}).official,'WEEK 5')
 assert.equal(survivorCoverState({...privateEntry,officialPoolWeek:9}).official,'UNVERIFIED')
 assert.equal(survivorCoverState({...privateEntry,officialPoolWeek:null}).official,'UNVERIFIED')
})

test('an eliminated entry is not presented as undecided and no actionable pick is suggested',()=>{
 const state=survivorCoverState({...privateEntry,entryStatus:'ELIMINATED'})
 assert.equal(state.status,'NOT_ACTIVE')
 assert.match(state.label,/NOT ACTIVE/)
})
