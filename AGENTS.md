# AGENTS.md

このファイルは `projects/context/AGENTS.md` を正本とする配布結果です。

## プロジェクト概要

このリポジトリは、Claude Code や Codex などの AI Agent 向けコンテキストを一元管理するためのリポジトリです。`AGENTS.md`、`CLAUDE.md`、Skill (`SKILL.md`) を正本管理し、各開発リポジトリには生成物またはコピーを配置する想定です。

## 管理方針

- 各開発リポジトリはコンテキストの正本を持ちません。
- Context Repository に正本を集約します。
- Skill を中心に運用し、具体的な手順は Skill に切り出します。
- 同じ情報を複数箇所で管理しないことを原則とします。
- 共通Skillの追加・更新では、該当する公開成果物を全削除し、更新後のSkillをサブエージェントで実行して再作成します。本文だけでなく同梱資料の更新も対象です。具体的な手順は `utils/skills/authoring/skill-authoring/SKILL.md` に従います。

## 現時点の構造

- ルート `README.md`: リポジトリ全体の概要と現況
- ルート `AGENTS.md`: このファイル。`projects/context/AGENTS.md` の配布先想定
- ルート `CLAUDE.md`: 将来生成されるファイルの配置先
- `cli/`: 将来 `context` CLI を実装する場所
- `docs/skills/`・`docs/plugins/`: Skillとpluginの導入方法・使い方を掲載する利用者向けガイド
- `docs/artifacts/skills/`・`docs/artifacts/plugins/`: ガイドから参照する実行成果物・配布物と検証記録
- `utils/skills/`: 関心ごとに分類した共通 Skill の正本。分類は最大2階層、直下配置も許容
- `projects/context/`: このリポジトリ自身を管理するプロジェクト定義

## 作業時の注意

- 具体的な操作手順は `AGENTS.md` に書かず、Skill または CLI に分離します。
- Skill の正本は `SKILL.md` とし、README は要約カタログとして扱います。
- `.codex/skills/*` は当面の互換配置であり、正本ではありません。
