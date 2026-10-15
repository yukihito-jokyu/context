import fs from 'node:fs';
import path from 'node:path';
import sourceVerification from './example-skill-source.cjs';
import pluginVerification from './check-plugin-examples.cjs';

// Read the saved execution result; never synthesize an example output here.
const root = 'docs/artifacts/skills';
const skills = sourceVerification.discoverSkills();
sourceVerification.verifySkillInventory(root, skills);
const check = process.argv.includes('--check');
for (const skill of skills) {
    const source = skill.source;
    const dir = path.join(root, skill.name);
    const record = JSON.parse(fs.readFileSync(path.join(dir, 'execution.json'), 'utf8'));
    const version = sourceVerification.verifyExampleSkillSource({record, exampleDir: dir, currentSource: source});
    sourceVerification.verifyArtifacts({record, exampleDir: dir});
    const input = fs.readFileSync(path.join(dir, 'input.md'), 'utf8');
    const prefix = `/skills/${skill.name}/`;
    const filePrefix = `pathname://${prefix}`;
    let section = `## 成果物の例\n\n${record.summary}\n\n**到達点：${record.stage}。**\n\n### 実行した依頼\n\n\`\`\`text\n${input.trim()}\n\`\`\`\n\n`;
    if (version === 'baseline') section = section.replace('### 実行した依頼', `**移行時の確認：${record.source_baseline.reason}**\n\nこのハッシュは移行時の変更検出用の基準です。同梱資料全体をこの版で再実行した証拠ではありません。\n\n### 実行した依頼`);
    if (record.preview) section += `### 実際の画面\n\n![${record.preview_alt}](${prefix}${record.preview})\n\n[画像を原寸で開く](${filePrefix}${record.preview})\n\n${record.preview_note ? record.preview_note + '\n\n' : ''}`;
    if (record.text_output) {
      const output = fs.readFileSync(path.join(dir, record.text_output), 'utf8');
      const excerpt = output.trim().split('\n').slice(0, record.excerpt_lines || 16).join('\n');
      section += `### 実出力の抜粋\n\n以下は保存した原本の冒頭です。全文は原本から取得できます。\n\n\`\`\`\`markdown\n${excerpt}\n\`\`\`\`\n\n`;
    }
    section += '### 成果物を取得する\n\n';
    for (const file of record.downloads) section += `- [${file.label}](${filePrefix}${file.file}#download)\n`;
    if (record.html_output) section += `- [実際のHTMLをブラウザで開く](${filePrefix}${record.html_output})\n`;
    section += `- [実行入力の原本](${filePrefix}input.md#download)\n- [実行・検証記録（JSON）](${filePrefix}execution.json#download)\n\n### 確認した結果\n\n`;
    for (const result of record.checks) section += `- ${result}\n`;
    section += '\n';
    const guide = `docs/skills/${path.relative('utils/skills', skill.dir)}.md`;
    const before = fs.readFileSync(guide, 'utf8');
    const after = before.replace(/## 成果物の例\n[\s\S]*?(?=## 確認するポイント)/, section);
    if (after === before && !before.includes(section)) throw new Error(`${guide}: 差し替える節がありません`);
    if (check) {
      if (after !== before) throw new Error(`${guide}: 原本からの表示更新が必要です`);
    } else fs.writeFileSync(guide, after);
}
pluginVerification.checkPluginExamples();
console.log(check ? '実例の表示と原本が一致しています' : '全スキルの実例を原本から反映しました');
