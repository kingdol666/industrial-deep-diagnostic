import fs from 'fs';
const tex = fs.readFileSync('main.tex','utf8');
const lines = tex.split(/\r?\n/);
const BS = String.fromCharCode(92);
lines.forEach((l,i)=>{
  const m = l.match(/\b([A-Za-z]{2,})\s+\1\b/g);
  if (m) console.log('DOUBLED L'+(i+1)+':', m.join(' | '), '::', l.slice(0,100));
});
lines.forEach((l,i)=>{
  if (l.trim().startsWith('%') || l.includes('&') || l.includes('item[')) return;
  const re = new RegExp('[a-zA-Z,.)](  +)[a-zA-Z(]');
  const m2 = l.match(re);
  if (m2 && !l.includes('{tabular}') && !l.includes(BS+' ')) {
    console.log('DBLSPACE L'+(i+1)+':', JSON.stringify(l.slice(0,120)));
  }
});
lines.forEach((l,i)=>{
  if (l.includes(BS)) return;
  const m = l.match(/[a-z]\.[A-Z][a-z]/g);
  if (m) console.log('PERIOD-NOSPACE L'+(i+1)+':', m.join('|'));
});
