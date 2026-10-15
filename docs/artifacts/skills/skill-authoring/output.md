sample専用の `sample-release-check` を新規作成し、カタログとプロジェクトの入口を整えました。

sample固有のリリース前確認なので、配置先は `projects/sample/skills/sample-release-check/SKILL.md` です。単一Skillでhooksが不要なため、配布単位はSkill単体と判断しました。既存の検証用構成にはSkillがなく、流用・更新する対象はありませんでした。提示されたプロンプトを本文にしたため、grill-skillによる要件定義は行っていません。

実際に作成したファイルは [sample/](sample/) に保存しました。

- [SKILL.md](sample/projects/sample/skills/sample-release-check/SKILL.md): 差分と確認記録から、利用者への影響・検証結果・残課題を整理する手順。
- [スキル群README](sample/projects/sample/skills/README.md): 用途と正本への相対リンク。
- [ルートREADME](sample/README.md): プロジェクトの説明と、架空と明示したGitHub URL。

ファイル作成、frontmatterの名前、カタログの相対リンク、プロジェクト固有配置を確認しました。成果物一式は [bundle.zip](bundle.zip) で取得できます。共通Skill更新ではないため、この題材内部で公開例の再作成を再帰的に実行する対象はありません。配布物生成・インストール・Skillの実運用は未実施です。作成内容の人間による確認は未実施です。
