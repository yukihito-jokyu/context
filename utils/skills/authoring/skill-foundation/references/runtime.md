# 共通ランタイムの動き

skill-foundation が作るスキルには、同じ6つのスクリプト（`_skillrt.py`、`run.py`、`hook.py`、`install.py`、`feedback.py`、`feedback_review.py`）が写される。これを共通ランタイムと呼ぶ。スキルごとの決まりは `assets/contract.json`（契約）に書き、ランタイムは書き換えない。この章では、ランタイムが実行をどう区切り、出力をどう検査し、hooks がいつ働くかを示す。

## 1. 実行の区切り（`run.py`）

スキルの1回の実行は `run.py start` で始まり、`run.py finish` で終わる。実行の状態はプロジェクトの `.skill-runs/<name>/state.json` に記録する。`.skill-runs/.gitignore` に `*` を書くので、git には載らない。

| コマンド | すること | 終了コード |
|---|---|---|
| `start [依頼文] [--set キー=値] [--guess キー=値] [--input-json JSON] [--restart]` | 入力を正規化し（依頼に無い入力は、`settings/` のユーザーの設定、スキルの設定、`--guess`、契約の既定値の順に補う）、出力の比較基準と実行履歴を記録して status を `active` にする | 0 成功、2 実行中の記録がある、3 聞くべき入力が無い |
| `check [--file パス]` | 出力を契約で検査する | 0 指摘なし、1 指摘あり |
| `finish` | 検査に通れば報告を `.skill-runs/<name>/report.md` に書いて出力し、status を `done` にする | 0 完了、1 指摘あり |
| `wait --question 質問` | status を `waiting` にする。hooks が応答の終了を止めなくなる | 0 |
| `resume` | status を `active` に戻す | 0 |
| `abort --reason 理由` | status を `aborted` にし、中断の報告を `report.md` に書いて出力する | 0 |
| `status` | 状態を表示する | 0 |

status は `active`、`waiting`、`done`、`failed`（応答の終了の差し戻しが上限を超えた）、`aborted` のどれかである。

スキル自身のファイルや hooks の設定は、実行中も変更できる。変更後に特別な検査手順を挟む必要はない。古い `assets/seal.json` が残っていても、開始や出力の検査には使わない。

| start の前の status | 記録の扱い |
|---|---|
| 記録なし | 新しく記録する |
| `done` | 新しく記録する |
| `active`、`waiting`（`--restart` が要る） | 実行履歴を最初の start から引き継ぐ。出力の基準は、最初の start の記録を使う。報告の「検証」に restart の回数を書く |
| `aborted`、`failed` | 新しく記録し、前の実行の status と理由を `previous` に残す。前の実行の status と理由を報告の「検証」に書く |

## 2. 出力の検査

`check`、`finish`、hooks は同じ検査を使う。指摘は `<ルールID> <パス>:<行> <説明>` の形で出る。ルールIDを SKILL.md の「4. ルール」で引けば、何を直すかが分かる。

- 出力ごとに、`path` の glob に当たるファイルのうち、start の後に作られたか変わったものを数え、`count` と照らす
- 数えたファイルを、検査の前に `format` で自動で直す（段 format）。直したことは「整形 <ルールID> <パス> <説明>」の行で出し、報告の「検証」にも書く。直せなかったとき（整形のコマンドの失敗など）は指摘にする
- 数えたファイルの中身を `checks` で検査する
- `together` の組（一緒に変えるファイルの組）のうち、start の後に変わったファイルがあるのに、同じ組のほかのファイルが変わっていなければ、その組のルールIDで指摘する（`--file` の無い `check`、`finish`、Stop だけ。編集の直後の検査では指摘しない）

## 3. hooks の働き

hooks は、このスキルの status が `active` のときだけ出力を検査する。指摘の原文と承認の収集は完了後も働く。詳しくは [feedback.md](feedback.md) に従う（収集 hooks の追加機能）。

