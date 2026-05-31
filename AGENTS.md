# AGENTS.md

このファイルは `projects/context/AGENTS.md` を正本とする配布結果です。

## プロジェクト概要

このリポジトリは、Claude Code や Codex などの AI Agent 向けコンテキストを一元管理するためのリポジトリです。`AGENTS.md`、`CLAUDE.md`、Skill (`SKILL.md`) を正本管理し、各開発リポジトリには生成物またはコピーを配置する想定です。

## 管理方針

- 各開発リポジトリはコンテキストの正本を持ちません。
- Context Repository に正本を集約します。
- Skill を中心に運用し、具体的な手順は Skill に切り出します。
- 同じ情報を複数箇所で管理しないことを原則とします。

## 現時点の構造

- ルート `README.md`: リポジトリ全体の概要と現況
- ルート `AGENTS.md`: このファイル。`projects/context/AGENTS.md` の配布先想定
- ルート `CLAUDE.md`: 将来生成されるファイルの配置先
- `cli/`: 将来 `context` CLI を実装する場所
- `utils/skills/`: 共通 Skill の正本
- `projects/context/`: このリポジトリ自身を管理するプロジェクト定義

## 作業時の注意

- 具体的な操作手順は `AGENTS.md` に書かず、Skill または CLI に分離します。
- Skill の正本は `SKILL.md` とし、README は要約カタログとして扱います。
- `.codex/skills/*` は当面の互換配置であり、正本ではありません。
