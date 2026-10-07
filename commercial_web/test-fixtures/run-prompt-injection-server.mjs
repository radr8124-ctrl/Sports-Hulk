process.env.ASK_RETRIEVAL_PATH = '/home/ubuntu/sports-hulk/commercial_web/test-fixtures/prompt-injection-retrieval.json'
process.env.ASK_NOW_ISO = '2026-10-07T12:00:00Z'
process.env.PORT = '8542'

await import('../server.js')
