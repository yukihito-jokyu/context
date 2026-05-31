# AGENTS.md

このファイルは context リポジトリ自身の方針を定義する正本です。

## プロジェクト概要

このリポジトリは、Claude Code・Codex などの AI Agent 向けコンテキストを一元管理するためのリポジトリです。`AGENTS.md`、`CLAUDE.md`、Skill (`SKILL.md`) を集約し、各開発リポジトリへ生成物またはコピーとして配布する前提で運用します。

## 方針

- コンテキストの正本は Context Repository 側に集約します。
- プロジェクト単位の管理は `projects/<repo-name>/` で行います。
- 共通 Skill は `utils/skills/` に配置します。
- プロジェクト固有 Skill は `projects/<repo-name>/skills/` に配置します。
- Skill を中心に運用し、具体的な手順や実行フローは Skill または CLI に分離します。
- 同じ情報を複数箇所で管理しないことを原則とします。

## 現時点で確定している構造

- ルート `README.md`: リポジトリ全体の概要と現況を記載する
- ルート `AGENTS.md`: このファイルの配布先想定
- ルート `CLAUDE.md`: 将来 `AGENTS.md` から生成される配置先
- `cli/`: Go 製 `context` CLI を実装する予定のディレクトリ
- `utils/README.md`: 共通 Skill カタログ
- `utils/skills/*/SKILL.md`: 共通 Skill の正本
- `projects/context/README.md`: このプロジェクトの概要
- `projects/context/skills/`: context 管理用 Skill の将来配置先

## 補足

- ルート `AGENTS.md` は現時点ではこの正本と同内容を手動で反映します。
- `.codex/skills/*` は当面の互換配置であり、正本は `utils/skills/*` です。
- `README.md` は正本ではなく、概要またはカタログを提供する文書です。
