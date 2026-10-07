export function survivorLinkNames(value) {
  const raw = Array.isArray(value) ? value : value ? [value] : []
  return [...new Set(raw.map(item => String(item || '').trim()).filter(Boolean))]
}

export function survivorEntryOwnedByOther(registry = {}, currentUserId, entryName) {
  const target = String(entryName || '').trim()
  if (!target) return false

  return Object.entries(registry || {}).some(([userId, stored]) => {
    if (String(userId) === String(currentUserId)) return false
    return survivorLinkNames(stored).includes(target)
  })
}

export function addSurvivorLink(registry = {}, userId, entryName) {
  const target = String(entryName || '').trim()
  const current = survivorLinkNames(registry?.[userId])
  if (target && !current.includes(target)) current.push(target)
  return {
    ...(registry || {}),
    [userId]: current,
  }
}
