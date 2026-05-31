# cli

このディレクトリには、Go 製の `context` CLI 実装があります。

現時点では `context deploy` の初期実装があります。現在できることは以下です。

- `context deploy <repo-name>` で `projects/<repo-name>` を解決する
- `context deploy` で対話的に project を選択する
- `CONTEXT_REPO`、実行ファイル相対、カレントディレクトリ親探索で context repository ルートを解決する
- deploy 開始前のセッション情報を表示する
- `utils/skills/*` と `projects/<repo-name>/skills/*` から `SKILL.md` を持つ Skill を候補化する
- 同名 Skill は project 側を優先して 1 つの候補にまとめる
- 対話実行では選択した Skill を、非対話実行では候補化された全 Skill を `.claude/skills/<skill-name>/SKILL.md` と `.codex/skills/<skill-name>/SKILL.md` に配布する
- Skill 配布時に `README.md` を配布対象から除外する

まだ未実装の主な範囲は以下です。

- AGENTS.md の配布
- CLAUDE.md の生成と配布
- 既存配布物に対する上書き確認
- `deploy` 以外のコマンド
