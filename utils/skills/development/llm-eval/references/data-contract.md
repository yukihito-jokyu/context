# LLM評価データ契約（このパッケージの提案形式）

この形式はモデル/言語に依存しない**提案**であり、Anthropicの`report/SCHEMA.md`と完全互換だとは主張しない。既存の評価フォーマットがある場合、破壊せず変換層を追加する。

## 1. ケースファイル（`cases.jsonl`）
```json
{"id":"case-001","split":"train","tags":["分類","境界"],"input":{"message":"請求書を再発行して"},"expected":{"label":"billing"},"source":"human-reviewed","metadata":{"language":"ja"}}
```
- `id`：安定した識別子。入力を変更したときは改訂を記録。
- `split`：`train`/`validation`/`test`。固定seedでカテゴリごとに層化。最終testを改善案作りに使わない。
- `input`：アプリの実入口に必要な全フィールド。添付物を含む場合は非公開性を検証。
- `expected`：**graderのみ**が利用する期待値。LLMが読める環境に置かない。
- `source`：`production-anonymized`/`bug`/`human-reviewed`/`synthetic`等。

## 2. 成功試行（`baseline/results.jsonl`または`v1/results.jsonl`）
```json
{"case_id":"case-001","rep":0,"status":"ok","model_requested":"provider/model@version","model_served":"provider/model@version","grade":{"correct":1,"format":1},"usage":{"input_tokens":321,"output_tokens":88},"latency_s":1.42,"trace_path":"baseline/traces/case-001_rep0.json","stop_reason":"completed"}
```
- `status` は `ok` / `truncated` / `refusal`（採点対象なら）など、**意味を定義**する。
- `model_served` は可能な限りAPI応答の実値。取得できなければ `unknown` として確認不能性を明示。
- `usage` はAPIの実値を優先。推定は `estimated` と明示し比較で混同しない。
- `grade` は独立の数値指標。成功でも必須値が欠けたら失敗として監査する。
- API失敗、rate limit、タイムアウト、grader crash等、採点不能な試行は`errors.jsonl`に分離。黙って0点にしない。
- `trace_path` はツール引数と結果を含め、秘密情報をマスクし、再現可能性を確保する。

## 3. 比較条件
- 1ケースにつき複数反復し、対応するcase/rep同士の差を比較する。
- ケース集合、採点基準、外部データの固定可能性、モデルのAPIパラメータ、実行環境は比較中に一致させる。
- 代表性を損なわない層化分割を行い、選択用と最終確認用を明確に分ける。
- 95% CIなどの誤差区間を示し、意思決定に必要な最小差と比べる。
- 費用は実モデルと実usageに紐付け、価格表とキャッシュの扱いを記録する。

## 4. 生成成果物
`eval-plan.md`、`cases.jsonl`、runner、grader、`results.jsonl`、`errors.jsonl`、traces、report、実行方法のREADME。ログをgitに含めるかは秘匿性と保存期間を確認する。

## 5. HTMLでの確認と実行履歴
- review.htmlと保存・コピー可能な確認記録を作る。詳細は [HTMLでのすり合わせ](html-review.md)。
- ケース集合、採点基準、集計方法を特定できる版または内容ハッシュを記録し、合意範囲を紐付ける。保存はそれ自体では合意ではない。
- 各実行に実行ID、日時または明示的な順序、ケース集合と採点基準の版、実行設定、事前合意の参照、正式評価/許可された動作確認の区別を記録する。既存形式では別manifestへ追加してもよい。
- ケース別判断・理由、代表性へのコメントと、結果への判断・コメントを分けて保存する。基準変更後の実行・再採点は新しいIDで記録する。
- 履歴グラフは同じケース集合・基準・指標の実測だけを同一系列として比較する。過去の合意状況や点数を後から変更しない。
