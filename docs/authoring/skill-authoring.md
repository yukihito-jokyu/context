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
2. 再利用範囲から配置先を決め、許可された範囲だけを変更します。
3. 対応するREADMEを更新し、正本と案内の関係を確認します。

## 成果物の例

提供したサンプル用プロンプトから実際に作成したSKILL.mdと要約カタログです。配置判断も保存しました。

**到達点：隔離領域でのスキル・カタログ作成。**

### 実行した依頼

```text
次のプロンプトを隔離したauthoring-demoで共通スキルにし、カタログを整備してください。contextの正本は変更しないでください。

プロンプト：対象ページと実行成果物の原本を読み、本文の抜粋が原本に含まれること、画面画像が同じ原本から撮影されたこと、取得リンクが届くことを確認する。複数ファイルは参照関係を保ったZIPを使う。確認済みと未確認を分けてMarkdownで報告する。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# 配置先の判断結果

入力: 「提供する成果物リンク確認のプロンプトを、隔離したサンプル作業領域で共通スキルにし、カタログを整備する。contextの正本は変更しない。」

## 調査した正本とカタログ

utils/skills/README.md、docs/authoring/index.md、skill-authoring、my-skill-creator、agent-trace、issue-traceのSKILL.mdを読んだ。

## 既存スキルを更新するか

既存の証跡記録とスキル作成の責務は分かれている。サンプルでは提供したプロンプトの範囲を成果物リンク検査に限定し、新規SKILL.mdを作成した。contextの既存スキルの動作は変更していない。

## 配置判断

- 検査内容はDocusaurusの設定に限定されず、複数プロジェクトの成果物展示に再利用できるため共通スキルと判定した。
- サンプル領域のutils/skills/documentation/artifact-links/SKILL.mdへ配置した。
````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///examples/skill-authoring/output.md#download)
- [成果物・入力の一式（ZIP）](pathname:///examples/skill-authoring/bundle.zip#download)
- [作成したサンプルSKILL.md](pathname:///examples/skill-authoring/SKILL.md#download)
- [実行入力の原本](pathname:///examples/skill-authoring/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/skill-authoring/execution.json#download)

### 確認した結果

- サンプル領域のdocumentation/artifact-linksへ配置。READMEから正本を参照。
- contextのスキル正本や互換配置へは導入していません。

## 確認するポイント

配置が用途と再利用性に合うか、同名候補がないか、内容変更の許可範囲を守ったかを確認します。READMEは要約、SKILL.mdは正本です。

## 関連するスキル

- [my-skill-creator](../authoring/my-skill-creator.md)：内容の作成・検証を行う。

## 正本を読む

詳細な手順と制約は[skill-authoringのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/authoring/skill-authoring/SKILL.md)を参照してください。
