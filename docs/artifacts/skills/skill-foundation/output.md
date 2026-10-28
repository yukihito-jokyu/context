最終の返答は、次の本文をそのまま使う。前後に文を足さず、要約しない。
========================================
## 結果

skill-foundation: 完了（検証に合格）

## 作ったスキル

- 名前: `write-commit-message`（コミットメッセージを書く）
- 目的: ステージ済みの git diff から、日本語1行のコミットメッセージをUTF-8テキストに出す
- 本体の置き場: `.claude/skills/write-commit-message`
- Codex の置き場: `.agents/skills/write-commit-message`（本体へのリンク）
- 対象の製品: Claude Code、Codex
- 言語: 日本語（ja）
- 起動: 依頼の内容から自動で選ばれる。明示は `/write-commit-message`（Claude Code）、`$write-commit-message`（Codex）
- 入力: なし
- 出力: `commit-message`（コミットメッセージ。`.skill-runs/write-commit-message/out/commit-message.txt`）

## ルールと守らせ方

| 区分 | ルールの数 | ID |
|---|---|---|
| スキル固有・機械が守ったかを確かめる（runtime・format・validate のどれかを含む） | 5 | OUT-01、OUT-02、OUT-03、OUT-04、OUT-05 |
| スキル固有・機械で確かめない（review か doc で確かめる） | 6 | IN-01、IN-02、STEP-01、STEP-02、STEP-03、STEP-04 |
| 標準（全スキル共通） | 6 | CTL-01、CTL-02、CTL-03、CTL-04、CTL-05、RPT-01 |
| 対象外にした軸 | 4 | O4（出力に日付とIDと連番を付けないため）、O6（実行ごとの新しい出力を作り、既存ファイルは書き換えないため）、O7（出力は1ファイルだけであるため）、X1（差分を要約する短い文であり引用やリンクを付けないため） |

- 段（control）: runtime 6、format 1、validate 9、script 4、template 0、review 2、doc 6
- 決めた根拠（スキル固有）: 依頼の指定 4、機械で守らせられる答え 2、道具・スクリプト・入力を増やさない答え 1、AI の判断と覚える概念が少ない答え 4

機械で守らせないルールと理由（spec の why_not_machine）:
- IN-01: 痕跡が残らない：中断時は出力を作らない
- IN-02: 意味の判断が要る：要約が差分と一致するかは文の意味を照合する
- STEP-01: 痕跡が残らない：出力保存前の操作順を出力の内容だけでは確かめられない
- STEP-02: 痕跡が残らない：中断した場合は本文が無い
- STEP-03: 痕跡が残らない：外部の操作はメッセージの検査では検出できない
- STEP-04: 痕跡が残らない：失敗した操作は出力の内容では検出できない

## 作ったスキルの検証

| 検証 | 結果 |
|---|---|
| `skill_lint.py --final` | エラー 0 件、警告 2 件 |
| `probe.py` | 違反例 19 件中 失敗 0 件／hooks の動作 20 件中 失敗 0 件（Claude Code、Codex） |

## 収束テスト

実施していない（理由: 利用者が収束テストを省くと指定した）。

## 確かめていないこと

- 収束テストを実施していないため、別の AI で結果が揃うかは測っていない
- Codex の hooks は、Codex の `/hooks` で信頼するまで動かない（それまでは `run.py check` と `finish` だけで検査される）
- skill_lint.py の警告: dev/results/probe-results.json OUT-02-a: 別のルール OUT-03 の指摘も出ています。1つの違反例は1つのルールだけを破るようにしてください（control-ladder.md の7章）

## プロジェクトに置いたもの

- `.claude/skills/write-commit-message/`: スキルの本体（ファイル 17 個）
- `.agents/skills/write-commit-message`: 本体へのリンク
- `.claude/settings.json`: `write-commit-message` の hooks を 4 つ登録（PostToolUse、PreToolUse、Stop、UserPromptSubmit）
- `.codex/hooks.json`: `write-commit-message` の hooks を 4 つ登録（PostToolUse、PreToolUse、Stop、UserPromptSubmit）

## 改変チェックの記録

- `.claude/skills/write-commit-message/assets/seal.json` に保護ファイル 9 件のハッシュを書いた
- これより後に保護ファイルを変えると、指紋を記録し直すまで `write-commit-message` の `run.py start` が止まる。変え方は、作ったスキルの SKILL.md の「8. 制御の仕組み」にある

## カタログ

- `.skill-runs/catalog.html` に一覧を書いた。ブラウザで開いて見る
- スキル 1 個のワークフロー図と独立検証の記録は、スキルごとのページに書いた: `write-commit-message`（`.skill-runs/catalog/write-commit-message.html`）

## 出力

- `.claude/skills/write-commit-message/SKILL.md`（skill-entry 作ったスキルの SKILL.md）

## 既定値で決めた値

- なし

## 入力で読めなかった値

- なし

## 検証

- `run.py finish`: 指摘 0 件

## 補足

- なし
