# skill-refiner plugin

このpluginのビルド処理は[build.py](build.py)に配置します。工程を検査するhooksと、正本のskill-refinerをコピーして配布物を作成します。インストールや有効化は行いません。

リポジトリのルートで実行します。

```sh
python3 utils/plugins/skill-refiner/build.py --agent codex --output /tmp/skill-refiner-codex
python3 utils/plugins/skill-refiner/build.py --agent claude-code --output /tmp/skill-refiner-claude
```

全プロジェクト共通の処理はルートのscripts、plugin専用のビルドはplugin直下、実行時のhook処理はpluginのscriptsに置きます。
