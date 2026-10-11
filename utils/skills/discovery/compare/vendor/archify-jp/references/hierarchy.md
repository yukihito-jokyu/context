# 階層化（ノードから詳細図への遷移）

全体図のノードをクリックして詳細図へ移り、詳細図から全体図やマップへ戻れる、図の集合を作るための契約です。すべての図の種類で使えます。

## 1. 仕組みの全体像

1. 各図の JSON で、ノードに `link`（遷移先）を書き、`meta.hierarchy` に親図とマップを書きます。
2. `deliver` すると、ノードに `data-node-link-*` 属性が付き、Viewer が遷移UIを表示します。
3. `archify hierarchy-sync` が、リンク構造から各図のパンくず（`meta.hierarchy.trail`）、同じ親を持つ図（`meta.hierarchy.siblings`）、遷移先の図の名前（`link.title`）と子図の数（`link.onward`）を計算して JSON に書き込みます。
4. `archify hierarchy-check` が、図をまたいだ整合性（遷移先・フォーカス先・親子関係・同期・HTML の同期）を検査します。
5. `archify map` が、ルートから辿れる全ての図を1枚の architecture 図（マップ図）として生成します。

## 2. ノードの `link`

`components` / `nodes` / `participants` / `states` / `classes` / `entities` の各ノードに書けます。sequence-er と workflow-er では、入れ子の sequence / workflow / er のノードに書きます。出力された SVG では、合成図の半分ごとにノード id へ接頭辞が付きます（sequence-er は `seq-<id>` と `er-<id>`、workflow-er は `flow-<id>` と `er-<id>`）。合成図へリンクするときの `focus` は、この接頭辞付きの id で書きます。

```json
{
  "id": "submit",
  "label": "注文を送る",
  "link": {
    "href": "../../orders/order-api/order-api.html",
    "focus": "create-order",
    "label": "注文作成"
  }
}
```

一式の見本は `examples/hierarchy/` にあります（全体図 `shop.architecture.json` と、関心ごと storefront／orders の詳細図3枚。囲みへのリンク、同じ階層の図、横断リンクと `focus`、参照元、`leaf_nodes` を含みます）。新しく階層を作るときは、この構成を参考にします。

| 項目 | 必須 | 意味 |
|---|---|---|
| `href` | ○ | この図の HTML から見た相対パス。`.html` で終わること。`http:` などのスキームや `/` 始まりは不可 |
| `focus` | | 遷移先で最初にフォーカスするノードID（`#focus=` になる）。詳細図どうしの横断リンクでは必須扱い（ないと `hierarchy/cross-link-unfocused`）。遷移先の図のどのノードとつながるかを、両方の図に表示するため |
| `view` | | 遷移先で開くガイドビューID（`#view=` になる） |
| `label` | | 詳細パネルのボタン文言「詳細図を開く: …」に使う。省略時はノードのラベル |
| `onward`・`title` | | 遷移先から先に進める図の数と、遷移先の図のタイトル。`hierarchy-sync`（`hierarchy-build` も実行）が書き込むので手で書かない |

### 囲みへのリンク（architecture）

複数のノードで1枚の詳細図になる場合は、ノードごとにリンクを重ねず、囲み（`boundaries`）に `id` と `link` を書きます。囲みに右下の遷移バッジが付き、中のノードはダブルクリック・詳細パネル・遷移先プレビューで囲みのリンクを使います。リンクを持つ囲みの中のノードには `link` を書けません（`hierarchy/group-link`）。`require_links` では、中のノードはリンク済みとして扱います。

```json
{ "kind": "region", "id": "storefront", "label": "storefront", "wraps": ["web", "cart"],
  "link": { "href": "storefront/checkout/checkout.html", "label": "チェックアウト画面" } }
```

`id` を持つ囲みは、接続（`connections`）の `from`／`to` にも書けます。「どの処理も同じ状態を使う」のような関心ごとどうしの関係を、ノードの総当たりではなく1本の線で描けます。

## 3. `meta.hierarchy`

