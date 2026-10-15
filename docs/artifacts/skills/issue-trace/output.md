Issue #79の対応範囲は、Skillとpluginのガイド・成果物を分け、Skill更新後の成果物をサブエージェントで作り直す運用を整えることです。今回は承認済み計画の調査まで進めました。

[Issue本文](https://github.com/yukihito-jokyu/context/issues/79)は空ですが、[計画コメント](https://github.com/yukihito-jokyu/context/issues/79#issuecomment-6194863317)に要件と完了条件があります。

> スキルとpluginの利用ガイド・導入案内・成果物を分ける。

計画が定める対応は次の5点です。

1. ガイドを `docs/skills/`・`docs/plugins/`、成果物を `docs/artifacts/skills/`・`docs/artifacts/plugins/` に分ける。
2. 既存の6分類・26スキルを移し、リンク・検索・ダウンロード・検証処理を合わせる。
3. Skill単体とpluginの導入案内を整え、skill-refiner・explain-htmlの用途、対応Agent、生成・導入、hooks、公開状況を説明する。
4. 本文と同梱資料の変更、古い成果物、記録外ファイルを検出し、更新時は該当成果物を全削除して再実行する。
5. 型検査・検索テスト・成果物検査・本番ビルド・サイトテストで確認する。

同じコメントの承認根拠には、会話内のユーザー発言「計画をissueに登録して対応してください」が記録されています。計画を再承認する段階ではありません。この調査依頼自体には投稿許可がないため、追加コメントは投稿していません。

[AGENTS.md](https://github.com/yukihito-jokyu/context/blob/main/AGENTS.md)のローカル作業中の内容も読み、正本を集約する方針と、公開成果物をサブエージェントで再作成する今回の未コミット規則を確認しました。現在の作業ツリーの規則はmainの公開済み内容と同一とは断定していません。GitHubの関連PR検索 `gh pr list --state all --search 79` は0件でしたが、Issueに関連するすべてのコミットを網羅した確認ではありません。

残事項は、各完了条件に対する実装と検証結果の照合、および人間による成果物の確認です。今回は実装・テスト実行を依頼されていないため、Issue全体の完了や検証成功は判定していません。Issueとの実装上の相違は、実装全体を調べていないため未判定です。取得したIssue本文と計画コメントは [issue-source.json](issue-source.json) に保存しています。
