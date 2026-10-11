---
title: explain-html
---

# explain-html

一つの事象・事柄を、全体像から具体例、詳細、条件と例外まで理解できるHTMLへまとめます。技術・業務・制度・自然現象など、題材の分野を限定しません。

## 依頼例

```text
explain-htmlで、この仕組みを初めて学ぶ読者向けに解説HTMLを作ってください。
全体像と一回の具体例から、詳細・成立条件・例外までつなげて説明してください。
図から対応するコードや記録へ移動でき、根拠と確認範囲も確かめられる形にしてください。
```

## 進め方

1. 題材、読者、理解したいこと、資料と確認範囲を確かめます。
2. 一次資料から項目を洗い出し、前提から具体例・詳細へ進む順序を決めます。
3. 関心別ページと全体図を作り、図と具体物を対応させます。コードのない題材には書類・記録・式・観測値などを使います。
4. 時間順や受け渡しを追う場合は段階再生を加え、出典照合、構造・意味・実表示をそれぞれ確認します。

似た対象の違いを中心に理解したい場合は[compare](compare.md)を使います。explain-htmlはcompareの表示・説明品質を引き継ぎ、単一題材を扱います。

実例は[技術題材のHTMLを開く](pathname:///examples/explain-html/technical/output.html)と[一般題材のHTMLを開く](pathname:///examples/explain-html/general/output.html)から直接確認できます。

## 成果物の例

スキルを実際に適用し、入力検査の技術題材と、会員証・貸出記録を扱う一般題材の解説HTMLを作成しました。資料は保存した架空仕様・制度であり、実在製品や実在制度の説明ではありません。

**到達点：2題材のHTML生成・構造と実ブラウザ操作確認済み。人間による成果物確認待ち。**

### 実行した依頼

```text
explain-htmlを使い、次の二つの題材で比較相手を置かない解説HTMLを作成してください。架空の仕様・制度であることを明記し、各題材の全項目を説明してください。

## 技術題材

説明用の架空仕様として、runnerはbefore(input)を同期実行し、falseならrun(input)を呼ばずblockedを返し、trueならrunが入力targetを返します。config.jsonのbeforeFileが検査関数を指定します。入力はtarget:sample.txt,allowed:true/falseです。この仕組みを初学者向けの解説HTMLにし、全体像、値の流れ、実行できる最小コード、停止と成功、設定まで説明してください。

## 一般題材

以下の架空の貸出制度を初めて利用する読者向けにHTMLで説明してください。利用者は会員証と本を窓口へ持参します。職員は会員証の有効性を確認し、無効なら貸出せず手続きを終了します。有効なら職員は貸出日から14日後を返却期限として貸出記録を作成し、本を利用者へ渡します。利用者は期限までに窓口へ返却します。期限を過ぎた貸出記録がある間は新規貸出ができず、返却すると職員が記録を閉じます。比較相手やコードを足さず、全体像、具体例、書類、条件と例外、資料の対応を説明してください。
```

### 実際の画面

![生成した単一題材の解説HTML：入力検査の全体像](/examples/explain-html/preview.png)

[画像を原寸で開く](pathname:///examples/explain-html/preview.png)

一般題材のHTMLも、下記の2題材一式から取得できます。

### 成果物を取得する

- [2題材のHTML・原文・モデル・検証記録（ZIP）](pathname:///examples/explain-html/bundle.zip#download)
- [単独導入できるexplain-htmlスキル一式（ZIP）](pathname:///examples/explain-html/skill.zip#download)
- [Chromeでの操作・表示検証結果（JSON）](pathname:///examples/explain-html/browser-validation.json#download)
- [原文と本文・図・具体物の読み合わせ記録（Markdown）](pathname:///examples/explain-html/semantic-review.md#download)
- [実際のHTMLをブラウザで開く](pathname:///examples/explain-html/technical/output.html)
- [実行入力の原本](pathname:///examples/explain-html/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/explain-html/execution.json#download)

### 確認した結果

- 技術題材と一般題材で各5ページ・全体図を生成。10図のshowcase検証9項目、deliver、標準SVG補助エクスポートが成功。
- 全体図チェックは各5ページ・5図、項目対応チェックは技術7項目、一般8項目で成功。原文・本文・図・具体物を別工程で読み合わせ。
- 技術実装をNode.jsで実行し、allowed:trueはsample.txt、allowed:falseはblockedと確認。
- Chromeで1440pxと390pxの全10ページを表示して横はみ出し・画像読み込みを測定。深いリンク、details展開、履歴、有限再生、二重開始、一時停止と再開、段階選択、全体表示、ページ移動時の停止、連続移動、図の拡大、reduced-motion、ダークOS下のライト配色、印刷、JavaScript無効時が成功。
- 単体スキルZIPをリポジトリ外で展開し、依存検査とHTML組み立てが成功。生成HTMLは元とバイト一致。
- npm run build、typecheck、test:docs（4件）、test:search（4件）、examples:checkが成功。
- 保存した画面を同一エージェントが目視確認。生成ベンチマーク・トリガー精度・第三者レビュー・ブラウザPNGエクスポートの画素一致は未検証。

## 確認するポイント

- 各ページの全体図から、具体例・コード・書類・条件の説明へ進めるか。
- 概要だけで終わらず、資料の各項目、成立条件と例外まで説明されているか。
- 本文、図、具体物で主体・順序・値・結果が一致するか。
- 未確認の情報、説明用の仮定、ブラウザ未検証の範囲が明記されているか。

## 正本を読む

[explain-htmlのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/explain-html/SKILL.md)
