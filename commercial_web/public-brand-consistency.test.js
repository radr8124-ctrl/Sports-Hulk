import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const directory = path.dirname(fileURLToPath(import.meta.url))
const source = name => readFileSync(path.join(directory, 'src', name), 'utf8')

test('active customer-facing account and Survivor UI uses Sports Zenith branding', () => {
  const files = [
    'brandConfig.js',
    'AuthShell.jsx',
    'SurvivorPickEditor.jsx',
    'SurvivorScoreCards.jsx',
  ]
  for (const file of files) {
    const content = source(file)
    assert.doesNotMatch(content, /Sports[ -]HULK/i, 'Legacy customer-visible brand in ' + file)
  }
  assert.match(source('brandConfig.js'), /PUBLIC_BRAND = 'Sports Zenith'/)
  assert.match(source('SurvivorPickEditor.jsx'), /Saved in Sports Zenith/)
  assert.match(source('SurvivorScoreCards.jsx'), /Saved in Sports Zenith/)
})
