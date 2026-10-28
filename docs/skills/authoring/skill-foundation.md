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

このプロジェクトでは両製品の plugin 管理へ導入し、`.codex/config.toml` と `.claude/settings.json` で有効にしています。単体スキルのリンクと直接登録の hooks は取り除いています。Claude Code の呼び出しは `/skill-foundation:skill-foundation`、Codex は plugin のスキルを選択します。再起動と hooks の信頼確認については plugin の導入手順を参照してください。

## 進め方

1. 依頼が対象かを確かめ、受け取るものと出力するものを決めます。
2. 名前・対象・言語・置き場を決め、骨組みを作ります。
3. 前提となる仕様や既存の決まりを調べ、出典と確認した日を残します。
4. ルールと出力の契約を `dev/spec.json` に書き、スクリプトと hooks で検査します。
5. 正しい見本が通り、ルールを破った出力が止まることを違反例で確かめます。
6. 実行する場合は収束テストで出力の違いを測り、別の AI に操作の記録を分析させて手順を改善します。
7. 配置・hooks・最終検査を確認し、合格時のファイルのハッシュと結果を記録します。

作ったスキルは、両製品向けなら `.claude/skills/<名前>/` が本体で、`.agents/skills/<名前>` がそのリンクです。スキルごとのルールや検証結果は、最後に生成する HTML カタログでも確認できます。

```bash
python3 <plugin-root>/runtime/skill-foundation/scripts/catalog.py --project .
```

既定の出力は `.skill-runs/catalog.html` と、その隣の `catalog/` 以下のスキル別ページです。収束テストを実施した場合は、エージェントの操作と分析も表示します。

## 成果物の例

更新後の skill-foundation を新しいサブエージェントが一時gitプロジェクトに適用し、write-commit-message を新規作成しました。実出力、生成スキルとカタログ、検証ログを保存しています。

**到達点：生成スキルの作成・検証と run.py finish が完了。収束テストは依頼で指定して省略。**

### 実行した依頼

```text
git diff を受け取り、日本語の1行コミットメッセージをUTF-8テキストに出すスキルを、Claude Code と Codex 両方向けに作る。収束テスト: 省く。入力不足はスキル既定値に従う。コミットや外部投稿は行わない。サンプル用の一時gitプロジェクト内のみに生成し、そのプロジェクトへのスキル配置とhooks登録は許可する
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
## 結果

skill-foundation: 完了（検証に合格）

## 作ったスキル

- 名前: `write-commit-message`（コミットメッセージを書く）
- 目的: ステージ済みの git diff を受け取り、日本語の1行コミットメッセージをUTF-8テキストに書く
- 本体の置き場: `.claude/skills/write-commit-message`
- Codex の置き場: `.agents/skills/write-commit-message`（本体へのリンク）
- 対象の製品: Claude Code、Codex
- 言語: 日本語（ja）
- 起動: 依頼の内容から自動で選ばれる。明示は `/write-commit-message`（Claude Code）、`$write-commit-message`（Codex）
- 入力: なし
- 出力: `commit-message`（コミットメッセージ。`.skill-runs/write-commit-message/out/commit-message.txt`）

## ルールと守らせ方
````

### 成果物を取得する

- [最終報告の原本（Markdown）](pathname:///skills/skill-foundation/output.md#download)
- [生成スキル・設定・カタログ（ZIP）](pathname:///skills/skill-foundation/write-commit-message.zip#download)
- [検証の要約（JSON）](pathname:///skills/skill-foundation/validation.json#download)
- [サブエージェントの生成・検査ログ](pathname:///skills/skill-foundation/execution.log#download)
- [生成スキルの最終検査ログ](pathname:///skills/skill-foundation/final-lint.log#download)
- [親エージェントの自己テストログ](pathname:///skills/skill-foundation/parent-selftest.log#download)
- [親エージェントの指定版probeログ](pathname:///skills/skill-foundation/parent-foundation-probe.log#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/skill-foundation/catalog.html)
- [実行入力の原本](pathname:///skills/skill-foundation/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/skill-foundation/execution.json#download)

### 確認した結果

- SKILL.md の手順に沿って受付、骨組み、調査、ルール、契約、違反例、収束テスト省略、仕上げを実施し、run.py finish が指摘0件で完了した。
- 生成スキルの最終検査はエラー0件、警告1件。警告は指定した収束テストの省略による。
- 生成スキルのprobeは19件、Claude Code・Codex形式のhooks確認は20件で、失敗はすべて0件。
- 生成したカタログのSVG12個をXMLとして読み取れることを確認した。
- 親エージェントの確認として指定版の自己テスト11段階成功と、別コピーでのprobe26件・hooks20件成功のログを添付した。
- 独立したAIによる出力の一致・レビュー検出率と、実際の製品セッションからの自動hooks呼出しは未確認。公開ログの環境パスは置換し、置換内容をvalidation.jsonに記録した。

## 確認するポイント

- 作ったスキルの目的・入力・出力が依頼と一致しているか。
- 違反例と hooks の動作確認、最終検査が通っているか。
- 収束テストを実施した範囲と、省いた範囲が区別されているか。
- 配置と hooks の登録に加え、製品側の再起動・信頼設定が済んでいるか。

`SKILL.md`、`scripts/`、`assets/`、`references/` は合格時のハッシュで保護します。後から修正する場合は、正本の「8. 制御の仕組み」の順に `dev/spec.json`、生成部分、違反例、最終検査を更新してください。

スクリプトとひな形の動作は `python3 <skill>/scripts/selftest.py` で確かめられます。これは独立した AI による収束テストとは別の確認です。

## 正本を読む

詳細な手順・場合分け・契約は [skill-foundation の SKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/authoring/skill-foundation/SKILL.md) を参照してください。
