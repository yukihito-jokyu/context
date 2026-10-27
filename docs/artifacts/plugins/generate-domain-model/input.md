# generate-domain-model plugin の公開配布物の再生成と検証

封印済みの `utils/skills/design/generate-domain-model/` と plugin 正本 `utils/plugins/generate-domain-model/` から、Codex 用と Claude Code 用の配布物を別々の隔離先へ新規生成する。既存成果物は使わない。

次を実行して確認する。

- `build.py --agent codex` と `build.py --agent claude-code` を実行し、選択した manifest・hooks・plugin scripts・Skill 全体を正本とバイト比較する。
- manifest と4種類の hook の登録、既存の出力先の拒否、ZIP 展開後の全ファイルの一致を確認する。
- 隔離したテスト用プロジェクトで、パッケージの hooks.json に書かれた command をそのまま起動する。
- inactive の Stop が出力も変更も生じないことを確認する。
- 同梱した `run.py start` の成功後、`skip_validation` を持つ model.json を PostToolUse が OUT-07 で block することを確認する。
- active の PreToolUse が、封印済み SKILL.md の編集要求に Claude Code では ask、Codex では deny を返すことを確認する。編集要求の event を渡すだけで、保護ファイル自体は変更しない。

実ユーザー環境へのインストール、有効化、外部投稿はしない。Agent クライアントの CLI は起動せず、Python と git の CLI を使う。`PYTHONDONTWRITEBYTECODE=1`、隔離した XDG_CONFIG_HOME、`GIT_CONFIG_GLOBAL=/dev/null`、`GIT_CONFIG_NOSYSTEM=1` によりキャッシュ作成とホームの git 設定の影響を避ける。検査用コードと実行場所は /private/tmp に限定する。
