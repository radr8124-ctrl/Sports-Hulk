process.env.ASK_RETRIEVAL_PATH = '/home/ubuntu/sports-hulk/commercial_web/test-fixtures/reporting-freshness-retrieval.json'
process.env.ASK_CONTEXT_PATH = '/home/ubuntu/sports-hulk/commercial_web/test-fixtures/reporting-conflict-context.json'
process.env.ASK_NOW_ISO = '2026-10-07T12:00:00Z'
process.env.PORT = '8531'

await import('../server.js')
