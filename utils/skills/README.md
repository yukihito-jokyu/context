# 共通 Skill

`utils/skills/` は、複数プロジェクトで再利用する Skill の正本です。各 Skill の詳細な手順は対応する `SKILL.md` を参照してください。

分類は主な用途に基づき、複数の用途を持つSkillも1か所で管理します。現在は分類1階層を使用します。配置・候補探索・同名競合・同梱Skillのルールは[スキル作成・管理](../../docs/skills/authoring/index.md#配置候補探索のルール)を参照してください。使い方・ワークフロー・成果物例は[スキル活用ガイド](../../docs/index.md)にまとめています。

## 調査・理解（`discovery/`）

| Skill | 概要 |
|---|---|
| [unknowns](discovery/unknowns/SKILL.md) | 未知を分類し、適切な未知管理 Skill を選ぶ。 |
| [blindspot](discovery/blindspot/SKILL.md) | 作業前に未知や見落としやすい論点を洗い出す。 |
| [reference](discovery/reference/SKILL.md) | 既存成果物から仕様、命名、設計意図を抽出する。 |
| [compare](discovery/compare/SKILL.md) | 似た技術・仕組み・実装を、図とコードで比較して理解できる単体HTMLにまとめる。 |
| [explain-html](discovery/explain-html/SKILL.md) | 分野を限定せず、読者の問いに合う概要図と具体図を使い分け、全体像から詳細・条件と例外まで理解できる単体HTMLにまとめる。 |
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
| [archify-jp](design/archify-jp/SKILL.md) | 自然言語または Mermaid から、検証済みのインタラクティブ HTML 図を生成する。ライフサイクルは対象の生涯と状態・イベント・活動を区別して記述する。 |
| [generate-domain-model](design/generate-domain-model/SKILL.md) | 業務の概念と関係からMermaid原本・PNG・検索できるHTMLカタログを作る。 |
| [generate-usecase-diagram](design/generate-usecase-diagram/SKILL.md) | 要件文またはMermaidからユースケース図の原本とPNGを生成し、複数図をローカルのHTMLカタログで閲覧する。 |

## コミット・PR・レビュー（`development/`）

| Skill | 概要 |
|---|---|
| [pattern-foundation](development/pattern-foundation/SKILL.md) | 開発時の書き方を揃える基盤を作り、機械による強制と独立エージェントの収束テストで検証する。 |
| [commit](development/commit/SKILL.md) | 変更を確認してコミットする。 |
| [pr](development/pr/SKILL.md) | Pull Request を作成する。 |
| [self-review-html](development/self-review-html/SKILL.md) | Git 差分と AI セルフレビューを HTML で提示し、指摘に基づいて修正する。 |
| [llm-eval](development/llm-eval/SKILL.md) | LLMアプリ・AIエージェントの評価ケース、採点方法、実行基盤を構築・監査し、HTMLで基準と結果を確認する。 |

## 証跡・判断の記録・説明（`documentation/`）

| Skill | 概要 |
|---|---|
| [agent-trace](documentation/agent-trace/SKILL.md) | エージェントの作業証跡を Markdown に記録し、最短経路の簡易手順書を作成する。 |
| [issue-trace](documentation/issue-trace/SKILL.md) | Issueの調査・計画・実装・人間の確認を進め、明示的な記録依頼がある場合に、その範囲で重要な判断と理由、結果、残課題をIssueへ記録する。内容への合意と投稿の許可を区別し、記録だけの依頼にも対応する。 |
| [notes](documentation/notes/SKILL.md) | 実装中の判断、逸脱、エッジケースを記録する。 |
| [pitch](documentation/pitch/SKILL.md) | 実装の背景、変更、判断理由、レビュー観点を説明資料にまとめる。 |
| [explanation-design](documentation/explanation-design/SKILL.md) | 読者が理解に到達できる説明構成を設計する。 |

## Skillの作成・管理（`authoring/`）

| Skill | 概要 |
|---|---|
| [skill-authoring](authoring/skill-authoring/SKILL.md) | Skill の追加、更新、配置・配布単位の判定とカタログ整備を行う。 |
| [skill-foundation](authoring/skill-foundation/SKILL.md) | 決定表・出力の契約・検査・収束テストを備え、実行者による結果の違いを減らすSkillを作る。 |
| [my-skill-creator](authoring/my-skill-creator/SKILL.md) | Skill の作成、改善、評価、最適化を行う。 |
| [skill-refiner](authoring/skill-refiner/SKILL.md) | 1つのSkillを題材別の新規担当で検証し、人間の指摘から独立評価・改善をHTMLで進める。 |

explain-htmlのArchify必須ゲートは[契約と検査範囲](discovery/explain-html/references/archify-gate.md)を参照してください。hooksを使うClaude Code向け[plugin定義](../plugins/explain-html/README.md)はビルド可能ですが未導入です。
