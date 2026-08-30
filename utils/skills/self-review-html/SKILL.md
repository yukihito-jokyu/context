---
name: self-review-html
description: Gitのターゲットとソース、WORKTREEまたはSTAGEDの差分をPR・MR形式のHTMLへ変換し、ユーザーが明示したスキルや任意ルールファイルに基づく行単位のAIセルフレビューを右側へ表示する。AI生成コードの認知負荷を下げるため、差分レビュー、PR前セルフレビュー、ルール適合確認、未コミット変更のレビュー、HTMLレビュー、変更行への指摘を求められた場合は必ず使用する。ユーザー指摘をJSONで受け取り、その内容に基づいてコードを修正するところまで行う。
---

# Self Review HTML

Git差分と適用ルールを左右で結び付け、ユーザーが低い認知負荷で確認・指摘できるHTMLを生成する。HTMLを開いた後は送信を待ち、指摘JSONを読んでコードを修正する。

## 必要環境

Git、Python 3.10以降、macOSの`open`コマンドを使用する。Python外部パッケージは不要。

## 入力を確定する

次を確認する。不足していて結果が変わる場合だけ質問する。

- `target`: 比較基準のブランチまたはコミット
- `source`: ブランチ、コミット、`WORKTREE`、`STAGED`
- 評価対象のスキルパス。指定されたものだけを使う。
- 任意のルールファイルパス

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

## 差分を収集する

```bash
python3 scripts/collect_diff.py \
  --repo <repository> \
  --target <target> \
  --source <source> \
  --output <workdir>/diff.json
```

スクリプトはGit状態を変更しない。失敗した場合はエラーを解決し、既存の部分生成物を上書きせず新しい作業領域で再実行する。

## ルールを抽出して評価する

`references/rule-extraction.md`を読み、指定されたスキルとルールだけを抽出する。次に`diff.json`の全追加行・削除行を評価し、`references/review-schema.md`どおりの`review-raw.json`を書く。

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
  --output <workdir>/report.html
```

同じ入力とテンプレートから同一バイト列を生成することをSHA-256で確認する。生成HTMLをブラウザで描画し、ファイルツリー、折りたたみ、評価と行の連動、任意行のドラッグ選択、`1-11,13`形式、指摘入力を確認する。

JSON入力なしの骨組みだけを確認する場合は、同じテンプレートを使って次を実行する。

```bash
python3 scripts/render_report.py \
  --shell \
  --template assets/report-template.html.tmp \
  --output <workdir>/report.html
```

骨組みではデータ行と評価カードを生成せず、データ依存の操作を無効化する。

## ユーザーの送信を待つ

次をフォアグラウンドで実行する。`open`でブラウザを開き、送信されるまで待機する。

```bash
python3 scripts/serve_review.py \
  --report <workdir>/report.html \
  --feedback <workdir>/feedback.json
```

ポートは8765から順に利用可能なものを選ぶ。URLやポートはHTML内容へ埋め込まない。60秒以上待つ場合は、ユーザーへ短い状況更新を行う。

## 指摘を反映する

`feedback.json`を検証して読む。

- `reviews[].feedback`が空なら、そのAI評価への追加指摘はない。
- 空でない指摘は`review_id`から元の評価と対象行へ結び付ける。
- `manual_comments`は`file`、`side`、`lines`、`line_range`を使って対象コードへ結び付ける。
- 指摘の意図を満たす最小限のコード変更を行う。
- 指摘がルール解釈を訂正する内容なら、コードを直す前に根拠を再確認する。

修正後は対象テストと静的検査を実行する。ユーザーが再レビューを求めた場合は、新しい差分内容から別のcontent-hash領域へHTMLを再生成し、同じ送信フローを繰り返す。

## 安全性

- Gitのcheckout、reset、commit、stashを自動実行しない。
- 指定外のスキルやルールを評価へ混ぜない。
- 生成物へ秘密情報やリポジトリ外のソース本文を埋め込まない。
- バイナリファイルは変更状態だけを示し、本文をHTMLへ埋め込まない。
