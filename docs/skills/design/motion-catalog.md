---
title: motion-catalog — カタログのアニメーションをプロジェクトに実装する
sidebar_label: motion-catalog
---

# motion-catalog

UIアニメーションのカタログ（23カテゴリ・608件）から動きを選び、対象のプロジェクトに実装します。カタログには、フェードインやスプリングのような「動き」、動きの見直しに使う「考え方」、複数の動きを組み合わせる「表現スタイル」が入っています。各項目の詳細ページに、値・決まり・参照実装がまとまっています。

実装先は素のHTML/CSSのほか、React・Vue・Svelte・ネイティブなどにも対応します。移すのは時間・イージング・キーフレーム・順序・きっかけだけです。色・形・クラス名は対象プロジェクトのものを使います。動きを減らす設定（`prefers-reduced-motion`）への対応は必ず入れます。

## 導入と前提

hooksを同梱しない単一Skillなので、[`npx skills add`](../../plugins/distribution.md)で導入します。

```sh
npx skills add https://github.com/yukihito-jokyu/context/tree/main/utils/skills --skill motion-catalog --agent codex claude-code
```

一覧ページ`catalog.html`をブラウザで開くと、全件の動きを見比べられます。各詳細ページで値を変えて、依頼用のプロンプトをコピーすることもできます。

## 渡す情報

使う動きのid（または名前）、対象の要素、値を変える場合はその値を渡します。動きが決まっていなければ、「弾むように」のような雰囲気や、「この画面に良い感じに動きを」のようなおまかせの依頼でもかまいません。

## 依頼例

```text
motion-catalog スキルで「フェードイン／アウト（fade-in-out）」を実装してください。対象は site/index.html の本の一覧のカード（.card）です。
```

```text
motion-catalogを使って、ボタンを押したときに弾むような動きを付けてください。
```

```text
motion-catalogを使って、このダッシュボード全体に良い感じに動きを付けてください。
```

## 進め方

依頼の形によって、読むものが変わります。

1. **idがある場合**：その項目の詳細ページだけを読み、対象の書き方に合わせて移植します。
2. **名前や雰囲気だけの場合**：一覧（`references/index.tsv`）から当てはまる行を探し、1〜3件の候補を示します。どれを使うか確かめてから、1の手順で実装します。
3. **おまかせの場合**：画面の性格と、場面ごとに使う動きを決めた計画を先に示します。確認が取れたら、選んだ項目ごとに実装します。
4. 終わったら、何をどのファイルのどこに入れたかを報告します。

## 成果物の例

本の一覧のページ（素のHTML/CSS）のカード6枚に、カタログの「フェードイン／アウト（fade-in-out）」をフェードインとして実装しました。詳細ページの値（260ms・cubic-bezier(0.22, 1, 0.36, 1)・透明度だけ）をそのまま使い、追加したのはCSS 2行だけです。

**到達点：site/index.htmlへの実装と、ヘッドレスのChromeでの動きと動きを減らす設定の確認まで。Chrome以外のブラウザと実機での確認は未実施。**

### 実行した依頼

```text
motion-catalog スキルで「フェードイン／アウト（fade-in-out）」を実装してください。対象は site/index.html の本の一覧のカード（.card）です。ページを開いたときにカードがフェードインで表示されるようにしてください。値は変えません。
```

### 実際の画面

![本の一覧ページを0msから260msまで6コマ並べた画像で、カードが何も見えない状態から薄く現れ、最後に完全に表示されるまでが分かる](/skills/motion-catalog/preview.png)

[画像を原寸で開く](pathname:///skills/motion-catalog/preview.png)

各コマは、読み込み直後にアニメーションを止めて時刻を合わせて撮ったもの（実時間の連写ではない）。ラベルは経過ミリ秒とそのときのカードの不透明度

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
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

````

### 成果物を取得する

- [実行報告（Markdown）](pathname:///skills/motion-catalog/output.md#download)
- [実装前のHTML](pathname:///skills/motion-catalog/before.html#download)
- [実装後のHTML](pathname:///skills/motion-catalog/after.html#download)
- [動きを減らす設定で開いた画面（PNG）](pathname:///skills/motion-catalog/reduced-motion.png#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/motion-catalog/after.html)
- [実行入力の原本](pathname:///skills/motion-catalog/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/motion-catalog/execution.json#download)

### 確認した結果

- 読んだのはSKILL.mdとanimations/fade-in-out.htmlだけで、catalog.html・references/index.tsv・references/porting.mdは読んでいない（素のHTML/CSSのため）
- ヘッドレスのChromeで、6枚のカードすべてに時間260ms・fill backwardsのアニメーションcard-fade-inが付いていた
- アニメーションの時刻を合わせたとき、カードの不透明度は0msで0、40msで0.56、80msで0.84、130msで0.96、260msで1だった
- 実時間で読み込んだとき、不透明度は約50msで0.66、約300ms以降で1だった
- アニメーションが終わった後、カードにアニメーションは残らず、不透明度は1だった
- 見本の「消える」側（180ms）は、消すきっかけがないため移していない
- prefers-reduced-motion: reduceを有効にしたとき、specの「透明度だけなのでそのままでよい」に従い同じフェードインのまま表示された
- preview.pngとreduced-motion.pngは画像を開いて確認した
- Chrome以外のブラウザ（Safari・Firefox）、実機・低速な端末、スクリーンリーダーでの確認はしていない

## 確認するポイント

実際にブラウザで開いて、動きのタイミングと見た目が画面に合っているかを確かめます。OSで動きを減らす設定にしたときに、動きが抑えられることも確かめます。5秒を超えて動き続けるもの（背景・ループ・自動再生）には、止める・再開するボタンが付いているかを確認します。WebGL・3D・物理シミュレーションなどが元になっている項目は、見本がそのまま移植されていないかを確認します。

## 正本を読む

詳細な手順と制約は[motion-catalogのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/motion-catalog/SKILL.md)を参照してください。
