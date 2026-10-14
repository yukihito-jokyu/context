# hooksと配布

Skillだけでもscriptsの工程検査を使える。hooksを同梱して導入する場合はpluginとして扱う。Context RepositoryではSkillを正本のまま管理し、plugin定義から参照する。

## 作成する配布物

リポジトリ内で実行する。既存出力へ上書きしない。

```sh
python3 utils/plugins/skill-refiner/build.py --agent codex --output /tmp/skill-refiner-codex
python3 utils/plugins/skill-refiner/build.py --agent claude-code --output /tmp/skill-refiner-claude
```

生成物には正本からコピーしたSkill全体、hooks設定、gate.pyを含む。外部の正本へのリンクに依存しない。生成物は手動編集しない。`utils/plugins/skill-refiner/bundle.json` はこのplugin専用の最小配布定義であり、汎用plugin生成形式を決めたものではない。

各Agentのplugin管理で導入・信頼する。導入やユーザー設定の変更は明示的に許可された場合のみ。hooksを実行するPythonとscriptsが対象環境に必要。Codexではpluginを有効にしてもhooksが自動的に信頼されるとは限らない。[公式plugin仕様](https://developers.openai.com/plugins/build/plugins)

## 作業領域の紐付け

hooksを有効にした後、実行するプロジェクトで紐付ける。

```sh
python3 <skill>/scripts/refine.py --workspace <workspace> activate --root <実行プロジェクト>
```

この操作は `.skill-refiner-active.json` を作る。gate.pyはhookのcwdから親方向にこのファイルを探す。環境変数 `SKILL_REFINER_WORKSPACE` で明示してもよい。紐付けがなければ他の作業には介入しない。作業終了時は紐付けファイルを取り除く。紐付けを残すと、その場所で別のエージェントを起動する操作も検査対象になる。

## 検査対象

- PreToolUse: 起動するpromptが発行済みチケットと完全一致し、工程が正しく、未処理の人間の回答がないか。Codexは `fork_turns=none` が必須。resume・再利用の操作を拒否する。
- PostToolUse / SubagentStart: 観測できたエージェントIDをチケットへ登録する。取得できない場合はその事実を記録し、親が実際の戻り値からregisterする。SubagentStartに制止機能はないため、検証メタ知識を追加しない。
- Edit / Write / apply_patch: 対象正本・固定版・候補版・制御記録への直接編集を拒否する。承認済みの変更はcontrollerが適用する。
- Bash: 実行前に固定版と完了成果物のハッシュを検査する。任意のshellの書き込み先を完全には解析しない。迂回による改変があれば、次のcontroller操作で停止する。

これらは工程の誤りを減らす仕組みであり、悪意あるローカルプロセスからの強制隔離ではない。承認データやPython自体を改変できる同一ユーザーに対する認証境界は持たない。対象環境での登録・tool名・実際のdenyを確認し、入力イベントによるadapterテストだけを実環境での有効化済みと報告しない。

仕様の参照先: [Codex hooks](https://learn.chatgpt.com/docs/hooks)、[Claude Code hooks](https://code.claude.com/docs/en/hooks)。実環境の対応はクライアントの版に依存する。
