---
title: skill-foundation plugin
sidebar_label: skill-foundation
---

# skill-foundation plugin

[skill-foundation](../skills/authoring/skill-foundation.md)と、検査用 hooks・収束テスト用エージェントを一つの導入単位にまとめます。スキルのルール・契約・検証処理は指定版の正本をそのまま使います。

## 依頼例

Claude Code では `/skill-foundation:skill-foundation`、Codex では plugin のスキルを選んで依頼します。

```text
git diff から日本語のコミットメッセージを書くスキルを作ってください。
Claude Code と Codex の両方で使います。メッセージだけを出力し、コミットは行いません。
収束テスト: 省く。
```

## 進め方

Python 3.9 以上と git を使います。リポジトリのルートで、存在しない出力先を指定して生成します。

```sh
python3 utils/plugins/skill-foundation/build.py --agent codex --output /tmp/skill-foundation-codex
python3 utils/plugins/skill-foundation/build.py --agent claude-code --output /tmp/skill-foundation-claude
```

配布物の `runtime/skill-foundation/` に、正本の全ファイルを変更せずにコピーします。`skills/skill-foundation/` は正本の手順を読む入口です。plugin 固有の接続処理が、未変更の検査スクリプトと専用エージェントを呼び出します。

Claude Code の plugin agent は `skill-foundation:skill-foundation-tester` です。専用型の `agent_type` を受け取ったときに、plugin の PreToolUse hook が元の `fence.py` を呼び出します。元のエージェント定義をそのまま plugin にコピーしても、frontmatter の hooks は登録されないため、plugin 側で接続しています。[Claude Code の plugin agent 仕様](https://code.claude.com/docs/en/plugins/components#frontmatter-fields-in-plugin-agents)

収束テストの CLI runner と、スキルの作成・検査処理は正本のままです。専用エージェントの準備だけを plugin 側の `scripts/convergence.py` が接続し、プロジェクトへのエージェント定義の書き出しを避けます。収束テストの実行回数の確認と、省略時の記録も正本に従います。

### このプロジェクトへの導入

ローカル配布物は `.plugin-build/skill-foundation/codex/` と `.plugin-build/skill-foundation/claude-code/` に生成します。これらは生成物で、Git の管理対象から除外しています。新しいチェックアウトでは、先に次の2コマンドを実行してください。既に生成先がある場合はビルドが上書きを拒否するため、更新時は既存の生成先を確認してから作り直します。

```sh
python3 utils/plugins/skill-foundation/build.py --agent codex --output .plugin-build/skill-foundation/codex
python3 utils/plugins/skill-foundation/build.py --agent claude-code --output .plugin-build/skill-foundation/claude-code
```

両製品用のローカルカタログは `.agents/plugins/marketplace.json` と `.claude-plugin/marketplace.json` に置きます。カタログ名は `context-local` です。

この2ファイルは plugin の名前と取得元を案内するカタログで、スキル本体ではありません。`.agents/plugins/marketplace.json` は Codex のリポジトリ内カタログ、`.claude-plugin/marketplace.json` は Claude Code の marketplace の標準位置です。[OpenAI のローカルカタログ仕様](https://developers.openai.com/plugins/build/plugins#build-your-own-curated-plugin-list)、[Claude Code の marketplace 仕様](https://code.claude.com/docs/en/plugin-marketplaces)

Claude Code は導入した plugin を `~/.claude/plugins/cache/context-local/skill-foundation/0.1.0/` に保存し、その中の `skills/skill-foundation/SKILL.md` を読み込みます。`.claude/skills/` は単体スキル用の導入経路です。この plugin はキャッシュ内から読み込むため、このプロジェクトの `.claude/skills/` へ同じスキルを追加しません。[Claude Code の plugin 構成](https://code.claude.com/docs/en/plugins/components#skills)


```sh
codex plugin marketplace add .
codex plugin add skill-foundation@context-local
claude plugin marketplace add ./
claude plugin install skill-foundation@context-local --scope project
```

Codex の有効化設定は `.codex/config.toml`、Claude Code は `.claude/settings.json` にあります。Codex CLI の `plugin add` はユーザー設定でも有効にするため、このプロジェクトだけで使う場合はユーザー設定側を無効にし、プロジェクト設定側を有効にします。設定の優先順位は [OpenAI の導入・有効化仕様](https://developers.openai.com/plugins/build/plugins#enable-or-disable-a-plugin-for-a-repo)を参照してください。

このプロジェクトは両製品向けの有効化設定を管理しています。同じスキルの単体配置・直接登録 hooks と plugin の二重登録は避けます。製品を再起動して plugin の読み込みを反映し、Codex では hooks の信頼確認を行ってください。今回の公開作例の再作成では、実製品への再導入や有効化は行っていません。

別のプロジェクトへの導入は[導入を始める](getting-started.md)を参照してください。このローカルカタログは外部へ公開していません。

## 成果物の例

新しいサブエージェントが両製品向けの配布物を生成し、空白を含む別の場所へ移動して ZIP 化・展開した後に検証しました。Codex 用は103ファイル、Claude Code 用は104ファイルで、同梱した正本97ファイルはすべて元のバイト列と一致しました。

**到達点：配布物の生成・移動・展開・hooks の直接実行まで検証済み。** 実セッションからの自動 hooks 呼び出し、実製品への導入、独立した AI による収束テストは未確認です。

### 配布物を取得する

- [Codex 用 plugin（ZIP）](pathname:///plugins/skill-foundation/skill-foundation-codex.zip#download)
- [Claude Code 用 plugin（ZIP）](pathname:///plugins/skill-foundation/skill-foundation-claude-code.zip#download)
- [検証結果の全文](pathname:///plugins/skill-foundation/verification.txt#download)
- [実行したコマンドと検証結果（JSON）](pathname:///plugins/skill-foundation/validation.json#download)
- [実行入力の原本](pathname:///plugins/skill-foundation/input.md#download)
- [実行・検証記録（JSON）](pathname:///plugins/skill-foundation/execution.json#download)

### 確認した結果

- 正本97ファイルと、合格時のハッシュに登録した49ファイルが一致しました。
- 展開後の設定に書かれた command を直接実行し、両製品の4イベント、保護ファイルの拒否・確認、終了前の差し戻し、待機からの再開を確認しました。
- 専用エージェントへの作業ディレクトリの制限と、収束テストの準備・プロンプトが専用型を案内することを確認しました。
- 7件の実行テストと Claude Code の manifest 検査に合格しました。

## 確認するポイント

- 対象製品用の配布物を使い、plugin 管理から読み込んでいるか。
- 単体スキルと plugin、または直接 hooks と plugin hooks が二重に登録されていないか。
- `runtime/skill-foundation/` のファイルと合格時のハッシュが正本と一致するか。
- 収束テストの実施範囲と、直接呼び出しで確認した hooks の範囲を区別しているか。
- 製品からの自動 hooks 呼び出しと、Codex の信頼確認が済んでいるか。

## 正本を読む

[plugin の配布定義・接続処理](https://github.com/yukihito-jokyu/context/tree/main/utils/plugins/skill-foundation)と、[スキル正本](https://github.com/yukihito-jokyu/context/tree/main/utils/skills/authoring/skill-foundation)で管理します。
