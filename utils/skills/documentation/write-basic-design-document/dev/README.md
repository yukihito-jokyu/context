# スキル固有の検査

リポジトリのルートから次を実行する。

```sh
python3 -m unittest discover -s utils/skills/documentation/write-basic-design-document/dev -p 'test_*.py'
```

Markdownの図と参照先、本文の文字の扱い、日本語・英語の表示、欠落やハッシュを書き換えた改変の検出を確認する。見本は`assets/examples/`にある。図の実描画と実行手順全体は、公開成果物を新規作成するときにも確認する。
