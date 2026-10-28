const test = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const path = require('node:path');

test('published repository files and nested ZIPs contain no local identity or recorded machine fingerprint', () => {
  const result = spawnSync('python3', ['scripts/check-public-environment.py'], {
    cwd: path.resolve(__dirname, '..'), encoding: 'utf8', maxBuffer: 4 * 1024 * 1024,
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
});
