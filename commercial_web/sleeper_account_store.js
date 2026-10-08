// Saves a public Sleeper read-only roster into an authenticated Sports Zenith
// user's private fantasy tables. No provider passwords or OAuth claims.
export function sleeperLeaguePayload(ownerId, team, previous = {}, at = new Date().toISOString()) {
  if (!ownerId || !team || !team.league_id || !team.user_id) {
    throw new Error('Verified user and public Sleeper league are required.')
  }
  const previousContext = previous.provenance && typeof previous.provenance === 'object'
    ? previous.provenance : {}
  if (previousContext.sleeper_user_id &&
    previousContext.sleeper_user_id !== team.user_id) {
    const error = new Error('This saved league belongs to a different Sleeper username. Resolve the existing link first.')
    error.code = 'SLEEPER_OWNER_MISMATCH'
    throw error
  }
  return {
    owner_id:ownerId,
    platform:'sleeper',
    provider_league_id:team.league_id,
    league_name:team.league_name,
    season:team.season,
    scoring: team.scoring || {},
    roster_settings: team.roster_settings || {},
    sync_status:'PUBLIC_READ_ONLY',
    last_synced_at:at,
    provenance:{
      ...previousContext,
      setup_method:'sleeper_username_public_readonly',
      sleeper_user_id:team.user_id,
      sleeper_username:team.username,
      sleeper_roster_id:team.roster_id,
      provider_identity_verified:false,
      source:'SLEEPER_PUBLIC_API',
      sync_updated_at:at,
    },
  }
}

export function sleeperRosterPayload(team, leagueId, at = new Date().toISOString()) {
  if (!leagueId || !team || !team.roster_id) throw new Error('Sleeper roster must belong to a saved league.')
  return {
    league_id:leagueId,
    provider_team_id:'sleeper-'+team.roster_id,
    team_name:team.team_name,
    roster:team.roster,
    starters:team.starters,
    bench:team.bench,
    available_players:[],
    updated_at:at,
  }
}

export async function saveSleeperFantasyTeam(client, ownerId, team) {
  if (!client || !ownerId) {
    const err = new Error('Sign in to Sports Zenith before importing a fantasy roster.')
    err.code = 'AUTH_REQUIRED'
    throw err
  }
  const selection = await client.database.from('fantasy_leagues')
    .select('id,provenance')
    .eq('owner_id',ownerId)
    .eq('platform','sleeper')
    .eq('provider_league_id',team.league_id)
    .limit(1)
  if (selection.error) throw new Error('Your private fantasy leagues could not be checked.')
  const existing = Array.isArray(selection.data) ? selection.data[0] : null
  const now = new Date().toISOString()
  const leagueRecord = sleeperLeaguePayload(ownerId,team,existing || {},now)
  let leagueId = existing?.id || null
  let inserted = false

  if (existing) {
    const result = await client.database.from('fantasy_leagues')
      .update(leagueRecord)
      .eq('id',existing.id).eq('owner_id',ownerId)
    if (result.error) throw new Error('The saved Sleeper league could not be updated.')
  } else {
    const result = await client.database.from('fantasy_leagues')
      .insert(leagueRecord).select('id')
    if (result.error || !result.data?.[0]?.id) {
      throw new Error('The Sleeper league could not be saved to your account.')
    }
    leagueId = result.data[0].id
    inserted = true
  }

  const undoNewLeague = async () => {
    if (!inserted) return
    try { await client.database.from('fantasy_leagues').delete()
      .eq('id',leagueId).eq('owner_id',ownerId) } catch {}
  }

  try {
    const rosterRecord = sleeperRosterPayload(team,leagueId,now)
    const found = await client.database.from('fantasy_rosters')
      .select('id').eq('league_id',leagueId)
      .eq('provider_team_id',rosterRecord.provider_team_id).limit(1)
    if (found.error) throw new Error('The existing fantasy roster could not be checked.')
    const savedRoster = Array.isArray(found.data) ? found.data[0] : null
    let rosterId = savedRoster?.id || null
    if (savedRoster) {
      const result = await client.database.from('fantasy_rosters')
        .update(rosterRecord).eq('id',rosterId).eq('league_id',leagueId)
      if (result.error) throw new Error('The imported fantasy roster could not be updated.')
    } else {
      const result = await client.database.from('fantasy_rosters')
        .insert(rosterRecord).select('id')
      if (result.error || !result.data?.[0]?.id) throw new Error('The imported fantasy roster could not be saved.')
      rosterId = result.data[0].id
    }
    return {
      status:'LINKED_PUBLIC_READ_ONLY',
      league_id:leagueId,
      roster_id:rosterId,
      provider_league_id:team.league_id,
      platform:'sleeper',
      league_name:team.league_name,
      team_name:team.team_name,
      season:team.season,
      roster_count:team.roster.length,
      last_synced_at:now,
      source:'SLEEPER_PUBLIC_API',
      identity_verified:false,
    }
  } catch (error) {
    await undoNewLeague()
    throw error
  }
}
