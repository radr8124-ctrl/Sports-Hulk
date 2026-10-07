import { unlink } from 'node:fs/promises'

const failedPath = '/tmp/sports-hulk-output-validation-failed.jsonl'
const evalPath = '/tmp/sports-hulk-output-validation-eval.jsonl'

await unlink(failedPath).catch(() => {})
await unlink(evalPath).catch(() => {})

process.env.ASK_RETRIEVAL_PATH = '/home/ubuntu/sports-hulk/commercial_web/test-fixtures/reporting-unsafe-source.json'
process.env.ASK_NOW_ISO = '2026-10-07T12:00:00Z'
process.env.ASK_FAILED_QUEUE_PATH = failedPath
process.env.ASK_EVAL_LEDGER_PATH = evalPath
process.env.PORT = '8538'

await import('../server.js')
