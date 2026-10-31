# 要件定義書を作る plugin

まず、このファイルからの相対パス `../../runtime/write-requirement-document/SKILL.md` を読み、その手順と参照資料に従う。正本でいう `<skill>` は `runtime/write-requirement-document/` を指す。本文・図・PNG・検査・出力形式は正本に従う。

plugin では次の接続方法を使う。

- `scripts/install.py` は実行しない。Skillを `.agents/skills`・`.codex/skills`・`.claude/skills` へ配置せず、プロジェクトの設定へ hooks を直接登録しない。入口と hooks は plugin 管理から読み込む。
- hooks の設定と呼び出し口は plugin の `hooks/hooks.json` と `scripts/hook.py` が所有する。出力検査は同梱した正本の汎用ランタイムを呼ぶ。hooks が使えない環境でも、正本の `run.py check` と `finish` は必ず実行する。
- plugin の入口・設定・`runtime/` を利用者のプロジェクトへ複製しない。実行記録と成果物だけを、利用者のプロジェクトの `.skill-runs/write-requirement-document/` に保存する。
- Python、Mermaid CLI、対応ブラウザの既存環境を `document.py doctor` で確認する。描画ツールを自動インストールしない。
