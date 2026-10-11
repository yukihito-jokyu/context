---
title: スキル作成・管理
---

# スキル作成・管理

スキルを作成・改善し、正本とカタログの関係を保って配置します。

| スキル | できること |
| --- | --- |
| [skill-authoring](skill-authoring.md) | 正本とカタログを整えて配置する |
| [my-skill-creator](my-skill-creator.md) | スキルを作成・改善して検証する |

組み合わせて使う場合は[ワークフロー](../workflows.md)を参照してください。各ページには入力と成果物の例を掲載しています。

## 配置・候補探索のルール

共通スキルは主な用途で分類し、最大2階層までの分類を使います。直下へ置く構成も許容します。現在の分類は[共通スキル一覧](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/README.md)で確認できます。

```text
utils/skills/<skill-name>/SKILL.md
utils/skills/<category>/<skill-name>/SKILL.md
utils/skills/<category>/<subcategory>/<skill-name>/SKILL.md
```

`SKILL.md`を直接持つディレクトリを一つの候補とし、候補名には末尾のスキル名だけを使います。分類名は小文字のkebab-caseにして、既存の分類を優先します。

探索でスキルを見つけたら、その配下の`vendor/`などを別候補として扱いません。同梱スキルはscripts・assets・referencesとともに親スキルの一部です。共通候補は分類をまたいで名前を一意にし、重複があれば全該当パスを示して配布を止めます。

プロジェクト固有スキルは`projects/<repo-name>/skills/<skill-name>/SKILL.md`へ配置します。同名の共通スキルよりプロジェクト側を優先しますが、共通側の重複エラーを隠してはいけません。

配布するときは分類階層を含めず、選んだスキルのディレクトリ全体を`.claude/skills/<skill-name>/`と`.codex/skills/<skill-name>/`へ同じ内容でコピーします。これは配置の考え方を示すもので、配布用CLIの実装済みを意味しません。
