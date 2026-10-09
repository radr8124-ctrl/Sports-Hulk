// Sports Zenith: don't turn archived prices or a research model into real bets.
export function showFrozenNFLResearch(data = {}, nowMs = Date.now()) {
  const schema = 'ZENITH_READONLY_NFL_NINE_FEATURE_FROZEN_GAME_INTELLIGENCE_V1'
  if (data?.schema !== schema ||
      data?.wagers_created_or_bets_promoted !== false ||
      data?.historic_2025_holdout_model_better_than_market !== false ||
      data?.real_book_executability_verified !== false ||
      data?.market_source_cannot_upgrade_stale_primary_NFL_live_best_bets !== true)
    return {status:'UNVERIFIED_SOURCE', rows:[], blocked:true}
  const incoming = Array.isArray(data.rows) ? data.rows : []
  const seen=new Set()
  const clean=[]
  for(const r of incoming) {
    const id=String(r?.event_id||'')
    const kickoff=Date.parse(r?.kickoff_utc||'')
    const quote=Date.parse(r?.book_quote_last_updated_at_utc||'')
    const model=Number(r?.forecast_home_pct)
    const market=Number(r?.book_market_fair_home_pct)
    const originalQuotePrice=Number(r?.original_home_american_price)
    if(!id || seen.has(id) || !Number.isFinite(kickoff) || kickoff<=nowMs ||
       !Number.isFinite(quote) || quote>nowMs || quote>=kickoff ||
       r?.approved_play !== false ||
       r?.model_beats_market_out_of_sample_proven !== false ||
       r?.actual_sportsbook_executable_current_price_verified !== false ||
       r?.model_uses_market_input !== true ||
       r?.score_form_model_historical_2025_worse_than_market_baseline !== true ||
       r?.score_or_game_result_included !== false ||
       r?.book_name !== 'Pinnacle' ||
       !Number.isFinite(model) || model<=0 || model>=100 ||
       !Number.isFinite(market) || market<=0 || market>=100 ||
       Math.abs(model-market)>40 ||
       !Number.isInteger(originalQuotePrice) || Math.abs(originalQuotePrice)<100 ||
       !r.away || !r.home || r.away===r.home) continue
    seen.add(id)
    clean.push({...r, priceAgeHours:(nowMs-quote)/3.6e6,
      originalPriceTooOldForLiveContext:(nowMs-quote)>24*3600*1000})
  }
  clean.sort((a,b)=>a.kickoff_utc.localeCompare(b.kickoff_utc)||a.event_id.localeCompare(b.event_id))
  return {status:'FROZEN_RESEARCH',blocked:true,rows:clean,
    originalLedgerSha:data.source_original_nine_feature_ledger_sha256||'',
    context:'Market-assisted 9-feature score-form challenger (not an independent proven advantage).'}
}
