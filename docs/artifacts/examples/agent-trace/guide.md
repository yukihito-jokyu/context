# archify-jpの実成果物を検証する手順書

## 前提

- contextリポジトリのルートで実行する。
- Node.jsとChrome、保存済みinput.jsonが必要。
- この手順書は同時記録したログの成功経路から整理した。

## 手順

1. 検証する。

   ```sh
   node utils/skills/design/archify-jp/bin/archify.mjs validate sequence docs/artifacts/examples/archify-jp/input.json --quality showcase --json
   ```

2. 配布するHTMLを生成する。終了コード0を確認してから次へ進む。

   ```sh
   node utils/skills/design/archify-jp/bin/archify.mjs deliver sequence docs/artifacts/examples/archify-jp/input.json docs/artifacts/examples/archify-jp/output.html --quality showcase --json
   ```

3. 検査して画像を取得する。

   ```sh
   node utils/skills/design/archify-jp/bin/archify.mjs visual-check docs/artifacts/examples/archify-jp/output.html --json
   ```

4. 確認する。1440×900と2048×1320のlight画像を開き、図のラベル、矢印、結論カードが読めるか目視する。

## 完了条件

生成検証9項目、エラー0、警告0。4サイズの包含検査が成功し、配布HTMLと画像を確認できること。サイトへの掲載と人間の最終確認は別に行う。
