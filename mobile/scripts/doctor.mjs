import {execFileSync} from 'node:child_process'
import {existsSync} from 'node:fs'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {normalizeZenithApiOrigin} from '../../commercial_web/src/nativeApiBridge.js'

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..')
const command=(cmd,args=[])=>{
 try{return execFileSync(cmd,args,{encoding:'utf8',timeout:5000,stdio:['ignore','pipe','ignore']}).trim().split('\n')[0]}
 catch{return null}
}
const origin=normalizeZenithApiOrigin(process.env.ZENITH_MOBILE_API_ORIGIN)
const state={
  node:process.versions.node,
  node22OrLater:Number(process.versions.node.split('.')[0])>=22,
  websiteSharedSource:existsSync(resolve(root,'../commercial_web/src/App.jsx')),
  androidScaffoldExists:existsSync(resolve(root,'android/app/src/main/AndroidManifest.xml')),
  iosScaffoldExists:existsSync(resolve(root,'ios/App/App.xcodeproj/project.pbxproj')),
  approvedHttpsBackendConfigured:Boolean(origin),
  javaInstalled:Boolean(command('java',['-version'])),
  androidSdkConfigured:Boolean(process.env.ANDROID_HOME||process.env.ANDROID_SDK_ROOT),
  isMac:process.platform==='darwin',
  xcodeAvailable:Boolean(command('xcodebuild',['-version'])),
  realDeviceSignInVerified:false,
  storeAccountsAndSigningVerified:false,
  legalStoreReviewApproved:false,
}
for(const [k,v] of Object.entries(state)) console.log(`${k}: ${v}`)
if (!state.node22OrLater || !state.websiteSharedSource) process.exitCode=2
