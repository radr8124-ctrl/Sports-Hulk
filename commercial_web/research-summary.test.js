import test from 'node:test'
import assert from 'node:assert/strict'
import { researchSummary } from './src/researchSummary.js'

test('Research Lab preserves the official published record without mixing shadow predictions', () => {
  const result=researchSummary({
    performance:{ generated_at:'2026-10-08T01:00:00Z',official:{published:1,settled:1,wins:0,losses:1,units:-1,status:'TRACKING'} },
    forward:{status:'SETTLEMENT_BACKLOG',summary:{tracked:7831,settled:6006,pending_overdue_48h:125}},
    selectivity:{method:'70_30_TIME_ORDERED_TRAIN_HOLDOUT',threshold_tests:[{},{}],actionable:[{sport:'NFL',lane:'PROP',market:'PASSING_YARDS',sample:41}],automatic_model_changes:false},
    fantasy:{weekly:{tracked:503,settled:29,proof_status:'BUILDING_FORWARD_SAMPLE'}},
    ask:{status:'READY',tracked:195,grounded_current:160,reporting_claim_count:7,supported_reporting_claim_count:7,
      retrieval_golden_cases:5,retrieval_golden_passed:5},
    health:{status:'ok',generated_at:'2026-10-08T05:01:00Z',sources:{nfl_scores:true,mlb_scores:false}},
  })
  assert.equal(result.official.published,1)
  assert.equal(result.official.settled,1)
  assert.equal(result.official.losses,1)
  assert.equal(result.official.units,-1)
  assert.equal(result.forward.tracked,7831)
  assert.equal(result.forward.settled,6006)
  assert.equal(result.calibration.thresholdTests,2)
  assert.equal(result.calibration.researchCandidates,1)
  assert.equal(result.calibration.automaticallyChanged,false)
  assert.equal(result.fantasy.lanes.find(x=>x.key==='weekly').settled,29)
  assert.equal(result.ask.evaluated,195)
  assert.equal(result.ask.supportedClaims,7)
  assert.deepEqual(result.sources,[{key:'nfl_scores',present:true},{key:'mlb_scores',present:false}])
})

test('Missing research records display unknown values, never invented zero or READY', () => {
  const r=researchSummary()
  assert.equal(r.official.published,null)
  assert.equal(r.official.settled,null)
  assert.equal(r.forward.tracked,null)
  assert.equal(r.calibration.thresholdTests,null)
  assert.equal(r.ask.evaluated,null)
  assert.equal(r.fantasy.lanes.find(x=>x.key==='weekly').tracked,null)
  assert.equal(r.official.status,'UNKNOWN')
  assert.equal(r.forward.status,'UNKNOWN')
  assert.equal(r.calibration.researchCandidates,null)
  assert.equal(r.sources.length,0)
})

test('Selectivity auto-promotion flag must be explicitly true; missing does not promote', () => {
  assert.equal(researchSummary({selectivity:{automatic_model_changes:'true'}}).calibration.automaticallyChanged,false)
  assert.equal(researchSummary({selectivity:{automatic_model_changes:true}}).calibration.automaticallyChanged,true)
})

test('Research output excludes arbitrary private fields and rejects invalid numeric metrics', () => {
  const r=researchSummary({
    performance:{token:'DO_NOT_LEAK',official:{published:'NaN',wins:-10,losses:'',units:'secret'}},
    ask:{tracked:'garbage',reporting_claim_count:-1},
  })
  assert.equal(JSON.stringify(r).includes('DO_NOT_LEAK'),false)
  assert.equal(r.official.published,null)
  assert.equal(r.official.wins,null)
  assert.equal(r.official.losses,null)
  assert.equal(r.official.units,null)
  assert.equal(r.ask.evaluated,null)
  assert.equal(r.ask.claimSamples,null)
})