```json
"hierarchy": {
  "parent": { "href": "../../overview.html", "label": "全体図" },
  "map": { "href": "../../overview.map.html", "label": "図のマップ" },
  "require_links": true,
  "leaf_nodes": [{ "id": "db", "reason": "マネージドDBで内部構造を描かない" }]
}
```

- `parent`: 図パネル左上に「上位: …」リンクを出します。ルート以外の図には必ず書きます（ないと警告）。
- `map`: 図パネル左上に「図のマップ」リンクを出します。
- `require_links`: `true` にすると、`link` も `leaf_nodes` もないノードがあれば描画自体を失敗させます（`hierarchy/missing-link`）。全体図に付けると、詳細図の作り忘れを防げます。
- `leaf_nodes`: 意図的に詳細図を持たないノードと、その理由です。
- `incoming`: 他の詳細図からこの図へ来る横断リンク（参照元）です。`hierarchy-sync` が書き込むので手で書きません。各要素は参照元の図（`href`・`label`）、リンク元のノード（`node`・`node_label`）、この図で着くノード（`focus`）です。親からの下向きリンクと、親へ戻るリンクは含みません。

## 4. Viewer での操作

- 図パネル上端の現在地タブ: 左から、マップと同じ形の小さな階層アイコン（今の段だけ色付き）、階層バッジ（L0／L1／L2…）、パンくず「全体図 › 関心ごと ›」、同じ親（全体図の直下なら同じ関心ごと）を持つ図のタブ、「マップで現在地を見る」。今の図のタブは下線と塗りで示し、他のタブを押すとその図へ移ります。関心ごとの段はマップ図の該当ノードへ、「マップで現在地を見る」は現在地を強調した状態のマップ図へ移ります。パネル上部の余白に収まるので、ページの高さは変わりません。図の上端に見出しがある図（合成図など）でタブと中身が重なるときは、図をタブの下から描き、その分だけ図の高さを縮めます。右上のツールバーの横に収まらない幅では、タブはツールバーの下へ下がり、それでも収まらなければパンくずとタブを2段に分けます。タブが並びきらないときは横にスクロールし、今の図のタブを常に見える位置に置きます。
- 「⌖ 位置」: 親の図の縮図を開きます。この図に対応するノードを濃く、同じ階層の図のノードを淡く塗り、タブと同じ番号を付けます。タブにマウスを乗せると縮図の該当ノードが光り、縮図の淡いノードや一覧から兄弟の図へ移れます。下の階層への吸い込みや兄弟への移動で到着したときは、数秒だけ自動で開きます（`#focus` 付きで着いたときは詳細パネルが開くので、自動では開きません）。縮図は `deliver` 時に親の図の出力済み HTML から読み取るため、親の図を先に `deliver` してください。親の図の配置が変わったのに子の図を出し直していない場合は `hierarchy/stale-html` になります。
- 遷移バッジの数字は、遷移先からさらに進める図の数です（`link.onward`）。
- リンクのあるノードにマウスを乗せる（またはフォーカスする）と、遷移先プレビューが出ます。遷移先の図の名前（`link.title`、`hierarchy-sync` が書き込みます）と関心ごと、この図との関係（下の階層／同じ関心ごと／別の関心ごと／上の階層）、開く場所（`link.label`）、親の図の縮図での「この図」と「遷移先」の位置（同じ親を持つ図へのリンクのとき。下の階層へのリンクでは縮図を出さず、名前と関係だけを示します）、バッジの数字の意味を示します。遷移先が同じ関心ごとの図なら、現在地タブの該当タブも光ります。
- 横断リンク（下の階層ではない図へのリンク）のプレビューには、さらに「遷移先の図」の縮図が出て、`focus` のノード（着くノード）を赤く示します。
- 他の詳細図からのリンクが着くノードには、左上角に参照元バッジ（入ってくる矢印と件数）が付きます。マウスを乗せると「参照元」として、参照元の図の縮図（リンク元のノードを青緑で表示）と「図の名前 › ノード名」を並べます。クリックすると詳細パネルに参照元へのリンクが並び、押すと参照元の図をリンク元のノードにフォーカスした状態で開きます。
- 遷移先・参照元の縮図は、`deliver` 時に相手の出力済み HTML から読み取ります。横断リンクでつながる図どうしは互いの縮図を埋め込むので、初めて作るときは両方を `deliver` した後にもう一度 `deliver` します（揃っていなければ `hierarchy/stale-html`）。下の階層への遷移では子の図を読まないので、親の図を先に出す順序は変わりません。

