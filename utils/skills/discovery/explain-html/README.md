# explain-html

一つの事象・事柄を、全体像から具体例、詳細、条件と例外まで理解できる単体HTMLへまとめます。技術・実装・業務・制度・自然現象など、分野を限定しません。

[SKILL.md](SKILL.md)をAIへ読ませ、題材、読者、入力資料、保存先を渡してください。compareと同じ説明品質・関心別ページ・全体図・段階再生・出典照合を使い、単一題材を説明します。技術題材の具体物はコードや設定、一般題材は書類・記録・式・観測値などです。

- [説明の組み立てと入力形式](references/reading-design.md)
- [図と具体物の対応](references/explanation-patterns.md)
- [段階再生](references/flow-motion.md)
- [納品前の確認](references/acceptance.md)
- [利用ガイドと実際の成果物例](https://github.com/yukihito-jokyu/context/blob/main/docs/discovery/explain-html.md)

Python 3.9以上、Node.js 18以上が必要です。同梱Archify 2.16.0はcompareの固定済み依存をバイト単位で引き継ぎ、MITライセンスと元の導入レシートを保持しています。生成時にcompareやグローバルのスキル配置を参照しません。通常の生成にはnpm installは不要です。

```sh
python3 scripts/sync_vendor.py --check
python3 scripts/render_html.py page-model.json output.html
python3 scripts/check_overviews.py output.html
python3 scripts/check_coverage.py output.html coverage.json
```

依存更新はユーザーが同期を依頼した場合だけ行います。固定版CLIによる更新と標準画像出力は[dependencies.md](references/dependencies.md)を参照してください。補助SVG処理はブラウザのPNGエクスポートとの一致を保証しません。
