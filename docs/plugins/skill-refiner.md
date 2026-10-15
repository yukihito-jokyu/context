---
title: skill-refiner plugin
sidebar_label: skill-refiner
---

# skill-refiner plugin

[skill-refiner Skill](../skills/authoring/skill-refiner.md)と工程検査用hooksをまとめたpluginです。対象スキルの成果物を人間が確認し、評価基準の合意、独立評価、改善へ進む際に、チケット・工程・新規エージェントIDなどを検査します。

## 渡す情報

対象スキルを1つ、そのスキルで実行する題材を1つ以上用意します。Python 3.10以降と、サブエージェントを利用できるAgentが必要です。配布物はCodex用とClaude Code用を生成できます。生成形式の対応と、個々のクライアントでhooksが動くことは別に確認します。

## 依頼例

```text
skill-refinerでunknownsを改善してください。
題材は「設計前に決める必要がある未確定事項を整理する」です。
成果物を見てから評価基準を決めたいです。
```

## 進め方

1. [導入を始める](getting-started.md)の手順で、対象Agent用の配布物を生成し、Agentでの読み込みを確認します。
2. 対象スキルと題材を伝えます。入力確認と承認はSkillのHTML画面で進めます。
3. 作業領域の設定後、hooksは対象作業の起動チケットと工程を検査し、起動後のIDを記録します。詳しい紐付け方法は[hooksの正本](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/authoring/skill-refiner/references/hooks.md)を確認します。
4. 制作・評価・改善の結果を確認し、承認した候補を正本へ反映します。

hooksはすべての操作経路の隔離や承認者認証を保証するものではありません。実際のAgentで、許可される操作と拒否される操作を確認してください。

## 成果物の例

サブエージェントが正本のビルド処理を実行し、次の配布物を新しく生成しました。ZIPを展開して、manifest・hooks設定とSkillの全ファイルが正本と一致することを検証しています。

- [Codex用ZIP](pathname:///plugins/skill-refiner/skill-refiner-codex.zip#download)
- [Claude Code用ZIP](pathname:///plugins/skill-refiner/skill-refiner-claude-code.zip#download)
- [実行入力](pathname:///plugins/skill-refiner/input.md#download)、[検証結果](pathname:///plugins/skill-refiner/verification.txt#download)、[実行記録](pathname:///plugins/skill-refiner/execution.json#download)

この例の到達点は配布物の生成と内容検証です。インストール・有効化・実クライアント上でのhooksの制止は未実施です。Skill自身を使った改善作業の例は[Skillガイド](../skills/authoring/skill-refiner.md#成果物の例)にあります。

## 確認するポイント

- 対象Agent向けのmanifestとhooks設定を選んでいるか。
- 対象スキルと題材、作業領域を確認できるか。
- 制作と評価が別の新規エージェントで実行され、人間の承認を挟んでいるか。
- 対象クライアントでhooksが実際に呼ばれ、想定した操作を拒否できるか。

## 正本を読む

[plugin定義・ビルド処理](https://github.com/yukihito-jokyu/context/tree/main/utils/plugins/skill-refiner)と[Skill正本](https://github.com/yukihito-jokyu/context/tree/main/utils/skills/authoring/skill-refiner)で管理します。共通の配置方針は[配布・導入ガイド](distribution.md)を参照してください。
