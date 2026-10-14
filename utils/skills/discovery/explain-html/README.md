# explain-html

一つの事象・事柄を、全体像から具体例、詳細、条件と例外まで理解できる単体HTMLへまとめます。技術・実装・業務・制度・自然現象など、分野を限定しません。

[SKILL.md](SKILL.md)をAIへ読ませ、題材、読者、入力資料、保存先を渡してください。compareと同じ説明品質・関心別ページ・全体図・段階再生・出典照合を使い、単一題材を説明します。技術題材の具体物はコードや設定、一般題材は書類・記録・式・観測値などです。

- [説明の組み立てと入力形式](references/reading-design.md)
- [図と具体物の対応](references/explanation-patterns.md)
- [段階再生](references/flow-motion.md)
- [納品前の確認](references/acceptance.md)
- [利用ガイドと実際の成果物例](https://github.com/yukihito-jokyu/context/blob/main/docs/discovery/explain-html.md)

Python 3.9以上、Node.js 18以上が必要です。同梱Archifyは元の2.16.0を無改変で保持します。vendorへ独自の修正を加えず、元スキルの正式な更新を確認した場合だけ同期を扱います。MITライセンスを保持しています。生成時にcompareやグローバルのスキル配置を参照しません。通常の生成にはnpm installは不要です。

```sh
python3 scripts/sync_vendor.py --check
python3 scripts/render_html.py page-model.json output.html --manifest diagram-agent-manifest.json
python3 scripts/check_overviews.py output.html
python3 scripts/check_coverage.py output.html coverage.json
```

依存更新はユーザーが同期を依頼した場合だけ行います。固定版CLIによる更新と標準画像出力は[dependencies.md](references/dependencies.md)を参照してください。補助SVG処理はブラウザのPNGエクスポートとの一致を保証しません。

資料名・確認日だけのページは、図を作らない具体的な理由をモデルへ記録できます。仕組みを説明するページには全体図を置きます。

図は読者の問いに合わせて構成・通信・手順・状態・変換を使い分け、概要から同じ具体例を追える詳細へつなぎます。制作要件は`diagram-plan.json`へ保存し、図の表記と本文の対応を確認します。初期表示は図全体とし、文字を読むための表示切替は標準で追加しません。

### 図の専任制作

1つの図に1つの新規エージェントを割り当て、その担当がネットでの詳細調査、具体的な表現の設計、作図、付随解説の雛形まで完成させます。記事担当は文脈と共有用語を渡し、返却された図と解説を統合します。[専任制作の手順](references/diagram-delegation.md)を参照してください。

図内は短い名称・判定・値に絞り、複数の処理は必要に応じてノードへ分けます。具体的な説明はPCで図の横、狭幅では直下へ置き、同じ番号で図の要素へ対応付けます。

1枚へ詰めると読めない局所経路は、同じ論理図の担当が標準モデルへ分け、全投影を検査します。

Archify使用は必須条件です。HTML生成と完了検査は同梱Archifyを実際に再実行し、モデル・配布HTML・標準SVG・記事画像の一致を確認します。自己申告や独自SVGでは通過しません。[ゲートの契約・担保範囲・Claude Code hooks](references/archify-gate.md)を参照してください。hooks付き配布はpluginです。今回の追加では実環境へのインストール・有効化を行いません。

本文はゆとりのあるゴシック（19px・行間1.85）を基準にします。最初に読む量を短い答えと具体例へ絞り、追加の仕様や条件は目的別に開けるようにします。読む量の設計は[reading-design.md](references/reading-design.md)に定めます。

標準画像と番号付き横解説の配置をテンプレートへ同梱しています。主図と局所投影それぞれの説明を保持し、統合後のPC・390px表示と前版コードの保持を確認します。

改修ではHTML生成に`--baseline before.html`を追加します。前版コードの欠落、行ID・字下げの変更、重複ID、内部リンク切れを出力前に拒否します。意味・実行結果の確認とは分けて扱います。
