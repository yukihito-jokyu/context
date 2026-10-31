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

Claude Code は導入した plugin を `~/.claude/plugins/cache/context-local/skill-foundation/<version>/` に保存し、その中の `skills/skill-foundation/SKILL.md` を読み込みます。`.claude/skills/` は単体スキル用の導入経路です。この plugin はキャッシュ内から読み込むため、このプロジェクトの `.claude/skills/` へ同じスキルを追加しません。[Claude Code の plugin 構成](https://code.claude.com/docs/en/plugins/components#skills)


```sh
codex plugin marketplace add .
codex plugin add skill-foundation@context-local
claude plugin marketplace add ./
claude plugin install skill-foundation@context-local --scope project
```

Codex の有効化設定は `.codex/config.toml`、Claude Code は `.claude/settings.json` にあります。Codex CLI の `plugin add` はユーザー設定でも有効にするため、このプロジェクトだけで使う場合はユーザー設定側を無効にし、プロジェクト設定側を有効にします。設定の優先順位は [OpenAI の導入・有効化仕様](https://developers.openai.com/plugins/build/plugins#enable-or-disable-a-plugin-for-a-repo)を参照してください。

このプロジェクトは両製品向けの有効化設定を管理しています。Codex にはユーザー指定の互換配置として、正本への `.codex/skills/skill-foundation` のリンクと `.codex/hooks.json` の直接登録もあります。製品を再起動して plugin の読み込みを反映し、Codex では hooks の信頼確認を行ってください。今回の公開作例の再作成では、実製品への再導入や有効化は行っていません。

別のプロジェクトへの導入は[導入を始める](getting-started.md)を参照してください。このローカルカタログは外部へ公開していません。

### 更新する

正本や配布定義を変えたら、既存のローカル生成先を作り直し、検証に通った配布物から導入済み plugin を更新します。現在の配布版は `0.4.1` です。Codex は同じ plugin を `add` し直し、Claude Code は導入した scope を指定して更新します。

```sh
codex plugin add skill-foundation@context-local
claude plugin update skill-foundation@context-local --scope project
```

Codex の `add` はユーザー設定でも有効にするため、プロジェクトだけで使う場合は更新後もユーザー設定を無効、プロジェクト設定を有効に揃えます。製品で plugin を読み込み直し、Codex の追加・変更された hooks は `/hooks` で確認・信頼してください。

生成スキルには、利用中の指摘と修正前後・確認画面でのユーザー承認を集める追加 hooks を必ず同梱します。収集の指示は hooks からだけ注入し、無効時はスキル本来の作成・検査・完了だけを行います。保存形式と改善用 Eval・収束テストへの渡し方は、[Skill ガイド](../skills/authoring/skill-foundation.md#利用中の指摘を改善へつなぐ)を参照してください。

## 成果物の例

新しいサブエージェントが plugin 0.4.1 の両製品向け配布物を生成し、別の場所へ移動してZIP化・展開した後に検証しました。Codex用は74ファイル、Claude Code用は75ファイルで、正本68ファイルのバイト列が一致しました。

**到達点：配布物の生成・移動・展開・hooksの直接実行と、単体動作の分離を検証済み。** 実セッションでのhooks自動発火、実ユーザー承認、独立AIの収束測定は未実施です。

### 配布物を取得する

- [Codex用plugin（ZIP）](pathname:///plugins/skill-foundation/skill-foundation-codex.zip#download)
- [Claude Code用plugin（ZIP）](pathname:///plugins/skill-foundation/skill-foundation-claude-code.zip#download)
- [検証結果の全文](pathname:///plugins/skill-foundation/verification.txt#download)
- [実行したコマンドと検証結果（JSON）](pathname:///plugins/skill-foundation/validation.json#download)
- [再実行用スクリプト](pathname:///plugins/skill-foundation/verify_plugin.py#download)
- [実行入力の原本](pathname:///plugins/skill-foundation/input.md#download)
- [実行・検証記録（JSON）](pathname:///plugins/skill-foundation/execution.json#download)

### 確認した結果

- 正本68ファイルが一致し、収集用スクリプト・確認画面・共通schema・Eval作成の処理を同梱しました。
- 各配布物の自己テスト17段階に合格しました。その中の16回帰テストで、収集モジュールとhooksが無い単体実行、収集の故障分離、日英の生成本文に収集責務を入れないこと、合成イベントでの確認画面/API・入力再現・Eval接続を検証しました。
- 古いsealを残した別コピーの微修正後も、開始・check・restart・finishが通りました。不正な出力と実行記録への直接編集は検出しました。
- 両製品の4イベントを設定内のcommandで直接実行し、終了前の差し戻しと待機からの再開を確認しました。
- Evalの検査後に収束テストの準備を実行し、専用エージェントの作業場所制限と案内を確認しました。独立AIは起動していません。
- plugin専用7テストとClaude manifest検査に合格し、59コマンド・14項目を記録しました。承認APIの試験は合成データだけで、実ユーザーの承認記録は作っていません。

## 確認するポイント

- 対象製品用の配布物を使い、plugin 管理から読み込んでいるか。
- 単体スキルと plugin、または直接 hooks と plugin hooks が二重に登録されていないか。
- `runtime/skill-foundation/` の全ファイルが正本と一致するか。
- 収束テストの実施範囲と、直接呼び出しで確認した hooks の範囲を区別しているか。
- 製品からの自動 hooks 呼び出しと、Codex の信頼確認が済んでいるか。

## 正本を読む

[plugin の配布定義・接続処理](https://github.com/yukihito-jokyu/context/tree/main/utils/plugins/skill-foundation)と、[スキル正本](https://github.com/yukihito-jokyu/context/tree/main/utils/skills/authoring/skill-foundation)で管理します。
