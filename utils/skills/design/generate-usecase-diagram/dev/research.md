# Mermaidユースケース構文の調査

## Mermaid 12.1.0（専用構文）

- 確認方法：`node_modules/mermaid/package.json` の version を取得して 12.1.0 を確認（2026-10-27）。公式の [Use case diagrams](https://mermaid.ai/open-source/syntax/usecase.html) と [原文](https://raw.githubusercontent.com/mermaid-js/mermaid/develop/packages/mermaid/src/docs/syntax/usecase.md) を参照し、以下の入力をローカルの `mermaid.parse()` と `mermaid.mermaidAPI.getDiagramFromText()` で実行した。
- 確認の状態：確認済み
- 分かったこと：専用ヘッダーは `usecase-beta`。関連は `A -- U`、包含は `U ..> : include V`、拡張は `V ..> : extend U`、汎化は `Special --|> General`。境界内は宣言のみで、関係は境界の外に書く。IDは図全体で共有される。
- 使った決定：OUT-02、OUT-04。

実証した入力（独自の日本語例）：

```mermaid
usecase-beta
direction LR
actor Customer("顧客")
actor Member("会員")
systemBoundary shop["注文システム"]
  Checkout("注文する")
  Payment("支払う")
  Coupon("割引を適用する")
end
Customer -- Checkout
Checkout ..> : include Payment
Coupon ..> : extend Checkout
Member --|> Customer
```

方向の意味：包含する側から含まれる側、拡張する側から基本のユースケース、特殊化された要素から一般の要素へ向く。include/extendの両端はユースケースに限る。汎化はactor同士、またはusecase同士に限る。通常の関連は既定を無向線にすると、操作の順序・データの流れを意図せず示すことを避けられる（この無向線の採用は本スキルの方針案）。

## Mermaid 12.1.0（構造検査API）

- 確認方法：公式配布物の `dist/diagrams/usecase/usecaseTypes.d.ts`、`usecaseAst.d.ts` を読み、ローカルNodeで下記APIと異常入力を実行（2026-10-27）。配布物の型定義と観測結果を根拠とする。
- 確認の状態：確認済み
- 分かったこと：最初に `parse()` を呼ばない `getDiagramFromText()` は、図の登録前だと UnknownDiagramErrorになる。`parse()` を先に呼ぶと、dbからactor/usecase/boundary/relationshipとソース位置付きASTを取得できる。構文・意味検証に独自のMermaid全体パーサーを作る必要はない。
- 使った決定：OUT-02、OUT-04。

```js
await mermaid.parse(source);
const diagram = await mermaid.mermaidAPI.getDiagramFromText(source);
const actors = [...diagram.db.getActors().values()];
const usecases = [...diagram.db.getUseCases().values()];
const boundaries = [...diagram.db.getSystemBoundaries().values()];
const relationships = diagram.db.getRelationships();
const ast = diagram.db.getAST();
```

ASTの `nodes[id].attrs.kind` は `actor` または `usecase`、所属は `attrs.parentId`。`groups[id].nodes` は境界内要素ID。関係は `edges[].attrs.relationshipType` と `source`/`target`。宣言の判定は `statements` を再帰走査し、`nodes[].defines === true` を数える。groupの中は `children` に入る。actor/getUseCasesのMapは重複をまとめるので、重複宣言を厳格に禁止するならASTの宣言数を使う。

| 実行した入力 | Mermaid 12.1.0の観測結果 | 作成スキルで追加する検査案 |
| --- | --- | --- |
| actor Aとusecase A | 異種ID衝突で失敗 | Mermaidの失敗をそのままエラーにする |
| 同じactor IDに異なるラベル | conflicting labelsで失敗 | 同上 |
| 同じID・同じラベルの宣言を2回 | 成功。Map上は1要素 | ASTのdefines宣言を数え、2回目をエラーにする |
| A -- U、Aのactor宣言なし | 成功。AもUも暗黙usecase | 全端点の明示宣言と、actorが1つ以上あることを契約にする |
| actor A、A -- U、Uの宣言なし | 成功。Uが暗黙usecase | Uの明示宣言を要求する |
| 関係より後でactor Aを宣言 | 成功。Aはactorとして解決 | 元入力の順序を勝手に変更する必要はない |
| 1つのusecaseが2境界へ所属 | more than one system boundaryで失敗 | Mermaidの失敗をエラーにする |
| actorからusecaseへinclude | use-case endpoints必須で失敗 | 同上 |
| actorからusecaseへ汎化 | actor-to-actor/use-case-to-use-case必須で失敗 | 同上 |
| 境界の入れ子 | 構文エラー | 同上 |
| 境界内に関係を書く | 構文エラー | 同上 |
| `U ..> V : include` | 構文エラー | 正式な `U ..> : include V` を案内する |
| 異なるusecase IDに同じラベル | 成功 | 別機能かのレビュー対象。ラベルだけを根拠に自動統合しない |

## 採用する限定構文の提案

- 新規生成は `usecase-beta`、`direction LR`、明示ID＋日本語の引用ラベル、トップレベルactor、1階層の明示ID付き `systemBoundary`、楕円usecase、4種類の関係に絞る。`A_` / `U_` / `S_` のID接頭辞は衝突を避ける任意の命名規則で、Mermaidの必須要件ではない。
- actorは対象システムの外、対象システムの機能であるusecaseはその境界内、とする。Mermaid自体はactorの境界内配置とusecaseの境界外配置を許すため、これは生成スキルの追加契約にする。
- 既存Mermaidは、明示宣言・境界・端点の検査後に原本を保持する。スタイルやMarkdownラベル等を受け付けない限定実装なら、未対応構文として説明して止める。無視して要素を落とさない。全Mermaid構文を正規表現で部分抽出して検査済みと扱わない。
- `A --> U` はMermaid上の通常関連。線のラベルにinclude/extendという語があるだけでは、UMLの包含・拡張にならない。
- 日本語は直接ラベルに置ける。引用符・括弧などの予約文字はentityにして、一つの物理行に収める。通常文字列のバックスラッシュnは改行にならないので、生成側は長いラベルを自動でこの形式に置換しない。

## カタログのメタデータ案（プロジェクト向け設計判断）

`catalog.json` の最小項目は `schema_version`、`title`、`description`、`diagrams`。図ごとに `id`、`title`、`summary`、`source`（相対mmdパス）、`image`（相対PNGパス）、`actors`。actorsはMermaidの構造から算出して表示名・IDを持たせ、別の手編集用actor一覧にしない。system名も境界の表示名から取得する。HTMLの画像には図題名と要約を使ったaltを付け、PNGとmmdのリンクを同じカードに置く。画像寸法・原本と画像のハッシュ・変換環境/版・検査結果は `validation.json` に置く。

## 要件を補作しないルールの具体例

- 「会員は注文できる」から支払いや認証を勝手に追加しない。明示されているactor・機能だけで図を作る。
- 「クーポンを使える」だけでは、注文を拡張するextendと断定しない。条件付き追加処理であることが分かる入力を確認する。
- 「毎回注文時に決済を行う」のように必須の再利用処理が示されていれば、注文から決済へのincludeとして記録できる。
- 「管理者は会員と同じ操作を行える」という要件がない限り、管理者から会員への汎化を権限名だけで追加しない。
- 要件に存在しない関係は、見た目をつなぐ目的で追加しない。入力から判断できない主要actor/対象システム/必須関係は確認事項として扱う。

## Chrome pipeとPNG

- 確認方法：独立調査でPython標準ライブラリからChrome 156.0.8078.48を起動し、日本語usecase-betaをPNGに変換した（2026-10-27）。[CDP Page.captureScreenshot](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-captureScreenshot)、[PNG仕様](https://www.w3.org/TR/png-3/)。
- 確認の状態：確認済み
- 分かったこと：remote-debugging-pipeのfd3/4でCDPを操作できる。Mermaid12完全版はELKを内蔵する。sandboxでChromeが起動を拒否される場合は実行権限が必要であり、成功扱いしない。PNGはsignature・IHDR・IDAT・IEND・CRCと展開データを検査できる。
- 使った決定：OUT-02、STEP-04、STEP-06。

## Context Repositoryの配置と公開サンプル

- 確認方法：AGENTS.md、docs/skills/authoring/index.md、utils/skills/authoring/skill-authoring/references/docs-examples.mdを読んだ（2026-10-27）。
- 確認の状態：確認済み
- 決まり：AGENTS.mdの管理方針。「同じ情報を複数箇所で管理しないことを原則とします。」正本はutils/skills/design/に置き、公開サンプルを新規サブエージェントで実行する。
- 分かったこと：foundation本体は変更せず隔離プロジェクトで実行する。完成したディレクトリを正本へ配置する。
- 使った決定：IN-02、OUT-01。

## 収束テストのCodex実行権限

- 確認方法：codex exec --help（0.164.0、2026-10-27）と初回の独立実行。
- 確認の状態：確認済み
- 分かったこと：workspace-writeだけではChromeが終了コード-6で起動できない。--approve-for-meはworkspace-writeを選び、権限要求を自動レビューへ渡す。--sandboxとの併記はCLIが終了コード2で拒否するため、--approve-for-meだけを指定する。テスト用runnerにこの指定を加え、必要な描画コマンドだけの権限要求を許可する。sandboxを無効化する指定は使わない。
- 使った決定：STEP-04。

## 収束テストで確かめたこと（2026-10-27）

第1ラウンドで保存名の既定値と確認記録の作成有無に揺れを確認した。OUT-04とSTEP-06の手順を明確にし、catalog.py preview/reviewで画面とカタログのハッシュを照合する。実画面、画面改変、古いカタログ、記録欠落の4ケースはresults/preview-gate.jsonで確認した。自動report.mdは実行先の絶対パスが必ず変わるため、第2ラウンド以降の比較から除外する。利用者向け出力と入力・確認記録は除外しない。
