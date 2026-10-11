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

成果物のMarkdownは文書探索と検索索引から除外し、原本として静的配信します。ダウンロードには`[原本](pathname:///examples/<skill-name>/<file>#download)`を使います。ファイルの存在と同一性は実行記録とサイトテストで確認し、ベースパスはリンク部品で付加します。画像は通常のMarkdown画像として参照できます。複数ファイルの画面は参照関係を保ったZIPで配ります。

`npm run serve`はHTML原本の拡張子を維持するプレビューを起動します。標準の`docusaurus serve`はHTML URLを整形するため、成果物原本の取得確認には使いません。

参考にした`rule`リポジトリに合わせ、日本語UI、ライト／ダーク切替、日本語本文検索、リンク・アンカーの厳格な検証を採用しています。検索は外部サービスを使わず、ビルド時に`docs/`の索引を生成します。Mermaid図も表示できます。

[公開ワークフロー](.github/workflows/docs-pages.yml)は、PRで型検査・検索テスト・本番ビルドを実行し、`main`へのpushまたは`main`からの手動実行で`build/`をデプロイします。初回はGitHubのSettings → Pages → Build and deployment → Sourceで「GitHub Actions」を選択してください。公開環境`github-pages`に承認ルールがある場合は、その承認も必要です。

`/context/`をベースパスに使います。リポジトリ名や公開先を変える場合は`docusaurus.config.ts`の`url`と`baseUrl`を更新します。生成物と依存パッケージはGit管理しません。
