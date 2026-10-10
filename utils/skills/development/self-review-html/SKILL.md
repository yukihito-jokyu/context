---
name: self-review-html
description: Gitのターゲットとソース、WORKTREEまたはSTAGEDの差分をPR・MR形式のHTMLへ変換し、ユーザーが明示したスキルや任意ルールファイルに基づく行単位のAIセルフレビューを右側へ表示する。AI生成コードの認知負荷を下げるため、差分レビュー、PR前セルフレビュー、ルール適合確認、未コミット変更のレビュー、HTMLレビュー、変更行への指摘を求められた場合は必ず使用する。ユーザー指摘をJSONで受け取り、その内容に基づいてコードを修正するところまで行う。
---

# Self Review HTML

Git差分と適用ルールを左右で結び付け、ユーザーが低い認知負荷で確認・指摘できるHTMLを生成する。HTMLを開くサーバーはバックグラウンドで起動し、後続ターンでユーザーから対応を依頼されたときに指摘JSONを読んでコードを修正する。

## 必要環境

Git、Python 3.10以降、macOSの`open`コマンドを使用する。Python外部パッケージは不要。

## 入力を確定する

次を確認する。不足していて結果が変わる場合だけ質問する。

- `target`: 比較基準のブランチまたはコミット
- `source`: ブランチ、コミット、`WORKTREE`、`STAGED`
- 任意の対象パス。指定された場合はrepository-relative prefixとして差分収集時に限定する。
- 評価対象のスキルパス。指定されたものだけを使う。
- 任意のルールファイルパス
- 任意の成果物保存先

`WORKTREE`は現在のブランチのコミット済み、ステージ済み、未ステージ、未追跡ファイルを統合する。`STAGED`はコミット済みとステージ済みを統合する。どのモードも共通祖先を基準にPR・MR形式で表示する。

## 作業領域を決める

リポジトリ内へ生成物を置くと未追跡差分へ混入するため、既定では次を使う。

```text
/tmp/self-review-html/<repository>/<content-hash>/
├── diff.json
├── review-raw.json
├── review.json
├── report.html
└── feedback.json
```

`content-hash`はtarget、source、差分内容、指定ルール内容のSHA-256先頭16文字とし、乱数や時刻を使わない。同一内容のディレクトリがある場合は各チェックサムを検証して再利用し、不一致なら停止する。生成済みHTMLやJSONを直接編集しない。

利用者が成果物保存先を指定した場合も、同じ正規成果物だけをその配下へ置く。差分全体の退避JSON、対象パスを絞る実行固有スクリプト、評価JSONを組み立てる実行固有スクリプト、再現性確認用HTML複製は作成しない。`feedback.json`は利用者が指摘を送信した場合だけ作成する。

## 差分を収集する

```bash
python3 scripts/collect_diff.py \
  --repo <repository> \
  --target <target> \
  --source <source> \
  [--path-prefix <repository-relative-path>]... \
  --output <workdir>/diff.json
```

対象パスが指定された場合は、`collect_diff.py`の`--path-prefix`で収集時に限定する。全差分を収集してから実行固有スクリプトで絞り込まない。複数指定はOR条件とする。

スクリプトはGit状態を変更しない。失敗した場合はエラーを解決し、既存の部分生成物を上書きせず新しい作業領域で再実行する。

## ルールを抽出して評価する

`references/rule-extraction.md`を読み、指定されたスキルとルールだけを抽出する。次に二段階で`diff.json`を評価し、`references/review-schema.md`どおりの`review-raw.json`をAIが直接、排他的に作成する。

`review-raw.json`を生成するための実行固有スクリプトは作成しない。構造、変更行の存在、行網羅、許可された出典は`validate_review.py`が検証する。検証エラーは`review-raw.json`の入力内容を修正して解消し、検証処理を複製しない。

1. 全追加行・削除行を`rule_in`、`rule_out`、`unknown`、`no_rule`の通常評価で覆う。
2. 全変更行を規約不足の視点で再走査し、実装が具体的な方針を選んでいるのに指定ルールへ根拠がない箇所を、独立した`rule_gap`評価として追加する。

