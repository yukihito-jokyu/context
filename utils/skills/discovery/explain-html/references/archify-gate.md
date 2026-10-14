# Archifyを必須にするゲート

Archify使用は制作上の必須条件であり、可読性・時間・座標調整を理由に独自SVGへ切り替えない。使えない場合は未完了として不足を報告する。理由を書けば例外になるという規則はない。

## 制作と検査

各図の専任担当が同梱CLIでshowcaseのdeliverを行い、そのstdout JSONをreceipt.jsonへ保存する。標準SVGはdependencies.mdの変更していないserializeSvg関数による限定DOMアダプターで取得する。ブラウザ操作や標準PNGと同一の検証をしたとは報告しない。現在の同梱版は無改変の2.16.0。vendorへ独自拡張を追加しない。エクスポート用serializeSvgの固定hashも照合し、版だけを見て任意の処理を認めない。

```sh
node <skill>/vendor/archify-jp/bin/archify.mjs deliver sequence model.json figure.html --quality showcase --json > receipt.json
python3 <skill>/scripts/export_standard_svg.py figure.html figure.svg --model model.json
```

manifestの図行に次を追加する。パスはmanifestの親フォルダ内。outputs.modelは実際の型付きモデル、outputs.figureは配布HTML。

```json
{
  "archify": {
    "type": "sequence",
    "viewer": "diagrams/request/figure.html",
    "svg": "diagrams/request/figure.svg",
    "receipt": "diagrams/request/receipt.json"
  }
}
```

記事には標準SVGを変更せずimgのdata URIまたはmanifestルートからの相対パスで埋め込み、data-archify-model-sha256へモデルの生バイトSHA256を付ける。HTML生成CLIはmanifestを必須にし、検査に失敗すると既存出力を更新しない。

```sh
python3 <skill>/scripts/render_html.py page-model.json output.html --manifest diagram-agent-manifest.json
python3 <skill>/scripts/check_diagram_delegation.py diagram-agent-manifest.json --article output.html
```

check_archify.pyは自己申告を読むだけではなく、一時フォルダで同梱Archifyのdeliverと標準SVG出力を実行し直す。現在のモデル→配布HTML→SVG→記事画像をバイト照合する。レシートとファイルのhashも照合する。未使用・変更・差し替え・登録図の未掲載・未検証のinline SVG/canvas等は失敗。現時点のゲートは標準SVGの限定DOM経路に対応し、ブラウザPNGとSVG overlayは未対応として停止する。写真はdata-explain-image-role="photo"で識別するが、図を写真と偽って除外しない。

## hooksでの自動検査

Claude Code用の未導入plugin正本はutils/plugins/explain-html。hooksをSkill本体の配布へ混ぜず、pluginとしてビルドする。

```sh
python3 utils/plugins/explain-html/build.py --output /tmp/explain-html-plugin
```

導入・有効化を許可された環境でpluginを登録した後、対象プロジェクトの.explain-html-active.jsonにmanifestと完成記事を相対指定する。紐付けがないプロジェクトには介入しない。

```json
{"manifest":"artifacts/diagram-agent-manifest.json","article":"artifacts/output.html"}
```

Stop hookは同じ完了検査を呼び、失敗や検査異常をstderr＋exit2で返す。stop_hook_activeだけを理由に検査を飛ばさない。Claude Codeは連続blockに上限を持つため、hookだけで永久に完了を禁止できるとは扱わない。最終生成CLIのゲートを併用する。[公式Stop仕様](https://code.claude.com/docs/en/hooks#stop)。人間への質問や未完了の草稿提示と「納品完了」を区別する。中断・紐付け解除により相談できる。Codexのhook adapterは今回追加しておらず、共通CLI検査を使う。

## テストが担保すること

- 本物の同梱CLI生成物と標準SVG、記事への一致した埋め込みが通る。
- 独自SVG・renderer自己申告・ファイル変更・偽hash・記事差し替え・未掲載・inline図・パス逸脱が拒否される。
- 不合格のHTML生成は既存出力を上書きしない。
- 未紐付けhookは介入せず、紐付け後の失敗と継続中の失敗はexit2、本物の合格成果物はexit0。

決定論的にしたものは、固定したvendorとモデルに対する再生成・バイト一致・参照判定である。調査、図の意味、ノード分割、文章、読みやすさ、人間の理解は対象外。HTML/CSSで描いた全グラフの検出、写真分類の正しさも完全には検出できない。同一ユーザーが検査器・vendor・紐付けを変更できる環境での認証や強制隔離ではない。hook入力テストの成功は、実クライアントに導入して停止を検証済みという意味ではない。

## 同じ論理図の局所投影

1枚へ全経路を詰めると読めない場合、同じ専任担当が主図と局所投影を作れます。担当行を増やさず、同じ行のarchify_variantsへid、reason、type、model、viewer、svg、receiptを登録します。idは行内で一意のkebab-case、reasonはどの関係をなぜ分けるかの具体的な理由。すべての投影を同じshowcase再生成・標準SVG一致・記事埋込み検査で照合します。未掲載の投影も失敗です。投影を別の論理図の担当回避へ使いません。図担当は一次資料・番号解説・実画面確認を各投影まで一貫して行います。

改修のコード保持はrender_html.pyの--baselineとcheck_article_content.pyで別に確認する。前版のコード文字列・行ID、内部参照から同じ比較結果を返すが、コードの実動作や図の意味の正しさは決定論的な検査の対象にしない。
