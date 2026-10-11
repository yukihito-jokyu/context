---
title: archify-jp — 構造や処理を探索可能な図にする
sidebar_label: archify-jp
---

# archify-jp

システム構成、処理順序、状態、データモデルを図で確認したいときに使います。図の仕様から検証済みの単体HTMLを作成します。

## 渡す情報

図の種類、伝えたい問い、構成要素と関係、コードや仕様の根拠、出力先を渡します。

## 依頼例

```text
archify-jpを使って、依頼登録の画面、API、DBの呼び出しをシーケンス図にしてください。根拠は登録ハンドラーとテーブル定義です。成功時と入力エラー時の違いを確認したいです。
```

## 進め方

1. 問いに合う図の種類を選び、仕様を組み立てます。
2. 検証とプレビューで構造・ラベル・レイアウトの診断を確認します。
3. 最終成果物を確定し、実ブラウザで確認した表示範囲とレシートを示します。

## 成果物の例

実際にarchify-jpのCLIで生成したシーケンス図です。

**到達点：単体HTML生成・CLI検証・画像確認済み。**

### 実行した依頼

```text
読者がスキル実行例を開き、実画面画像を確認してHTML・文章・ZIPの原本を取得する流れをシーケンス図にしてください。日本語の単体HTMLを生成し検証してください。
```

### 実際の画面

![生成したシーケンス図を1440×900で開いた実画面](/examples/archify-jp/preview.png)

[画像を原寸で開く](pathname:///examples/archify-jp/preview.png)

### 成果物を取得する

- [生成した原本（HTML）](pathname:///examples/archify-jp/output.html#download)
- [生成に使った入力（JSON）](pathname:///examples/archify-jp/input.json#download)
- [ブラウザ検証結果（環境パスを伏せたJSON）](pathname:///examples/archify-jp/browser-validation.json#download)
- [実際のHTMLをブラウザで開く](pathname:///examples/archify-jp/output.html)
- [実行入力の原本](pathname:///examples/archify-jp/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/archify-jp/execution.json#download)

### 確認した結果

- validate / deliverが終了コード0。showcaseの9項目、エラー0、警告0。
- visual-checkで1440×900、1600×1000、1920×1080、2048×1320のlight/dark包含検査が成功。
- 1440×900と2048×1320のlight画像を目視確認。検査JSONのvisualReviewは自動処理ではpendingのまま保持。

## 確認するポイント

原本を開き、図の主体・順序・分岐が入力と一致するか、文字が読めるか、エクスポートが動くかを確認します。生成検証、ブラウザ検査、目視確認の範囲は実行記録で区別します。

## 関連するスキル

- [compare](../discovery/compare.md)：二つの仕組みを比較する。

## 正本を読む

ライフサイクル図は、注文やセッションなど同じ対象の生涯を追うために使います。新規入力ではschema v2を選び、対象と観測範囲、開始・終了、状態・フェーズ・イベント・活動の種類を明示します。状態の変化、処理の順序、関連付けは別の関係として記述し、配置から実行順序を推測させません。部分の完了、反復、並行性は必要な範囲で説明します。既存v1の固定配置は維持されます。

記述方法は[ライフサイクルの記述ルール](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/references/lifecycle.md)、適用例は[注文](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/examples/order.lifecycle.json)、[React Effect](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/examples/react-effect.lifecycle.json)、[Claude Code Hooks](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/examples/claude-hooks.lifecycle.json)を参照してください。ReactやClaude Codeの例は省略範囲を明示した説明用のモデルで、製品固有の書き方を一般ルールとして強制しません。

詳細な手順と制約は[archify-jpのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/SKILL.md)を参照してください。
