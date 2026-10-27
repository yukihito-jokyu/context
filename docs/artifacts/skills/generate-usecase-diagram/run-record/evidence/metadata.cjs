const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const base='<user-home>/Documents/github_projects/context';
const work='/private/tmp/context-85-public-example';
const out=base+'/docs/artifacts/skills/generate-usecase-diagram';
const helper=require(base+'/scripts/example-skill-source.cjs');
const source='utils/skills/design/generate-usecase-diagram/SKILL.md';
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
const sourceBefore=JSON.parse(fs.readFileSync(work+'/.skill-runs/generate-usecase-diagram/evidence/source-before.json','utf8'));
const current=helper.sourceManifest(path.dirname(base+'/'+source));
if(JSON.stringify(current)!==JSON.stringify(sourceBefore)) throw new Error('Source manifest changed');
const files=[];
function walk(rel='') {for(const f of fs.readdirSync(path.join(out,rel),{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name,'en'))){const r=rel?rel+'/'+f.name:f.name;if(f.isSymbolicLink())throw new Error('Symlink');if(f.isDirectory())walk(r);else if(f.isFile()&&r!=='execution.json')files.push(r);}}
walk();
const record={
 schema_version:1,skill:'generate-usecase-diagram',skill_source:source,
 skill_sha256:digest(fs.readFileSync(base+'/'+source)),recorded_at:new Date().toISOString(),
 runner:{kind:'subagent',agent_id:'/root/usecase_public_example',task:fs.readFileSync(work+'/.skill-runs/generate-usecase-diagram/evidence/runner-task.txt','utf8')},
 input:'input.md',
 summary:'図書館システムの貸出と蔵書管理を2枚に分け、Mermaid原本・PNG・HTMLカタログを新規生成した例です。必須の資格確認、希望時の貸出票発行、主任司書の役割継承を表します。',
 stage:'start・build・preview・全PNGと実画面の目視・review・check・finishを実施（利用者の最終確認は未実施）',
 checks:[
  'start・build・preview・review・check・finishは成功。sandbox内の初回buildはChrome exit=-6で停止し、その実行だけ権限レビュー後に再実行して成功しました。',
  '全2枚のPNGとpreview後・review後の実画面をview_imageで開き、日本語、境界、関係線を目視しました。include・extend・汎化の向きを要件と照合しました。',
  'Chromeによる自動操作検査で、一覧2枚、検索0件、拡大と閉じる、原本表示、取得リンク6本、相対リンク、横方向のはみ出しなしを確認しました。',
  '追加の対話ブラウザでの手動操作はfile://のURLポリシーにより未実施です。利用者の最終確認は未実施です。',
  'finishのstdout全文をoutput.mdへ保存し、カタログの7ファイルをZIPの同名ファイルとバイト単位で照合しました。',
  'sourceManifestで実行前後の正本76ファイルが一致しました。verifyExampleSkillSourceとverifyArtifactsを実行し、全公開ファイルをSHA-256付きで登録しました。'
 ],
 downloads:[{file:'catalog.zip',label:'HTML・Mermaid原本・PNG・変換記録の一式（ZIP）'},{file:'output.md',label:'finishの実出力全文（Markdown）'},{file:'validation.json',label:'コマンド・画像目視・HTML操作の検証記録（JSON）'},{file:'catalog/diagrams/d01.mmd',label:'貸出のMermaid原本'},{file:'catalog/diagrams/d01.png',label:'貸出のPNG'},{file:'catalog/diagrams/d02.mmd',label:'蔵書管理のMermaid原本'},{file:'catalog/diagrams/d02.png',label:'蔵書管理のPNG'}],
 text_output:'output.md',html_output:'catalog/index.html',preview:'preview.png',
 preview_alt:'図書館システムの貸出と蔵書管理の2枚を表示したHTMLカタログの実画面',
 preview_note:'review後に既存Chromeで保存し、view_imageで開いて確認した実画面です。操作は自動検査で確認し、利用者の最終確認は未実施です。',
 ...current,
 artifacts:files.sort().map(file=>{const b=fs.readFileSync(path.join(out,file));return {file,sha256:digest(b),bytes:b.length};})
};
fs.writeFileSync(out+'/execution.json',JSON.stringify(record,null,2)+'\n');
const sourceStatus=helper.verifyExampleSkillSource({record,currentSource:base+'/'+source});
helper.verifyArtifacts({record,exampleDir:out});
console.log(JSON.stringify({verifyExampleSkillSource:sourceStatus,verifyArtifacts:'passed',source_files:record.source_files.length,artifacts:record.artifacts.length,source_sha256:record.source_sha256},null,2));
