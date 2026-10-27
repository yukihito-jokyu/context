---
title: generate-domain-model-from-code plugin
sidebar_label: generate-domain-model-from-code
---

# generate-domain-model-from-code plugin

[generate-domain-model-from-code Skill](../skills/design/generate-domain-model-from-code.md)と、出力・保護ファイル・実行の終了を検査するhooksをまとめたpluginです。対象形式はCodexとClaude Codeです。

## 渡す情報

Skillには対象コードと調査範囲を渡します。利用環境にPython 3.9以上、Mermaid CLI、起動可能なブラウザーが必要です。配布物にはこれらの外部ツールを含めません。

## 依頼例

```text
注文と支払いのコードから、根拠付きのドメインモデル図を作ってください。
PNGとHTMLカタログまで生成し、未確認の関係は確認事項として残してください。
```

## 進め方

1. [導入を始める](getting-started.md)で生成と導入の違いを確認します。
2. `python3 utils/plugins/generate-domain-model-from-code/build.py --agent codex --output /tmp/domain-model-codex` で対象Agentの配布物を生成します。Claude Code用は `--agent claude-code` にします。
3. 生成した配布物を対象Agentで読み込みます。Codexのhooksは利用者が信頼するまで実行されません。
4. 対象コードを指定してSkillを実行し、検査済みのカタログを確認します。

hooksはSkillの実行中に出力の検査、保護ファイルの編集の制止、応答終了前の確認を行います。`scripts/gate.py` が同梱したSkillのランタイムへ渡すため、出力の契約はSkill側で一元管理します。自動のSkill起動と、生成したpluginが実クライアントで有効になることは別々に確認します。

## 成果物の例

新しいサブエージェントが正本から両Agent向けの配布物を生成しました。各95ファイルの内容とZIP展開後の内容が正本と一致し、配布物内のhookコマンドが検査の省略指定と保護ファイルの編集を制止することを隔離環境で確認しています。

- [Codex用ZIP](pathname:///plugins/generate-domain-model-from-code/generate-domain-model-from-code-codex.zip#download)
- [Claude Code用ZIP](pathname:///plugins/generate-domain-model-from-code/generate-domain-model-from-code-claude-code.zip#download)
- [実行入力](pathname:///plugins/generate-domain-model-from-code/input.md#download)、[検証結果](pathname:///plugins/generate-domain-model-from-code/verification.txt#download)、[実行記録](pathname:///plugins/generate-domain-model-from-code/execution.json#download)

この例の到達点は配布物の生成・内容検証と、隔離環境でのhookコマンドの実行です。実クライアントへの導入・有効化とイベント配送は未確認です。コードからカタログを作る実行例は[Skillガイド](../skills/design/generate-domain-model-from-code.md#成果物の例)で確認できます。

## 確認するポイント

対象Agentのmanifest・hooksを選んでいるか、同梱Skillが正本と一致するかを確認します。配布物の生成・コマンドによるhooks検査と、実クライアントでの導入・有効化は区別します。

## 正本を読む

[plugin定義とビルド処理](https://github.com/yukihito-jokyu/context/tree/main/utils/plugins/generate-domain-model-from-code)と[Skill正本](https://github.com/yukihito-jokyu/context/tree/main/utils/skills/design/generate-domain-model-from-code)を参照してください。
