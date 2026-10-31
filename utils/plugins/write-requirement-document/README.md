# write-requirement-document plugin

[要件定義スキルの正本](../../skills/documentation/write-requirement-document/SKILL.md)を、出力検査用 hooks と一緒に配布する。編集する本体は `utils/skills/documentation/write-requirement-document/` に維持する。`.agents/skills`・`.codex/skills` へ本体やリンクを置かない。

配布物では `skills/write-requirement-document/SKILL.md` が入口、`runtime/write-requirement-document/` が正本のコピーである。入口は単体配置用の `install.py` を実行しないよう指示する。hooks の登録と接続はこの plugin が所有し、汎用の検査処理は未変更の正本を呼ぶ。直接登録した hooks は併用しない。

## 生成

リポジトリ外の、まだ存在しない出力先を指定する。

```sh
python3 utils/plugins/write-requirement-document/build.py --agent codex --output /tmp/requirements-codex
python3 utils/plugins/write-requirement-document/build.py --agent claude-code --output /tmp/requirements-claude
```

配布対象の正本全ファイルをバイト列を変えずに同梱する。ローカルの `dev/results/`、`dev/convergence-report.md`、キャッシュは含めない。入口の metadata は正本から取得する。ビルドは導入・有効化やプロジェクト設定の書き換えを行わない。

利用には Python 3.10以上、既存の Mermaid CLI 11以降・Node.js・対応ブラウザが必要。環境は `document.py doctor` で確かめる。描画ツールは plugin に同梱・自動導入しない。

## 検証

```sh
python3 -m unittest discover -s utils/plugins/write-requirement-document/tests -p 'test_*.py' -v
```

plugin 専用のテストは `tests/` に置く。配布物の移動、正本との一致、設定に書いた4イベントの直接実行、不正出力の差し戻し、実行記録の編集拒否、待機と再開、check・finish、単体配置を作らないことを検証する。

導入方法、公開配布物、確認範囲は[利用ガイド](../../../docs/plugins/write-requirement-document.md)を参照する。実製品からの自動 hooks 呼び出し、利用者の信頼設定、製品へのインストールは直接実行テストと区別する。

## 指摘収集の追加機能

有効な hooks だけが、指摘の原文・修正前後・スキルの版を共通形式へ保存し、入力保存・指摘分類・承認画面の案内を注入する。スキル本体の SKILL.md・ルール表・チェックリストに収集の指示を追加しない。run.py の start/check/finish は収集処理を呼ばず、hooks 無効時も要件定義書を作成・検証・出力できる。収集の失敗で本来の処理を止めない。

修正後の承認は `python3 <plugin-root>/runtime/write-requirement-document/scripts/feedback.py review` の localhost 画面でユーザーが行う。AI は承認ボタン・承認 API を操作しない。記録はプロジェクトの `.skill-feedback/write-requirement-document/` に保存し、`feedback.py export --out <新しいデータセット>` から skill-foundation の改善用 Eval と収束テストへ渡す。
