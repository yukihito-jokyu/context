---
title: write-requirement-document plugin
sidebar_label: write-requirement-document
---

# write-requirement-document plugin

会話や議事録から図付きHTMLの要件定義書を作るスキルと、出力を検査する hooks をまとめて配布します。本文・図・未決事項のつながりと読みやすさは[スキルのガイド](../skills/documentation/write-requirement-document.md)で説明しています。

編集する正本は `utils/skills/documentation/write-requirement-document/` に保ちます。`.agents/skills`・`.codex/skills` に本体やリンクを配置せず、利用時は plugin の入口を読み込みます。hooks の設定と呼び出し口は `utils/plugins/write-requirement-document/` が管理します。

## 依頼例

```text
次の議事録から、業務担当者と開発者が確認する要件定義書をHTMLで作ってください。
部署ごとの紙台帳では、備品の予約が重なっています。
社員は空き時間を確認し、開始・終了時刻を指定して予約します。
自分の予約を取り消せます。管理担当者は備品を登録します。
貸出・返却の記録と購入は対象外です。未指定の条件は未決事項として残してください。
```

## 進め方

### 配布物を生成する

Python 3.10以上を用意し、このリポジトリのルートで実行します。必要な製品の行を選び、まだ存在しないリポジトリ外の出力先を指定してください。

```sh
python3 utils/plugins/write-requirement-document/build.py --agent codex --output /tmp/requirements-codex
python3 utils/plugins/write-requirement-document/build.py --agent claude-code --output /tmp/requirements-claude
```

生成した配布物は、次の構成になります。

```text
<plugin-root>/
├── .codex-plugin/plugin.json     # Claude Code用は.claude-plugin/plugin.json
├── skills/write-requirement-document/SKILL.md
├── runtime/write-requirement-document/
├── hooks/hooks.json
├── scripts/hook.py
└── README.md
```

`skills/` は正本を読む入口です。`runtime/` には配布対象の正本をバイト列を変えずに同梱し、ローカルの検証記録とキャッシュを除きます。`hooks/` と `scripts/hook.py` は plugin が所有し、同梱した正本の汎用ランタイムへ検査を渡します。正本を移動したり、編集用の複製を管理したりする構成ではありません。

### plugin として読み込む

[導入を始める](getting-started.md)の手順で、生成した対象製品用の配布物を読み込みます。Claude Codeの確認用ローカル読み込みは次のとおりです。

```sh
claude --plugin-dir /tmp/requirements-claude
```

Claude Codeでは `/write-requirement-document:write-requirement-document`、Codexでは読み込んだ plugin のスキルを選んで依頼します。Codexのローカルカタログと信頼確認は、導入ガイドの[Codex／ChatGPT desktop](getting-started.md#codexchatgpt-desktop)を参照してください。このリポジトリのビルド処理は、導入・有効化・信頼設定を行いません。

この plugin では、同梱 Skill の `scripts/install.py` を実行しません。以前の単体導入がある場合は、そのスキルの本体・リンクと直接登録した hooks を確認し、plugin からの一組に揃えてください。このリポジトリでは、要件定義スキルのリンクと4イベントの直接登録を削除済みです。

### 要件定義書を作る

Python、既存のMermaid CLI 11以降・Node.js・対応ブラウザが必要です。最初に `runtime/write-requirement-document/scripts/document.py doctor` で描画経路を確認します。描画ツールは同梱・自動インストールしません。

成果物と実行記録は、利用者のプロジェクトの `.skill-runs/write-requirement-document/` に保存します。`PreToolUse` は実行記録の直接編集を拒否し、`PostToolUse` は編集した原本の契約を検査します。図・PNG・HTMLの同期を含む全体検査は `run.py check` と `finish`、および終了前の `Stop` で行います。`UserPromptSubmit` は質問待ちから再開するために使います。

出力を検査する hooks は実行中に働き、指摘収集の hooks は完了後も提示版と発言を記録します。収集は追加機能であり、案内は有効な hooks だけが注入します。スキルの本文・ルール・チェックリストへ収集の指示を追加しません。製品側で hooks を無効にしても、要件定義書の作成・`check`・`finish` は機能します。収集側の失敗も本来の完了を妨げません。Codexでは hooks の信頼確認が必要です。実製品からの自動実行と、設定したコマンドを直接呼ぶ検証は区別します。

修正版の承認は `python3 <plugin-root>/runtime/write-requirement-document/scripts/feedback.py review` の localhost 画面で受け取ります。記録は `.skill-feedback/write-requirement-document/` の共通形式で保存し、`feedback.py export` から skill-foundation の改善用 Eval・収束テストへ渡せます。現在の配布版は `0.1.1` です。

## 成果物の例

両製品向け配布物と、移動・展開後の実行検証記録を掲載します。同梱見本を使う検証であり、実際の利用者資料から新しい要件定義書を作成したという記録ではありません。新規作成の実例は[スキルの成果物](../skills/documentation/write-requirement-document.md#成果物の例)を参照してください。

- [Codex用plugin（ZIP）](pathname:///plugins/write-requirement-document/write-requirement-document-codex.zip#download)
- [Claude Code用plugin（ZIP）](pathname:///plugins/write-requirement-document/write-requirement-document-claude-code.zip#download)
- [検証結果の全文](pathname:///plugins/write-requirement-document/verification.txt#download)
- [実行コマンドと検証結果（JSON）](pathname:///plugins/write-requirement-document/validation.json#download)
- [plugin専用テストの実行結果](pathname:///plugins/write-requirement-document/unit-tests.log#download)
- [manifest検査の実行結果](pathname:///plugins/write-requirement-document/manifest-validation.log#download)
- [再実行用スクリプト](pathname:///plugins/write-requirement-document/verify_plugin.py#download)
- [実行入力の原本](pathname:///plugins/write-requirement-document/input.md#download)
- [実行・検証記録（JSON）](pathname:///plugins/write-requirement-document/execution.json#download)

両形式とも配布物は49ファイルで、同梱した正本44ファイルは元のバイト列と一致しました。11項目・74コマンドの検証、plugin専用の7テスト、Claude Codeのmanifest検査が成功しています。設定した4イベントの直接実行、hooksとcollectorを除いたcoreのcheck・finish、単体配置と直接登録を作らないことを確認しました。

収集の追加機能は合成データで確認しました。hooksだけが案内を注入し、初回Stopで提示版を保存します。その後、合成の指摘と修正版を結び付け、未承認のまま保存することと、未承認データのexportが拒否されることを確認しました。実利用者による確認画面の承認と、独立したモデルによるEval・収束テストは未実施です。

製品へのインストール、信頼設定、実セッションからの自動 hooks 呼び出しは、この配布物の検証に含めません。

## 確認するポイント

- Skillの本体やリンクを `.agents/skills`・`.codex/skills` に置かず、plugin の入口から読み込んでいるか。
- 直接登録した hooks と plugin の hooks を二重に使っていないか。
- 本文・Mermaid・PNG・manifestが揃い、原資料と条件が一致するか。
- 未指定の条件に、確認する質問と確定できない範囲が書かれているか。
- ビルド、直接実行テスト、製品への導入・信頼・自動実行を区別しているか。

## 正本を読む

[pluginの配布定義と接続処理](https://github.com/yukihito-jokyu/context/tree/main/utils/plugins/write-requirement-document)、[Skillの正本](https://github.com/yukihito-jokyu/context/tree/main/utils/skills/documentation/write-requirement-document)で管理します。共通の管理方針は[Skillとpluginの配布・導入](distribution.md)を参照してください。
