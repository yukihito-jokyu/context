# Archify JSON IR schema

各型付きレンダラーは、レイアウト処理を始める前に、このフォルダー内のいずれかのschemaで検証されたJSON中間表現（IR）を受け取ります。

## ファイル

| schema | 対象 | 構造配列 |
|--------|---------|-------------------|
| `workflow.schema.json` | `diagram_type: "workflow"` | `lanes`, `phases`, `groups`, `mainPath`, `nodes`, `edges` |
| `sequence.schema.json` | `diagram_type: "sequence"` | `participants`, `segments`, `messages`, `activations` |
| `dataflow.schema.json` | `diagram_type: "dataflow"` | `stages`, `nodes`, `flows` |
| `lifecycle.schema.json` | `diagram_type: "lifecycle"` | `lanes`, `states`, `transitions` |
| `architecture.schema.json` | `diagram_type: "architecture"` | `components`, `boundaries`, `connections` |
| `common.schema.json` | 共有 `$defs` のみ（最上位文書なし） | — |

各図schemaは、`schema_version`、`diagram_type`、`meta`（`title` を含む）、その構造配列を要求します。ただし `segments`、`activations`、`cards` は任意です。すべての階層で `additionalProperties: false` を設定するため、不明なフィールドは暗黙に無視されず拒否されます。

各 `meta` オブジェクトは、生成HTMLでオプトインのSVG／CSSモーションを有効にする `animation: "trace"` も受け入れます。既定の静的出力には省略するか `"none"` を設定します。`locale: "ja" | "en" | "zh-CN"` も受け入れます。このフィールドは、固定Viewer UI、レンダラー所有の既定凡例とアクセシビリティ文言、文書タイトル接尾辞、`<html lang>` 値を選択します。作成済み文字列を翻訳するものではありません。省略時は日本語になります。未対応のlocale値は推測や暗黙の書き換えを行わず、schema検証で失敗します。

`visual_preset` は、`classic`（安定した既定値）、`signal-flow`（発光感のあるモーション重視表示）、`blueprint`（高コントラストのエンジニアリングレビュー）、`editorial`（温かみのある出版形式の設計レビューと文書化）を受け入れます。プリセットが変更するのはViewerのスタイルだけで、セマンティックIDやジオメトリは変更しません。Sequenceの `meta` はさらに `column_fit` を受け入れます。既定の `fixed` は過去の108px列間隔と86px参加者ボックスを維持するため、viewBoxの幅に関係なく作成済み図を同じ座標へレンダリングします。`spread` は代わりにviewBoxから間隔とボックス幅を導出し、幅広いキャンバスの右側を空白にせず、列間距離とラベル領域へ変換します。どちらでもレーン順、ID、メッセージの意味は変わりません。

最大5つの引導 `views` も含められます。各viewは一意の `id`、読者向け `label`、既存セマンティックノードIDの空でない `focus` リスト、任意の短い `note` を持ちます。

### 凡例表示契約

各 `meta` オブジェクトは、そのレンダラーですでに選択されたschemaバージョンを変更せず、同じ任意の凡例形式を受け入れます。

```json
"legend": {
  "mode": "auto",
  "entries": {
    "security": { "label": "restricted data", "visible": true }
  }
}
```

`mode` は `auto`（既定）、`all`、`hidden` です。`auto` は型付きIRに存在する種別だけを含み、`all` はレンダラーの完全で安定したカタログを含み、`hidden` は凡例全体を除去してエントリ上書きより優先されます。明示的 `viewBox` を省略したArchitecture文書では、最終SVGレイアウトに使用するものと同じ、解決済み凡例の計測領域から自動viewBoxを決定します。全レンダラーにおいて、`meta.legend` を省略した旧文書は互換性を保つ暗黙の `auto` を使用します。解決済み凡例が作成済みの明示viewBoxに重ならずに収まらない場合、Archifyは以前は有効だったschema-v1文書を重大な失敗に変えず、凡例全体を省略します。作成者が `meta.legend`（明示的な `mode: "auto"` を含む）を追加するとレイアウトは意図的なものとなり、収まらないラベルや帯はパス接頭辞付き診断で失敗します。エントリには、空でなく長さ制限内の `label`、booleanの `visible`、またはその両方を設定できます。`visible: false` は解決済みエントリを除去し、`visible: true` は対応しているが未使用の種別を視覚凡例へ強制的に追加します。不明な種別とプロパティは厳格な検証で失敗します。

