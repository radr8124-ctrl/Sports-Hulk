import test from 'node:test'
import assert from 'node:assert/strict'
import {previewFantasyRosterFile} from './src/fantasyRosterFileParser.js'

test('ESPN-style player column CSV imports names only, never private metadata',()=>{
  const content='Player,Position,Team,Owner Email\nJosh Allen,QB,BUF,private@example.test\nTrey McBride,TE,ARI,private@example.test\n'
  const r=previewFantasyRosterFile(content,'ESPN_roster.csv')
  assert.deepEqual(r.names,['Josh Allen','Trey McBride'])
  assert.equal(r.count,2)
  assert.equal(r.column,'Player')
  assert.equal(r.format,'CSV')
  assert.equal(JSON.stringify(r).includes('private@example.test'),false)
  assert.match(r.note,/Nothing is saved or sent/)
})

test('Yahoo-style quoted names and embedded commas parse safely',()=>{
  const data='"Player Name","Team","Status"\r\n"Allen, Josh","BUF","ACTIVE"\r\n"CeeDee Lamb","DAL","ACTIVE"'
  const r=previewFantasyRosterFile(data,'yahoo.csv')
  assert.deepEqual(r.names,['Josh Allen','CeeDee Lamb'])
  assert.equal(r.reformatted,1)
  assert.equal(r.column,'Player Name')
  assert.equal(r.count,2)
})

test('CBS-style Name column and Excel BOM are accepted',()=>{
  const d='\uFEFFName,Position\r\nJahmyr Gibbs,RB\r\nDallas Cowboys D/ST,DEF'
  assert.deepEqual(previewFantasyRosterFile(d,'cbs.csv').names,['Jahmyr Gibbs','Dallas Cowboys D/ST'])
})

test('plain text one name per line never needs a provider login',()=>{
  const r=previewFantasyRosterFile('Josh Allen\n\nJames Cook\nTrey McBride','names.txt')
  assert.deepEqual(r.names,['Josh Allen','James Cook','Trey McBride'])
  assert.equal(r.format,'TXT')
})

test('single-column CSV lists without headings are handled',()=>{
  const r=previewFantasyRosterFile('Josh Allen\nJames Cook\n','league.csv')
  assert.equal(r.count,2)
  assert.equal(r.column,'First column (one name per row)')
})

test('duplicate players, blank cells, unsafe formula strings are not imported',()=>{
  const d='Player,Position\nJosh Allen,QB\njosh allen,QB\n,QB\n=HYPERLINK("abc"),RB\nTyler Lockett,WR'
  const r=previewFantasyRosterFile(d,'roster.csv')
  assert.deepEqual(r.names,['Josh Allen','Tyler Lockett'])
  assert.equal(r.duplicates,1)
  assert.equal(r.skipped,2)
})

test('multiple columns without player header refuse guessing',()=>{
  assert.throws(()=>previewFantasyRosterFile('Team,Points,Record\nBUF,100,5-0','roster.csv'),/Could not identify the player column/)
})

test('CSV with unclosed quoted field returns a helpful error',()=>{
  assert.throws(()=>previewFantasyRosterFile('Player,Team\n"Josh Allen,BUF','roster.csv'),/unfinished quoted field/)
})

test('unsupported format, oversized data, blank data and zero valid players fail closed',()=>{
  assert.throws(()=>previewFantasyRosterFile('Josh Allen','file.xlsx'),/Choose a .csv or .txt/)
  assert.throws(()=>previewFantasyRosterFile(' ','file.csv'),/empty/)
  assert.throws(()=>previewFantasyRosterFile('x'.repeat(257*1024),'file.csv'),/File is too large/)
  assert.throws(()=>previewFantasyRosterFile('Player\n=CMD\n#INVALID\n','file.csv'),/No valid player names/)
})

test('more than 60 valid names is rejected, not silently truncated',()=>{
  const data='Player\n'+Array.from({length:61},(_,i)=>'Player '+(i+1)).join('\n')
  assert.throws(()=>previewFantasyRosterFile(data,'61_players.csv'),/More than 60 distinct players/)
})

test('only name fields are returned, not whole CSV rows or provider secrets',()=>{
  const r=previewFantasyRosterFile('Player,oauth_access_token,yahoo_cookie\nJames Cook,veryprivate123,privatecookie123','roster.csv')
  const output=JSON.stringify(r)
  assert.ok(!output.includes('veryprivate123'))
  assert.ok(!output.includes('privatecookie123'))
})

test('one file with 1001 rows is limited',()=>{
  const d='Player\n'+Array.from({length:1001},(_,i)=>'Player '+(i+1)).join('\n')
  assert.throws(()=>previewFantasyRosterFile(d,'big.csv'),/Too many rows/)
})
