import {useEffect,useState} from 'react'
import {curateSportsNews} from '../news_curation.js'

// Both Home and the full newsroom see the same collection, provenance and
// honest failure status; a failed fetch cannot silently mean no news.
export default function useSportsNews(){
 const [value,setValue]=useState({
  loading:true,status:'LOADING',stories:[],reason:null,generatedAt:null,rawNewsRows:0,
 })
 useEffect(()=>{
  let live=true
  const refresh=async()=>{
   try{
    const response=await fetch('/ask_retrieval.json?ts='+Date.now(),{cache:'no-store'})
    if(!response.ok)throw new Error('Article feed HTTP '+response.status)
    const body=await response.json()
    const result=curateSportsNews(body,Date.now())
    if(live)setValue({...result,loading:false})
   }catch{
    if(live)setValue({loading:false,status:'DATA_SOURCE_FAILURE',stories:[],
      reason:'FETCH_OR_PARSE_FAILED',generatedAt:null,rawNewsRows:0})
   }
  }
  refresh()
  const interval=setInterval(refresh,5*60*1000)
  return()=>{live=false;clearInterval(interval)}
 },[])
 return value
}