| イベント | 働き |
|---|---|
| PreToolUse | 実行記録の `state.json` と `report.md`、指摘・承認の収集記録への直接の編集を deny にする。スキル自身のファイルは編集できる |
| PostToolUse | 編集されたファイルが出力なら、`format` で自動で直してから、その中身を検査する（`stage: finish` の検査は除く）。直したときは、読み直すよう伝える |
| Stop | 完了後と質問待ちでは提示する成果物の版を保存する。実行中は出力全体を検査し、応答の終了を差し戻す。指摘が無くても、finish を実行するよう差し戻す。差し戻しが `max_stop_blocks` 回を超えたら status を `failed` にして止めるのをやめる。バックグラウンドの作業を待つときは止めない |
| UserPromptSubmit | 指摘の原文と提示済みの版を記録し、`waiting` を `active` に戻す。ユーザーの発言は止めない。承認は修正前後の確認画面で受け取る |

実行の途中でユーザーに質問するときは、先に `run.py wait --question <質問>` を実行する。wait をしないで応答を終えようとすると、Stop の hook が差し戻す。

## 4. 報告

`finish` は次の形の本文を出す。最終の返答は、この本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。節の並びは `run.py` が固定する。

- 決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを「## 補足」に入れる。形が違えば、`check` と `finish` が RPT-01 の指摘にする
- 契約の `report.sections` に登録したコマンドの出力は、「## 結果」の直後に入る。スキルが自分の結果を集計して見せるときに使う（例：skill-foundation の `report_skill.py`）。`run` の中では `{skill}`、`{root}`、`{run}`、`{in:キー}` が置き換わる。コマンドが失敗したら RPT-01 の指摘にし、finish は終わらない。`"stage": "finish"` を付けた節（終えるときだけ行うもの）は、`check` では実行せず、`finish` だけが実行する
- `report.include_output` を指定したスキルは、その出力の中身を本文の前に置く
- 中断するときは `run.py abort --reason <理由>` を実行する。abort は同じ形の本文を出し、「## 結果」を `<name>: 中断（理由: <理由>）`、「## 検証」を「中断したため、検証していない」にする。「## 出力」には、中断までに書いた出力が入る。最終の返答は、この本文もそのまま使う
- 報告を AI が手で書くと、理由や途中の出力が抜ける。finish と abort のどちらも本文を `report.md` に保存するので、返答と保存した本文を比べられる

```text
## 結果
<name>: 完了（検証に合格）

<report.sections の出力>

## 出力
- `<パス>`（<出力ID> <表示名>）

## 既定値で決めた値
- <表示名>（<キー>）: <値>

## 入力で読めなかった値
- なし

## 検証
- `run.py finish`: 指摘 0 件
- 自動で直した（format）: <ルールID> `<パス>`（直したときだけ）
- <restart したときは回数、前の実行が中断なら status と理由>

## 補足
- <notes.md の項目。無ければ「なし」>
```

## 5. 置き場所と hooks の登録（`install.py`）

| 使い方 | すること |
|---|---|
| `install.py --project <ルート>` | `targets` に従い置き場所を作り、hooks を登録する |
| `--check` | 置き場所と hooks が揃っているかを確かめるだけにする。もう一方の置き場が本体へのリンクでなければ問題にする（`--mode copy` を付けると、複製でもよい） |
| `--mode copy` | シンボリックリンクの代わりに写す（`dev/` は写さない） |
| `--no-hooks` | hooks を登録せず、スキル本来の作成・検査・完了だけを使う |
| `--uninstall` | このスキルの hooks の項目を外す |
| `--dry-run` | 変更せずに、することを表示する |

## 収集の追加機能との境界

run.py の start/check/finish は収集を呼ばない。生成スキルの SKILL.md・ルール表・チェックリストにも収集の指示を入れない。収集と必要な指示の注入は、有効な hooks だけが行う。install.py --no-hooks と製品側の hooks 無効化を許容する。追加機能の失敗は本来の出力検査や完了を止めない。詳しくは [feedback.md](feedback.md) を参照する。
