# 実行入力

plugin 専用テストを所有者の `utils/plugins/skill-foundation/tests/test_plugin.py` へ移した後の公開配布物を再作成する。

`utils/plugins/skill-foundation/` の現在の12ファイルを配布定義とし、`utils/skills/authoring/skill-foundation/` の指定版97ファイルを一切変更せずに使う。旧版は参照しない。公開成果物の削除後、新しい一時作業場所で `build.py` から Codex と Claude Code 向けを実際に生成し、空白のある別の場所へ移動、ZIP 化、展開して再検証する。

確認する内容は、正本全97ファイルの SHA-256、seal の49ファイル、manifest、hooks の4イベント、正本へ案内する薄い入口、`skill-foundation:skill-foundation-tester` の fence、`convergence.py prepare` と `prompts` がプロジェクトへ専用エージェント定義を書き出さないこと。展開後の hooks 設定に記載された command を直接実行する。

リポジトリのルートで専用テスト7件を実行し、結果を保存する。

```sh
python3 -m unittest discover -s utils/plugins/skill-foundation/tests -p 'test_*.py' -v
```

実モデルは起動しない。ユーザーホームの設定や実リポジトリの導入設定は変更しない。実セッションによる自動 hooks 発火、Codex の信頼 UI、独立した AI による収束テストは未確認として区別する。このプロジェクトへの導入確認は親エージェントが別に記録する。

保存先は `docs/artifacts/plugins/skill-foundation/`。両製品の ZIP、実行入力、検証全文、JSON、専用テストと manifest 検査のログ、再実行用スクリプト、`execution.json` を保存する。plugin 全体と同梱スキル全体の正本一覧は `scripts/example-skill-source.cjs` の `sourceManifest` で作り、全成果物の SHA-256 を登録する。

## 再実行

再実行には現在の Context Repository 全体と Python 3、Node.js、git、Claude Code CLI が必要。Claude Code CLI は manifest の静的な検証だけに使い、設定用ディレクトリを一時作業場所へ分離する。

```sh
python3 docs/artifacts/plugins/skill-foundation/verify_plugin.py \
  --repo-root . \
  --workdir /tmp/skill-foundation-plugin-verification-new
```

`--workdir` には存在しないディレクトリを指定する。結果はその中の `results/` に出力する。専用テストはリポジトリ内の所有者ディレクトリから実行するため、テストファイルだけのコピーでは再実行できない。

## 公開時の置換

公開ログと JSON では、リポジトリの個人絶対パスを `<repository>`、今回の一時作業場所を `<workdir>`、ユーザーホームを `<user-home>`、システムの一時パスを `<system-temp>` に置換する。ZIP 内の正本ファイルのバイト列は変更しない。
