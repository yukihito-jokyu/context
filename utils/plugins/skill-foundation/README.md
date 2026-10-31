# skill-foundation plugin

[skill-foundation の正本](../../skills/authoring/skill-foundation/SKILL.md)を、出力検査用 hooks と収束テスト用エージェントと一緒に配布する。正本のファイルは変更せず、ビルドで `runtime/skill-foundation/` にコピーする。`skills/skill-foundation/` はその正本を読む入口であり、plugin 固有の接続方法だけを持つ。metadata はビルド時に正本から取得する。

リポジトリのルートで、存在しない出力先を指定する。

```sh
python3 utils/plugins/skill-foundation/build.py --agent codex --output /tmp/skill-foundation-codex
python3 utils/plugins/skill-foundation/build.py --agent claude-code --output /tmp/skill-foundation-claude
```

生成物には正本全体、plugin の入口、対象製品用の manifest・hooks、接続用スクリプトを含む。Claude Code 用には専用エージェントも含む。`scripts/hook.py` が未変更の正本の検査を呼び出す。Claude Code の plugin agent の frontmatter に hooks は登録せず、plugin の PreToolUse から専用エージェントの `agent_type` を判定して `fence.py` を呼ぶ。`scripts/convergence.py` は専用エージェントの配置方法だけを差し替え、元の収束テスト処理を実行する。

ビルドは導入・有効化を行わない。Claude Code では `/skill-foundation:skill-foundation` で呼び出す。Codex では plugin のスキルを選んで依頼する。既存の単体導入から移行するときは、同じスキルと hooks の直接登録を整理し、plugin の一組だけを読み込む。

検証範囲、配布物、導入手順は[利用ガイド](../../../docs/plugins/skill-foundation.md)を参照する。収束テストの実行可否・回数の確認と、Codex の hooks の信頼確認は省略しない。

## 検証

この plugin 専用のテストは `tests/` に置く。リポジトリのルートから次で実行する。

```sh
python3 -m unittest discover -s utils/plugins/skill-foundation/tests -p 'test_*.py' -v
```

配布物の移動後の起動、正本との一致、微修正後の実行、終了前検査、専用エージェントの制御を検証する。リポジトリ全体の文書テストとは別に実行する。

利用用の正本には開発用の `dev/` を含めない。配布した正本のバイト列を照合し、同梱の `selftest.py` で新しいスキルを組み立てて Eval・設定・出力検査を確かめる。収束テストの準備では、先に `eval_check.py` を実行して Eval の検査結果を作る。

スキル自身の編集を制限するルールと seal による開始拒否は使わない。ユーザーの微修正後も通常どおり実行でき、出力の契約検査は継続する。

生成するスキルには、指摘・修正前後の実ファイル・確認画面でのユーザー承認・使ったスキルの版を共通形式で収集する hooks を追加機能として必ず同梱し、既定で登録する。生成した SKILL.md・ルール表・チェックリストには収集の指示を入れず、必要な指示は有効な hooks だけが注入する。hooks 無効時もスキルの本来の処理は機能する。収集側の失敗で本来の完了を止めない。`feedback.py review` の localhost 画面で修正前後を確認して承認する。会話や AI の判断だけで承認済みにしない。`feedback.py export` と `feedback_eval.py` で、承認済みの収集データとスキルから改善用 Eval・収束テストの候補を作れる。

`runtime/skill-foundation/scripts/feedback_selftest.py` は、合成イベントと localhost の確認画面で収集・承認・古い画面の拒否・Eval への接続を検証する。実モデルを起動せず、実ユーザーの承認も作らない。サンドボックスで検証するときは localhost の待ち受けを許可する。
