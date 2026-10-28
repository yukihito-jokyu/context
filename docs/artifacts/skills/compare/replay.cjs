const fs = require('node:fs');
const {searchDocuments} = require('./search-core.js');
const input = JSON.parse(fs.readFileSync('search-input.json','utf8'));
for (const query of input.queries) {
  const A = searchDocuments(input.documents.map(d => ({...d,content:''})),query);
  const B = searchDocuments(input.documents,query);
  console.log(JSON.stringify({query,A,B}));
}