- 1回クリック: 従来どおりフォーカス。詳細パネルに「詳細図を開く: …」ボタンが出ます。
- ダブルクリック、または Shift+Enter: その場で遷移します。
- 遷移できるノードの右下角に矢印バッジが付きます。バッジは実行時だけの装飾で、SVG/PNG エクスポートには入りません。
- 下の階層へ移るとき（マップ図からの遷移、または遷移先がこの図のディレクトリより下にあるとき）は、選んだノードへ吸い込まれるように拡大してから遷移し、遷移先の図は中央から広がって現れます。同じ親を持つ図（兄弟の図）への遷移は、親の図の上を移動する演出になります。今の図が親の図の中の自分の枠まで引いて親の図全体が見え、親の図の線に沿って経路が光り（遷移先プレビューの経路と同じ）、遷移先の枠へ入ってから遷移先の図が現れます。上部に「親の図 の中を移動: この図 → 遷移先」と出ます。ノードのダブルクリック、詳細パネル、現在地タブ、「⌖ 位置」の縮図と一覧のどこから移っても同じで、途中でクリックかキーを押すとすぐ遷移します。親の図の縮図がない（親を `deliver` していない）場合や、兄弟でない図への横のリンク、上位への遷移（パンくず）は即座に切り替わります。OS の「視差効果を減らす」設定や Viewer の静止表示では演出しません。

## 5. 推奨ディレクトリ構成

```
<root>/
├── overview.architecture.json / overview.html   … ルート（require_links: true）
├── overview.map.architecture.json / overview.map.html … マップ図（hierarchy-build／archify map の出力）
└── <関心ごと>/<図名>/
    ├── <図名>.<type>.json                         … 詳細図（parent は "../../overview.html"、map は "../../overview.map.html"）
    └── <図名>.html
```

さらに下の階層（孫の図）は、親の詳細図のディレクトリの下に `<図名>/<孫の図名>/` として置きます（例: `records/patient-model/consent/consent.class.json`、`parent` は `"../patient-model.html"`、`map` は `"../../../overview.map.html"`）。孫の図の関心ごとは、全体図の直下の関心ごと（例では records）のままです。

`examples/hierarchy/` はこの構成です。関心ごとは、マップ図から見た `<関心ごと>/<図名>/` のディレクトリ名で決まります（マップの関心ごとの段、パンくず、同じ階層の図のタブに使われます）。

整合性チェックは、遷移先 HTML と同じディレクトリにある `<図名>.<type>.json`（または `meta.output` がその HTML を指す JSON）を仕様として読みます。

## 6. 整合性チェックとマップ

通常は次の1コマンドで、同期・出力・マップ・検査をまとめて行います（9節）。

```bash
node bin/archify.mjs hierarchy-build <root.json> --strict [--repo-root <dir>] [--scan <dir>] [--quality showcase|standard] [--no-preview-check] [--no-visual-check] [--json]
```

`--no-preview-check` はプレビュー検査、`--no-visual-check` は各図の visual-check（どちらも Chrome を使う）を省きます。結果は「スキップ」と報告されるので、省いた場合はその確認をしていないことを報告します。

個別に実行する場合のコマンドは次のとおりです。

```bash
# 図をまたいだ整合性を検査（--scan で、ルートから辿れない図も警告）
node bin/archify.mjs hierarchy-check <root.json> --scan <root-dir> --json

# マップ図を生成（チェックと同じ走査結果を使う）
node bin/archify.mjs map <root.json> <map.html> --scan <root-dir>
```

`hierarchy-check` は仕様と出力 HTML の対応を調べます。遷移先プレビューの見た目は、出力 HTML をブラウザで開いて検査します（Chrome/Chromium が必要）。

