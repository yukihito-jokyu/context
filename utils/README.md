# utils

`utils/` は複数プロジェクトで再利用する共通 Skill を管理する領域です。複数Skillやhooksをまとめて配布する場合は、Skill正本とは別にpluginの配布定義を管理する方針です。

## 正本関係

- `utils/skills/` 配下の各Skillの `SKILL.md` が正本です。
- この `README.md` は Skill カタログです。
- `README.md` と `SKILL.md` に差分がある場合は `SKILL.md` を正とします。

## 配布単位とpluginの配置

単一Skillとpluginの使い分け、合意済みの`utils/plugins/<plugin-name>/`構造、Codex・Claude Codeへの導入方法は[配布・導入ガイド](../docs/authoring/plugin-distribution.md)を参照してください。plugin配布定義と生成処理は未実装です。

## Skill カタログ

関心ごとの分類と配置先は[共通Skill一覧](skills/README.md)を参照してください。以下は各Skillの用途と使い方の要約です。

### [agent-trace](skills/documentation/agent-trace/SKILL.md)

- 目的: エージェントの作業証跡を Markdown に記録し、最短経路の簡易手順書を作成する
- 使うタイミング: 作業ログや操作履歴を残したいとき、または完了後に再現手順をまとめたいとき
- 使い方: `.agent-trace/<yyyymmdd-HHmmss>/` に `<task-slug>.md` を記録し、「ログをまとめて」の指示で `<task-slug>-guide.md` を生成する

### [issue-trace](skills/documentation/issue-trace/SKILL.md)

- 目的: Issueを基準に、調査・実装・修正・方針決定の証跡を記録する
- 使うタイミング: タスクの作業経緯や検証結果をIssueに残したいとき
- 使い方: 対象Issueと実態を確認し、重要な発見・判断・結果・残課題の変化を簡潔に記録する。テンプレートの情報は短い段落へまとめられ、最新状態と終了理由も残す。投稿結果は内部で確認する

### [archify-jp](skills/design/archify-jp/SKILL.md)

- 目的: 自然言語または Mermaid から、検証済みの探索可能なインライン SVG 図を単体 HTML として生成する
- 使うタイミング: アーキテクチャ、ワークフロー、シーケンス、データフロー、ライフサイクル、クラス、ER 図を可視化したいとき
- 使い方: 図の種類と内容を入力し、Skill のスキーマ・レンダラー・検証手順に沿って HTML と必要な検証結果を作成する

### [generate-domain-model](skills/design/generate-domain-model/SKILL.md)

- 目的: 業務の概念と関係からMermaid原本・PNG・HTMLカタログを生成する
- 使うタイミング: 仕様や業務説明を図に整理し、複数の図を一覧・検索・拡大したいとき
- 使い方: 資料とカタログ名を渡し、根拠のある概念・関係・多重度を作成する。資料で確定できない点は未確認事項に残し、PNGとHTMLの対応を検査する

### [generate-domain-model-from-code](skills/design/generate-domain-model-from-code/SKILL.md)

- 目的: コードの根拠付きで業務概念と関係のMermaid・PNG・HTMLカタログを生成する
- 使うタイミング: ローカルリポジトリを調査し、実装の行・抜粋・ハッシュを辿れる図を作りたいとき
- 使い方: 対象と調査範囲を渡し、コードを読みmodel.jsonを作る。生成した図とカタログを検査する

### [unknowns](skills/discovery/unknowns/SKILL.md)

- 目的: AI開発における未知管理の入口として、作業リスクと使うべき子スキルを選ぶ
- 使うタイミング: 要件、仕様、設計、実装方針に曖昧さがある作業を始める前
- 使い方: 作業目的と既知・未知・参照対象を整理し、リスク別に必要な子スキルと実行順序を決める

### [blindspot](skills/discovery/blindspot/SKILL.md)

- 目的: 作業前に無自覚の未知と見落としやすい論点を洗い出す
- 使うタイミング: 未知のコード領域や大きな変更に入る前、何を見落としているか分からないとき
- 使い方: 現時点の理解と不安点を入力し、手戻りになりやすい論点と確認質問を出す

### [prototype](skills/discovery/prototype/SKILL.md)

