export function claimEvidenceRows(claimSources = [], limit = 4) {
  const rows = []
  const seen = new Set()

  for (const item of Array.isArray(claimSources) ? claimSources : []) {
    const claim = String(item?.claim || '').trim()
    const source = String(item?.source || item?.label || '').trim()
    if (!claim || !source) continue

    const evidenceId = String(item?.evidence_id || '').trim()
    const key = [claim, source, evidenceId].join('|')
    if (seen.has(key)) continue
    seen.add(key)

    rows.push({
      claim,
      source,
      url: item?.url || null,
      evidence_type: item?.evidence_type || null,
      evidence_id: evidenceId || null,
      updated_at: item?.updated_at || null,
      tier: item?.tier || null,
    })

    if (rows.length >= Math.max(1, Number(limit) || 4)) break
  }

  return rows
}
