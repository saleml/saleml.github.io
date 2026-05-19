
import fs from 'fs';
const root = process.argv[2];
const data = JSON.parse(fs.readFileSync(`${root}/assets/data/deadlines.json`, 'utf8'));
let code = fs.readFileSync(`${root}/assets/js/deadlines.js`, 'utf8');
code = code.replace(/^let CONFERENCES = \[\];\n*/m, '');
const api = new Function('CONFERENCES', code + `
  sortConferences(CONFERENCES);
  return true;
`);
api(data.conferences);
console.log('node-sort-ok');
