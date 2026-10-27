# 要件からユースケース図を作る

このスキルは、外部の役割であるアクターと、その役割がシステムで達成する目的を描く。操作の時系列はシーケンス図、処理の分岐はフローチャートへ分ける（IN-01）。入力と本資料、見本だけから開始し、既存実装を表す依頼では対象機能の根拠を読む（IN-02）。

## 入力を整理する

対象システム、アクター、達成する目的、関係の根拠を抜き出す。利用者が「会員は注文できる」と指定しただけなら、認証・支払いを追加しない。希望時にだけ追加する処理であることが分かる場合にextendを使う。毎回実行する再利用処理であることが分かる場合にincludeを使う。継承する役割・機能が明示されている場合に汎化を使う（STEP-02、OUT-03）。

新規の図では、入力に登場した順にアクターを`A01`、ユースケースを`U01`、境界を`S01`から番号付けする。図IDが利用者から指定されていない場合は、入力の機能範囲の順に`d01`、`d02`から振る。利用者が指定した図IDは小文字kebab-caseにする。図IDの昇順がカタログの順序になる。複数の図でMermaidの要素IDを再利用してよい。図の中ではIDと宣言を重複させない（OUT-04）。

## Mermaidの書き方

公式の[専用構文](https://mermaid.ai/open-source/syntax/usecase.html)を使う。検証対象はMermaid 12完全版である。次は独自の小さな例である。

```mermaid
usecase-beta
direction LR
actor A01("会員")
systemBoundary S01["注文システム"]
  U01("注文する")
  U02("支払う")
  U03("クーポンを適用する")
end
A01 -- U01
U01 ..> : include U02
U03 ..> : extend U01
```

- 通常の関連は`A01 -- U01`とする。
- includeは包含する機能から必須の再利用機能へ向ける。
- extendは条件付きで追加する機能から基本の機能へ向ける。
- 汎化は特殊な役割・機能から一般の役割・機能へ`--|>`を向ける。
- 関係は境界の外に書く。アクターは境界の外、全ユースケースは宣言した境界の中に置く。

全要素と境界を明示IDで1回ずつ宣言する。Mermaidが許容する暗黙ユースケースと宣言の反復は、このスキルの検査ではエラーにする。境界の入れ子、異種要素間の汎化、不正なinclude・extendはMermaidの構文解析で拒否する。既存原本の本文は保持する。設定のfrontmatterとinitディレクティブがある原本は、削除を依頼するか、設定を除いた入力を受け取ってから変換する（OUT-02、OUT-08）。

## JSONにまとめて変換する

`assets/examples/request.json`を構造の見本にする。見本の題材を利用者の要件として流用しない。入力JSONは`title`、`description`、`diagrams`を持つ。各図は`id`、`title`、`summary`と、Mermaid本文を入れる`mermaid`、または既存原本のパスを入れる`source`のどちらか一方を持つ。`source`の相対パスはJSONファイルのディレクトリを基準にする。

```json
{"title":"蔵書検索","description":"会員が蔵書を検索する。","diagrams":[{"id":"d01","title":"蔵書を検索する","summary":"会員が蔵書を検索する。","source":"search.mmd"}]}
```

入力JSONと作業中の原本は`.skill-runs/generate-usecase-diagram/source/`に置く。公開する出力の`catalog.json`にはMermaid本文を重ねて持たせず、原本と画像のパス、原本から解析したアクターと境界を記録する（STEP-03）。

```sh
python3 <skill>/scripts/catalog.py preflight
python3 <skill>/scripts/catalog.py build --request .skill-runs/generate-usecase-diagram/source/request.json --name catalog
python3 <skill>/scripts/catalog.py check --catalog artifacts/usecase/catalog/catalog.json
```

既存Mermaidを完全版として利用できるプロジェクトではパッケージを導入しない。自動探索で見つからないときは`--mermaid /path/to/node_modules/mermaid/dist/mermaid.min.js`または`USECASE_MERMAID_JS`を指定する。Chromeも`--browser`または`USECASE_CHROME`で指定できる。CDP pipeはPOSIX用であり、Windowsは未対応である。Chromeの起動がsandboxで拒否された場合は成功扱いせず、その実行権限の範囲で再実行する（STEP-04）。

1図はアクターとユースケースの合計40個まで、1カタログは24図までである。画像の寸法と面積にも上限がある。上限を超えるときは機能範囲で分割し、入力の機能を落とさない（OUT-05）。

## 更新と失敗

更新を依頼されたときだけ`build`へ`--replace`を付ける。新規依頼で出力が存在する場合は、別のカタログ名を使うか更新の意図を確認する。出力が完全に一致する場合は、既存一式を検査して再利用する。シンボリックリンクや未管理ファイルのある出力先を置換しない（OUT-06）。

`build`は全図の変換と検査が成功した後に出力先を置換する。入力検査・描画・検査に失敗したら指摘を修正して再実行する。失敗した図の省略や以前の画像への差し替えで成功扱いしない。描画できない状況が継続する場合は、理由を指定して`run.py abort`を実行する（STEP-05）。

## 検査と目視

PNGはバイナリなので、共通ランタイムのUTF-8検査には直接渡さない。`catalog.py check`がPNGの署名、CRC、画素データ、原本との対応を検査する。`report.sections`もfinish時に毎回`catalog.py report`を実行するため、内容が変わらない出力の再利用時とPNGだけが変わった場合にも一式を検査する。HTMLは同じメタデータと原本からの生成結果との完全一致を確かめる（STEP-06、OUT-07）。

ブラウザで`index.html`を開き、PNGの日本語、ラベルと線の重なり、一覧・検索・拡大・閉じる・原本表示・取得リンクを確認する。目視前は`visual_review.status`が`pending`である。実際に確認した後だけ、確認した内容を次のコマンドで記録する。利用者による最終確認を代わりに承認しない。

ブラウザの操作検査と実画面の保存には`catalog.py preview --catalog <出力>/catalog.json --out .skill-runs/generate-usecase-diagram/preview.png`を必ず実行する。画面とカタログのハッシュは同じ場所の`preview.json`に保存される。reviewはこの記録が無い場合と一致しない場合に止まる。操作検査の成功だけで目視済みとはせず、保存した画像と各PNGを開いて確認する。

```sh
python3 <skill>/scripts/catalog.py review --catalog artifacts/usecase/catalog/catalog.json --notes "PNG全図の日本語と線、HTMLの一覧・検索・拡大・原本リンクを確認した"
```

このスキルの生成・検査で外部接続や検査のskipを使わない。`validation.json`のハッシュは出力の対応と変更を検出する値であり、利用者が内容に合意した証拠ではない（OUT-08）。

カタログ名を依頼から推測しない。指定が無い場合と「お任せ」は`catalog`とし、startにnameを渡さない。確認待ちが無い実行でもnotes.mdに`- なし`を保存し、確認記録の置き場を揃える。最終返答はfinishの本文をそのまま使い、短く書き換えない。
