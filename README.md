# context

AI Agent 向けコンテキストを一元管理するリポジトリです。

このリポジトリでは `AGENTS.md`、`CLAUDE.md`、Skill (`SKILL.md`) を管理し、各開発リポジトリには生成物またはコピーを配布する想定です。正本は Context Repository 側に集約します。

## 正本の扱い

- `projects/context/AGENTS.md` がこのリポジトリ自身の `AGENTS.md` 正本です。
- ルート `AGENTS.md` は現時点ではその配布結果を手動で反映したものです。
- [`utils/skills/` 配下の各Skillの `SKILL.md`](utils/skills/README.md) が共通 Skill の正本です。
- 共通 Skill は関心ごとで分類し、分類は最大2階層まで、直下の配置も許容します。配置と候補探索のルールは[スキル作成・管理](docs/authoring/index.md#配置候補探索のルール)を参照してください。
- `.codex/skills/<skill-name>/` は当面の互換配置です。分類階層を含めず、対応する正本のSkillディレクトリと同一内容を保つ前提です。
- `README.md` はカタログまたは概要文書であり、Skill の正本ではありません。

## Skillとpluginの配布方針

CodexとClaude Codeを対象に、配布する内容に応じて導入方法を選びます。

| 配布するもの | 導入方法 | 導入・更新・削除の単位 |
| --- | --- | --- |
| 単一Skillでhooksの同梱が不要 | `npx skills add` | Skill |
| 複数Skillをまとめたパッケージ | 各Agentのplugin管理 | plugin |
| hooksを同梱するSkill | Skill数にかかわらず各Agentのplugin管理 | plugin |

### 編集するディレクトリ構造

Skillの正本は`utils/skills/`に置き、pluginの配布定義から参照します。plugin用にSkill本文を手動複製せず、配布時に正本から生成します。以下は合意済みの編集用構造です。現在は[skill-refiner](docs/authoring/skill-refiner.md)と[explain-html](docs/discovery/explain-html.md)に、対応Agent向けのhooks設定と専用生成処理を用意しています。汎用の`build-plugins.*`と配布カタログは未実装です。

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

`bundle.yaml`は、このリポジトリ独自の配布定義です。含めるSkillの正本を参照するためのもので、具体的なスキーマは未決定です。Agentごとの`plugin.json`と`hooks.json`は配布物を組み立てるための設定として管理します。plugin固有のhooks処理は、そのpluginの`scripts/`へ配置します。

### 公開側のパッケージ構造

編集用の配布定義から、各Agentが読み込めるpluginを生成します。分類階層を外したSkillディレクトリ全体と、必要なhooks・処理を同梱します。以下は、カタログと生成したpluginを公開リポジトリへ置く場合の配置例です。利用者のインストール先や、固定の生成先を示すものではありません。

```text
公開リポジトリのルート（配置例）/
├── .claude-plugin/marketplace.json   # Claude Code用の配布カタログ
├── .agents/plugins/marketplace.json # Codex用の配布カタログ
└── plugins/
    ├── claude-code/<plugin-name>/
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/<skill-name>/
    │   ├── hooks/hooks.json          # hooksを同梱する場合
    │   └── scripts/
    └── codex/<plugin-name>/
        ├── .codex-plugin/plugin.json
        ├── skills/<skill-name>/
        ├── hooks/hooks.json          # hooksを同梱する場合
        └── scripts/
```

各カタログは、そのAgent向けのplugin名と取得先を定義します。`plugins/claude-code/`と`plugins/codex/`は、このリポジトリで公開物を分けるための配置例で、Agentが要求する固定パスではありません。Codex側のmanifestはサポートされる互換形式です。公開先・生成先・カタログ名は未決定です。[Claude Codeのカタログと取得先](https://code.claude.com/docs/en/plugin-marketplaces)、[Codexのカタログと取得先](https://developers.openai.com/plugins/build/plugins)

### 利用者側のインストール先

カタログから取得したpluginの保存先は、各Agentのplugin管理が決めます。上の公開リポジトリの構造を利用者のプロジェクトへそのままコピーする方式ではありません。

| Agent・導入方式 | インストールしたpluginの保存先 | 有効化設定 |
| --- | --- | --- |
| Claude Codeの通常のmarketplace導入 | 既定では`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` | ユーザー単位は`~/.claude/settings.json`、プロジェクト単位は`.claude/settings.json` |
| Codex系のdesktopでのmarketplace導入（OpenAI公式の説明） | `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/` | ユーザー単位は`~/.codex/config.toml`、プロジェクト単位は`.codex/config.toml` |

Claude Codeの保存領域は`CLAUDE_CODE_PLUGIN_CACHE_DIR`で変更できます。また、ローカルの相対パスを取得先にしたpluginなどは、配置した場所から直接読み込む方式もあります。[Claude Codeの保存先と読み込み方式](https://code.claude.com/docs/en/plugins/loading#find-plugins-on-disk)

Codexの表はOpenAI公式がdesktop導入について示す保存先です。Codex CLIの`plugin add`は確認済みですが、そのコマンドを実行した後の保存先は今回検証していません。保存先を決め打ちしてコピーせず、対応するクライアントのplugin管理で導入します。[OpenAIの保存先と設定](https://developers.openai.com/plugins/build/plugins#how-local-marketplaces-work)

プロジェクト単位の有効化設定と、plugin本体の物理的な保存先は別です。`--scope project`を指定しても、plugin本体が必ずプロジェクト直下へ配置されるとは限りません。

### 単一Skillを導入する

`<skill-name>`を導入するSkill名へ置き換えます。

```sh
npx skills add https://github.com/yukihito-jokyu/context/tree/main/utils/skills --skill <skill-name> --agent codex claude-code
```

既定ではプロジェクト単位で導入します。全プロジェクトで使う場合は`--global`を付けます。導入先はSkills CLIが管理します。[Skills CLIのオプション](https://github.com/vercel-labs/skills/blob/main/README.md)

### pluginを導入する

pluginは、配布カタログを登録した後、plugin名を指定して導入します。以下はカタログ公開後の導入方法です。このリポジトリのpluginはまだ公開していません。

- `<owner>/<repo>`：配布カタログを公開したGitHubリポジトリ
- `<plugin-name>`：カタログに登録されたplugin名
- `<marketplace-name>`：カタログ内に定義された名前

**Claude Code**

```sh
claude plugin marketplace add <owner>/<repo>
claude plugin install <plugin-name>@<marketplace-name>
```

既定ではユーザー単位で導入します。プロジェクト単位にする場合は`install`へ`--scope project`を付けます。plugin内のSkillは`/<plugin-name>:<skill-name>`で呼び出します。[Claude Codeの導入方法](https://code.claude.com/docs/en/discover-plugins)

**Codex**

```sh
codex plugin marketplace add <owner>/<repo>
codex plugin add <plugin-name>@<marketplace-name>
```

`plugin add`は調査環境のCodex CLI 0.162.1で確認したコマンドです。利用環境の`codex plugin --help`で対応を確認できます。hooks同梱pluginの公開案内はCodex desktopへの手動導入向けであり、公開pluginディレクトリへの掲載対象外です。[Codexのカタログ登録とhooksの対応](https://developers.openai.com/plugins/build/plugins)

Skill単体の導入からpluginへ切り替えるときは、同じSkillが両経路から読み込まれないよう、以前の導入を整理します。以後、そのパッケージの更新・削除は各Agentのplugin管理で行います。

## 予定・未実装

- Go 製 `context` CLI の実装
- `context deploy` / `context deploy <repo-name>` の実装
- `CLAUDE.md` の生成
- `.claude/skills/` と `.codex/skills/` への配布フロー
- `projects/<repo-name>/` ごとの個別コンテキスト管理

## 補足

- 共通 Skill は `utils/skills/` に配置します。
- プロジェクト固有 Skill は将来的に `projects/<repo-name>/skills/` に配置します。
- `SKILL.md` が正本、`README.md` はその要約カタログという関係を前提に運用します。

## プロジェクト一覧

### context

- 説明: この Context Repository 自身を管理するためのプロジェクト定義
- GitHub: <https://github.com/yukihito-jokyu/context>
- 詳細: [projects/context/README.md](projects/context/README.md)

## スキル活用ガイド

[`docs/`](docs/index.md)に、スキルの使い方・ワークフロー・成果物の例をまとめています。`utils/skills/`と同じ6分類を使い、スキルごとの正本へリンクします。公開先は[GitHub Pages](https://yukihito-jokyu.github.io/context/)です（初回デプロイ前は閲覧できません）。

### ローカルで確認する

Node.js 22以上を使い、リポジトリのルートで実行します。

```sh
npm ci
npm start
```

本番と同じビルドを確認する場合は次を実行します。

```sh
npm run typecheck
npm run test:search
npm run examples:check
npm run build
npm run test:docs
npm run serve
```

### 更新と公開

`docs/`内のMarkdownを編集します。カテゴリは`_category_.json`、入口と分類の並びは`sidebars.ts`で管理します。スキルの実行手順を変更する場合は、`utils/skills/`配下の正本を先に更新し、対応するガイドを合わせてください。

成果物例は`docs/artifacts/examples/<skill-name>/`の実行入力、実出力、画像、検証記録を正として保存します。`execution.json`には利用した正本と成果物のSHA-256、到達点を残します。実例を更新したら`npm run examples:sync`で各ページの「成果物の例」を原本から反映します。`npm run examples:check`は原本・正本・表示の不一致を検出し、CIでも実行します。

正本更新後も過去の実例を保持する場合は、実行時の本文を成果物内へ保管し、`skill_snapshot`と`skill_version_note`で実行版と現在版の違いを明記します。元のSkillハッシュを保持し、保管本文も原本一覧へ登録します。検査は保管版の改変・説明の欠落・実例外の保存先を拒否し、公開ガイドに旧手順の実例であることを表示します。

成果物のMarkdownは文書探索と検索索引から除外し、原本として静的配信します。ダウンロードには`[原本](pathname:///examples/<skill-name>/<file>#download)`を使います。ファイルの存在と同一性は実行記録とサイトテストで確認し、ベースパスはリンク部品で付加します。画像は通常のMarkdown画像として参照できます。複数ファイルの画面は参照関係を保ったZIPで配ります。

`npm run serve`はHTML原本の拡張子を維持するプレビューを起動します。標準の`docusaurus serve`はHTML URLを整形するため、成果物原本の取得確認には使いません。

参考にした`rule`リポジトリに合わせ、日本語UI、ライト／ダーク切替、日本語本文検索、リンク・アンカーの厳格な検証を採用しています。検索は外部サービスを使わず、ビルド時に`docs/`の索引を生成します。Mermaid図も表示できます。

[公開ワークフロー](.github/workflows/docs-pages.yml)は、PRで型検査・検索テスト・本番ビルドを実行し、`main`へのpushまたは`main`からの手動実行で`build/`をデプロイします。初回はGitHubのSettings → Pages → Build and deployment → Sourceで「GitHub Actions」を選択してください。公開環境`github-pages`に承認ルールがある場合は、その承認も必要です。

`/context/`をベースパスに使います。リポジトリ名や公開先を変える場合は`docusaurus.config.ts`の`url`と`baseUrl`を更新します。生成物と依存パッケージはGit管理しません。