- 目的: UIや成果物を軽量に可視化し、言語化しにくい判断基準を引き出す
- 使うタイミング: 画面、レポート、資料、体験など、見れば判断できる要素を本実装前に確認したいとき
- 使い方: ダミーデータや複数案を使ってプロトタイプを作り、反応から仕様や判断基準を抽出する

### [html-requirements-workshop](skills/design/html-requirements-workshop/SKILL.md)

- 目的: 曖昧な画面構想を、HTMLモックと自然言語フィードバックの反復で要件へ具体化する
- 使うタイミング: 何を作るか固まっておらず、画面を見ながら目的・操作・詳細設計を擦り合わせたいとき
- 使い方: 構造化入力から履歴付きのモックを生成・検証し、承認結果を要件Markdownと承認済みHTMLへ統合する

### [react-requirements-workshop](skills/design/react-requirements-workshop/SKILL.md)

- 目的: 曖昧な React UI 構想を、動く画面案とフィードバックの反復で要件へ具体化する
- 使うタイミング: React の画面を見ながら目的・操作・詳細設計を擦り合わせたいとき、または Design System に沿った画面要件と案の履歴を残したいとき
- 使い方: 専用の作業領域に Design System 準拠の React 画面案とレビュー UI を生成・検証し、フィードバックを次の案と要件 Markdown へ反映して、承認済みの画面と要件を保管する

### [interview](skills/discovery/interview/SKILL.md)

- 目的: 曖昧な点や既知の未知を、一問ずつ質問して明確にする
- 使うタイミング: 回答次第で設計、UX、作業順が変わる論点があるとき
- 使い方: 最重要質問を一つだけ提示し、回答から仕様・制約・優先順位を更新する

### [reference](skills/discovery/reference/SKILL.md)

- 目的: 既存コードや成果物から、合わせるべき仕様・命名・設計意図を抽出する
- 使うタイミング: 既存コード、既存画面、既存仕様、参考実装に合わせる必要があるとき
- 使い方: 参照対象を読み、合わせるべき点と合わせなくてよい点を分けて適用方針を作る

### [compare](skills/discovery/compare/SKILL.md)

- 目的: 似た技術・仕組み・実装の違いを、全体図からコード・設定まで比較して理解できる単体HTMLにまとめる
- 使うタイミング: 似た機能の仕組みや変更前後の構造を、図と具体例で比較して理解したいとき
- 使い方: 比較対象と資料を渡し、同梱ArchifyとHTMLテンプレートを使って、全体像・動作・実装・使い分けを関心別ページで説明する

### [explain-html](skills/discovery/explain-html/SKILL.md)

- 目的: 一つの事象・事柄を、全体像から具体例、詳細、条件と例外まで理解できる単体HTMLにまとめる
- 使うタイミング: 技術・業務・制度・自然現象などの仕組みを、図と具体物で掘り下げて理解したいとき
- 使い方: 題材と資料を渡し、同梱Archifyとテンプレートを使って、関心別ページ・必要な段階再生・出典照合を備えた解説を作る

### [plan](skills/planning/plan/SKILL.md)

- 目的: 実装前に重要判断を先頭へ出した、レビュー可能な実装計画を作る
- 使うタイミング: データモデル、型、UX、責務分割などの判断を含む実装前
- 使い方: 重要判断、実装ステップ、機械的変更、未決定事項、レビュー観点を分けて計画する

### [notes](skills/documentation/notes/SKILL.md)

- 目的: 実装中の判断、計画からの逸脱、エッジケースを記録する
- 使うタイミング: 実装中に計画外の判断や保守的な選択が発生したとき
- 使い方: 計画から変更した点、変更理由、遭遇したエッジケース、選んだ対応を残す

### [pitch](skills/documentation/pitch/SKILL.md)

- 目的: 実装後に、背景・変更内容・判断理由・レビュー観点を説明資料へまとめる
- 使うタイミング: レビュー前や他者へ変更内容を説明する前
- 使い方: 計画、実装ノート、実装結果をまとめ、確認してほしい点と注意点を明示する

### [explanation-design](skills/documentation/explanation-design/SKILL.md)

