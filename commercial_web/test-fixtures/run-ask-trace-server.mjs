import { unlink } from 'node:fs/promises'

const tracePath = '/tmp/sports-hulk-ask-trace.jsonl'
const evalPath = '/tmp/sports-hulk-ask-trace-eval.jsonl'
const failedPath = '/tmp/sports-hulk-ask-trace-failed.jsonl'

await unlink(tracePath).catch(() => {})
await unlink(evalPath).catch(() => {})
await unlink(failedPath).catch(() => {})

process.env.ASK_RETRIEVAL_PATH = '/home/ubuntu/sports-hulk/commercial_web/test-fixtures/reporting-fact-source-retrieval.json'
process.env.ASK_TRACE_LEDGER_PATH = tracePath
process.env.ASK_EVAL_LEDGER_PATH = evalPath
process.env.ASK_FAILED_QUEUE_PATH = failedPath
process.env.PORT = '8540'

await import('../server.js')
