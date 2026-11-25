sample専用の `sample-release-check` を新規作成し、カタログとプロジェクトの入口を整えました。

sample固有のリリース前確認なので、配置先は `projects/sample/skills/sample-release-check/SKILL.md` です。単一Skillでhooksが不要なため、配布単位はSkill単体と判断しました。検証用構成には `AGENTS.md` とルート `README.md` だけがあり、既存のSkillやカタログはなかったため、流用・更新ではなく新規作成としました。提示されたプロンプトを本文にしたため、grill-skillによる要件定義は行っていません。

実際に作成・更新したファイルは [sample/](sample/) に保存しました。

- [SKILL.md](sample/projects/sample/skills/sample-release-check/SKILL.md): 変更差分と検証記録から、利用者への変更・確認結果・残課題を読み取りで整理する手順。新規作成。
- [スキル群README](sample/projects/sample/skills/README.md): 用途と正本への相対リンクを持つ要約カタログ。新規作成。
- [ルートREADME](sample/README.md): プロジェクトの説明に、カタログへのリンクと架空と明示したGitHub URLを追加。

ファイルの存在、frontmatterの名前、カタログとルートREADMEのリンク、プロジェクト固有配置を確認しました（[verification.txt](verification.txt)）。成果物一式は [bundle.zip](bundle.zip) で取得できます。共通Skill更新ではないため、この題材内部で公開成果物の再作成を実行する対象はありません。配布物生成・インストール・Skillの実運用は未実施です。作成内容の人間による確認は未実施です。
