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
3. 図ごとに読者の問いと型の採用理由を決め、概要から同じ具体例を追える詳細へ分けます。通信の往復、条件分岐、状態変化、変換などに合う図を使い、コードのない題材には書類・記録・式・観測値などを対応させます。初期表示は図全体とし、文字を読むための表示切替は標準で追加しません。
4. 時間順や受け渡しを追う場合は段階再生を加え、出典照合、構造・意味・実表示をそれぞれ確認します。

似た対象の違いを中心に理解したい場合は[compare](compare.md)を使います。explain-htmlはcompareの表示・説明品質を引き継ぎ、単一題材を扱います。

実例は[技術題材のHTMLを開く](pathname:///examples/explain-html/technical/output.html)と[一般題材のHTMLを開く](pathname:///examples/explain-html/general/output.html)から直接確認できます。

## 成果物の例

非同期API、備品貸出、水循環、CSV売上集計の4題材を独立したサブエージェントで生成しました。下の入力とHTMLは非同期APIの実出力で、他3題材の入力・HTML・モデル・検証記録はZIPに含みます。架空題材は説明用で、水循環はUSGS一次資料に基づきます。

**到達点：4題材のHTML生成・静的検証・独立内容レビューを実施。図の意味に不一致あり。ブラウザ表示・操作は未検証。**

### 実行した依頼

```text
次の架空APIを初めて使う開発者向けに、仕組みを理解できる単体HTMLを作ってください。利用者は画像変換を依頼します。クライアントは同じ依頼の再送では同じrequestKeyを使い、POST /jobsへ画像IDとrequestKeyを送ります。サーバーは初回にjob_17を作り202とjobIdを返し、同じrequestKeyの再送では重複ジョブを作らず同じjobIdを返します。ワーカーはqueuedのジョブをrunningへ移し、成功ならcompletedとresultUrl、失敗ならfailedとreasonを保存します。クライアントはGET /jobs/job_17で状態を取得し、completedなら結果を表示、failedなら理由を表示します。POSTの202は完了ではありません。POSTが503なら同じrequestKeyで最大2回再試行し、なお503なら受付結果不明と表示します。図、具体的な通信例、条件、状態、資料まで説明してください。実在APIとして説明しないでください。
```

### 成果物を取得する

- [4題材の実出力・モデル・検証記録（ZIP）](pathname:///examples/explain-html/generic-examples.zip#download)
- [更新したexplain-htmlスキル一式（ZIP）](pathname:///examples/explain-html/skill.zip#download)
- [更新前の実例の実行記録（JSON）](pathname:///examples/explain-html/execution-before-issue72.json#download)
- [実際のHTMLをブラウザで開く](pathname:///examples/explain-html/generic-api/index.html)
- [実行入力の原本](pathname:///examples/explain-html/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/explain-html/execution.json#download)

### 確認した結果

- 各HTMLの全体図・項目対応、Archifyのモデル検証と標準SVG補助出力が成功。
- 内部リンク、ID重複、埋込SVGと保存原図の一致を静的検査。
- 表示や操作はブラウザのfile URLがポリシー拒否されたため未検証。別経路による回避はしていない。
- 各題材・各版は1試行であり、生成の安定性や網羅的な品質は証明していない。
- 前回の2題材実行・ブラウザ検証記録はexecution-before-issue72.jsonと既存ファイルに保持。現在の新版へ過去のブラウザ結果を流用していない。
- 独立レビューで凡例の不一致、図に不足する結果・条件、空レーンや余白を確認。汎用指示を補足したが、その追加後の再生成は未実施。初回成果物を合格済みの完成見本とは扱わない。
- 新版15/20・旧版13/20。表示方針も含む5条件の各1試行評価であり、図の理解だけの改善率や統計的な優位性ではない。

## 確認するポイント

- 各ページの全体図から、具体例・コード・書類・条件の説明へ進めるか。
- 概要だけで終わらず、資料の各項目、成立条件と例外まで説明されているか。
- 本文、図、具体物で主体・順序・値・結果が一致するか。
- 未確認の情報、説明用の仮定、ブラウザ未検証の範囲が明記されているか。

## 正本を読む

[explain-htmlのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/explain-html/SKILL.md)
