import { unlink } from 'node:fs/promises'

const tempEval = '/tmp/sports-hulk-golden-eval.jsonl'
const tempFailed = '/tmp/sports-hulk-golden-failed.jsonl'

await unlink(tempEval).catch(() => {})
await unlink(tempFailed).catch(() => {})

process.env.ASK_RETRIEVAL_PATH = '/home/ubuntu/sports-hulk/commercial_web/test-fixtures/reporting-golden-retrieval.json'
process.env.ASK_NOW_ISO = '2026-10-07T12:00:00Z'
process.env.ASK_EVAL_LEDGER_PATH = tempEval
process.env.ASK_FAILED_QUEUE_PATH = tempFailed
process.env.PORT = '8535'

await import('../server.js')
