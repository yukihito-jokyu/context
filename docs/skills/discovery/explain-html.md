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

現在の手順で新規制作した[画像変換APIの解説HTML](pathname:///skills/explain-html/output.html)を確認できます。

## 成果物の例

提供された架空画像変換APIを同じ題材で新規制作。4名が調査・設計・作図・短い番号解説・表示確認を担当し、統合担当が5関心の単体HTMLを組み立てました。

**到達点：4論理図・5標準投影の再生成一致、記事HTMLと表示・操作の確認済み。探索用原図Viewerの縦overflowは未達として記録。。**

### 実行した依頼

```text
次の架空APIを初めて使う開発者向けに、仕組みを理解できる単体HTMLを作ってください。利用者は画像変換を依頼します。クライアントは同じ依頼の再送では同じrequestKeyを使い、POST /jobsへ画像IDとrequestKeyを送ります。サーバーは初回にjob_17を作り202とjobIdを返し、同じrequestKeyの再送では重複ジョブを作らず同じjobIdを返します。ワーカーはqueuedのジョブをrunningへ移し、成功ならcompletedとresultUrl、失敗ならfailedとreasonを保存します。クライアントはGET /jobs/job_17で状態を取得し、completedなら結果を表示、failedなら理由を表示します。POSTの202は完了ではありません。POSTが503なら同じrequestKeyで最大2回再試行し、なお503なら受付結果不明と表示します。図、具体的な通信例、条件、状態、資料まで説明してください。実在APIとして説明しないでください。

現在のexplain-html手順で新規制作する。各図は別の専任担当が制作し、同梱Archify 2.16.0を無改変で使用する。PCと狭幅で確認し、図の横に短い対応解説を置く。
```

### 実際の画面

![全体図と番号解説を新しい記事のPC画面で表示](/skills/explain-html/preview.png)

[画像を原寸で開く](pathname:///skills/explain-html/preview.png)

### 成果物を取得する

- [図と通信例を含む解説原本（HTML）](pathname:///skills/explain-html/output.html#download)
- [図・入力・調査・検証記録一式（ZIP）](pathname:///skills/explain-html/bundle.zip#download)
- [専任担当と標準図の対応（JSON）](pathname:///skills/explain-html/diagram-agent-manifest.json#download)
- [架空仕様と説明先の照合表（JSON）](pathname:///skills/explain-html/coverage.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/explain-html/output.html)
- [実行入力の原本](pathname:///skills/explain-html/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/explain-html/execution.json#download)

### 確認した結果

- 図担当はoverview/request/states/retryの各1名をfork_turns=noneで新規起動。実IDと担当範囲をmanifestへ起動直後に記録。各担当の一次資料実閲覧と最終返却を照合。
- 同梱Archify 2.16.0を無改変で使用。editorial/showcaseで4論理図・5標準投影をdeliver。限定DOM標準serializerでSVG出力。図種の変更理由を図計画へ反映。
- render_html.py --manifest、check_diagram_delegation.py --article --observed-agentsによる全標準出力の再生成・バイト一致を確認。check_overviews.pyとcheck_coverage.pyも成功。
- インメモリ模擬実装を実行し、同じキーの同じjobId、queued/running/成功・失敗終端、初回＋最大2追加送信を確認。再送応答202は模擬実装の仮定であり原文未指定と明示。実APIへの通信は未実施。
- 実Chromeで統合後1440px/390px×5ページを確認。各図・必要caption・番号解説を実掲載幅で観察。ページ移動、深いコードリンク、details、履歴、連続選択、有限の解説再生、reduced-motion、JavaScript無効を検査。静止画像の目視範囲はbrowser-check.jsonに記録。
- 現行の必須ゲートはinline SVG overlayを認めないため、画像を無改変のまま番号解説の段階強調を採用。独自SVGは使用していない。
- 主要文字は図により約10〜12px、枝・補助文字は約7pxで小さい。条件は19pxのcaptionと対応解説にも保持。標準Viewer自体のvisual-checkは縦overflowで未達。記事内の収まりと分けて各reviewへ記録。印刷・タブ非表示・再生パルスの目視は未実施。
- 公開直前に最新版sanitize(bytes, relativePath)で実ホームパスと実環境詳細版をマスクし、作業/正本パスを<workdir>/<repository>へ置換。ZIPもマスク後ファイルから作成。全成果物SHAはマスク後に登録。
- 利用者承認、外部投稿、plugin導入は未実施。

## 確認するポイント

- 各ページの全体図から、具体例・コード・書類・条件の説明へ進めるか。
- 概要だけで終わらず、資料の各項目、成立条件と例外まで説明されているか。
- 本文、図、具体物で主体・順序・値・結果が一致するか。
- 未確認の情報、説明用の仮定、ブラウザ未検証の範囲が明記されているか。

## 正本を読む

[explain-htmlのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/discovery/explain-html/SKILL.md)
