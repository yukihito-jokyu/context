---
title: skill-authoring — 正本とカタログを整えて配置する
sidebar_label: skill-authoring
---

# skill-authoring

スキルを共通／プロジェクト固有へ配置し、READMEカタログと正本の関係を保ちたいときに使います。内容の変更と配置の変更を区別して扱います。

## 渡す情報

対象スキル、作成・改善・配置のどれを行うか、再利用範囲、許可する変更を渡します。

## 依頼例

```text
skill-authoringを使って、完成した調査スキルを共通スキルとして配置してください。内容は変更せず、分類とREADMEカタログを整備してください。
```

## 進め方

1. 既存スキルとの重複や流用可能性を確認します。
2. 再利用範囲から配置先を決め、依頼範囲に応じてSkill単体とpluginの配布単位を判定します。許可された範囲だけを変更します。
3. 対応するREADMEを更新し、正本と案内の関係を確認します。

複数Skillのパッケージ化やhooksの同梱を扱う場合は、[Skillとpluginの配布・導入](../../plugins/distribution.md)に沿って正本と配布定義を分けます。情報整理の依頼では、構造と導入方法の記録までを行います。

## 成果物の例

更新後のskill-authoringを実行し、独立した検証用構成にプロジェクト専用SkillとREADMEを実際に作成しました。

**到達点：プロジェクト専用Skill作成済み・配布と人間の確認は未実施。**

### 実行した依頼

```text
# 入力

skill-authoringを使い、独立した検証用ディレクトリにsample専用のSkillを追加してください。既存のREADMEと配置を調べてから、新しいSKILL.mdとカタログを作成してください。

対象: /private/tmp/issue79-skill-authoring-sample（公開サイトを持たない、架空のsampleプロジェクト専用の検証用構成）。共通Skill追加ではありません。

以下のプロンプトを本文として使ってください。

「sampleのリリース前に、指定された変更差分と検証記録を読み取り、利用者への変更、成功・失敗・未実施の確認、残課題を短く整理する。コミット、タグ、push、公開は行わない。公開可否は人間が判断する。秘密情報は引用しない。」

単一Skillでhooks不要です。題材のGitHub URLは https://github.com/example/sample （架空の配置例）です。grill-skillは起動しません。Context本体のSkill追加・配布・インストールは対象外です。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
sample専用の `sample-release-check` を新規作成し、カタログとプロジェクトの入口を整えました。

sample固有のリリース前確認なので、配置先は `projects/sample/skills/sample-release-check/SKILL.md` です。単一Skillでhooksが不要なため、配布単位はSkill単体と判断しました。既存の検証用構成にはSkillがなく、流用・更新する対象はありませんでした。提示されたプロンプトを本文にしたため、grill-skillによる要件定義は行っていません。

実際に作成したファイルは [sample/](sample/) に保存しました。

- [SKILL.md](sample/projects/sample/skills/sample-release-check/SKILL.md): 差分と確認記録から、利用者への影響・検証結果・残課題を整理する手順。
- [スキル群README](sample/projects/sample/skills/README.md): 用途と正本への相対リンク。
- [ルートREADME](sample/README.md): プロジェクトの説明と、架空と明示したGitHub URL。

ファイル作成、frontmatterの名前、カタログの相対リンク、プロジェクト固有配置を確認しました。成果物一式は [bundle.zip](bundle.zip) で取得できます。共通Skill更新ではないため、この題材内部で公開例の再作成を再帰的に実行する対象はありません。配布物生成・インストール・Skillの実運用は未実施です。作成内容の人間による確認は未実施です。
````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///skills/skill-authoring/output.md#download)
- [作成したSkill・README・入力の一式（ZIP）](pathname:///skills/skill-authoring/bundle.zip#download)
- [確認結果（text）](pathname:///skills/skill-authoring/verification.txt#download)
- [実行入力の原本](pathname:///skills/skill-authoring/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/skill-authoring/execution.json#download)

### 確認した結果

- 既存構成・カタログを読み、プロジェクト固有配置とSkill単体の配布単位を判断。
- SKILL.md・READMEを実際に作成し、存在・名前・リンク・配置を確認。

## 確認するポイント

Context Repositoryの共通Skillを追加・更新した場合は、本文や同梱資料に対応する成果物がサブエージェントで作り直されているかも確認します。古い成果物は全削除し、入力・実出力・検証記録を保存します。具体的な手順は[成果物の再作成](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/authoring/skill-authoring/references/docs-examples.md)を参照してください。

配置が用途と再利用性に合うか、同名候補がないか、内容変更の許可範囲を守ったかを確認します。READMEは要約、SKILL.mdは正本です。

## 関連するスキル

- [my-skill-creator](../authoring/my-skill-creator.md)：内容の作成・検証を行う。

## 正本を読む

詳細な手順と制約は[skill-authoringのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/authoring/skill-authoring/SKILL.md)を参照してください。
