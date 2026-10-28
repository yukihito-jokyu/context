# 実行入力

個人ホームパスと観測した実行環境の詳細版を匿名化した現在の正本から、explain-html の Claude Code plugin 配布物を再生成する。旧成果物は全削除し、新しい隔離場所で build.py、ZIP 化、展開、正本との全ファイル・バイト列の一致検査、manifest と hooks の JSON 検査を実行する。導入・有効化・実クライアントによる hooks 発火は行わない。

## 再実行

```sh
python3 docs/artifacts/plugins/explain-html/verify_plugin.py --repo-root . --workdir /tmp/explain-html-plugin-new
```

`--workdir` には存在しないディレクトリを指定する。Python 3 が必要。結果はその中の results/ に出力する。公開記録の環境パスと詳細版は置換し、ZIP 内の正本ファイルはバイト一致を保つ。
