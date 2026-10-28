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

公開ガイドの読者が実行例の画面を確認して原本を取得する流れを、新しいモデルから実際に生成したシーケンス図。

**到達点：新規モデルのCLI生成・検証・Chrome表示検査・1440×900ライト画像の目視確認済み。**

### 実行した依頼

```text
読者がスキル実行例を開き、実画面画像を確認してHTML・文章・ZIPの原本を取得する流れをシーケンス図にしてください。日本語の単体HTMLを生成し検証してください。
```

### 実際の画面

![新しく生成したシーケンス図を1440×900で開いた実画面](/skills/archify-jp/preview.png)

[画像を原寸で開く](pathname:///skills/archify-jp/preview.png)

### 成果物を取得する

- [生成した原本（HTML）](pathname:///skills/archify-jp/output.html#download)
- [新規作成した生成モデル（JSON）](pathname:///skills/archify-jp/input.json#download)
- [ブラウザ検証結果（環境情報をマスク）](pathname:///skills/archify-jp/browser-validation.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/archify-jp/output.html)
- [実行入力の原本](pathname:///skills/archify-jp/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/archify-jp/execution.json#download)

### 確認した結果

- validate / deliver が成功。showcase の9項目、エラー0、警告0。
- Chrome visual-check が1440×900・2048×1320の各ライト/ダークで成功。
- 1440×900ライト画像で主体・5通信・原本の取得順序・表示範囲を目視確認。その他の画像の目視とエクスポート操作は未実施。
- 公開ログから実ユーザーのホームパスと詳細な実行環境版を伏せ、作業ディレクトリを<workdir>へ置換。環境マスク後に成果物SHAを記録。利用者承認は要求も実施もしていない。

## 確認するポイント

原本を開き、図の主体・順序・分岐が入力と一致するか、文字が読めるか、エクスポートが動くかを確認します。生成検証、ブラウザ検査、目視確認の範囲は実行記録で区別します。

## 関連するスキル

- [compare](../discovery/compare.md)：二つの仕組みを比較する。

## 正本を読む

ライフサイクル図は、注文やセッションなど同じ対象の生涯を追うために使います。新規入力ではschema v2を選び、対象と観測範囲、開始・終了、状態・フェーズ・イベント・活動の種類を明示します。状態の変化、処理の順序、関連付けは別の関係として記述し、配置から実行順序を推測させません。部分の完了、反復、並行性は必要な範囲で説明します。既存v1の固定配置は維持されます。

記述方法は[ライフサイクルの記述ルール](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/references/lifecycle.md)、適用例は[注文](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/artifacts/skills/order.lifecycle.json)、[React Effect](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/artifacts/skills/react-effect.lifecycle.json)、[Claude Code Hooks](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/artifacts/skills/claude-hooks.lifecycle.json)を参照してください。ReactやClaude Codeの例は省略範囲を明示した説明用のモデルで、製品固有の書き方を一般ルールとして強制しません。

詳細な手順と制約は[archify-jpのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/design/archify-jp/SKILL.md)を参照してください。
