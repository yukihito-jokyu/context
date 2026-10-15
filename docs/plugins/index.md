---
title: Plugins
sidebar_label: Plugins
---

# Plugins

pluginは、作業手順であるSkillと、その工程を検査するhooksをまとめた配布物です。Skillだけを使いたい場合は[Skills](../skills/index.md)、hooksも含めて使いたい場合はこの案内から選びます。

| plugin | できること | 生成できる形式 |
| --- | --- | --- |
| [skill-refiner](skill-refiner.md) | スキルの独立実行・評価・改善工程をhooksで検査する | Codex、Claude Code |
| [explain-html](explain-html.md) | 解説HTMLのArchify完了検査をStop hookから呼ぶ | Claude Code |

まず[導入を始める](getting-started.md)で、生成と導入の違いを確認してください。現在、このリポジトリにはpluginごとのローカル生成処理があります。公開marketplaceはまだありません。

配布物の配置・導入先・将来の公開方針は[Skillとpluginの配布・導入](distribution.md)にまとめています。各pluginのページには、実際に生成したZIPと検証記録を掲載しています。
