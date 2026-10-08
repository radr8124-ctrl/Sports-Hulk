import path from 'node:path'

// Unrecognized JSON, JS, CSS and API paths must fail closed.
// Browser navigation to extensionless paths can still use the SPA entry point.
export function missingStaticResourceKind(pathname) {
  const value = String(pathname || '').split('?')[0].trim()
  if (value === '/api' || value.startsWith('/api/')) return 'API_NOT_FOUND'
  const ext = path.posix.extname(value).toLowerCase()
  if (ext && ext !== '.html') return 'STATIC_NOT_FOUND'
  return 'SPA_FALLBACK'
}

export function pathIsInsideDir(directory, filePath) {
  const root = path.resolve(directory)
  const candidate = path.resolve(filePath)
  return candidate === root || candidate.startsWith(root + path.sep)
}
