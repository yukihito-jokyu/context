---
title: pattern-foundation — 書き方を揃える開発基盤を作る
sidebar_label: pattern-foundation
---

# pattern-foundation

同じ依頼でも作者によって実装の置き場所や命名が分かれる場合に、書き方を揃える開発基盤を作ります。規約を決め、formatter・linter・構造検査などで強制し、独立したエージェントに同じ課題を解かせて違いを測ります。

基盤には参照実装、設計文書、AGENTS.md・CLAUDE.md、実装用・レビュー用スキルも含めます。新規作成と、既存リポジトリへの後付けに対応します。

## 渡す情報

作る基盤の用途、使う技術・ツール、作成先を伝えます。既存リポジトリに追加する場合は、対象パスと変更してよい範囲も指定します。生成するスキル名や検査コマンド名に希望があれば、あわせて渡してください。

## 依頼例

```text
pattern-foundationを使って、PythonのCLI開発で書き方を揃える基盤を sample-cli-foundation/ に新規作成してください。実装用スキル名はimpl、レビュー用はreviewにしてください。規約を機械で強制し、独立エージェントの収束テストで残る違いを確認したいです。
```

## 進め方

1. 用途・技術・ツール・作成先をmanifestにまとめ、文書・スキル・検査の骨組みを生成します。
2. 公式資料を調べ、命名や配置など作者ごとに選択が分かれる点について、条件と答えを決めます。
3. 規約を検査と参照実装へ落とし込み、違反例を実行して検査が失敗することを確かめます。
4. AGENTS.md、実装用・レビュー用スキル、生成先のhooksを仕上げます。
5. 独立エージェントに同じ課題を解かせ、出力の違いを分類して規約や仕組みを調整し、結果を報告します。

収束テストは既定で3人・通常課題3つに、最終ラウンドの追加課題を組み合わせ、最大3ラウンド実行します。実行前にセッション数を確認します。

このスキルは単体で管理します。同梱のhooksテンプレートは生成先の基盤へ配置するためのもので、スキルの導入時に有効化するplugin用hooksではありません。導入方法は[初めて使う](../getting-started.md)を参照してください。

## 成果物の例

架空のPython CLI基盤に受付と骨組み生成だけを適用した例です。manifestを含む24ファイルを保存し、再実行時の既存ファイル保全を確認しました。ルール強制・hooks実動作・収束テストは未実施です。

**到達点：受付と骨組み生成（フェーズ0・1）のみ完了・status: building。**

### 実行した依頼

```text
Python標準ライブラリだけを使う架空のCLI基盤 sample-cli-foundation を新規作成してください。日本語、実装スキル名 impl、レビュースキル名 review、check は python3 scripts/check.py、fix は python3 scripts/fix.py とします。今回は受付と骨組み生成（フェーズ0・1）だけを実行し、status: building で止めてください。バージョン調査、ルール確定、アプリ実装、hooks実動作確認、収束テストは実行対象外です。外部API/インストール/投稿は行わないでください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# sample-cli-foundation の受付・骨組み生成結果

Python標準ライブラリだけを使うCLI基盤について、受付情報を manifest にまとめ、同梱の init_foundation.py で骨組みを生成しました。今回は指定されたフェーズ0・1までを実行し、状態は `building` のままです。

## 生成したもの

ZIPの `sample-cli-foundation/` に、manifest を含む24ファイルを保存しました。文書やスキルに残る `TODO(pattern-foundation)` は、後続フェーズで埋める未完成箇所です。

- `.foundation/manifest.json`：Python、CLI分野、新規作成、日本語、実装用 `impl` とレビュー用 `review`、指定のcheck/fixコマンドを記録。
- `AGENTS.md` と `CLAUDE.md`：エージェント向け入口のひな形。`CLAUDE.md` は `@AGENTS.md` の1行。
- `.claude/skills/impl/` と `.claude/skills/review/`：実装・レビュー手順のひな形。
- `.claude/settings.json`：生成先プロジェクトで使うhooks設定のひな形。
- `docs/design/` と `README.md`：設計、調査、ルール、ADR、収束結果のひな形。
- `.foundation/bin/`：基盤内で使う検査・hooks・収束テスト用のPythonスクリプト6本。
- `.foundation/probes.json` と `.foundation/convergence/`：違反例・収束課題・レビュー課題のひな形。

````

### 成果物を取得する

- [受付・骨組み生成の実出力（Markdown）](pathname:///skills/pattern-foundation/output.md#download)
- [生成した骨組み一式（ZIP・未完成）](pathname:///skills/pattern-foundation/sample-cli-foundation.zip#download)
- [実コマンドと検証結果（JSON）](pathname:///skills/pattern-foundation/validation.json#download)
- [実行入力の原本](pathname:///skills/pattern-foundation/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/pattern-foundation/execution.json#download)

### 確認した結果

- init_foundation.pyが終了コード0で23ファイルを生成し、manifestを合わせた24ファイルをZIPに保存。
- 再実行前後の全ファイルのSHA-256が一致。別コピーで変更したAGENTS.md・hooks設定・guard.pyも再実行で保全。
- rules_check.py・violation_probe.py・guard.py・convergence.pyの--helpが終了コード0。補助ライブラリを含む生成Pythonスクリプト6本の構文解析も成功。
- hooks.pyは--help非対応で、利用方法を表示し終了コード1。hooks実動作の検証は未実施。
- manifestのstatusはbuildingのまま。TODOを残し、check/fix実装・probe・収束テスト・最終検査は未実施と記録。

## 確認するポイント

決めた規約が実際の検査に組み込まれ、違反例を検出できるかを確認します。機械で強制できない規約には、レビュー方法と機械化しない理由が必要です。

骨組みの生成だけでは、基盤の完成や書き方の収束は確認できません。掲載例は受付と骨組み生成までの実行です。技術調査、規約の確定、アプリ実装、hooksの実動作、収束テスト、最終検査は実施しておらず、生成物には未記入のひな形が残ります。

既存リポジトリへの後付けでは、既存の違反を一括で書き換えず、新しい違反を防ぐところから進めます。既存コードを書き換える場合は、別途その範囲を確認します。

## 正本を読む

詳細な手順と制約は[pattern-foundationのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/development/pattern-foundation/SKILL.md)を参照してください。
