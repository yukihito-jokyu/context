# フローチャートとERの統合図

`workflow-er` は左に処理フローチャート、右にER図を置く。処理ノードまたはA番号をクリック・Enter・Spaceで選ぶと、そのSQLの対象列と関係を右で強調する。フローチャートの分岐・合流・呼出し元からの経路を保持する。ERが不要なら通常のworkflowを使う。

`schemas/workflow-er.schema.json` と `examples/task-operations.workflow-er.json` を読む。`workflow` に通常のworkflow（新規ではschema_version:2）、`er` に通常のerを入れる。`accesses` の `node` はworkflow.nodesのID。1ノードにつき1アクセスとし、SQLが複数あれば処理ノードを分ける。取得・条件・結合・更新・DELETE、`source`、`evidence` の意味と根拠検証は [sequence-er.md](sequence-er.md) と共通。SQLとDDLの根拠を必須とし、推測の列やFKを追加しない。

```bash
node bin/archify.mjs validate workflow-er input.json --repo-root /path/to/repo --quality showcase --json
node bin/archify.mjs deliver workflow-er input.json output.html --repo-root /path/to/repo --quality showcase --json
```

`layout.workflowWidth` は左領域の幅、`erWidth` は右領域の幅。`height`、`footerY`、`controlsY`、必要な場合だけERの `routes` を調整する。左の既存workflow SVGを拡縮せず置くので、コンパイル結果のviewBox以上の幅と高さを確保する。ノード内のAチップは右下に置くため、tagや長いラベルと重ならない余白を確保する。`workflowHeading`、`caption`、`context`、`scope`、`default` で説明と初期選択を指定する。Viewerの探索IDはノード `flow-<id>`、テーブル `er-<id>`。meta.views.focusにもこのIDを使う。

同梱例は架空の検証用SQL。TEJUNなど実プロジェクトの仕様として流用しない。validate/deliver後にvisual-check、ノード選択、種類切替、キーボード操作、SVG書き出しを確認する。