対応キーはレンダラーが所有します。

| レンダラー | `meta.legend.entries` のキー |
|---|---|
| Architecture | `frontend`, `backend`, `database`, `cloud`, `security`, `messagebus`, `external` |
| Workflow | `frontend`, `backend`, `security`, `messagebus`, `database`, `cloud`, `external` |
| Sequence | `emphasis`, `return`, `security`, `dashed`, `default` |
| Dataflow | `emphasis`, `security`, `dashed`, `database`, `default` |
| Lifecycle | `start`, `active`, `waiting`, `decision`, `success`, `failure`, `neutral`, `external` |

ラベルは表示専用です。安定種別の改名、ノード／関係の変更、Semantic Lensのエッジ事実の作成は行いません。SequenceメッセージとDataflowのフローバリアントエントリは視覚キーです。正確なコンパイル済みノード事実に裏付けられたコンポーネント／状態エントリは、対話的なSemantic Legendブリッジを受け取ります。実際の `nodes[].type: "database"` 事実が存在する場合のDataflow `database` も含まれます。

各関係コレクション（`connections`、`edges`、`messages`、`flows`、`transitions`）は、共有IDパターンを使う作成者管理の任意 `id` を受け入れます。レンダラーはソース順のランタイムキーを別に保持し、作成済みIDは配列の並べ替え後も維持される安定した `#relation=<id>` Viewerリンクを可能にします。IDなし文書も有効で、その関係ピンは現在のページ内に留まります。

各セマンティックノードコレクション（`components`、`nodes`、`participants`、`states`）は任意の `brand` も1つ受け入れます。`archify brands --json` が返す正規文字列、または `archify brands capture <url> --json` が返すダイジェスト固定済み `{ "url", "sha256" }` オブジェクトです。既知IDと既知ブランドドメインは同梱ベクターカタログを使用します。未知URLは作成前にその明示コマンドで取得する必要があり、renderとvalidateは固定されていないネットワーク取得を決して行いません。安全でない、利用不能、変更済み、未対応のコンテンツはブランド診断によって安全側に失敗します。`brand` の省略は以前の出力を維持します。

## schema_versionポリシー

Workflowはschemaバージョン1と2に対応します。バージョン1は固定レイアウト互換契約のままです。バージョン2は可読ワークフローコンパイラーを有効にし、`archify migrate workflow ... --to-schema 2` で明示的に生成できます。他の4つの図schemaは `schema_version` を `1` に固定します。

Workflowは任意の `semanticChecks` も受け入れます。`allowedRoots` と `allowedTerminals` は意図的なグラフの起点と終点の集合を閉じ、`requiredEdges` は正確な作成済み関係を要求し、`requiredPaths` は中間ノードを許可しながら有向到達可能性を要求します。コンパイラーはレイアウト前にこれらの事実を評価し、型付き `workflow/*` 診断を返します。このフィールドは追加的でジオメトリ中立です。省略すると既存のワークフロー動作を維持し、満たされた契約を含めてもSVGやレイアウトレシートのバイト列は変わりません。

現在検証に合格するファイルは、2.xリリース系列を通じて、宣言したバージョン内で検証とレンダリングに合格し続けなければなりません。追加的なViewer、アクセシビリティ、表示改善によって生成HTMLを強化できますが、作成済みIRを再解釈したり、以前は有効だったプロファイルなしのv1ファイルを新たな重大レイアウト失敗に変えたりしてはいけません。破壊的IR変更には新しいバージョンが必要ですが、追加的で後方互換性のあるフィールドには不要です。

## 共有定義（common.schema.json）

5つの図schemaは `common.schema.json#/$defs/...` を参照します。

