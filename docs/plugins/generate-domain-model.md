---
title: generate-domain-model plugin
sidebar_label: generate-domain-model
---

# generate-domain-model plugin

[generate-domain-model Skill](../skills/design/generate-domain-model.md)と出力検査用hooksをまとめたpluginです。業務の概念と関係からMermaid原本・PNG・HTMLカタログを生成します。実行中は、出力の検査・スキル自身の保護・終了前の検査を行います。

## 依頼例

pluginを導入したAgentで、次のように依頼します。

```text
generate-domain-modelを使って、docs/order-spec.mdから受注と支払の業務概念を図にしてください。
カタログ名はsalesです。Mermaid原本・PNG・HTML一覧を生成し、資料にない多重度は確認事項として残してください。
```

## 進め方

リポジトリのルートで、出力先を存在しないディレクトリにして実行します。

```sh
python3 utils/plugins/generate-domain-model/build.py --agent codex --output /tmp/domain-model-codex
python3 utils/plugins/generate-domain-model/build.py --agent claude-code --output /tmp/domain-model-claude
```

ビルドは正本のSkill全体と対象Agent用のmanifest・hooksをまとめます。Mermaid CLIとブラウザは同梱しません。[環境の準備](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/generate-domain-model/references/setup.md)を参照してください。

導入方法は[pluginの導入ガイド](getting-started.md)に従います。作成した配布物の検査と、実際のクライアントへの導入・有効化は、それぞれ確認します。Codexではhooksの信頼設定も必要です。

## 成果物の例

新しいサブエージェントが、正本のSkill全体とAgent別のmanifest・hooksから2種類のpluginを生成しました。各ZIPを展開した93ファイルが正本とバイト一致し、保護ファイル16件の封印も一致しました。

**到達点：配布物の生成・展開内容の照合・hooksの直接実行を検証済み。** 実クライアントへの導入・有効化・クライアント経由のhooks実動作は未検証です。

### 配布物を取得する

- [Codex用plugin（ZIP）](pathname:///plugins/generate-domain-model/generate-domain-model-codex.zip#download)
- [Claude Code用plugin（ZIP）](pathname:///plugins/generate-domain-model/generate-domain-model-claude-code.zip#download)
- [検証結果の全文](pathname:///plugins/generate-domain-model/verification.txt#download)
- [実行入力の原本](pathname:///plugins/generate-domain-model/input.md#download)
- [実行・検証記録（JSON）](pathname:///plugins/generate-domain-model/execution.json#download)

### 確認した結果

- 両ZIPのCRC、全ファイル一覧、正本とのバイト一致、manifest・hooksの参照先を確認しました。
- 各Agent向けに29ケースを直接実行し、全4イベント、出力検査、保護ファイルの拒否・確認、終了前の差し戻し、待機からの再開を確認しました。
- 実行前後でpluginと同梱Skillのファイル一覧・SHA-256が一致しました。

## 確認するポイント

- Agentに合うmanifestとhooksを選んでいるか。
- Mermaid CLIとブラウザを実行できるか。
- 起動したスキルが原本・PNG・HTMLを生成し、検査に通ってから完了しているか。
- 実クライアントでhooksの呼び出しと差し戻しを確認したか。

## 正本を読む

[配布定義とビルド処理](https://github.com/yukihito-jokyu/context/tree/main/utils/plugins/generate-domain-model)と[Skill正本](https://github.com/yukihito-jokyu/context/tree/main/utils/skills/design/generate-domain-model)で管理します。
