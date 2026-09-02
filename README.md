# context

AI Agent 向けコンテキストを一元管理するリポジトリです。

このリポジトリでは `AGENTS.md`、`CLAUDE.md`、Skill (`SKILL.md`) を管理し、各開発リポジトリには生成物またはコピーを配布する想定です。正本は Context Repository 側に集約します。

## 正本の扱い

- `projects/context/AGENTS.md` がこのリポジトリ自身の `AGENTS.md` 正本です。
- ルート `AGENTS.md` は現時点ではその配布結果を手動で反映したものです。
- [`utils/skills/*/SKILL.md`](utils/skills/README.md) が共通 Skill の正本です。
- `.codex/skills/*` は当面の互換配置であり、`utils/skills/*` と同一内容を保つ前提です。
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
- GitHub: <https://github.com/yukihito/context>
- 詳細: [projects/context/README.md](projects/context/README.md)
