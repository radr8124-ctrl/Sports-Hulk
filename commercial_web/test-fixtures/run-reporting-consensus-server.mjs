process.env.ASK_RETRIEVAL_PATH = '/home/ubuntu/sports-hulk/commercial_web/test-fixtures/reporting-consensus-retrieval.json'
process.env.ASK_NOW_ISO = '2026-10-07T12:00:00Z'
process.env.PORT = '8534'

await import('../server.js')
