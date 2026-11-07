<!-- generated-by: write-detailed-design-document; body-sha256: 1cd20a7d36a56c0fa803285dacde1aed22a14304c3c969e55afc20b528685ab5 -->
# 根拠と未決事項と変更

[入口に戻る](README.md)

引き継いだ記述と追加提案を分け、未決の影響と要件変更の判断を辿れるようにする。

## sources

<a id="S001"></a>
### S001

[requirement.md 3行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/requirement.md:3:1)

> 利用者は備品の数量を指定して予約し、予約結果と残数を確認できる。最後の1個へ同時に予約しても、在庫は負にならず、成立する予約は1件だけである。

SHA-256: `f48dfbbb161879d79830f2066cc45fa5c3e8db6c5f24a9a26986bd194d39ed22` / requirement

<a id="S002"></a>
### S002

[requirement.md 4行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/requirement.md:4:1)

> 予約の有効期間は作成から10分とする。利用者の取消か期限切れで予約分の数量を在庫へ戻す。取消と期限処理が競合しても返却は1回だけとする。保存側の判定時刻が期限と等しければ期限切れとする。

SHA-256: `f48dfbbb161879d79830f2066cc45fa5c3e8db6c5f24a9a26986bd194d39ed22` / requirement

<a id="S003"></a>
### S003

[requirement.md 5行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/requirement.md:5:1)

> 作成の同じ受付用識別子・同じ内容の再送は新しい予約を作らない。違う内容なら競合として返す。

SHA-256: `f48dfbbb161879d79830f2066cc45fa5c3e8db6c5f24a9a26986bd194d39ed22` / requirement

<a id="S004"></a>
### S004

[requirement.md 6行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/requirement.md:6:1)

> 保存確定後に応答する。応答切断後は識別子で確定した結果を照会し、予約や在庫の更新を自動で繰り返さない。

SHA-256: `f48dfbbb161879d79830f2066cc45fa5c3e8db6c5f24a9a26986bd194d39ed22` / requirement

<a id="S005"></a>
### S005

[requirement.md 7行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/requirement.md:7:1)

> 画面は在庫数、予約の状態、操作結果を表示し、期限切れ後は取消を受け付けない。キーボードで予約・取消・結果照会を行える。

SHA-256: `f48dfbbb161879d79830f2066cc45fa5c3e8db6c5f24a9a26986bd194d39ed22` / requirement

<a id="S006"></a>
### S006

[basic-design.md 3行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/basic-design.md:3:1)

> この資料は設計案である。実装と負荷・競合試験は未実施である。

SHA-256: `887f247ad827415e314ad00b16904c4ec5b131074f92101d17537b9629b6c3d2` / basic_design

<a id="S007"></a>
### S007

[basic-design.md 5行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/basic-design.md:5:1)

> ブラウザ画面はHTTPのJSON APIを呼ぶ。サーバー側は受付・予約サービス・期限監視・保存リポジトリを分け、PostgreSQLへ備品と予約と受付結果を保存する。外部の実行基盤やエージェントは使わない。

SHA-256: `887f247ad827415e314ad00b16904c4ec5b131074f92101d17537b9629b6c3d2` / basic_design

<a id="S008"></a>
### S008

[basic-design.md 6行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/basic-design.md:6:1)

> 作成は在庫確認と数量の引当と予約と受付結果を一つの保存単位で確定する。同時再送は受付用識別子の一意制約で照合する。取消と期限処理は同じ予約の状態を条件にして一方だけが在庫を戻す。

SHA-256: `887f247ad827415e314ad00b16904c4ec5b131074f92101d17537b9629b6c3d2` / basic_design

<a id="S009"></a>
### S009

[basic-design.md 7行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/basic-design.md:7:1)

> 時刻は保存側のUTCとし、画面の押下時刻を期限判定に使わない。期限処理が遅れても、取消の受付では期限を再検査する。

SHA-256: `887f247ad827415e314ad00b16904c4ec5b131074f92101d17537b9629b6c3d2` / basic_design

