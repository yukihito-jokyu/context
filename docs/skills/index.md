---
slug: /skills/
title: スキル活用ガイド
sidebar_label: このガイドについて
sidebar_position: 1
---

# スキル活用ガイド

AIエージェントに作業を頼むとき、目的に合うスキルを選び、必要な情報を渡し、成果物を確認するためのガイドです。スキルは、調査や計画などの進め方を定めた指示書です。

初めて利用する方は[初めて使う](getting-started.md)から、複数のスキルをつなぐ場合は[ワークフロー](workflows.md)から読み進めてください。各スキルのページには、依頼例、進め方、成果物の例、確認するポイントを掲載しています。

## 目的から選ぶ

| 今やりたいこと | 分類 | 最初の候補 |
| --- | --- | --- |
| 不明点を整理し、調べる方向を決める | [調査・理解](discovery/index.md) | [unknowns](discovery/unknowns.md) |
| 調査を着手可能な計画やIssueへ変える | [計画・Issue分割](planning/index.md) | [plan](planning/plan.md) |
| 画面を見ながら要件を固める、図で構造を伝える | [画面要件・図](design/index.md) | [HTML要件すり合わせ](design/html-requirements-workshop.md) |
| 差分をレビューし、コミットやPRを作る | [コミット・PR・レビュー](development/index.md) | [self-review-html](development/self-review-html.md) |
| 判断と作業の根拠を残し、他者へ説明する | [記録・説明](documentation/index.md) | [notes](documentation/notes.md) |
| スキルを作成・改善し、カタログに配置する | [スキル作成・管理](authoring/index.md) | [my-skill-creator](authoring/my-skill-creator.md) |

## ガイドと正本の関係

分類とスキル名は、リポジトリの[共通スキル一覧](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/README.md)に合わせています。各スキルの詳しい手順は`utils/skills/`配下の`SKILL.md`が正本です。

各ページの成果物例は、正本を実際に適用して得た出力です。入力、到達点、検証結果を添え、文章の全文、実画面の画像、HTMLやZIPの原本を取得できます。対話や承認を伴うスキルでは、初回案・回答待ち・投稿前など、実際に進めた段階を明記しています。

ガイドを読んだ後は、各ページの「正本を読む」からエージェントが使う指示書を確認できます。ガイドだけを渡して詳細な手順を再現させず、実際の作業ではスキル本体と必要な同梱資料を利用してください。
