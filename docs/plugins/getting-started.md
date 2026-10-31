---
title: Pluginの導入を始める
sidebar_label: 導入を始める
---

# Pluginの導入を始める

現在は、このリポジトリを取得してpluginの配布物をローカル生成できます。公開marketplaceの登録だけで導入する経路は未提供です。生成できた後、利用するAgentでの読み込み・信頼・有効化を別に確認します。

## 1. 用途とAgentを選ぶ

- スキル改善の工程を検査するなら[skill-refiner](skill-refiner.md)。Codex用またはClaude Code用を選びます。
- 解説HTMLの完成検査を自動で呼ぶなら[explain-html](explain-html.md)。Claude Code用を使います。
- 業務の概念をMermaid・PNG・HTMLカタログにするなら[generate-domain-model](generate-domain-model.md)。Codex用またはClaude Code用を選びます。
- コードの根拠を辿れる図を作るなら[generate-domain-model-from-code](generate-domain-model-from-code.md)。Codex用またはClaude Code用を選びます。
- 図付きHTMLの要件定義書を作るなら[write-requirement-document](write-requirement-document.md)。Codex用またはClaude Code用を選びます。

hooksを必要としない場合は[Skill単体の導入](../skills/getting-started.md)を選べます。Skillの導入だけではpluginのhooksは登録されません。

## 2. 配布物を生成する

Python 3.10以降を用意し、このリポジトリのルートで実行します。出力先には、まだ存在しないリポジトリ外のディレクトリを指定してください。

```sh
python3 utils/plugins/skill-refiner/build.py --agent codex --output /tmp/skill-refiner-codex
python3 utils/plugins/skill-refiner/build.py --agent claude-code --output /tmp/skill-refiner-claude
python3 utils/plugins/explain-html/build.py --output /tmp/explain-html-plugin
```

必要な行だけ実行します。既存の出力先への上書きは拒否されます。配布物には正本からコピーしたSkill、Agent別のmanifest・hooks設定、hook処理が入ります。

## 3. Agentで読み込みと有効化を確認する

生成処理はAgentの設定を変更しません。生成先を残したまま、次の方法で読み込みを確認します。

### Claude Code

利用するプロジェクトから、生成したディレクトリを指定してセッションを起動します。

```sh
claude --plugin-dir /tmp/skill-refiner-claude
# explain-htmlを使う場合
claude --plugin-dir /tmp/explain-html-plugin
```

必要な行だけ実行し、`/plugin`で読み込み状態を確認します。この指定は開発・確認用の読み込みです。継続的な配布はmarketplaceを使います。[Claude Code公式のローカル読み込み](https://code.claude.com/docs/en/plugins/create#develop-without-a-marketplace)

### Codex／ChatGPT desktop

skill-refinerのCodex用生成物を、導入先プロジェクトの `plugins/skill-refiner/` へコピーします。次は導入先プロジェクトで実行する例です。

```sh
mkdir -p plugins
cp -R /tmp/skill-refiner-codex plugins/skill-refiner
```

同プロジェクトの `.agents/plugins/marketplace.json` に次のエントリを追加します。既存のカタログがある場合は上書きせず、`plugins`一覧へ追加してください。

```json
{
  "name": "local-context",
  "plugins": [
    {
      "name": "skill-refiner",
      "source": {"source": "local", "path": "./plugins/skill-refiner"},
      "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
      "category": "Productivity"
    }
  ]
}
```

`source.path`はプロジェクトルートからの相対パスです。ChatGPT desktopを再起動し、Plugins Directoryで`local-context`を選び、pluginを導入します。hooksの定義を確認して信頼し、新しいセッションで動作を確かめます。CLIで導入一覧に載ることだけでhooksの動作確認を済ませないでください。[OpenAI公式のローカルplugin導入](https://developers.openai.com/plugins/build/plugins#install-a-local-plugin-manually)

このリポジトリの公開marketplaceは未提供です。[配布・導入ガイド](distribution.md#pluginを導入する)の公開カタログ用コマンドは、公開後の例です。

同じSkillを単体でも導入している場合は、現在の導入一覧を確認し、どちらから読み込まれているかを整理します。plugin由来のSkillの呼び出し方もAgent側で確認します。

## 4. 対象の作業とhooksを確認する

個別ページの手順に従って対象の作業領域を指定します。配布物の生成成功だけでは、実際のAgentによるhooksの実行まで確認できません。個別ページの成果物例は、ローカル生成とZIP内容の検証までを示します。

更新時は編集用の正本から再生成し、Agentのplugin管理に従って更新します。生成済みのSkillやhooksを直接編集すると、次の生成で変更が失われます。
