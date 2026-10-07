import { unlink } from 'node:fs/promises'

const evalPath = '/tmp/sports-hulk-claim-coverage-eval.jsonl'
const clickPath = '/tmp/sports-hulk-claim-coverage-click.jsonl'

await unlink(evalPath).catch(() => {})
await unlink(clickPath).catch(() => {})

process.env.ASK_RETRIEVAL_PATH = '/home/ubuntu/sports-hulk/commercial_web/test-fixtures/reporting-fact-source-retrieval.json'
process.env.ASK_EVAL_LEDGER_PATH = evalPath
process.env.ASK_SOURCE_CLICK_LEDGER_PATH = clickPath
process.env.PORT = '8533'

await import('../server.js')
