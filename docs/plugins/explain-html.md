---
title: explain-html plugin
sidebar_label: explain-html
---

# explain-html plugin

[explain-html Skill](../skills/discovery/explain-html.md)と、Archifyによる図の完了検査を呼ぶClaude Code用Stop hookをまとめたpluginです。解説HTMLに掲載する図について、モデル・配布HTML・標準SVG・記事画像の一致を検査します。

## 渡す情報

解説したい題材と保存先を用意します。完成検査の対象には、図の担当・成果物を記録したmanifestと記事HTMLが必要です。配布物の生成にはPython 3、検査にはSkill正本に記載されたPython・Node.jsの実行環境を使います。Codex用hook adapterは未提供です。

## 依頼例

```text
explain-htmlで、HTTPリクエストがサーバーに届くまでの仕組みを解説してください。
通信の流れを図で示し、完成時に図と記事の検査結果を確認したいです。
```

## 進め方

1. [導入を始める](getting-started.md)の手順でClaude Code用配布物を生成し、Agentでの読み込みを確認します。
2. 題材を伝え、Skillの手順で記事と図を制作します。
3. 対象プロジェクトの`.explain-html-active.json`に、manifestと記事HTMLの相対パスを指定します。具体例は[Archifyゲートの正本](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/explain-html/references/archify-gate.md)を参照します。未紐付けのプロジェクトにはhookは介入しません。
4. 完成時は生成CLIの検査とStop hookの結果を確認します。Claude Codeには連続blockの上限があるため、hookと生成CLIを併用します。

## 成果物の例

サブエージェントが正本のビルド処理から[Claude Code用ZIP](pathname:///plugins/explain-html/explain-html-claude-code.zip#download)を生成しました。ZIPを展開し、manifest・hooks設定とSkillの全ファイルが正本と一致することを検証しています。

[実行入力](pathname:///plugins/explain-html/input.md#download)、[検証結果](pathname:///plugins/explain-html/verification.txt#download)、[実行記録](pathname:///plugins/explain-html/execution.json#download)を確認できます。

この例は配布物の生成と内容検証までです。インストール・有効化・実クライアント上のStop hook動作は未実施です。解説HTML自身の例は[Skillガイド](../skills/discovery/explain-html.md#成果物の例)を参照してください。

## 確認するポイント

- Claude Code用の配布物を選んでいるか。
- 対象プロジェクトと、検査するmanifest・記事HTMLの紐付けが正しいか。
- 図の一致検査と、文章や図の意味・読みやすさの確認を区別しているか。
- CLIによる完成検査に加え、利用環境でStop hookが呼ばれることを確認したか。

## 正本を読む

[plugin定義・ビルド処理](https://github.com/yukihito-jokyu/context/tree/main/utils/plugins/explain-html)と[Skill正本](https://github.com/yukihito-jokyu/context/tree/main/utils/skills/discovery/explain-html)で管理します。共通の配置方針は[配布・導入ガイド](distribution.md)を参照してください。
