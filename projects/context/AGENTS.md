# AGENTS.md

このファイルは context リポジトリ自身の方針を定義する正本です。

## プロジェクト概要

このリポジトリは、Claude Code・Codex などの AI Agent 向けコンテキストを一元管理するためのリポジトリです。`AGENTS.md`、`CLAUDE.md`、Skill (`SKILL.md`) を集約し、各開発リポジトリへ生成物またはコピーとして配布する前提で運用します。

## 方針

- コンテキストの正本は Context Repository 側に集約します。
- プロジェクト単位の管理は `projects/<repo-name>/` で行います。
- 共通 Skill は `utils/skills/` に関心ごとで分類して配置します。分類は最大2階層とし、直下配置も許容します。
- プロジェクト固有 Skill は `projects/<repo-name>/skills/` に配置します。
- Skill を中心に運用し、具体的な手順や実行フローは Skill または CLI に分離します。
- 同じ情報を複数箇所で管理しないことを原則とします。
- 共通Skillの追加・更新では、該当する公開成果物を全削除し、更新後のSkillをサブエージェントで実行して再作成します。本文だけでなく同梱資料の更新も対象です。具体的な手順は `utils/skills/authoring/skill-authoring/SKILL.md` に従います。

## 現時点で確定している構造

- ルート `README.md`: リポジトリ全体の概要と現況を記載する
- ルート `AGENTS.md`: このファイルの配布先想定
- ルート `CLAUDE.md`: 将来 `AGENTS.md` から生成される配置先
- `cli/`: Go 製 `context` CLI を実装する予定のディレクトリ
- `utils/README.md`: 共通 Skill カタログ
- `utils/skills/` 配下の各Skillの `SKILL.md`: 共通 Skill の正本
- `docs/skills/`・`docs/plugins/`: Skillとpluginの導入方法・使い方を掲載する利用者向けガイド
- `docs/artifacts/skills/`・`docs/artifacts/plugins/`: ガイドから参照する実行成果物・配布物と検証記録
- `projects/context/README.md`: このプロジェクトの概要
- `projects/context/skills/`: context 管理用 Skill の将来配置先

## 補足

- ルート `AGENTS.md` は現時点ではこの正本と同内容を手動で反映します。
- `.codex/skills/<skill-name>/` は分類階層を含めない互換配置であり、正本は `utils/skills/` 配下の対応するSkillディレクトリです。
- `README.md` は正本ではなく、概要またはカタログを提供する文書です。
