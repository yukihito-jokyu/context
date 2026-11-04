# write-commit-message の調査

スキルが前提にする事実（ツールのバージョン、コマンドの引数、入出力の形式、公式の書き方）を、出典付きで記録する。記憶で書かない。「確認の状態」が「未確認」の項目が残っている間は、`skill_lint.py --final` が通らない。

## git diff --cached が返す範囲

- 確認方法：`git diff --help`（git 2.50.1、2026-10-26 に確認）。「This form is to view the changes you staged for the next commit relative to the named <commit>」「--staged is a synonym of --cached」とある
- 確認の状態：確認済み
- 分かったこと：`--cached` はステージ済みの変更だけを返し、未ステージの変更を含まない。HEAD が無いリポジトリでも、ステージ済みの変更をすべて返す
- 使ったルール：IN-01、IN-02、STEP-03

## コミットメッセージの1行目と2行目

- 確認方法：`git help commit` の DISCUSSION 節（git 2.50.1、2026-10-26 に確認）。「a single short (no more than 50 characters) line summarizing the change, followed by a blank line」とある
- 確認の状態：確認済み
- 分かったこと：1行目は50文字以内の要約、2行目は空行、その後に詳しい説明を書く。最初の空行までが題名として扱われる
- 使ったルール：OUT-02、OUT-05

## プロジェクトのコミットメッセージの決まり

- 確認方法：プロジェクトの `CLAUDE.md` の「コミットメッセージ」の節を読んだ（2026-10-26）
- 確認の状態：確認済み
- 決まり：`CLAUDE.md` の「コミットメッセージ」の節。「1行目は `<チケットID> <日本語の要約>` の形にする」「Conventional Commits の接頭辞（`feat:` など）は付けない」「行末に句点を付けない」とある
- 分かったこと：1行目の形、接頭辞を付けないこと、日本語で書くこと、行末に句点を付けないことが、プロジェクトの決まりとして書いてある。既存のコミットを数える必要は無い
- 使ったルール：OUT-02、OUT-03

## GitHub Actions の実行を止めるコミットメッセージの記法

- 確認方法：[Skipping workflow runs](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/skipping-workflow-runs)（GitHub Docs、2026-10-26 に確認）
- 確認の状態：確認済み
- 分かったこと：コミットメッセージに `[skip ci]`、`[ci skip]`、`[no ci]`、`[skip actions]`、`[actions skip]` のどれかがあると、`push` と `pull_request` のワークフローが実行されない。メッセージの最後に、空行を2つ挟んで `skip-checks:true` か `skip-checks: true` の trailer を書いても止まる
- 使ったルール：OUT-06
