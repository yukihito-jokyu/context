# skill-foundation plugin

このファイルは plugin 用の入口である。まず、このファイルからの相対パス `../../runtime/skill-foundation/SKILL.md` を読み、そこに書かれた手順と参照資料に従う。正本全体は `runtime/skill-foundation/` に含まれている。正本でいう `<skill>` と `<skill-foundation>` は、そのディレクトリを指す。

plugin での実行に限り、次の接続方法を使う。ルール、契約、検査、出力は正本に従う。

- skill-foundation 自身の `install.py` は実行しない。plugin が skill-foundation の hooks を提供する。作成した別のスキルの `install.py` は正本の手順どおり実行する。
- skill-foundation の `scripts/convergence.py` を呼ぶときは、代わりに plugin ルートの `scripts/convergence.py` を使う。引数は正本と同じにする。この接続処理は、runner `subagent` の準備時にプロジェクトへ専用エージェントを書き出さず、同梱のエージェントを案内する。ほかのスクリプトは正本のものを使う。
- Claude Code の Agent ツールでは、専用のエージェント型を `skill-foundation:skill-foundation-tester` に読み替える。プロンプトの前後に文を足さず、新しいエージェントに渡す。専用型が利用できなければ、通常のエージェントで代用せず、正本の STEP-03 に従って起動できる CLI を使う。Codex のサブエージェントでは専用型の fence は働かないという正本の限界も維持する。
- plugin のコード、設定、`runtime/` は編集しない。スキルの作成先と実行記録は、利用者のプロジェクト内にする。