<a id="S010"></a>
### S010

[basic-design.md 8行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/basic-design.md:8:1)

> 通知は保存確定後に画面へ返す。通信切断後や再起動後も受付用識別子で確定結果を照会し、外部への更新を再実行したことにしない。

SHA-256: `887f247ad827415e314ad00b16904c4ec5b131074f92101d17537b9629b6c3d2` / basic_design

<a id="S011"></a>
### S011

[basic-design.md 9行目](/private/tmp/write-detailed-design-public-6rui8g6x/docs/basic-design.md:9:1)

> APIの項目・サイズ・エラー、物理列・索引・移行、取得順と原子性、画面の操作可否と更新、試験条件は詳細設計で具体化する。

SHA-256: `887f247ad827415e314ad00b16904c4ec5b131074f92101d17537b9629b6c3d2` / basic_design

## issues

<a id="U001"></a>
### U001 PostgreSQLの対象版、隔離・ロック・受付衝突・耐久性・移行が実装で成立するか未検証である。

| 項目 | 内容 |
| --- | --- |
| 未決の内容 | PostgreSQLの対象版、隔離・ロック・受付衝突・耐久性・移行が実装で成立するか未検証である。 |
| 検証内容・状態 | 対象版を固定し公式仕様を確認した上で、C003/C004/C008/C010/C013を実DBで停止注入・同時実行する。COMMIT確認不能、接続切断、lock_timeout、statement_timeout、デッドロックの実際の戻り値と全体ROLLBACKを観測する。移行は空DBと既存データで試す。今回は接続も移行も実行しない。 |
| 採用できる結果 | 負在庫0回、数量返却一回、受付結果一件、途中状態の確定0回となり、保存時刻とHTTP応答と再起動後結果が一致する。対象版・設定・試験ログを根拠として残してから採用を判断する。 |
| 独立して進める範囲 | APIの型、画面の文言、試験のデータ準備と期待値は進められる。DB実装の本番利用と性能・耐久性の成立の断言は保留する。 |
| 確認する担当 | 保存・DB担当と試験担当。担当者の指名は未実施である。 |
| 影響する設計 | [D003](common.md#D003)<br>[D006](common.md#D006)<br>[T001](data.md#T001)<br>[T002](data.md#T002)<br>[T003](data.md#T003)<br>[P001](common.md#P001)<br>[P002](common.md#P002)<br>[RC001](recovery.md#RC001)<br>[RC004](recovery.md#RC004) |

<a id="U002"></a>
### U002 DB時計の補正・切替と監視遅延、候補件数・待ち時間の提案値は未検証である。

| 項目 | 内容 |
| --- | --- |
| 未決の内容 | DB時計の補正・切替と監視遅延、候補件数・待ち時間の提案値は未検証である。 |
| 検証内容・状態 | UTC設定と時計補正、DB切替時の時刻差、期限直前・等号・直後、ロック待機中の期限跨ぎを測る。代表データ量で候補100件/秒と部分索引の処理計画・遅延を測定する。今回は負荷試験と外部仕様確認を実施しない。 |
| 採用できる結果 | 保存側t>=expires_atで取消成立がなく、遅延時も二重返却0回となる。許容する最大返却遅延と時計差を利用者側と決め、測定値がそれを満たしてから周期と件数を採用する。 |
| 独立して進める範囲 | 期限の等号規則、状態条件、遅延時の画面表示と候補再走査の実装設計は進められる。性能保証と周期の採用は保留する。 |
| 確認する担当 | 運用・DB担当と業務判断者。採用承認は未実施である。 |
| 影響する設計 | [D006](common.md#D006)<br>[F002](features.md#F002)<br>[F003](features.md#F003)<br>[IF005](interfaces.md#IF005)<br>[P002](common.md#P002)<br>[T002](data.md#T002) |

<a id="U003"></a>
### U003 受付結果の無期限保持、ブラウザ識別子の保持と、not_recordedが続く未確認操作の運用確認は未決である。

| 項目 | 内容 |
| --- | --- |
| 未決の内容 | 受付結果の無期限保持、ブラウザ識別子の保持と、not_recordedが続く未確認操作の運用確認は未決である。 |
| 検証内容・状態 | 保存容量、個人情報の保持規定、ログとDBから未到着・確定ROLLBACKを調べる運用手順、ブラウザ再読込・別利用者ログインを確認する。今回の設計では受付結果と終端予約を消さない。 |
| 採用できる結果 | 必要な再送・照会期間に同じ識別子の意味を失わず、利用者間で情報が混ざらない。未確認のまま更新を自動再実行しない。保持と運用手順について判断の記録を得る。 |
| 独立して進める範囲 | 不変record・本人別識別子・GETのみの回復を実装設計できる。保持期間の短縮と未確認操作の自動解決は行わない。 |
| 確認する担当 | 業務判断者・運用担当・画面担当。担当者の指名は未実施である。 |
| 影響する設計 | [D004](common.md#D004)<br>[D007](common.md#D007)<br>[T002](data.md#T002)<br>[T003](data.md#T003)<br>[F004](features.md#F004)<br>[RC002](recovery.md#RC002)<br>[RC003](recovery.md#RC003)<br>[UI001](ui.md#UI001) |

<a id="U004"></a>
### U004 APIの追加上限・本人権利・認証とCSRFの受渡しは未採用かつ未結合である。

| 項目 | 内容 |
| --- | --- |
| 未決の内容 | APIの追加上限・本人権利・認証とCSRFの受渡しは未採用かつ未結合である。 |
| 検証内容・状態 | UUIDと数量・サイズの値域、エラーコード、認証済みactor_idの不変性と偽装不可、CSRF失敗、別人予約・別人受付の非開示を実装後に確認する。今回は外部接続試験をしない。 |
| 採用できる結果 | 全項目の欠落・null・未知項目・型・上限で契約どおりのcodeを返し、本文から本人を偽装できない。業務とセキュリティの判断者が提案値と本人操作権を承認した記録を残す。 |
| 独立して進める範囲 | 提案契約のクライアント型、エラー表示、確認条件は進められる。認証統合と本番公開の判断は保留する。 |
| 確認する担当 | API担当・認証担当・業務判断者。採用承認は未実施である。 |
| 影響する設計 | [D002](common.md#D002)<br>[D005](common.md#D005)<br>[IF001](interfaces.md#IF001)<br>[IF002](interfaces.md#IF002)<br>[IF003](interfaces.md#IF003)<br>[IF004](interfaces.md#IF004) |

<a id="U005"></a>
### U005 キーボード、ブラウザ保存領域、HTMLとMermaidの実描画は未確認である。

| 項目 | 内容 |
| --- | --- |
| 未決の内容 | キーボード、ブラウザ保存領域、HTMLとMermaidの実描画は未確認である。 |
| 検証内容・状態 | 対象ブラウザでC011/C015/C016を実行し、フォーカス・aria-live・保存不能・再読込と古い応答を確認する。review.htmlとG001〜G003の表示を別途確認する。今回はブラウザを起動しない。 |
| 採用できる結果 | 全操作をキーボードだけで行え、期限到来後の取消不可とunknownの照会が読み上げられ、識別子が再読込後も本人へ結び付く。図・HTMLの文字欠けと意味の欠落がない。 |
| 独立して進める範囲 | Markdown、API、物理データ、画面項目と試験期待値の照合は進められる。描画済み・操作確認済みとは報告しない。 |
| 確認する担当 | 画面担当と文書レビュー担当。担当者の指名は未実施である。 |
| 影響する設計 | [D007](common.md#D007)<br>[UI001](ui.md#UI001)<br>[G001](features.md#G001)<br>[G002](common.md#G002)<br>[G003](data.md#G003) |

## changes

要件間・基本設計間に今回の入力から確認できる不一致はなく、元の要件は変更しない。値域・権利・取消識別子・物理方式はD002〜D007の未採用の詳細提案であり、要件変更の承認として扱わない。
