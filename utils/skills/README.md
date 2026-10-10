# 共通 Skill

`utils/skills/` は、複数プロジェクトで再利用する Skill の正本です。各 Skill の詳細な手順は対応する `SKILL.md` を参照してください。

分類は主な用途に基づき、複数の用途を持つSkillも1か所で管理します。現在は分類1階層を使用します。配置・候補探索・同名競合・同梱Skillのルールは[要件定義](../../docs/requirements.md#23-共通skill管理)を参照してください。

## 調査・理解（`discovery/`）

| Skill | 概要 |
|---|---|
| [unknowns](discovery/unknowns/SKILL.md) | 未知を分類し、適切な未知管理 Skill を選ぶ。 |
| [blindspot](discovery/blindspot/SKILL.md) | 作業前に未知や見落としやすい論点を洗い出す。 |
| [reference](discovery/reference/SKILL.md) | 既存成果物から仕様、命名、設計意図を抽出する。 |
| [compare](discovery/compare/SKILL.md) | 似た技術・仕組み・実装を、図とコードで比較して理解できる単体HTMLにまとめる。 |
| [interview](discovery/interview/SKILL.md) | 曖昧な点や既知の未知を一問ずつ明確にする。 |
| [prototype](discovery/prototype/SKILL.md) | UI や成果物を軽量に可視化して判断基準を引き出す。 |
| [quiz](discovery/quiz/SKILL.md) | AI 生成物や変更内容への理解漏れを確認する。 |

## 計画・Issue分割（`planning/`）

| Skill | 概要 |
|---|---|
| [grill-issue](planning/grill-issue/SKILL.md) | Issue を精査し、議論を経て実装計画を立てる。 |
| [plan](planning/plan/SKILL.md) | 重要判断を明示したレビュー可能な実装計画を作る。 |
| [to-issues](planning/to-issues/SKILL.md) | 計画や PRD を独立して着手可能な Issue に分割する。 |

## 画面要件・図の作成（`design/`）

| Skill | 概要 |
|---|---|
| [html-requirements-workshop](design/html-requirements-workshop/SKILL.md) | HTML モックを反復しながら曖昧な画面要件を固める。 |
| [react-requirements-workshop](design/react-requirements-workshop/SKILL.md) | Design System に沿う React 画面を枠付きプレビューで見ながら要件を固める。画面案と承認履歴を保存し、起動済みサーバーを再利用する。 |
| [archify-jp](design/archify-jp/SKILL.md) | 自然言語または Mermaid から、検証済みのインタラクティブ HTML 図を生成する。 |

## コミット・PR・レビュー（`development/`）

| Skill | 概要 |
|---|---|
| [commit](development/commit/SKILL.md) | 変更を確認してコミットする。 |
| [pr](development/pr/SKILL.md) | Pull Request を作成する。 |
| [self-review-html](development/self-review-html/SKILL.md) | Git 差分と AI セルフレビューを HTML で提示し、指摘に基づいて修正する。 |

## 証跡・判断の記録・説明（`documentation/`）

| Skill | 概要 |
|---|---|
| [agent-trace](documentation/agent-trace/SKILL.md) | エージェントの作業証跡を Markdown に記録し、最短経路の簡易手順書を作成する。 |
| [issue-trace](documentation/issue-trace/SKILL.md) | Issueの調査・計画・実装や実行・人間のフィードバックへの対応を進め、各段階の結果と判断理由を記録する。計画と修正は承認後にまとめ、記録だけの依頼にも対応する。 |
| [notes](documentation/notes/SKILL.md) | 実装中の判断、逸脱、エッジケースを記録する。 |
| [pitch](documentation/pitch/SKILL.md) | 実装の背景、変更、判断理由、レビュー観点を説明資料にまとめる。 |
| [explanation-design](documentation/explanation-design/SKILL.md) | 読者が理解に到達できる説明構成を設計する。 |

## Skillの作成・管理（`authoring/`）

| Skill | 概要 |
|---|---|
| [skill-authoring](authoring/skill-authoring/SKILL.md) | Skill の追加、更新、配置判定とカタログ整備を行う。 |
| [my-skill-creator](authoring/my-skill-creator/SKILL.md) | Skill の作成、改善、評価、最適化を行う。 |
