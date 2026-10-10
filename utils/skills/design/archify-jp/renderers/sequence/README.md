# シーケンスレンダラー

`diagram_type: "sequence"` のJSONファイルを標準Archify HTMLテンプレートへレンダリングします。

```bash
node archify/renderers/sequence/render-sequence.mjs input.sequence.json output.html
```

レンダラーは、同梱のスタンドアロンバリデーターを使用して、入力を `archify/schemas/sequence.schema.json` に照らして検証します。依存関係をインストールする必要はありません。

`output.html` を省略すると、レンダラーはJSONファイルの `meta.output` を使用します。それもなければ、現在の作業ディレクトリの `sequence.html` へフォールバックします。

## 入力

シーケンスJSONファイルには、次の値を設定する必要があります。

```json
{
  "schema_version": 1,
  "diagram_type": "sequence",
  "meta": {
    "title": "Cache Miss Request Sequence",
    "viewBox": [920, 760]
  },
  "participants": [],
  "segments": [],
  "messages": [],
  "activations": [],
  "cards": []
}
```

タイムラインはviewBoxの高さに合わせて拡縮します。高い `meta.viewBox` はメッセージ領域を増やし、低いものは切り抜かずに可読領域を縮めます。完全な実例は `archify/examples/cache-miss-request.sequence.json` にあります。

schemaは次の場所にあります。

```text
archify/schemas/sequence.schema.json
```

## 凡例

既定の視覚凡例は `messages[].variant` から種別を導出します（`variant` の省略は `default` を意味します）。`meta.legend.entries` で対応するキーは、安定順で `emphasis`、`return`、`security`、`dashed`、`default` です。これらは視覚的なメッセージキーであり、Semantic Lens操作ではありません。ラベル／表示状態の上書きによってエッジの事実が作られることはありません。

## レイアウト上限

| 定数 | 値 |
|----------|-------|
| viewBox | 既定 `[920, 760]`、schema最小値 `[480, 480]` |
| 参加者ボックス | `fixed`（既定）: y 72で86×54。`spread`: viewBox相対で86pxから最大190pxの幅 |
| 参加者列 | `fixed`: 中心 x = 62 + index×108。`spread`: 利用可能なviewBox幅全体へ列を分配 |
| 参加者数 | 最終ボックスの終端が width − 40以下でなければならず、収まらないレイアウトは安全側に失敗 |
| ライフライン | y 142からheight − 65まで。帯の高さは120px以上 |
| メッセージの `y` 範囲 | `[160, height − 83]` |
| メッセージ間隔 | 水平領域を共有するメッセージ間で垂直28px以上 |
| 矢印幅 | 2参加者間の水平距離60px以上 |
| セグメント | `[72, lifeline bottom + 20]` 内にある `to > from` のyピクセル範囲 |
| 凡例行 | y = height − 54 |

`segments[].from/to` と `activations[].from/to` は参加者IDではなく、yピクセル座標です。activationも `to > from` である必要があります。

### 列の適合

シーケンス図では、既存文書の過去の座標を維持するため、既定で `meta.column_fit: "fixed"` を使用します。幅広いviewBoxで右側に空白が残る場合、または意味のある参加者ラベルが固定86pxボックスに収まらない場合は、`"spread"` を使用します。Spreadは、参加者順、ライフライン、メッセージの意味を維持したまま、viewBoxからボックス幅と列間隔を導出します。

## 設計規則

- 読者が追うべきストーリー順に、参加者を上部へ並べます。
- 時間は下方向へ進みます。
- `emphasis` は主要リクエスト経路に使用します。
- `security` は認証、同意、権限、ポリシー呼び出しに使用します。
- `return` は控えめな応答メッセージに使用します。
- `dashed` は非同期トレース、イベント、ログ、非ブロッキング処理に使用します。
- セグメントは淡い背景ガイドとして使い、セグメントラベルを短く保ちます。
- ラベルは簡潔にします。ただし、意味のある参加者ラベルを固定ボックスに収めるためだけに短縮する前に、`meta.column_fit: "spread"` を試してください。

schema違反は、要素のidまたはlabelを注記したパス接頭辞付きメッセージを出力して0以外で終了します。レンダラーはさらに、参加者の欠落、参加者IDの重複、ボックスより幅広い参加者ラベル、不明なメッセージ端点、可読タイムライン外のメッセージ、水平に重なるメッセージ間の狭すぎる垂直間隔、無効なsegmentまたはactivation範囲、viewBoxを超える参加者など、検出可能なレイアウト問題でも失敗します。共有Clean Flow契約では参加者ヘッダーをセマンティックボックスとして扱う一方、メッセージが途中のライフライン、activationバー、segment枠を横切ることを明示的に許可します。テキスト幅はCJKを考慮して推定し、全角グリフを2単位として数えます。

洗練された配信には、`meta.quality_profile` を `showcase` に設定します。その場合、無関係なメッセージの正規X交差は `composition/proper-crossing` で失敗します。既定の `standard` では成果物レシートの警告に留めます。メッセージは引き続き途中のライフラインを横切れます。同一直線上の経路は正規X規則の対象外ですが、別のゲートが、無関係なメッセージが8px以上重なると `standard` では警告し、`showcase` では失敗します。共有セマンティック端点、点での接触、それより短い重なりは有効なままです。Showcaseはさらに、8px未満の経路区間と16px未満の内部折れ区間を拒否します。通常の8～15pxの端点スタブは有効なままです。
