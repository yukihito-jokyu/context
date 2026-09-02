# データフローレンダラー

`diagram_type: "dataflow"` のJSONファイルを標準Archify HTMLテンプレートへレンダリングします。

```bash
node archify/renderers/dataflow/render-dataflow.mjs input.dataflow.json output.html
```

レンダラーは、同梱のスタンドアロンバリデーターを使用して、入力を `archify/schemas/dataflow.schema.json` に照らして検証します。依存関係をインストールする必要はありません。

`output.html` を省略すると、レンダラーはJSONファイルの `meta.output` を使用します。それもなければ、現在の作業ディレクトリの `dataflow.html` へフォールバックします。

## 入力

データフローJSONファイルには、次の値を設定する必要があります。

```json
{
  "schema_version": 1,
  "diagram_type": "dataflow",
  "meta": {
    "title": "Product Analytics Data Flow",
    "viewBox": [940, 720]
  },
  "stages": [],
  "nodes": [],
  "flows": [],
  "cards": []
}
```

完全な実例は `archify/examples/product-analytics.dataflow.json` にあります。

schemaは次の場所にあります。

```text
archify/schemas/dataflow.schema.json
```

## 凡例

既定の視覚凡例は `flows[].variant` から種別を導出し（`variant` の省略は `default` を意味します）、databaseノードが存在する場合にのみ `database` を追加します。`meta.legend.entries` で対応するキーは、安定順で `emphasis`、`security`、`dashed`、`database`、`default` です。この範囲のArchifyにはコンパイル済みエッジ種別の事実がないため、フローバリアントは視覚表現専用のままです。存在する `database` エントリは異なります。正確な `nodes[].type: "database"` の事実から得られるため、通常のSemantic Legendの件数、アクセシブル名、キーボード操作を公開します。databaseノードなしで `database` を強制表示した場合は、視覚表現専用のままです。

## レイアウト上限

| 定数 | 値 |
|----------|-------|
| viewBox | 既定 `[940, 720]`、schema最小値 `[360, 360]` |
| ステージ（2～5） | 中心 x = 100 + stage×215、ステージ帯の幅168、ヘッダー y 46 |
| 行上端（`row` 0～4） | y = 128, 242, 356, 470, 584（`yOffset` を加算） |
| 既定ノード | 112×58 |
| ノード領域 | xは `[24, width − 24]` 内、yは `[104, height − 74]` 内 |
| ノード間隔 | 任意の2ノード間で10px以上（ステージと行をまたいで検査） |
| フロー長 | 端点間34px以上 |
| 凡例行 | y = height − 36 |

フローの経路プリセットは、`straight`、`vertical-channel`、`bottom-channel`、`top-channel`、明示的な `via` 点、または既定の `auto`（中点エルボー）です。

## 設計規則

- source、ingest、process、store、consumeといったデータライフサイクル境界にステージを使用します。
- ステージ索引と行索引でノードを配置します。一般的な場合に生SVGを手動配置しないでください。
- フローラベルでは、転送プリミティブではなくデータ資産を命名します。例: `clickstream`、`identity map`、`normalized facts`、`feature vectors`。
- `classification` は短い機密性またはガバナンスの文脈に使用します。例: `PII touch`、`non-PII`、`approved only`、`batch`、`read-only`。
- `security` はPII、ポリシー、同意、アクセス制御、制限付き結合に使用します。
- `emphasis` は主要データ経路に、`dashed` は非同期またはバッチ派生に使用します。
- 狭いプレビューに収まるよう、ラベルを短く保ちます。

schema違反は、要素のidまたはlabelを注記したパス接頭辞付きメッセージを出力して0以外で終了します。レンダラーはさらに、ステージの欠落、ノードIDの重複、可読な図領域外のノード、ノードの重なり、ラベルとノードまたは他ラベルとの衝突、ノードより幅広いラベル、不明なフロー端点、フローラベルの欠落、短すぎて読めないフロー、無関係なノードを横切るフロー（Clean Flowの2pxクリアランス）、viewBoxを超えるステージなど、検出可能なレイアウト問題でも失敗します。ステージ枠は意図的な通過コンテナーのままです。テキスト幅はCJKを考慮して推定し、全角グリフを2単位として数えます。

洗練された配信には、`meta.quality_profile` を `showcase` に設定します。その場合、無関係な正規X交差は `composition/proper-crossing` で失敗します。既定の `standard` では成果物レシートの警告に留めます。同一直線上のステージ経路は正規X規則の対象外ですが、別のゲートが、無関係なフローが8px以上重なると `standard` では警告し、`showcase` では失敗します。共有セマンティック端点、点での接触、それより短い重なりは有効なままです。Showcaseはさらに、8px未満の経路区間と16px未満の内部折れ区間を拒否します。通常の8～15pxの端点スタブは有効なままです。