- `id` — 要素識別子。パターン `^[a-zA-Z][a-zA-Z0-9_-]*$`
- `point` — 数値の `[x, y]` 組（`via` と `labelAt` で使用）
- `componentType` — `frontend`, `backend`, `database`, `cloud`, `security`, `messagebus`, `external`
- `locale` — 範囲を限定したレンダラーロケール。`ja`、`en`、`zh-CN`
- `brandMark` — 任意の組み込みブランドIDまたは明示的HTTP(S)サイトURLを1つ
- `variant` — `default`, `emphasis`, `security`, `dashed`（sequenceメッセージはローカルに `return` を追加）
- `legendMode` と `legendEntry` — レンダラー所有の各キーマップで使用する共有の厳格なモードとラベル／表示状態上書き形式
- `guidedViews` — `meta.views` が受け入れる範囲限定の読み取り専用読者経路
- `cards` — SVG下にレンダリングされる要約カードブロック

Lifecycle状態の `type` はモード固有（`start`／`active`／`waiting`／...）で、`lifecycle.schema.json` に留まります。

## ランタイム検証

開発時には `scripts/generate-validators.mjs` が、ajvのdraft 2020-12スタンドアロンジェネレーターを `strict: true`、`allErrors: true` で使用し、5つのschemaをすべてコンパイルします。生成された `renderers/shared/generated-validators.mjs` はコミットされSkillに同梱されるため、ランタイム検証にnpmやネットワーク依存関係はありません。`renderers/shared/validator.mjs` は、レンダラー自身のレイアウト検査前に、一致するスタンドアロンバリデーターを適用します。続いて共有ローダーが、JSON Schemaでは簡潔に表現できないコレクション横断の事実を検査します。view IDの重複、focus IDの重複、図のセマンティックコレクションに存在しないfocus ID、モードの関係コレクション内で重複する作成済み関係IDです。

Architectureは、オプトインでリビジョン固定済みのリポジトリ証拠にも対応します。`meta.repository` は公開GitHub URLと完全なcommit SHAを指定し、コンポーネントはリポジトリ相対POSIXパス、任意の行範囲、任意のラベルを持つ1～3個の `sources` を保持できます。形式をschema検査した後、レンダラーは `--repo-root` を要求します。ローカルGit originが一致し、Gitがcommit、blob、要求行を証明しなければなりません。検証済み証拠はSemantic PassportとNode Finder向けに正規SVG外へ埋め込まれます。通常文書と視覚エクスポートはリポジトリ証拠を保持しません。

## 視覚品質とエンジニアリング上の真実

`meta.quality_profile` と `meta.engineering_profile` は異なる問いに答えます。`quality_profile` は5モードすべてで利用でき、Archifyが構成をどの程度厳格に判定するかを制御します。`engineering_profile` はArchitecture専用の任意セマンティック契約です。省略すると通常のv1動作を維持します。

最初のエンジニアリングプロファイルは `deployment-ownership` です。ユーザーが安全側に失敗するデプロイレビューを求め、ソースの事実が判明している場合にのみ有効にします。外部以外の各コンポーネントが `tag` で所有者を指定し、正確に1つの `region` に属する必要があります。文書には `region` と `security-group` の両境界が必要です。各 `database` は `security-group` 内にあり、各security groupには1つの共有regionからのメンバーだけを含め、regionまたはsecurity-group所属が変わる各connectionは実際の横断メカニズムを `label` で指定しなければなりません。

このプロファイルが検証するのは作成済みIRだけです。インフラストラクチャを発見したり、所有者を推測したり、図が稼働環境と一致することを証明したりはしません。事実が不明な場合は、捏造せずプロファイルを未設定にするか、その事実を取得します。

`npm test` はジェネレーターをcheckモードで実行し、コミット済みバリデーターがschemaとずれている場合に失敗します。

## エラー形式

schema違反は0以外で終了します。各ajvエラーは、インスタンスパスに最も近い包含要素の `id` または `label` を注記し、その後にメッセージとパラメーターを続け、1行ずつ報告されます。

```text
workflow schema validation failed:
  /nodes/3 (id/label: "router") must NOT have additional properties {"additionalProperty":"colour"}
```

schemaは形式エラー（型、enum、範囲、不明フィールド）を検出します。重なりやラベル衝突などのジオメトリ問題はレンダラーの役割です。
