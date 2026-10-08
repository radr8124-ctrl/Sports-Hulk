// Only server-assigned permissions or explicit server-side allowlists grant
// the ability to replace the global Survivor pool sheet.
// The user-controlled user_metadata field must NEVER grant privileges.
export function canManageSurvivorPool(user, { ids = '', emails = '' } = {}) {
  if (!user || !user.id) return false
  const admin = user.app_metadata || {}
  const allowedIds = String(ids || '').split(',').map(x => x.trim()).filter(Boolean)
  const allowedEmails = String(emails || '').split(',').map(x => x.trim().toLowerCase()).filter(Boolean)
  const roleSet = new Set([
    admin.role, ...(Array.isArray(admin.roles) ? admin.roles : []),
  ].filter(Boolean).map(x => String(x).toLowerCase()))
  return admin.survivor_pool_manager === true ||
    roleSet.has('survivor_pool_manager') ||
    allowedIds.includes(String(user.id)) ||
    (typeof user.email === 'string' &&
      allowedEmails.includes(user.email.trim().toLowerCase()))
}
