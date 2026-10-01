# シーケンスとERの統合図

DB呼び出しがどのテーブル・カラムを取得、条件、結合・参照、更新、削除に使うか説明するときに選ぶ。ERが関係しなければ通常のsequenceだけを描く。空のERや仮のテーブルは追加しない。

既存シーケンスの参加者、メソッド名、順序、戻り値、TX境界を保持し、既存sequence形式を `sequence` に入れる。実DDL・マイグレーションから作った既存er形式を `er` に入れる。SQLから `accesses` を作り、各 `message` をsequenceのメッセージIDに対応づける。A番号は既存のラベルを置換せず、追加の選択チップとして表示する。

各アクセスには `id`, `message`, `title`, `operation` (SELECT/UPDATE/DELETE)、`read`, `filter`, `join`, `write` (entity.columnの配列)、`delete` (entityの配列)、`relations`、`source`を指定する。SELECTの取得列はread、WHERE等の条件列はfilter、JOIN／サブクエリの参照列はjoin、UPDATEのSET対象列はwriteとする。DELETEは行の削除でありwriteへ入れない。関係は `id` (er.relationshipsのID)、`kind` (inner/left/subquery)で指定する。実FK制約が確認できる場合だけerのforeign_keyを設定する。SQL上の参照関係とDB制約を混同しない。

`source` はリポジトリ相対 `path`、1始まり `line`、その行から始まる完全一致の `quote`、任意の `sql`。各テーブルのDDLを `evidence` に同じ形式と `entity` で記す。相対パス解決には明示的に `--repo-root` を渡す。SQLやDDLの意味、マイグレーションの適用順、アクセス対応の正しさはAIがコードを調査して判断する。スクリプトはID・列・関係・操作区分と引用の一致を検証し、任意SQLを解釈しない。

```bash
node bin/archify.mjs validate sequence-er input.json --repo-root /path/to/repo --quality showcase --json
node bin/archify.mjs deliver sequence-er input.json output.html --repo-root /path/to/repo --quality showcase --json
node scripts/render-sequence-er-bundle.mjs --input views.json --repo-root /path/to/repo --out-dir /path/to/new-output
```

最初の小規模例は `examples/join-update-delete.sequence-er.json` を使い、根拠ルートはスキルディレクトリとする。複数画面の入力は `{schema_version:1,title,views:[{slug,title,sequence,er,accesses,evidence,...}]}`。各ビューは1入力→1HTMLのdeliverを通す。出力先が存在する場合は拒否し、失敗時は途中出力を除去する。単体deliverは既存の正常成果物を保持する。

レイアウトは `sequenceWidth`, `erWidth`, `height`, `footerY`, `controlsY`、必要な場合だけ `routes` (ER関係ID→SVGパス)を指定する。既定値は1100/780/920/795/850。ビューが収まることをブラウザーで確認する。`sequenceHeading`, `caption`, `context`, `scope`, `default`で説明や初期選択を指定する。`navigation`は安全な相対HTML名とlabel/currentを持つリンク配列。探索IDは参加者 `seq-<id>`、テーブル `er-<id>`に分ける。統合図のmeta.viewsのfocusにもこのIDを使う。ERなしの委譲では通常sequenceと同じ元の参加者IDを使う。

右のER領域には取得、条件、結合・参照、更新、DELETEの表示切替を置く。ボタンを押すとその種類だけ表示し、同じボタンでOFF、「すべて」で全表示へ戻す。結合・参照の線はテーブルホバーと同じ流れる線で示す。アニメーション停止・動きを減らす設定を尊重する。表の重複色は列端の色帯でも示す。JOINは実線、サブクエリ参照は点線で示す。

ERを省略したsequence-er入力は通常sequenceレンダラーへ委譲する。accessesを伴うERなし入力は拒否する。内容・密度・配置は入力に依存するため、validate/deliver後にvisual-checkと実操作、SVG書き出しを確認する。同一入力の2回一致は実行ケースの再現性であり、任意密度での配置保証ではない。
