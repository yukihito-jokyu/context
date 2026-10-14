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

現在の手順で新規制作した[画像変換APIの解説HTML](pathname:///examples/explain-html/output.html)を確認できます。

## 成果物の例

現在のexplain-html手順で、架空の画像変換APIを新規制作しました。全体構成・通信・状態・再送の4図は、それぞれ別の専任エージェントが調査・作図・解説を担当しています。過去の成果物・実行記録は削除しました。

**到達点：新規HTML生成・Archify再生成照合・PC/狭幅の表示と操作を確認。図内文字の狭幅可読性には未達が残る。**

### 実行した依頼

```text
次の架空APIを初めて使う開発者向けに、仕組みを理解できる単体HTMLを作ってください。利用者は画像変換を依頼します。クライアントは同じ依頼の再送では同じrequestKeyを使い、POST /jobsへ画像IDとrequestKeyを送ります。サーバーは初回にjob_17を作り202とjobIdを返し、同じrequestKeyの再送では重複ジョブを作らず同じjobIdを返します。ワーカーはqueuedのジョブをrunningへ移し、成功ならcompletedとresultUrl、失敗ならfailedとreasonを保存します。クライアントはGET /jobs/job_17で状態を取得し、completedなら結果を表示、failedなら理由を表示します。POSTの202は完了ではありません。POSTが503なら同じrequestKeyで最大2回再試行し、なお503なら受付結果不明と表示します。図、具体的な通信例、条件、状態、資料まで説明してください。実在APIとして説明しないでください。

現在のexplain-html手順で新規制作する。各図は別の専任担当が制作し、同梱Archify 2.16.0を無改変で使用する。PCと狭幅で確認し、図の横に短い対応解説を置く。
```

### 実際の画面

![新規画像変換API解説の全体像ページ](/examples/explain-html/page-overview-1440.png)

[画像を原寸で開く](pathname:///examples/explain-html/page-overview-1440.png)

新規制作したHTMLを1440px幅のChromeで撮影。狭幅の図中文字に課題が残るため、品質合格済みの見本とは扱いません。

### 成果物を取得する

- [新規解説HTML（単体）](pathname:///examples/explain-html/output.html#download)
- [4図の専任担当と生成元（JSON）](pathname:///examples/explain-html/diagram-agent-manifest.json#download)
- [入力仕様と説明先の対応（JSON）](pathname:///examples/explain-html/coverage.json#download)
- [新規記事のブラウザ確認記録（JSON）](pathname:///examples/explain-html/browser-check.json#download)
- [実際のHTMLをブラウザで開く](pathname:///examples/explain-html/output.html)
- [実行入力の原本](pathname:///examples/explain-html/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/explain-html/execution.json#download)

### 確認した結果

- 別々の実エージェント4人の起動と返却を照合。各担当がRFC 9110の一次資料を実際に閲覧。架空API独自の約束とHTTP一般仕様を分離。
- 同梱Archify 2.16.0は無改変。4図をshowcase配布し、検査器が再生成した標準SVG・記事埋込み・モデルhashを照合。
- 5ページの全体図/文字による資料一覧、入力仕様8項目の説明先、ID重複とページ内参照を静的検査。これは説明の正しさや人間の理解を認証する検査ではありません。
- 1440pxと390pxで5ページを新たに表示確認。ページ切替、コード行への直接リンクとdetails展開、戻る操作、説明の段階選択・再生・停止、JavaScript無効時の表示を確認。
- 架空APIの実装・実通信、コード抜粋の実動作、ブラウザPNGと補助標準SVGの画像一致は未検証。
- 通信ページの段階再生は解説を強調する操作です。図の矢印の動き・図と解説の動的同期は未実装。
- 一部の図は390px幅で図内の文字が18px基準を満たしません。横解説19pxとは別の問題として各図review.jsonに記録。主観的な品質点数は付けていません。

## 確認するポイント

- 各ページの全体図から、具体例・コード・書類・条件の説明へ進めるか。
- 概要だけで終わらず、資料の各項目、成立条件と例外まで説明されているか。
- 本文、図、具体物で主体・順序・値・結果が一致するか。
- 未確認の情報、説明用の仮定、ブラウザ未検証の範囲が明記されているか。

## 正本を読む

[explain-htmlのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/explain-html/SKILL.md)
