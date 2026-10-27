# plugin配布物の生成・検証入力

封印済みのgenerate-domain-model-from-code正本から両Agent用pluginを新規生成し、全同梱ファイル・選択manifest/hooks/scripts・ZIP展開のbyte一致と既存出力拒否を検査する。隔離gitプロジェクトで配布物hooks.jsonの実際のcommandを起動し、inactive Stopのno-op、run.py start後のskip_validationを持つmodel.jsonへのPostToolUseによるOUT-07 block、active PreToolUseのClaude ask/Codex denyを確認する。正本・保護ファイルを変更せず、実クライアントへの導入・有効化・外部投稿は行わない。

## 正本と出力

- plugin: `utils/plugins/generate-domain-model-from-code/`
- 同梱Skill: `utils/skills/design/generate-domain-model-from-code/`（`dev/`を含む全ファイル）
- Agent: `codex`、`claude-code`
- 生成先: 新規の`/private/tmp/domain-model-plugin-sample.*/build-<agent>`
- 旧成果物を使わず、それぞれ`build.py --agent <agent> --output <新規出力先>`で生成する。

## 検査用入力

隔離したgitプロジェクトに`order.py`と`README.md`を置く。ZIPを展開した配布物の`hooks/hooks.json`からcommandを取り出し、実行する。

1. 実行記録がない状態でStopイベントを渡す。
2. 同梱`run.py start`で`repo=<隔離プロジェクト>`、`name=hook-verification`、`scope=.`を指定する。
3. 出力先のmodel.jsonに`{\n  "skip_validation": true\n}`を書き、PostToolUseイベントを渡す。
4. 同梱SKILL.mdの編集を要求するPreToolUseイベントを渡す。イベント入力だけで確認し、編集ツールは起動せず、保護ファイルは変更しない。

`PYTHONDONTWRITEBYTECODE=1`、隔離した`XDG_CONFIG_HOME`、`GIT_CONFIG_GLOBAL=/dev/null`、`GIT_CONFIG_NOSYSTEM=1`を使用する。検査コードと環境は`/private/tmp`内に置く。正本の変更、インストール、有効化、外部投稿は行わない。
