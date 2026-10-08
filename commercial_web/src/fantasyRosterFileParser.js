// Local-only provider-neutral roster import (CSV or plain text).
// Parsing never transmits, evaluates, or saves source files.
const NAME_COLUMNS = new Set(['player', 'player name', 'playername', 'players', 'name', 'full name', 'fullname', 'athlete', 'athlete name'])
const MAX_PLAYERS = 60
const MAX_ROWS = 1000

function parseDelimitedRows(input, separator=',') {
  const rows = []
  let field = ''
  let row = []
  let quoted = false
  const pushRow = () => {
    row.push(field)
    field = ''
    if (row.some(cell => cell.trim())) rows.push(row)
    row = []
    if (rows.length > MAX_ROWS) throw new Error('Too many rows. Import at most 1,000 CSV rows.')
  }
  for(let i=0;i<input.length;i++){
    const ch=input[i]
    if (quoted) {
      if (ch === '"') {
        if (input[i+1] === '"') { field+='"'; i++ }
        else quoted=false
      } else field+=ch
    } else if (ch === '"' && field.length===0) {
      quoted=true
    } else if (ch === separator) {
      row.push(field);field=''
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && input[i+1] === '\n') i++
      pushRow()
    } else field+=ch
    if (field.length > 1000) throw new Error('CSV contains a field longer than 1,000 characters.')
  }
  if (quoted) throw new Error('CSV contains an unfinished quoted field.')
  if (field || row.length) pushRow()
  return rows
}

function canonicalHeading(value){
  return String(value||'').trim().toLowerCase().replace(/[_-]+/g,' ').replace(/\s+/g,' ')
}

function cleanName(value){
  let name=String(value||'').trim().replace(/\s+/g,' ')
  if (!name || name.length>120 || name.length<2 || /[<>\r\n]/.test(name)) return null
  if (/^[-=#@+]/.test(name)) return null
  // The current manual editor accepts commas as separators, so never pass
  // an embedded comma as an individual imported name.
  if (name.includes(',')) {
    const pieces=name.split(',').map(x=>x.trim())
    if(pieces.length!==2 || !pieces[0] || !pieces[1]) return null
    name=pieces[1]+' '+pieces[0]
  }
  return name
}
export function previewFantasyRosterFile(content, filename='roster.csv') {
  if (typeof content!=='string' || !content.trim()) throw new Error('This file is empty.')
  if (new TextEncoder().encode(content).length > 256*1024) throw new Error('File is too large. Use a CSV or TXT file smaller than 256 KB.')
  const ext=String(filename||'').trim().toLowerCase().split('.').pop()
  if (!['csv','txt'].includes(ext)) throw new Error('Choose a .csv or .txt roster file (export Excel as CSV first).')
  const source=content.replace(/^\uFEFF/,'')
  const rows=ext==='txt'
    ? source.split(/\r?\n/).filter(line=>line.trim()).map(line=>[line.trim()])
    : parseDelimitedRows(source, ',')
  if (!rows.length) throw new Error('No roster rows found.')
  if (rows.length>MAX_ROWS) throw new Error('Too many rows. Import at most 1,000 roster rows.')
  const header=rows[0].map(canonicalHeading)
  let index=header.findIndex(cell=>NAME_COLUMNS.has(cell))
  const headerFound=index>=0
  if (index<0) {
    if (rows.some(row=>row.length!==1)) {
      throw new Error('Could not identify the player column. Use a CSV with a Player, Player Name or Name heading, or upload a one-name-per-line TXT file.')
    }
    index=0
  }
  const candidates=headerFound?rows.slice(1):rows
  const names=[]
  const seen=new Set()
  let skipped=0,duplicates=0,reformatted=0
  for(const row of candidates){
    const val=cleanName(row[index])
    if (!val) { skipped++; continue }
    const key=val.toLowerCase()
    if (seen.has(key)) { duplicates++; continue }
    if (String(row[index]||'').includes(',')) reformatted++
    seen.add(key);names.push(val)
    if(names.length>MAX_PLAYERS) throw new Error('More than 60 distinct players found. Remove extra rows and try again.')
  }
  if(!names.length) throw new Error('No valid player names found. Review the file headers and player column.')
  return {
    names,
    count:names.length,
    sourceRows:candidates.length,
    duplicates,
    skipped,
    reformatted,
    column:headerFound?rows[0][index]:'First column (one name per row)',
    format:ext.toUpperCase(),
    note:'Preview only. Files stay in your browser. Nothing is saved or sent until you choose Analyze & save my team.',
  }
}
