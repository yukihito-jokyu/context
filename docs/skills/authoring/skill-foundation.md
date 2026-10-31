---
title: skill-foundation — ルールと検査を備えたスキルを作る
sidebar_label: skill-foundation
---

# skill-foundation

Claude Code と Codex 向けに、ルール・出力の契約・hooks・違反例・収束テストを備えたスキルを作ります。出力の形を決めて機械で検査し、別の AI が使ったときの結果の違いも確かめます。

## 渡す情報

何を受け取り、何を出力するスキルかを伝えます。名前、対象の製品、言語、収束テストの扱いも指定できます。指定がなければ、名前は依頼から決め、対象は Claude Code と Codex の両方、日本語の依頼なら日本語にします。

収束テストは独立した AI を複数回動かします。既定では直前に回数を示して実行するかを聞きます。最初から決める場合は「収束テスト: 実行」か「収束テスト: 省く」と指定してください。省いた場合も、違反例と最終検査は実行します。

## 依頼例

```text
skill-foundation を使って、git diff から日本語のコミットメッセージを書くスキルを作ってください。
Claude Code と Codex の両方で使います。コミット操作は行わず、メッセージをテキストファイルに出力してください。
収束テスト: 省く。
```

plugin 経由では Claude Code の `/skill-foundation:skill-foundation`、Codex の plugin スキルから呼び出します。

## 導入と hooks

hooks を含む導入には [skill-foundation plugin](../../plugins/skill-foundation.md) を使います。スキル・hooks・専用エージェントを同じ単位で導入・更新・削除します。正本は `utils/skills/authoring/skill-foundation/` に維持し、plugin のビルドが正本全体を変更せずに同梱します。

このプロジェクトでは両製品の plugin 管理へ導入し、`.codex/config.toml` と `.claude/settings.json` で有効にしています。Codex の互換配置として、`.codex/skills/skill-foundation` は正本へのシンボリックリンクにし、`.codex/hooks.json` にも直接 hooks を登録しています。Claude Code の呼び出しは `/skill-foundation:skill-foundation`、Codex は plugin または互換配置のスキルを選択します。再起動と hooks の信頼確認については plugin の導入手順を参照してください。

## 進め方

1. 依頼が対象かを確かめ、受け取るものと出力するものを決めます。
2. 名前・対象・言語・置き場を決め、骨組みを作ります。
3. 前提となる仕様や既存の決まりを調べ、出典と確認した日を残します。
4. ルールと出力の契約を `dev/spec.json` に書き、スクリプトと hooks で検査します。
5. 正しい見本が通り、ルールを破った出力が止まることを違反例で確かめます。
6. 実行する場合は収束テストで出力の違いを測り、別の AI に操作の記録を分析させて手順を改善します。
7. 配置・hooks・最終検査を確認し、結果を記録します。

既定の配置では、両製品向けの本体は `.claude/skills/<名前>/`、Codex の `.agents/skills/<名前>` は本体へのリンクです。このリポジトリのように共通正本を管理する場合は、`utils/skills/.../<名前>/` に本体を置き、対象製品すべての標準位置からリンクできます。最終検査ではリンク先と hooks の登録を確認します。スキルごとのルールや検証結果は、最後に生成する HTML カタログでも確認できます。

```bash
python3 <plugin-root>/runtime/skill-foundation/scripts/catalog.py --project .
```

既定の出力は `.skill-runs/catalog.html` と、その隣の `catalog/` 以下のスキル別ページです。収束テストを実施した場合は、エージェントの操作と分析も表示します。

## 利用中の指摘を改善へつなぐ

新しく作るスキルには、成果物への指摘・修正前後の実ファイル・承認・スキルの版を収集する hooks を追加機能として必ず同梱し、既定で登録します。スキルの本文やルールに収集の指示は入れず、有効な hooks からだけ案内します。hooks を無効にしてもスキル本来の作成・検査・完了は機能し、収集側の失敗も完了を妨げません。完了後に届いた指摘も、原文と成果物の版を結び付けて `.skill-feedback/<skill-name>/` に保存します。

修正版の承認は、`python3 <skill>/scripts/feedback.py review` で起動する localhost の確認画面で受け取ります。ユーザーは修正前後・差分・元のファイルを見て承認します。会話の相づちや AI の判断を承認にはしません。

`feedback.py export --out <新しいデータセット>` は承認済みの事例を共通形式で取り出します。foundation の `feedback_eval.py --dataset <データセット> --skill <スキル> --out <新しい作業場所>` は、スキルのコピーと改善用 Eval・収束テストの候補を作ります。評価条件の一般化と入力の不足をユーザーと確認してから、独立した実行で元の版と改善候補を比べます。再現に必要な入力ファイルは、スキルの利用時に `feedback.py context --file <入力ファイル>` で保存します。

