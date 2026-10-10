import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';

const here = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.join(here, '..');
const skill = readFileSync(path.join(skillRoot, 'SKILL.md'), 'utf8');
const authoringContract = readFileSync(path.join(skillRoot, 'references', 'authoring-contract.md'), 'utf8');
const frontmatter = skill.match(/^---\n([\s\S]*?)\n---/);

test('skill description is portable across 1024-character runtimes and remains searchable', () => {
  assert.ok(frontmatter, 'SKILL.md must start with YAML frontmatter');
  const description = frontmatter[1].match(/^description:\s*(.+)$/m)?.[1]?.trim();
  assert.ok(description, 'frontmatter must include a one-line description');
  assert.ok(description.length <= 1024, `description is ${description.length} characters; maximum is 1024`);
  assert.ok(Buffer.byteLength(description, 'utf8') <= 1024, 'description must also fit a 1024-byte runtime limit');

  for (const trigger of ['architecture', 'workflow', 'sequence', 'data-flow', 'lifecycle', 'class', 'ER', 'Mermaid']) {
    assert.match(description, new RegExp(`\\b${trigger}\\b`, 'i'), `description must retain the ${trigger} trigger`);
  }
  assert.match(description, /単体HTML/i);
  assert.match(description, /使用します/);
});

test('literal packaged-skill path references resolve inside the installed skill root', () => {
  const references = [...skill.matchAll(/`((?:assets|bin|examples|recipes|references|renderers|schemas|scripts)\/[^`\s]+)`/g)]
    .map((match) => match[1])
    .filter((reference) => !/[<>{}*\[\]]/.test(reference));

  assert.ok(references.length > 0, 'expected literal packaged-skill references');
  for (const reference of new Set(references)) {
    assert.equal(existsSync(path.join(skillRoot, reference)), true, `SKILL.md references missing packaged path ${reference}`);
  }
});

test('main skill stays a bounded authoring router with progressive references', () => {
  const lines = skill.trimEnd().split('\n');
  assert.ok(lines.length <= 160, `SKILL.md is ${lines.length} lines; keep the entrypoint at 160 or fewer`);
  for (const reference of [
    'references/authoring-contract.md',
    'references/viewer-runtime.md',
    'references/delivery-contract.md',
  ]) {
    assert.match(skill, new RegExp(reference.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.equal(existsSync(path.join(skillRoot, reference)), true, `${reference} must ship with the skill`);
  }
});

test('update awareness is notification-only and never replaces the requested workflow', () => {
  assert.match(skill, /`scripts\/check-update\.mjs`/);
  assert.match(skill, /`silent`[\s\S]*言及せず/);
  assert.match(skill, /`update_available`[\s\S]*簡潔な通知/);
  assert.match(skill, /通知は情報であり、許可ではありません/);
  assert.match(skill, /`severity` が `security`[\s\S]*セキュリティ更新[\s\S]*ユーザーの選択権/);
  assert.match(skill, /ユーザーの元の作業を続行/);
  assert.match(skill, /インストール済みバージョンは変更しません/);
  assert.doesNotMatch(skill, /npx skills update|gh skill update/i);
});

test('language behavior stays within the bounded locale contract', () => {
  assert.match(skill, /主要な作成言語を1つ/);
  assert.match(skill, /明示されていない場合は、依頼または会話で優勢な言語/);
  assert.match(skill, /`meta\.locale` が制御するのはレンダラー所有のViewer UIだけ/);
  assert.match(skill, /日本語には `"ja"`、英語には `"en"`、簡体字中国語には `"zh-CN"`/);
  assert.match(skill, /`meta\.locale` を省略した場合[\s\S]*日本語/);
  assert.match(skill, /固定Viewer UIと `<html lang>` が日本語にフォールバック/);
  assert.match(skill, /レンダラーは作成済みの内容を翻訳しません/);
  assert.match(skill, /製品名.*コード識別子.*プロトコル.*APIパス.*環境名/);
  assert.match(authoringContract, /`meta\.locale` が制御するのはレンダラー所有の読者向け表示だけ/);
  assert.match(authoringContract, /日本語は `"ja"`、英語は `"en"`、簡体字中国語は `"zh-CN"`/);
  assert.match(authoringContract, /成果物が完全にはローカライズされない/);
  assert.match(authoringContract, /別の言語や中国語ロケールを `zh-CN` へ暗黙に置き換えてはいけません/);
  assert.match(authoringContract, /作成済み内容を翻訳することはありません/);
  assert.match(authoringContract, /レンダラー所有の既定凡例ラベルは `meta\.locale` に従います/);
  assert.match(authoringContract, /フォールバックはレンダラー所有の表示面だけに適用/);
});

test('skill keeps the title hierarchy compact by default', () => {
  assert.match(skill, /既定では `meta\.subtitle` を省略/);
  assert.match(skill, /タイトル、ノード、カードを言い換えただけのサブタイトルを作ってはいけません/);
  assert.match(authoringContract, /省略または空のサブタイトルによって、生成Viewerに空の表示行が残ってはいけません/);
});
