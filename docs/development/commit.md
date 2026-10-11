---
title: commit — 変更を小さな単位でコミットする
sidebar_label: commit
---

# commit

実装や文書更新が済み、差分を履歴へ残したいときに使います。関連の近いファイルを確認し、小さな粒度でコミットします。

## 渡す情報

対象の差分、Issue番号、含める変更の範囲を渡します。

## 依頼例

```text
commitを使って、今回の担当者フィルターの変更をコミットしてください。Issue #123に対応します。別作業の差分は含めず、関連が分かる粒度にしてください。
```

## 進め方

1. 作業差分とコミット対象を確認します。
2. リポジトリのテンプレートに沿う日本語メッセージを作ります。
3. 関連する変更をステージングしてコミットし、残る差分を確認します。

## 成果物の例

専用サンプルリポジトリで実際に作成したコミットと差分です。context本体はコミットしていません。

**到達点：サンプル内のコミット作成済み・push未実施。**

### 実行した依頼

```text
隔離したcommit-demoの実差分を確認し、READMEの原本リンクと生成HTMLを小さい粒度でコミットしてください。contextの.commit-templateを参照し、日本語と末尾#57を使ってください。pushは行わないでください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# コミット実行結果

隔離したcommit-demoで、実差分を確認してREADMEとHTML原本を別コミットにした。context本体はコミットしていない。

```text
6f4802e 📚 生成した図のHTML原本を追加 #57
05a41f4 📚 実行成果物の原本リンクを追加 #57
```

日本語、テンプレートの絵文字、末尾の#57を使用した。pushは実施していない。実際の差分はchanges.patch。
````

### 成果物を取得する

- [実出力の全文（Markdown）](pathname:///examples/commit/output.md#download)
- [成果物・入力の一式（ZIP）](pathname:///examples/commit/bundle.zip#download)
- [実コミットの差分（patch）](pathname:///examples/commit/changes.patch#download)
- [実コミット一覧（text）](pathname:///examples/commit/commits.txt#download)
- [実行入力の原本](pathname:///examples/commit/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/commit/execution.json#download)

### 確認した結果

- READMEとHTML原本を別々の実コミットに保存。実SHAとchanges.patchを取得。

## 確認するポイント

絵文字などの形式は実際の.commit-templateに従います。意図しない差分が含まれていないか、日本語メッセージと判明しているIssue番号があるかを確認します。

## 関連するスキル

- [pr](../development/pr.md)：コミットをPRとして共有する。

## 正本を読む

詳細な手順と制約は[commitのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/development/commit/SKILL.md)を参照してください。
