# compare

似た技術を、全体図から実行の流れ、具体的なコードまで理解する比較HTMLへまとめるスキルです。関心別ページ、暖かいライト配色、大きい文字、左右比較、情報の網羅性、主語を明記した文章、流れと遷移の動きを含みます。

使うAIへ[SKILL.md](SKILL.md)を読ませ、比較対象と資料を渡してください。スキルは題材をHooksとModsに限定しません。制作者は一次資料から確認範囲を決め、全項目と説明先を対応づけます。

Archifyは`vendor/archify-jp`に同梱しています。同期には次のコマンドを使います。

```sh
python3 scripts/sync_vendor.py
python3 scripts/sync_vendor.py --check
```

同期スクリプトは`npx skills add`の固定CLI版を通じて、`~/.agents/skills/archify-jp`から日本語版を取得します。現在の同梱版は2.16.0です。同期に失敗してもスクリプトは既存のvendorを残します。

Python 3.9以上、Node.js 18以上が必要です。通常の同期にはnpm/npxとネットワーク接続も必要です。同梱版で図を作るだけならnpm installは不要です。同期先・版・内容の記録は[dependencies.json](dependencies.json)と[dependencies.lock.json](dependencies.lock.json)で確認できます。

- [依存関係とエクスポート](references/dependencies.md)
- [納品前の確認](references/acceptance.md)
- [全体図から詳細への遷移](references/navigation-and-export.md)
- [HTMLテンプレート](assets/comparison.html)

vendorはMITライセンスを含む元のArchifyパッケージを保持しています。画像は標準のeditorialエクスポートを使います。ブラウザ操作を使えない環境の補助SVG処理は、ブラウザのPNG出力や見た目の一致を保証しません。
