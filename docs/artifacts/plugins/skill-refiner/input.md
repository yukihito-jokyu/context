# skill-refiner plugin build example

Issue #79のpluginガイド用。委任されたサブエージェント `/root/plugin_guides` が正本のbuild.pyを使い、リポジトリ外の未作成ディレクトリで配布物を生成する。対象: codex, claude-code。生成物をZIPにし、展開後の全ファイルが正本とバイト一致することを確認する。インストール・有効化・実クライアントでのhook実行は行わない。