- 目的: 情報をそのまま文章化・HTML化せず、読者が理解に到達する説明順序と前提を設計する
- 使うタイミング: 記事、解説、HTMLページ、技術説明、比較説明などを作る前
- 使い方: 伝達設計を先に作り、読者前提・必要知識・情報の依存関係・抽象と具体の配置を確認してから表現へ変換する

### [quiz](skills/discovery/quiz/SKILL.md)

- 目的: AI生成物や変更内容について、理解漏れを確認するクイズを作る
- 使うタイミング: 実装後、レビュー前、大きな変更を理解できているか確認したいとき
- 使い方: 判断理由、影響範囲、エッジケースを問う問題と解答を作る

### [grill-issue](skills/planning/grill-issue/SKILL.md)

- 目的: Issue の内容を読み取り、実装計画を詰める
- 使うタイミング: 着手前に要件や設計判断を整理したいとき
- 使い方: `gh issue view <issue-number>` で Issue を確認し、必要な論点を一問ずつ詰める

### [commit](skills/development/commit/SKILL.md)

- 目的: 差分を整理して適切な粒度でコミットする
- 使うタイミング: 実装後に変更をコミットしたいとき
- 使い方: 差分を見て関連ファイルごとにステージングし、日本語メッセージで順次コミットする

### [pr](skills/development/pr/SKILL.md)

- 目的: コミット内容を元に Pull Request を作成する
- 使うタイミング: 作業ブランチの内容を GitHub に提案したいとき
- 使い方: 作業内容を確認し、テンプレートに沿って日本語で Pull Request を作成する

### [skill-authoring](skills/authoring/skill-authoring/SKILL.md)

- 目的: Skill の追加・更新・配置判定を行い、関連する README.md も整備する
- 使うタイミング: 新しい Skill を追加したいとき、既存 Skill の内容や配置を見直したいとき
- 使い方: 明示された許可範囲だけを扱い、配置・移動では Skill 本体を変更せず README カタログを同期する。内容の作成・更新を依頼された場合だけ `SKILL.md` と同梱ファイルを変更する。配布を扱う場合はSkill単体とpluginの単位を判定する

### [my-skill-creator](skills/authoring/my-skill-creator/SKILL.md)

- 目的: 新規 Skill の作成・既存 Skill の改善を、評価と反復を通じて支援する
- 使うタイミング: Skill をゼロから設計したい、既存 Skill の品質やトリガー精度を検証・改善したいとき
- 使い方: 構成・実物モック・決定論設計・生成物を段階的に合意し、専用ワークスペースで候補版を反復する。評価と独立検証後に再承認を得て正本へ反映する

### [self-review-html](skills/development/self-review-html/SKILL.md)

- 目的: Git 差分と指定ルールによる行単位の評価・ルール不足候補を、承認や指摘が可能な HTML レビュー画面として提示する
- 使うタイミング: PR 前のセルフレビュー、未コミット変更の確認、対象パスを限定したルール適合確認を行いたいとき
- 使い方: 比較対象、任意の対象パス、評価ルールを指定し、生成された HTML で評価を承認または指摘する

### [llm-eval](skills/development/llm-eval/SKILL.md)

- 目的: LLMアプリ・AIエージェントの評価ケース、採点方法、再現可能な実行基盤を構築・監査する
- 使うタイミング: モデルやプロンプトの変更前に品質を測りたいとき、既存の評価が妥当か確認したいとき
- 使い方: 対象機能と品質基準を整理し、ケースと採点方法をHTMLで合意してから評価を実行する。結果と点数推移をHTMLで確認し、ベースラインを残す

### [skill-refiner](skills/authoring/skill-refiner/SKILL.md)

- 目的: 指定した1つのSkillを題材ごとに独立実行し、人間の指摘から評価基準と改善案を作る
- 使うタイミング: 既存Skillの成果物を見ながら検証・評価・改善したいとき
- 使い方: Skill名と題材を渡し、HTMLで指摘・承認・結果を確認する。再実行と再評価には新規担当を使う

### [to-issues](skills/planning/to-issues/SKILL.md)

- 目的: 計画や PRD を、独立して着手できる垂直スライスのイシューへ分割する
- 使うタイミング: 実装計画をイシュー化したいとき、作業を AFK/HITL 単位で分解したいとき
- 使い方: 会話や既存イシューを読み、トレーサー弾の分割案をユーザー確認後に依存順でイシュー公開する