`rule_gap`は通常評価と別review ID、別カードにし、一つの評価へ複数verdictを共存させない。同じ変更行を通常評価と`rule_gap`が参照することは許可するが、`rule_gap`だけで通常評価の行網羅を満たしてはならない。提案は未承認であり、ユーザーが明示的に指示するまでルールやコードへ適用しない。

評価は行または複数行へまとめる。根拠、出典、判定理由、ルール外の場合の修正案を記録する。該当ルールがない変更行も`no_rule`で明示し、評価対象から落とさない。

## 評価を検証する

指定した各スキル・ルールファイルを`--allowed-source`で渡す。

```bash
python3 scripts/validate_review.py \
  --diff <workdir>/diff.json \
  --review <workdir>/review-raw.json \
  --allowed-source <explicit-rule-or-skill-path> \
  --output <workdir>/review.json
```

検証失敗時はHTMLを生成せず、AI評価を修正して新しいファイルへ再検証する。検証を無効化して進めない。

## HTMLを生成する

```bash
python3 scripts/render_report.py \
  --diff <workdir>/diff.json \
  --review <workdir>/review.json \
  --template assets/report-template.html.tmp \
  --verify-determinism \
  --output <workdir>/report.html
```

`--verify-determinism`は同じ入力をメモリ上で二度描画してSHA-256を比較し、一つの`report.html`だけを書き出す。

JSON入力なしの骨組みだけを確認する場合は、同じテンプレートを使って次を実行する。

```bash
python3 scripts/render_report.py \
  --shell \
  --template assets/report-template.html.tmp \
  --output <workdir>/report.html
```

骨組みではデータ行と評価カードを生成せず、データ依存の操作を無効化する。

## レビューサーバーを起動する

次を長時間実行セッションとして起動する。`open`でブラウザが開き、サーバーを起動できたことを確認したら、指摘送信を待機またはpollせずユーザーへ制御を返す。サーバープロセスはバックグラウンドで継続させる。

```bash
python3 scripts/serve_review.py \
  --report <workdir>/report.html \
  --feedback <workdir>/feedback.json
```

ポートは8765から順に利用可能なものを選ぶ。URLやポートはHTML内容へ埋め込まない。`feedback.json`はレビュー画面から指摘が送信されたときに作成される。このターンではその作成を待たず、サーバーを停止しない。

## 指摘を反映する

後続ターンでユーザーがレビュー指摘への対応を依頼した場合にだけ、対象の`feedback.json`を検証して読む。ファイルがまだ存在しない場合も待機せず、その事実を伝える。

`feedback.json`を検証して読む。

- `reviews[].approved`が`true`の通常評価は、ユーザーがその評価と推奨修正を承認したものとして対応対象にする。
- `reviews[].approved`が`false`かつ`reviews[].feedback`が空なら、そのAI評価への対応指示はない。
- 空でない指摘は`review_id`から元の評価と対象行へ結び付ける。
- 空でない指摘は承認状態より優先して解釈する。
- `manual_comments`は`file`、`side`、`lines`、`line_range`を使って対象コードへ結び付ける。
- `rule_gap`は未承認の提案として扱い、`approved`が`true`でも、その評価や指摘だけを根拠にルールファイルまたはコードを変更しない。ユーザーが変更対象と内容を明示した場合だけ、通常の承認範囲で反映する。
- 指摘の意図を満たす最小限のコード変更を行う。
- 指摘がルール解釈を訂正する内容なら、コードを直す前に根拠を再確認する。

修正後は対象テストと静的検査を実行する。新しい差分内容から別のcontent-hash領域へHTMLを再生成し、レビューサーバーを再びバックグラウンドで起動して、指摘送信を待たずユーザーへ制御を返す。

## 安全性

- Gitのcheckout、reset、commit、stashを自動実行しない。
- 指定外のスキルやルールを評価へ混ぜない。
- 生成物へ秘密情報やリポジトリ外のソース本文を埋め込まない。
- バイナリファイルは変更状態だけを示し、本文をHTMLへ埋め込まない。
