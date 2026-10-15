---
title: Skillとpluginの配布・導入
sidebar_label: Skillとpluginの配布・導入
---

# Skillとpluginの配布・導入

このリポジトリでは、CodexとClaude Codeを対象に、Skill単体の配布とplugin配布を使い分けます。Skillは作業手順と同梱資料、pluginは複数Skillやhooksを一つの導入単位にまとめるパッケージです。

[Issue #63の合意](https://github.com/yukihito-jokyu/context/issues/63#issuecomment-6104876148)に基づく管理方針を説明します。現在は[skill-refiner](skill-refiner.md)と[explain-html](../skills/discovery/explain-html.md)について、正本を参照する配布定義、Agent別のhooks設定、専用生成処理を作成しています。汎用の配布定義・生成処理と公開カタログは未作成です。以下のツリーは共通の配置方針、marketplaceコマンドは公開後の例です。

## 配布単位を選ぶ

| 配布するもの | 選ぶ方法 | 導入・更新・削除の単位 |
| --- | --- | --- |
| 単一Skillでhooksの同梱が不要 | `npx skills add` | Skill |
| 複数Skillをまとめたパッケージ | plugin | plugin |
| hooksを同梱するSkill | Skill数にかかわらずplugin | plugin |

単一Skillのみならplugin化の利点は小さく、すべてのSkillをpluginへ移行する必要はありません。hooks自体を使うためにpluginが必須という意味でもありません。ここでは、Skillと必要なhooksをまとめて導入できる配布方法としてpluginを選びます。[Claude Codeのpluginの用途](https://code.claude.com/docs/en/plugins#decide-whether-you-need-a-plugin)、[OpenAIのplugin構成](https://developers.openai.com/plugins/build/plugins)

## 編集する正本の構造

Skill本文を一度だけ管理し、pluginごとの配布定義から参照します。

ルートの`scripts/`にはプロジェクト全体で使う処理を置きます。特定pluginのビルドは`utils/plugins/<plugin-name>/build.py`、実行時のhook処理は同pluginの`scripts/`に置きます。ビルドは正本を配布形式へコピーするために必要で、インストールや有効化は行いません。

```text
context/
├── utils/
│   ├── skills/
│   │   └── <分類>/<skill-name>/
│   │       ├── SKILL.md
│   │       ├── scripts/              # Skill自身が使う処理
│   │       └── references/
│   └── plugins/
│       └── <plugin-name>/
│           ├── build.py              # このplugin専用のビルド
│           ├── bundle.yaml           # 含めるSkill等の配布定義
│           ├── scripts/              # このpluginのhooksが使う処理
│           ├── claude-code/
│           │   ├── plugin.json
│           │   └── hooks.json        # 必要な場合のみ
│           └── codex/
│               ├── plugin.json
│               └── hooks.json        # 必要な場合のみ
└── scripts/
    └── build-plugins.*
```

`utils/skills/`は既存の正本です。分類は[配置・候補探索のルール](../skills/authoring/index.md#配置候補探索のルール)に従い、Skillのscripts・referencesなどは必要な場合に置きます。

`utils/plugins/<plugin-name>/`はpluginごとの配布定義と固有処理の正本です。`bundle.yaml`は参照するSkill等を指定するリポジトリ独自の定義で、Agentの標準仕様ではありません。具体的なキーやスキーマは未決定です。

Agentごとの`plugin.json`と`hooks.json`は配布物を組み立てるための設定です。plugin固有のhooks処理はそのpluginの`scripts/`に置き、複数pluginで再利用する必要が出た時点で共通処理の切り出しを検討します。現段階では独立した`utils/hooks/`を設けません。

この構成は編集用です。`scripts/build-plugins.*`でSkill正本と必要なファイルをコピーし、各Agentが読み込む配布形式へ組み立てる方針です。生成物を手動編集せず、Skill正本への外部リンクにも依存させません。生成処理の言語・拡張子・出力先は未決定です。

## 公開側のパッケージ構造

編集用構造と、インストールするpluginの構造は異なります。以下はカタログと生成したpluginを公開リポジトリへ置く場合の配置例です。利用者側の保存先や固定の生成先ではなく、公開場所や名前も未決定です。

```text
公開リポジトリのルート（配置例）/
├── .claude-plugin/marketplace.json
├── .agents/plugins/marketplace.json
└── plugins/
    ├── claude-code/<plugin-name>/
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/<skill-name>/       # 正本からコピーしたSkill全体
    │   ├── hooks/hooks.json          # hooksを同梱する場合
    │   └── scripts/                  # pluginのhooksが使う処理
    └── codex/<plugin-name>/
        ├── .codex-plugin/plugin.json
        ├── skills/<skill-name>/
        ├── hooks/hooks.json
        └── scripts/
```

カタログはplugin名と取得先を案内するものです。Claude CodeとCodexのカタログは書式が異なり、それぞれ対応するpluginを参照します。`plugins/claude-code/`と`plugins/codex/`は公開物を整理するための配置例で、Agentが要求する固定パスではありません。同じSkill本文を含めても、manifestとhooks設定はAgentに合わせて生成します。[Claude Codeのmarketplace仕様](https://code.claude.com/docs/en/plugin-marketplaces)、[OpenAIのmarketplace仕様](https://developers.openai.com/plugins/build/plugins)

Codex側の例はサポートされる互換形式です。OpenAIにはルート`plugin.json`を使うportable形式もありますが、ここでは承認済み構成との関係が分かるように互換形式を示しています。hooksが不要ならhooks設定とその処理を含めません。[OpenAIのmanifest形式](https://developers.openai.com/plugins/build/plugins)

## 利用者側のインストール先

公開するパッケージの配置と、取得後にAgentが保存する場所は異なります。インストール先は各Agentのplugin管理が決めます。

| Agent・導入方式 | plugin本体の保存先 | 有効化設定 |
| --- | --- | --- |
| Claude Codeの通常のmarketplace導入 | 既定では`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` | ユーザー単位は`~/.claude/settings.json`、プロジェクト単位は`.claude/settings.json` |
| Codex系のdesktopでのmarketplace導入（OpenAI公式の説明） | `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/` | ユーザー単位は`~/.codex/config.toml`、プロジェクト単位は`.codex/config.toml` |

Claude Codeは`CLAUDE_CODE_PLUGIN_CACHE_DIR`で保存領域を変更できます。ローカルの相対パスを取得先にしたpluginなどは、配置場所から直接読み込む方式もあります。[保存先と読み込み方式](https://code.claude.com/docs/en/plugins/loading#find-plugins-on-disk)

Codexの表はOpenAI公式のdesktop導入の説明です。CLIの`plugin add`実行後の保存先は今回未検証です。クライアントのplugin管理で導入し、公開物の構造をプロジェクトへそのままコピーしない方針です。[OpenAIの保存先と設定](https://developers.openai.com/plugins/build/plugins#how-local-marketplaces-work)

プロジェクト単位の有効化は設定の適用範囲であり、plugin本体の物理的な保存先とは別です。

## Skill単体を導入する

`npx skills add`はSkillを探索し、選んだSkillを対象Agent向けに導入します。次はこのリポジトリのSkill正本を指定する例です。`<skill-name>`を導入する名前へ置き換えます。

```sh
npx skills add https://github.com/yukihito-jokyu/context/tree/main/utils/skills --skill <skill-name> --agent codex claude-code
```

導入範囲は既定でプロジェクト単位です。全プロジェクトで利用する場合は`--global`を付けます。実際の導入先はSkills CLIが管理するため、このリポジトリの未実装の配布用CLIによるコピー先と同一とは限りません。オプションと対応Agentは[Skills CLIのREADME](https://github.com/vercel-labs/skills/blob/main/README.md)で確認してください。

pluginへ移行してもこの経路は残します。ただし、`npx skills add`でSkillを導入することは、各Agentのplugin管理へパッケージを登録することではありません。

## pluginを導入する

公開済みの配布カタログをAgentへ登録し、その中のpluginを導入します。以下の`<owner>/<repo>`、`<plugin-name>`、`<marketplace-name>`は、将来の公開先・plugin名・カタログ内に定義した名前へ置き換えるものです。このリポジトリを現在pluginとして導入できるという例ではありません。

### Claude Code

```sh
claude plugin marketplace add <owner>/<repo>
claude plugin install <plugin-name>@<marketplace-name>
```

カタログ登録は一度行い、その後はplugin名で導入します。導入は既定でユーザー単位です。プロジェクト単位で有効にする場合は`install`に`--scope project`を付けます。plugin由来のSkillの呼び出しには`/<plugin-name>:<skill-name>`という名前空間が付きます。[導入方法とscope](https://code.claude.com/docs/en/discover-plugins)、[plugin由来のSkill](https://code.claude.com/docs/en/plugins)

### Codex

```sh
codex plugin marketplace add <owner>/<repo>
codex plugin add <plugin-name>@<marketplace-name>
```

`marketplace add`の登録方法は[OpenAI公式ドキュメント](https://developers.openai.com/plugins/build/plugins)で確認できます。`plugin add`は調査環境のCodex CLI 0.162.1のヘルプで確認しました。利用するバージョンの`codex plugin --help`と`codex plugin add --help`で、導入コマンドの対応を確認してください。[コマンド確認の調査記録](https://github.com/yukihito-jokyu/context/issues/63#issuecomment-6104827977)

pluginを導入できることと、同梱hooksが実行されることは区別します。OpenAIの公開案内では、hooks同梱pluginはCodex desktopへの手動インストール向けで、公開pluginディレクトリへの掲載対象外です。また、hooksには利用者の信頼確認が必要です。対象クライアントで実行されるかは実配布時に検証します。[同梱hooksの対応と制約](https://developers.openai.com/plugins/build/plugins)

## 導入経路を移行するとき

単体導入したSkillをplugin経由へ切り替える場合は、Skills CLI側の導入一覧と、Agent側のplugin一覧を確認します。同じSkillが両経路から読み込まれないよう、旧経路の導入を整理し、呼び出し名とhooksの登録元を確認します。

plugin内のSkillとhooksはpluginを単位に更新・有効化・削除します。各Agentのplugin管理の更新方法に従い、従来のSkill単体の更新コマンドでpluginも更新されたと判断しません。

## この方針の根拠と到達点

[管理方針](https://github.com/yukihito-jokyu/context/blob/c916ae3683fc1153837e15288056f3eb0071ac2a/projects/context/AGENTS.md#L11-L16)は、Skillの分類付き正本配置と重複管理の回避を定めています。正本から配布物を生成することで、Skill本文の一元管理とAgent固有形式への対応を両立します。編集用ツリー自体は公式指定ではなく、この方針と[Issue #63で承認された設計](https://github.com/yukihito-jokyu/context/issues/63#issuecomment-6104876148)に基づきます。

このガイドで決めたのは共通の構造と導入方針です。`bundle.yaml`の汎用スキーマ、カタログの公開先、共通の配布バージョン・更新手順は今後の作業です。skill-refinerでは専用の`bundle.json`と生成処理を使い、正本からローカル配布物を作成できます。導入・実環境でのhooksの有効化・公開は別に確認します。

Skillの追加・整備では[skill-authoring](../skills/authoring/skill-authoring.md)を使い、配布方針の案内だけを頼まれた場合は、plugin作成やインストールまで依頼されたと解釈しません。
