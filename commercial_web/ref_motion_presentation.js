// Automatic referee calls are purely theatrical; no live sports inference.
export const REF_AUTO_FIRST_DELAY_MS=12000
export const REF_AUTO_REPEAT_DELAY_MS=27000
export const REF_MANUAL_PAUSE_MS=40000

const CALLS=['flag','strike','whistle']
const SECTION_CALL={
  welcome:'flag',
  scores:'strike',
  signals:'flag',
  news:'whistle',
  picks:'flag',
  learning:'strike',
}

export function nextRefCall(section,previous='idle'){
  const preferred=SECTION_CALL[section]||'flag'
  if(preferred!==previous)return preferred
  return CALLS[(CALLS.indexOf(preferred)+1)%CALLS.length]
}

export function canAutoPerform({
  enabled=false,reducedMotion=false,visible=false,minimized=false,expanded=false,hovered=false,
}={}){
  return Boolean(enabled&&!reducedMotion&&visible&&!minimized&&!expanded&&!hovered)
}

export function nextRefDelay({hasPerformed=false,manualPauseUntil=0,now=Date.now()}={}){
  const desired=hasPerformed?REF_AUTO_REPEAT_DELAY_MS:REF_AUTO_FIRST_DELAY_MS
  return Math.max(desired,Math.max(0,manualPauseUntil-now))
}