```bash
# リンクのあるノードすべてにライト／ダークでホバーし、カードと縮図の経路を検査
node scripts/check-link-preview.mjs <root-dir> [--json] [--theme light|dark|both]
```

検出するもの: ページのスクリプトの例外やビューアの停止（このときカードが1枚も出ないため、検査対象0件の合格として見逃さない）、現在地タブが右上のツールバーに隠れる・タブ同士で重なる・図の中身に重なる・今の図のタブが見えないか押し縮められて切れる（幅 1440・1024・800・600 と、スクロールした状態で確認）、カードが出ない・背景が透ける・ノードに重なる・パネルからはみ出す・現在地タブを隠す、遷移先の縮図で着くノードが光らない、参照元バッジがない・参照元の行数が合わない・参照元の縮図でリンク元のノードが光らない、ブラウザ標準のツールチップが残る、縮図の経路線の端が「この図」「遷移先」「経路上の囲みや中継ノード」のどれにも着いていない、経路が遷移先に届いていない、「N 本経由」と強調した線の本数が合わない。

マップ図は通常の architecture 図です。`<map>.architecture.json` を書き出し、`deliver --quality showcase` と同じ検証を通して `<map>.html` を確定するので、見た目・Viewer・エクスポートは他の図と同じです。

- 1つの図を1ノードにし、ノードの `link` からその図へ遷移します。
- ノードの色は図の種類を表し、凡例も図の種類名に置き換わります。リンク先が存在しない場合は「未作成」の外部ノードを点線で結びます。
- ルートを中央に置き、`<関心ごと>/<図名>/` の関心ごとディレクトリを境界として左右に振り分けます。線は上位図から詳細図への遷移だけを描き、横断リンクの本数はカードに出します。
- 整合性チェックの結果も下部カードに出ます。マップ図の仕様 JSON は `--scan` の孤立検出から除外されます。

`scripts/check-hierarchy.mjs` を直接実行しても同じです。終了コードは、0 がエラーなし、1 が整合性エラー（`--strict` では警告も含む）、2 が使い方の誤りです。

| コード | 重大度 | 内容 |
|---|---|---|
| `hierarchy/link-target-missing` | error | 遷移先 HTML がない。詳細図を作る |
| `hierarchy/link-target-spec-missing` | error | 遷移先 HTML はあるが、対応する仕様 JSON がない |
| `hierarchy/link-target-ambiguous` | error | 遷移先に対応する仕様 JSON が複数ある |
| `hierarchy/focus-missing` | error | `focus` のノードが遷移先にない |
| `hierarchy/view-missing` | error | `view` のガイドビューが遷移先にない |
| `hierarchy/missing-link` | error | `require_links` の図に、遷移先も末端理由もないノードがある |
| `hierarchy/leaf-unknown` | error | `leaf_nodes` に存在しないノードがある |
| `hierarchy/parent-mismatch` | error | `parent` に指定した図が、この図へリンクしていない |
| `hierarchy/map-missing` | error | `map` の HTML がない（`archify map` で生成する） |
| `hierarchy/html-missing` | error | 仕様に対応する HTML がない（`deliver` する） |
| `hierarchy/sync-stale` | error | パンくず／同じ階層の図／子図の数がリンク構造と一致しない（`hierarchy-sync` して `deliver`） |
| `hierarchy/stale-html` | error | HTML のリンクが仕様と一致しない（`deliver` し直す） |
| `hierarchy/group-link` | error | リンクを持つ囲みの中のノードにも `link` がある、または囲みの `id` が重複している |
| `hierarchy/parent-missing` | warning | ルート以外の図に `parent` がない |
| `hierarchy/split-destination` | warning | 同じ遷移先・同じ開く場所へのリンクが複数のノードに分かれている。囲みにまとめて囲みにリンクする |
| `hierarchy/cross-link-unbacked` | warning | 詳細図から別の詳細図へのリンク（横断リンク）に対応する線が、共通の親図にない。親図で線を引くか、リンクを見直す |
| `hierarchy/cross-link-unfocused` | warning | 横断リンクに `focus` がなく、遷移先のどのノードとつながるかが分からない。遷移先で対応するノードの id を `link.focus` に書く |
| `hierarchy/orphan` | warning | `--scan` 配下に、ルートから辿れない図がある |
| `hierarchy/self-link` | warning | 自分自身の図へのリンク |
| `hierarchy/map-inconsistent` | warning | 図ごとにマップの参照先が違う |

