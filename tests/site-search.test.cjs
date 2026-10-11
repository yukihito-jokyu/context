const {test} = require('node:test');
const assert = require('node:assert/strict');
const {searchDocuments} = require('../plugins/site-search/search-core');

const documents = [
  {title: 'issue-trace — Issueを進める', permalink: '/context/documentation/issue-trace/', content: '調査記録と計画の承認をIssueへ残す'},
  {title: 'ワークフロー', permalink: '/context/workflows/', content: 'issue-traceで調査と計画を記録する'},
  {title: '成果物の例', permalink: '/context/design/archify-jp/', content: '構成と順序を図で示す'},
];

test('日本語本文を部分一致で検索する', () => {
  assert.deepEqual(searchDocuments(documents, '承認').map(d => d.permalink), ['/context/documentation/issue-trace/']);
});
test('英字の大小と全角文字を正規化し、タイトルの一致を優先する', () => {
  assert.equal(searchDocuments(documents, 'ＩＳＳＵＥ－ＴＲＡＣＥ')[0].title, documents[0].title);
});
test('空白区切りのすべての語に一致する文書を返す', () => {
  assert.equal(searchDocuments(documents, '調査　承認').length, 1);
  assert.equal(searchDocuments(documents, '調査 図').length, 0);
});
test('空文字と不一致は結果なし、件数上限を守る', () => {
  assert.deepEqual(searchDocuments(documents, '   '), []);
  assert.deepEqual(searchDocuments(documents, '存在しない語'), []);
  assert.equal(searchDocuments(documents, '調査', 1).length, 1);
});
