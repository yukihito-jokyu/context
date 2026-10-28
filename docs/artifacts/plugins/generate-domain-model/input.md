# 実際のビルド・検証依頼

Issue #86のgenerate-domain-model pluginについて、新規サブエージェントとして公開用の配布物を実際に作成・検証する。

- 担当する公開先は `docs/artifacts/plugins/generate-domain-model/` だけとし、既存の対象成果物があれば全削除して再作成する。他の成果物、正本、ガイドは変更しない。
- `utils/plugins/generate-domain-model/` のREADME、bundle.json、build.py、Agent別manifest/hooksと、同梱する `utils/skills/design/generate-domain-model/` のSKILL.md・必要なruntimeを読む。正本はready・sealedであり、変更しない。
- `/private/tmp/context-model-plugin-refresh/generate-domain-model` でbuild.pyを `--agent codex` と `--agent claude-code` で実行し、`generate-domain-model-codex.zip` と `generate-domain-model-claude-code.zip` を保存する。
- ZIPを実際に展開し、全ファイル一覧とバイト列を正本のSkill全体、Agent別manifest/hooksと照合する。assets/seal.jsonの封印も検査する。
- 各ZIPに含まれるhooks.jsonから4イベントのcommandを読み、PLUGIN_ROOTまたはCLAUDE_PLUGIN_ROOTを展開して、使い捨てgitプロジェクトにJSONを標準入力で渡して直接実行する。無効時、実行中の出力検査、保護ファイルと実行記録の編集制御、finish前のStop差し戻し、waitとpromptによる再開を確かめる。
- 有効な出力を検査するケースでは、同梱の封印済みサンプルをコピーして再検査する。Mermaid CLIによる新規描画やPNG・HTMLの目視確認はこのplugin配布物検証では行わない。runtime・検査・封印のバイパスや緩和はしない。
- ユーザーホームや実repoにはインストール・有効化しない。投稿・PR・commitは行わない。依存追加と外部ネットワークアクセスも行わない。
- 直接hook実行の検証と、実クライアントへの導入・有効化・クライアントが呼び出すhooksの実動作を区別し、後者は未検証と記録する。
- `scripts/example-skill-source.cjs` の `sourceManifest` で実行前後の正本ファイル一覧とSHA-256を取得し、不変を確かめる。input.md、verification.txt、ZIPとexecution.jsonを保存し、execution.json以外の全成果物をfile/sha256で登録する。source_baselineは使わない。
