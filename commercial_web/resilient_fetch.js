const CIRCUITS = new Map()

function makeError(message, code, status = null) {
  const error = new Error(message)
  error.code = code
  if (status != null) error.status = status
  return error
}

function circuitState(key) {
  const normalized = String(key || 'default')
  if (!CIRCUITS.has(normalized)) CIRCUITS.set(normalized, { failures: 0, open_until: 0 })
  return CIRCUITS.get(normalized)
}

function isRetriableStatus(status) {
  return status === 408 || status === 429 || status >= 500
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, Math.max(0, Number(ms) || 0)))
}

export async function resilientFetch(url, options = {}, config = {}) {
  const timeoutMs = Math.max(1, Number(config.timeoutMs) || 5000)
  const retries = Math.max(0, Number(config.retries) || 0)
  const retryDelayMs = Math.max(0, Number(config.retryDelayMs) || 75)
  const failureThreshold = Math.max(1, Number(config.failureThreshold) || 3)
  const cooldownMs = Math.max(1, Number(config.cooldownMs) || 30000)
  const breakerKey = String(config.breakerKey || 'default')
  const fetchImpl = config.fetchImpl || globalThis.fetch
  const now = config.now || (() => Date.now())
  const sleep = config.sleep || wait
  const state = circuitState(breakerKey)

  if (state.open_until > now()) {
    throw makeError('Dependency circuit is open', 'CIRCUIT_OPEN')
  }

  let lastError = null

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)

    try {
      const response = await fetchImpl(url, { ...options, signal: controller.signal })
      clearTimeout(timer)

      if (!isRetriableStatus(Number(response?.status || 0))) {
        state.failures = 0
        state.open_until = 0
        return response
      }

      lastError = makeError(`Dependency returned ${response.status}`, 'RETRIABLE_HTTP_STATUS', response.status)
    } catch (error) {
      clearTimeout(timer)
      const aborted = controller.signal.aborted || error?.name === 'AbortError'
      lastError = aborted
        ? makeError('Dependency request timed out', 'DEPENDENCY_TIMEOUT')
        : error
    }

    if (attempt < retries) await sleep(retryDelayMs * (attempt + 1))
  }

  state.failures += 1
  if (state.failures >= failureThreshold) {
    state.open_until = now() + cooldownMs
  }

  throw lastError || makeError('Dependency request failed', 'DEPENDENCY_FAILED')
}

export function circuitSnapshot(key) {
  const state = circuitState(key)
  return { failures: state.failures, open_until: state.open_until }
}

export function resetCircuitBreakersForTests() {
  CIRCUITS.clear()
}
