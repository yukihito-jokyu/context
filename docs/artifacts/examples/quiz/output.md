# Review Quiz

## 1. クイズ

### Q1

なぜMarkdown原本をdocs/artifactsへ置くだけでは不十分で、文書探索からの除外が必要なのか。

### Q2

HTML原本をダウンロードするリンクを、通常の文書リンクと区別する理由は何か。

### Q3

React成果物はなぜindex.htmlだけではなく、画面一式のZIPで渡すのか。

### Q4

HTML要件スキルのブラウザ検証に成功したら、承認済み画面として扱ってよいか。

### Q5

compareの実例で「原本」はAで0件、Bで一致した。検索関数の実装を変更したからか。

## 2. 解答

### A1

原本Markdownまでドキュメントとして索引化すると、利用ガイドのページと実出力の全文が混ざる。docusaurus.config.tsのexcludeで文書から除外し、staticDirectoriesで原本を配信する。

### A2

クライアントルーターによる文書遷移を避け、ファイルを保存する操作にするため。MDXComponents/Aは#download付きリンクをnative anchorとdownload属性へ変換する。

### A3

Reactのproduction buildはJSとCSSを相対参照する。HTMLだけでは参照先が欠ける。スキルのfreeze_snapshotが生成したZIPを展開して、付属する表示一式を配信する。

### A4

扱わない。自動検証は注釈位置やモードなどを検査する。初回案の内容に対する人間の承認とは別なので、この実例は確認待ち。

### A5

実装は同じ。Aの呼出元はcontentを空にし、Bは実出力全文を渡した。結果の差は実入力の違いから生じた。検索速度の差は測定していない。

## 3. 理解できていない場合に確認すべき箇所

- docusaurus.config.tsとsrc/theme/MDXComponents/A/index.tsx。
- react-requirements-workshopのfreeze_snapshotと配布ZIP。
- HTML/Reactのbrowser-validation.jsonと画面案の到達点。
- compareのsearch-input.json、search-results.json、search-core.js。
