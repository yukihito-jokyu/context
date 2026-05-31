# cli

このディレクトリには、Go 製の `context` CLI 実装があります。

現時点では `context deploy` の初期実装があります。現在できることは以下です。

- `context deploy <repo-name>` で `projects/<repo-name>` を解決する
- `context deploy` で対話的に project を選択する
- `CONTEXT_REPO`、実行ファイル相対、カレントディレクトリ親探索で context repository ルートを解決する
- deploy 開始前のセッション情報を表示する

まだ未実装の主な範囲は以下です。

- 実際の deploy 処理
- shared skills の選択と適用
- `deploy` 以外のコマンド
