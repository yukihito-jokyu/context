# motion-catalog 実行報告：本の一覧のカードにフェードイン

| 項目 | 内容 |
|---|---|
| 使った id | `fade-in-out`（フェードイン／アウト、種類は motion） |
| 読んだファイル | `SKILL.md`、`animations/fade-in-out.html`（手順A。`catalog.html`・`references/index.tsv`・`references/porting.md` は読んでいません） |
| 対象 | `site/index.html` の本の一覧のカード（`.card`、6枚） |
| 入れた場所 | `site/index.html` の `<style>` の末尾（`.card p` の規則の直後） |
| 値 | 現れる時間 `in` = 260ms（params の初期値のまま）、イージング `cubic-bezier(0.22, 1, 0.36, 1)`（spec の「現れる」）、`opacity 0 → 1`。ずらし（遅延）はなし（params・spec にないため）。消える側（`out` = 180ms）は、今回はきっかけがないので入れていません |
| 動きを減らす設定への対応 | spec の「もともと透明度だけなので、そのままでよい」に従い、同じフェードインのままにしています（専用の規則は追加していません） |
| 確かめた方法 | ヘッドレスの Chrome でページを開き、アニメーションの時刻を 0〜260ms に合わせて撮影・不透明度を取得。`prefers-reduced-motion: reduce` を有効にして読み込み直後も撮影 |

## 何をどこに入れたか

`site/index.html` の `<style>` の末尾に、カードの登場アニメーションとキーフレームを追加しました。HTML は変えていません。見た目（色・余白・角丸など）は元のページのままで、透明度だけが変わります。

登場のアニメーションなので、`animation-fill-mode` は `backwards` にしています（終わった後に何も残さない）。詳細ページの見本にある「1200ms 後に消える」部分はプレビューのための繰り返しなので、移していません。

## 差分の要点

```css
/* motion-catalog: fade-in-out（フェードイン）。ページを開いたときにカードを透明度だけで表示する */
.card { animation: card-fade-in 260ms cubic-bezier(0.22, 1, 0.36, 1) backwards; }
@keyframes card-fade-in { from { opacity: 0; } to { opacity: 1; } }
/* 動きを減らす設定：透明度だけの動きなので、そのままにする（fade-in-out の spec どおり） */
```

## 確かめたこと

- 6枚のカードすべてに、時間 260ms・`fill: backwards` のアニメーション `card-fade-in` が付いていること。
- アニメーションの時刻を合わせたときのカードの不透明度が、0ms で 0、40ms で 0.56、80ms で 0.84、130ms で 0.96、260ms で 1 になること（`preview.png`）。
- 実時間で読み込んだときも、約 50ms で 0.66、約 300ms 以降は 1 になること。
- アニメーションが終わった後は、カードにアニメーションが残らず、不透明度が 1 であること。
- `prefers-reduced-motion: reduce` を有効にしても同じフェードインが動き、撮影時点でカードが表示されていること（`reduced-motion.png`）。

## 確かめていないこと

- Chrome 以外のブラウザ（Safari・Firefox）での表示。
- 実機・低速な端末での見え方や、スクリーンリーダーでの読み上げ。
- 動きを減らす設定で時間を短くする選択肢（spec では任意のため、入れていません）。