## 7. マップ図の立体表示

マップ図（`meta.hierarchy.role: "map"`）は、開くと階層スタック表示になります。各階層（L0 全体図／L1 関心ごと／L2 詳細図…）を半透明の板として段違いに重ね、親子を板をまたぐ線で結びます。

- ドラッグで回転、「重なり」で板の間隔、「戻す」で初期角度。「平面」で通常の architecture 図に切り替えます（エクスポートと検証は平面図が対象）。
- カードへのホバー・フォーカス・クリック、背景のクリックは、裏にある平面図の同じノードへ渡します。強調（ホバーの関係トレース、フォーカス、上流／下流、レンズなど）は平面図に実際に効いている薄さと発光を写すので、平面と同じ見え方になります。クリックで詳細パネル（「詳細図を開く」付き）が開き、ダブルクリックまたは Enter でその図を開きます。
- 平面側の強調がないときは、現在地（`#here`）からルートまでの経路と配下を強調します。
- `#here=<マップからの相対パス>` または `#focus=<ノードID>` で開くと、その図を現在地として強調します。各図の「図のマップ」リンクはこれを自動で付けます。

## 8. 親図（全体図）の描き方

- 囲みは詳細図の単位（関心ごと）と一致させます。1枚の詳細図を構成するノードは1つの囲みにまとめ、囲みにリンクします。
- 詳細図どうしの横断リンクは、親図の線で裏付けます（`hierarchy/cross-link-unbacked`）。どの詳細図からどこへ移れるかが、全体図の線をたどって分かる状態にします。
- 横断リンクには `focus` を書き、ノードどうしのつながりにします（`hierarchy/cross-link-unfocused`）。遷移元には着くノードが、遷移先には参照元が表示されます。
- 複数のノードが同じ共通部品を使う関係は、囲みどうしの線で描きます。ノードの総当たりで描くと線が交差して読めなくなります（3対3の総当たりは平面上で交差を避けられません）。
- 遷移先プレビューは、親図の縮図に「この図」と「遷移先」を示し、親図の線で何本経由してつながるかを表示します。

## 9. 推奨の作業順

1. `examples/hierarchy/` を参考に、全体図と詳細図の仕様を作る。全体図に `link`・`require_links: true`・`map`、詳細図に `parent`・`map` を書く。横断リンクには `focus` を書く。
2. 各仕様を `validate --quality showcase` で個別に合格させる。
3. `archify hierarchy-build <root.json> --strict` を実行する。次をこの順で行い、結果をまとめて返す。
   1. `hierarchy-sync`（パンくず・同じ階層の図・参照元・子図の数を仕様へ書き込む）
   2. 親の図から順に `deliver`（子の図は親の図の縮図を埋め込むため）
   3. 横断リンクでつながる図をもう一度 `deliver`（互いの縮図を埋め込むため。必要な図だけ）
   4. `meta.hierarchy.map` があればマップ図を生成
   5. `hierarchy-check`（`--scan` の既定はルート仕様のディレクトリ）
   6. 遷移先プレビューの検査（Chrome/Chromium がなければ「スキップ」と報告。合格扱いにしない場合は Chrome のある環境で再実行する）
   7. 各図とマップの `visual-check`（1440×900〜2048×1320 に収まるか。はみ出す図は不合格）
4. 「結果: 合格」になるまで、報告された図や診断を直して 3 を繰り返す。architecture の図がリポジトリの根拠（`sources`）を持つ場合や、sequence-er／workflow-er が SQL/DDL の根拠を持つ場合は `--repo-root` を渡す（該当する種類の図にだけ渡されます）。
