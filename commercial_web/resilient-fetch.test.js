import test from 'node:test'
import assert from 'node:assert/strict'
import { resilientFetch, circuitSnapshot, resetCircuitBreakersForTests } from './resilient_fetch.js'

test('dependency timeout aborts hung fetch', async () => {
  resetCircuitBreakersForTests()
  const fetchImpl = (_url, options = {}) => new Promise((_resolve, reject) => {
    options.signal?.addEventListener('abort', () => {
      const error = new Error('aborted')
      error.name = 'AbortError'
      reject(error)
    })
  })

  await assert.rejects(
    resilientFetch('https://example.com', {}, {
      timeoutMs: 10,
      retries: 0,
      breakerKey: 'timeout-test',
      fetchImpl,
    }),
    error => error?.code === 'DEPENDENCY_TIMEOUT'
  )
})

test('transient 503 is retried once and success resets circuit', async () => {
  resetCircuitBreakersForTests()
  let calls = 0
  const fetchImpl = async () => {
    calls += 1
    return calls === 1 ? { status: 503, ok: false } : { status: 200, ok: true }
  }

  const response = await resilientFetch('https://example.com', {}, {
    timeoutMs: 100,
    retries: 1,
    retryDelayMs: 0,
    breakerKey: 'retry-test',
    fetchImpl,
    sleep: async () => {},
  })

  assert.equal(response.status, 200)
  assert.equal(calls, 2)
  assert.deepEqual(circuitSnapshot('retry-test'), { failures: 0, open_until: 0 })
})

test('circuit opens after repeated dependency failures', async () => {
  resetCircuitBreakersForTests()
  let calls = 0
  const fetchImpl = async () => {
    calls += 1
    throw new Error('network down')
  }
  const now = () => 1000

  for (let i = 0; i < 2; i += 1) {
    await assert.rejects(
      resilientFetch('https://example.com', {}, {
        retries: 0,
        breakerKey: 'breaker-test',
        failureThreshold: 2,
        cooldownMs: 5000,
        fetchImpl,
        now,
      })
    )
  }

  const snapshot = circuitSnapshot('breaker-test')
  assert.equal(snapshot.failures, 2)
  assert.equal(snapshot.open_until, 6000)

  await assert.rejects(
    resilientFetch('https://example.com', {}, {
      retries: 0,
      breakerKey: 'breaker-test',
      failureThreshold: 2,
      cooldownMs: 5000,
      fetchImpl,
      now,
    }),
    error => error?.code === 'CIRCUIT_OPEN'
  )

  assert.equal(calls, 2)
})

test('non-retriable 404 passes through and does not open circuit', async () => {
  resetCircuitBreakersForTests()
  let calls = 0
  const fetchImpl = async () => {
    calls += 1
    return { status: 404, ok: false }
  }

  const response = await resilientFetch('https://example.com', {}, {
    retries: 2,
    breakerKey: '404-test',
    fetchImpl,
  })

  assert.equal(response.status, 404)
  assert.equal(calls, 1)
  assert.deepEqual(circuitSnapshot('404-test'), { failures: 0, open_until: 0 })
})
