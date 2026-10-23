# sample-cli-foundation の受付・骨組み生成結果

Python標準ライブラリだけを使うCLI基盤について、受付情報を manifest にまとめ、同梱の init_foundation.py で骨組みを生成しました。今回は指定されたフェーズ0・1までを実行し、状態は `building` のままです。

## 生成したもの

ZIPの `sample-cli-foundation/` に、manifest を含む24ファイルを保存しました。文書やスキルに残る `TODO(pattern-foundation)` は、後続フェーズで埋める未完成箇所です。

- `.foundation/manifest.json`：Python、CLI分野、新規作成、日本語、実装用 `impl` とレビュー用 `review`、指定のcheck/fixコマンドを記録。
- `AGENTS.md` と `CLAUDE.md`：エージェント向け入口のひな形。`CLAUDE.md` は `@AGENTS.md` の1行。
- `.claude/skills/impl/` と `.claude/skills/review/`：実装・レビュー手順のひな形。
- `.claude/settings.json`：生成先プロジェクトで使うhooks設定のひな形。
- `docs/design/` と `README.md`：設計、調査、ルール、ADR、収束結果のひな形。
- `.foundation/bin/`：基盤内で使う検査・hooks・収束テスト用のPythonスクリプト6本。
- `.foundation/probes.json` と `.foundation/convergence/`：違反例・収束課題・レビュー課題のひな形。

## 確認した結果

`init_foundation.py` の初回実行は終了コード0で、23ファイルを作成しました。事前に作成したmanifestを合わせて24ファイルです。再実行も終了コード0となり、全ファイルのSHA-256が一致しました。

別の作業用コピーで `AGENTS.md`、`.claude/settings.json`、`.foundation/bin/guard.py` に識別用の変更を加えてから再実行し、変更済みファイルを含む全ファイルが上書きされないことを確認しました。公開ZIPには、この確認用変更を入れていません。

生成した `rules_check.py`、`violation_probe.py`、`guard.py`、`convergence.py` は、`--help` で終了コード0となりました。補助ライブラリを含む6本はPythonの構文解析にも成功しました。`hooks.py --help` は利用方法を表示して終了コード1を返します。これは実装どおりの結果で、hooksの実動作確認は行っていません。

## 未実施・未決定の範囲

バージョン調査、ルール確定、アプリ実装、formatter・linter選定、check/fix実装、違反probe、hooks実動作確認、収束テスト、`rules_check.py --final` は未実施です。manifestの技術バージョンは、フェーズ2で調査するまで空文字としています。

分野は同梱プロファイルの `cli-library` を既定値として選びました。配布先・対応Python版・ライセンスは、今回の骨組み生成に不要なため未決定です。収束テストの設定は同梱例の既定値を記録しただけで、外部エージェントを起動していません。外部API、依存インストール、外部投稿も行っていません。

このZIPは初期化後の骨組みを確認するための成果物です。機械で規約を強制できる完成済みの開発基盤としては扱えません。後続作業では、フェーズ2の調査から再開する必要があります。
