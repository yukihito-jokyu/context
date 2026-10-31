## 結果

skill-foundation: 完了（検証に合格）

## 作ったスキル

- 名前: `write-commit-message`（コミットメッセージを書く）
- 目的: ステージ済みの差分とチケットIDから、このリポジトリの形式のコミットメッセージを1つ書く
- 本体の置き場: `.claude/skills/write-commit-message`
- Codex の置き場: `.agents/skills/write-commit-message`（本体へのリンク）
- 対象の製品: Claude Code、Codex
- 言語: 日本語（ja）
- 起動: 依頼の内容から自動で選ばれる。明示は `/write-commit-message`（Claude Code）、`$write-commit-message`（Codex）
- 入力: `ticket`（チケットID。start の前に聞く）
- 出力: `commit-message`（コミットメッセージ。`.skill-runs/write-commit-message/out/commit-message.txt`）

## ルールと守らせ方

| 区分 | ルールの数 | ID |
|---|---|---|
| スキル固有・機械が守ったかを確かめる（runtime・format・validate のどれかを含む） | 7 | STEP-02、OUT-01、OUT-02、OUT-03、OUT-04、OUT-05、OUT-06 |
| スキル固有・機械で確かめない（review か doc で確かめる） | 5 | IN-01、IN-02、STEP-01、STEP-03、STEP-04 |
| 標準（全スキル共通） | 4 | CTL-01、CTL-03、CTL-04、RPT-01 |
| 対象外にした軸 | 3 | O6（出力は実行ごとの置き場（.skill-runs）に新しく書き、既存のファイルを変えないため）、O7（出力はコミットメッセージの1ファイルだけで、一緒に変えるファイルが無いため）、X1（コミットメッセージは差分そのものを説明する文で、引用やリンクを付けないため） |
| 廃止したルール（ID は再利用しない） | 1 | CTL-02 |

- 段（control）: runtime 4、format 1、validate 8、script 4、template 0、review 3、doc 5
- 決めた根拠（スキル固有）: 依頼の指定 1、プロジェクトの既存の決まり 2、出力を使う道具や形式の公式の決まり 1、機械で守らせられる答え 4、道具・スクリプト・入力を増やさない答え 1、AI の判断と覚える概念が少ない答え 3

機械で守らせないルールと理由（spec の why_not_machine）:
- IN-01: 痕跡が残らない：中断したときは出力が無く、検査するものが無い
- IN-02: 意味の判断が要る：本文がステージ済みの差分に無い変更を書いているかは、差分と読み比べないと分からない
- STEP-01: 痕跡が残らない：手順の順序とスクリプトの出力を使ったかは、出力に残らない（本文の形は STEP-02 が検査する）
- STEP-03: 費用が見合わない：`git commit` は出力のファイルではなくリポジトリの履歴に残り、確かめるには実行の前後で HEAD を比べる仕組みが要る。読み取りだけに使う1つの決まりのためには大きい
- STEP-04: 痕跡が残らない：失敗は出力が無い状況で起き、検査するものが無い

## 作ったスキルの検証

| 検証 | 結果 |
|---|---|
| `skill_lint.py --final` | エラー 0 件、警告 2 件 |
| `probe.py` | 違反例 21 件中 失敗 0 件／hooks の動作 18 件中 失敗 0 件（Claude Code、Codex） |

## 収束テスト

実施していない（理由: 公開作例の隔離実行で、実ユーザーとの価値の確認と独立AIの実行を行わないため）。

## 確かめていないこと

- 収束テストを実施していないため、別の AI で結果が揃うかは測っていない
- Codex の hooks は、Codex の `/hooks` で信頼するまで動かない（それまでは `run.py check` と `finish` だけで検査される）
- skill_lint.py の警告: dev/eval/eval.json skip_reason: Eval を省いています（公開作例の隔離実行で、実ユーザーとの価値の確認と独立AIの実行を行わないため）

## プロジェクトに置いたもの

- `.claude/skills/write-commit-message/`: スキルの本体（ファイル 26 個）
- `.agents/skills/write-commit-message`: 本体へのリンク
- `.claude/settings.json`: `write-commit-message` の hooks を 4 つ登録（PostToolUse、PreToolUse、Stop、UserPromptSubmit）
- `.codex/hooks.json`: `write-commit-message` の hooks を 4 つ登録（PostToolUse、PreToolUse、Stop、UserPromptSubmit）

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
