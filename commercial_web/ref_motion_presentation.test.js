import test from 'node:test'
import assert from 'node:assert/strict'
import {
  REF_AUTO_FIRST_DELAY_MS, REF_AUTO_REPEAT_DELAY_MS, REF_MANUAL_PAUSE_MS,
  nextRefCall, canAutoPerform, nextRefDelay,
} from './ref_motion_presentation.js'

test('automatic Ref calls have readable, unhurried pacing',()=>{
  assert.equal(REF_AUTO_FIRST_DELAY_MS,12000)
  assert.equal(REF_AUTO_REPEAT_DELAY_MS,27000)
  assert.equal(REF_MANUAL_PAUSE_MS,40000)
})

test('the referee makes different sports calls depending on the page section',()=>{
  assert.equal(nextRefCall('welcome','idle'),'flag')
  assert.equal(nextRefCall('scores','idle'),'strike')
  assert.equal(nextRefCall('news','idle'),'whistle')
  assert.equal(nextRefCall('learning','idle'),'strike')
})

test('the referee rotates away from immediately repeating the same call',()=>{
  assert.notEqual(nextRefCall('scores','strike'),'strike')
  assert.notEqual(nextRefCall('news','whistle'),'whistle')
  assert.equal(nextRefCall('not-a-section','idle'),'flag')
  for(const current of ['flag','strike','whistle']){
    assert.ok(['flag','strike','whistle'].includes(nextRefCall('welcome',current)))
  }
})

test('autoplay is blocked when hidden, reducing motion, minimized, hovering or using controls',()=>{
  const base={enabled:true,reducedMotion:false,visible:true,minimized:false,expanded:false,hovered:false}
  assert.equal(canAutoPerform(base),true)
  for (const change of [
    {enabled:false},{reducedMotion:true},{visible:false},{minimized:true},{expanded:true},{hovered:true},
  ]) assert.equal(canAutoPerform({...base,...change}),false)
})

test('long pause after manually opening the referee and between automatic calls',()=>{
  assert.equal(nextRefDelay({hasPerformed:false,manualPauseUntil:0,now:1000}),12000)
  assert.equal(nextRefDelay({hasPerformed:true,manualPauseUntil:0,now:1000}),27000)
  assert.equal(nextRefDelay({hasPerformed:false,manualPauseUntil:41000,now:5000}),36000)
  assert.equal(nextRefDelay({hasPerformed:true,manualPauseUntil:41000,now:5000}),36000)
})
