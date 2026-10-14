# explain-html plugin

正本Skillは`utils/skills/discovery/explain-html`です。このplugin定義はClaude CodeのStop hookからArchify必須ゲートを自動実行するためのものです。Skill正本を移動しません。

```sh
python3 utils/plugins/explain-html/build.py --output /tmp/explain-html-plugin
```

ビルド先は未作成かつリポジトリ外に指定します。ビルドは導入・信頼・有効化を行いません。対象プロジェクトの紐付け、テストの担保範囲、連続block上限とCLIゲートの併用は[正本の契約](../../skills/discovery/explain-html/references/archify-gate.md)を参照してください。Codex用hook adapterは未提供です。
