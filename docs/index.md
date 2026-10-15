---
slug: /
title: Skill・plugin活用ガイド
sidebar_label: このガイドについて
sidebar_position: 1
---

# Skill・plugin活用ガイド

このリポジトリで管理するSkillとpluginを選び、導入し、成果物を確認するためのガイドです。

SkillはAIエージェントが作業を進めるための指示書と同梱資料です。pluginはSkillとhooksなどをまとめた導入単位です。作業の頼み方はSkillのページ、導入とhooksの設定はpluginのページで確認できます。

| したいこと | 読み始める場所 |
| --- | --- |
| 目的に合うSkillを選ぶ | [Skill一覧](skills/index.md) |
| Skill単体を導入して依頼する | [Skillを初めて使う](skills/getting-started.md) |
| 複数のSkillをつなぐ | [ワークフロー](skills/workflows.md) |
| hooksを含むpluginを選ぶ | [Plugin一覧](plugins/index.md) |
| pluginの配布物を生成し、導入を確認する | [Pluginの導入を始める](plugins/getting-started.md) |

個別ページには、実際の入力・出力と確認結果を掲載しています。確認待ちの例もあるため、完成したかどうかは各例の到達点を見て判断してください。原本と検証記録はSkillとpluginで分けて保存しています。

詳しい実行手順は `utils/skills/`、pluginの配布定義と固有処理は `utils/plugins/` が正本です。管理・配布の関係は[配布・導入ガイド](plugins/distribution.md)で説明しています。
