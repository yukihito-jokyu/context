# generate-domain-model plugin

コードからMermaid原本・PNG・HTMLカタログを作るSkillと、出力・保護ファイル・実行の終了を検査するhooksをまとめます。

Skill正本は `../../skills/design/generate-domain-model/` です。plugin固有の入口は `scripts/gate.py` に置き、同梱したSkillの共通ランタイムへ渡します。

```sh
python3 utils/plugins/generate-domain-model/build.py --agent codex --output /tmp/domain-model-codex
python3 utils/plugins/generate-domain-model/build.py --agent claude-code --output /tmp/domain-model-claude
```

生成だけでは導入・有効化されません。Python 3.9以上、Mermaid CLIとブラウザーは利用環境に必要です。導入方法・検証範囲・配布物は[公開ガイド](../../../docs/plugins/generate-domain-model.md)を参照してください。