0.4.0で生成したスキルを移行するときは、更新後の foundation の `scripts/init_skill.py --dir <スキルの場所> --update-runtime` を実行します。共通スクリプトを更新し、以前の収集ルールを生成本文から除きます。単体導入では hooks の登録も更新します。新規導入で登録を省く場合は `install.py --no-hooks`、登録済みの hooks を停止する場合は製品側の無効化を使います。pluginで配る場合は配布物を再生成します。

## 成果物の例

最新の同梱仕様からコミットメッセージを書くスキルを生成し、hooksを発火させずに本来の処理を実行した。その後、合成Stopで指摘収集の追加機能を検証した。

**到達点：生成・配置・単体実行とhooks追加機能の直接検証に合格。Evalと独立AI収束は省略、実ユーザー承認は未発生。**

### 実行した依頼

```text
最新の同梱 write-commit-message の仕様と手順から、ステージ済みの差分とチケットIDを受け取り、日本語のコミットメッセージを書くスキルを作成してください。Claude CodeとCodexの両方を対象とし、1行目は「チケットID 要約」、本文は変更ファイルの数に応じた箇条書きにします。コミット・プッシュは行いません。公開作例の隔離実行なので、実ユーザーとの価値の確認が必要なEvalと、独立AIによる収束テストは省きます。指摘収集hooks・確認画面・共通形式は追加機能として必ず同梱し、生成スキルの本文やルールに収集指示を加えないでください。hooksなしでも本来の価値が機能することを確かめてください。

作成元: 最新の正本に同梱した assets/example/write-commit-message。
題材のstaged差分は src/app.py と src/util.py の新規2ファイル、入力チケットは abc-12。
生成後はhooksを発火させずにスキルを使ってメッセージを作成し、収集記録が無いことを確認する。その後、合成Stopイベントを直接渡し、追加機能の提示版保存を検証する。コミット・プッシュは実行しない。
指摘や確認画面での実ユーザー承認はこの作例では発生していない。会話による承認や合成承認を収集実績に混ぜない。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
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
````

### 成果物を取得する

- [生成したスキル一式](pathname:///skills/skill-foundation/write-commit-message.zip#download)
- [生成時の実報告](pathname:///skills/skill-foundation/output.md#download)
- [実行して作成したコミットメッセージ](pathname:///skills/skill-foundation/commit-message.txt#download)
- [実行に使ったステージ済み差分](pathname:///skills/skill-foundation/usage-diff.patch#download)
- [生成スキルの実行報告](pathname:///skills/skill-foundation/usage-report.md#download)
- [生成したカタログHTML](pathname:///skills/skill-foundation/catalog.html#download)
- [実行コマンドと出力](pathname:///skills/skill-foundation/execution-log.jsonl#download)
- [検証結果](pathname:///skills/skill-foundation/validation.json#download)
- [違反例とhooksの検証記録](pathname:///skills/skill-foundation/probe-results.json#download)
- [最終lintの結果](pathname:///skills/skill-foundation/final-lint.txt#download)
- [この作例を再実行するスクリプト](pathname:///skills/skill-foundation/reproduce_skill.py#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/skill-foundation/catalog.html)
- [実行入力の原本](pathname:///skills/skill-foundation/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/skill-foundation/execution.json#download)

### 確認した結果

- 通常フローを25コマンドで実行し、最終lintはエラー0件。Eval・収束の明示省略による警告2件を記録した。
- 違反例などのprobe 21件と、両製品のhooks接続18件に合格した。
- 生成SKILL.md・ルール詳細・出力契約には、指摘収集の専用ルールや収集コマンドを入れていない。
- 共通runtime 6ファイル、schema、収集の参照文書が正本とbyte単位で一致した。
- hooksを一度も発火させず、差分なしの中断、チケットの正規化、2ファイルのコミットメッセージ作成、check・finishを実行し、収集記録が作られないことを確認した。
- その後、合成Stopを直接実行して提示版1件を共通形式へ保存し、整合性を検査した。実ユーザーの指摘・承認は0件。
- 実製品のhooks自動発火・信頼UI、実ユーザー承認、Evalの価値確認、独立AIの収束は未実施。

## 確認するポイント

- 作ったスキルの目的・入力・出力が依頼と一致しているか。
- 違反例と hooks の動作確認、最終検査が通っているか。
- 収束テストを実施した範囲と、省いた範囲が区別されているか。
- 配置と hooks の登録に加え、製品側の再起動・信頼設定が済んでいるか。

スキルの本文・スクリプト・設定は、実行中も修正できます。変更を理由に開始や完了を拒否する検査はありません。出力は現在の契約で検査します。

スクリプトとひな形の動作は `python3 <skill>/scripts/selftest.py` で確かめられます。これは独立した AI による収束テストとは別の確認です。

## 正本を読む

詳細な手順・場合分け・契約は [skill-foundation の SKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/authoring/skill-foundation/SKILL.md) を参照してください。
