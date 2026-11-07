# 共通ランタイムの動き

skill-foundation が作るスキルには、同じ7つのスクリプト（`_skillrt.py`、`run.py`、`hook.py`、`install.py`、`feedback.py`、`feedback_review.py`、`setup.py`）と、利用中の指摘の記録の形（`assets/feedback.schema.json`）とその説明（`references/feedback.md`）が写される。これを共通ランタイムと呼ぶ。スキルごとの決まりは `assets/contract.json`（契約）に書き、ランタイムは書き換えない。この章では、ランタイムが実行をどう区切り、出力をどう検査し、hooks がいつ働き、利用中の指摘をどう集めるかを示す。

## 1. 実行の区切り（`run.py`）

スキルの1回の実行は `run.py start` で始まり、`run.py finish` で終わる。実行の状態はプロジェクトの `.skill-runs/<name>/state.json` に記録する。`.skill-runs/.gitignore` に `*` を書くので、git には載らない。

| コマンド | すること | 終了コード |
|---|---|---|
| `start [依頼文] [--set キー=値] [--guess キー=値] [--input-json JSON] [--restart]` | 入力を正規化し（依頼に無い入力は、`settings/` のユーザーの設定、スキルの設定、`--guess`、契約の既定値の順に補う）、出力の基準と契約のハッシュを記録して status を `active` にする | 0 成功、2 実行中の記録がある、3 聞くべき入力が無い |
| `check [--file パス]` | 出力を契約で検査する | 0 指摘なし、1 指摘あり |
| `finish` | 検査に通れば報告を `.skill-runs/<name>/report.md` に書いて出力し、status を `done` にする | 0 完了、1 指摘あり |
| `wait --question 質問` | status を `waiting` にする。hooks が応答の終了を止めなくなる | 0 |
| `resume` | status を `active` に戻す | 0 |
| `abort --reason 理由` | status を `aborted` にし、中断の報告を `report.md` に書いて出力する | 0 |
| `status` | 状態を表示する | 0 |

status は `active`、`waiting`、`done`、`failed`（応答の終了の差し戻しが上限を超えた）、`aborted` のどれかである。

スキル自身のファイル（SKILL.md、scripts/、assets/、references/）は、実行中でも直せる。ユーザーが使いながら微修正できるようにするためである。品質は出力の検査で確かめる。ただし契約（`assets/contract.json`）を変えると検査そのものが変わるので、start が契約のハッシュを記録し、finish と abort が前の実行の終わりから契約が変わっていれば報告の「検証」に1行出す（止めない）。検査を緩める変更でないかは、それを見て人が確かめる。

start をやり直しても、出力の基準は消えない。基準を取り直せると、出力を書いてから restart するだけで「start の後に作った出力」の数え方をすり抜けられるからである。

| start の前の status | 記録の扱い |
|---|---|
| 記録なし | 新しく記録する |
| `done` | 新しく記録する。前の実行が終えたときの契約のハッシュを引き継ぎ、finish で今の契約と比べる |
| `active`、`waiting`（`--restart` が要る） | 出力の基準、契約のハッシュ、履歴を最初の start から引き継ぐ。出力の基準は、前の記録にあるファイルは前の値を使う。報告の「検証」に restart の回数を書く |
| `aborted`、`failed` | 新しく記録し、前の実行の status と理由を `previous` に残す。契約のハッシュは `done` と同じく引き継ぐ。どちらも報告の「検証」に書く |

## 2. 出力の検査

`check`、`finish`、hooks は同じ検査を使う。指摘は `<ルールID> <パス>:<行> <説明>` の形で出る。ルールIDを SKILL.md の「4. ルール」で引けば、何を直すかが分かる。

- 出力ごとに、`path` の glob に当たるファイルのうち、start の後に作られたか変わったものを数え、`count` と照らす
- 数えたファイルを、検査の前に `format` で自動で直す（段 format）。直したことは「整形 <ルールID> <パス> <説明>」の行で出し、報告の「検証」にも書く。直せなかったとき（整形のコマンドの失敗など）は指摘にする
- 数えたファイルの中身を `checks` で検査する
- 出力に `binary: true` を付けた出力（画像など）は、文字列として読まない。`format` と `checks` は `command` の種類だけを使う（`skill_lint.py` がほかの種類を指摘する）
- `together` の組（一緒に変えるファイルの組）のうち、start の後に変わったファイルがあるのに、同じ組のほかのファイルが変わっていなければ、その組のルールIDで指摘する（`--file` の無い `check`、`finish`、Stop だけ。編集の直後の検査では指摘しない）

## 3. hooks の働き

出力の検査の hooks は、このスキルの status が `active` のときだけ働く。実行していないセッションでは検査しない（CTL-04）。利用中の指摘の収集（6章）は、検査とは別に、完了の後も働く。スキル自身のファイルと hooks の設定の編集は、実行中でも止めない。hooks の登録が揃っているかは `install.py --check` で確かめる。

| イベント | 働き |
|---|---|
| PreToolUse | 実行記録（`state.json` と `report.md`）の編集ツールでの直接の編集を拒否する（Claude Code、Codex とも deny）。収集の記録（`.skill-feedback/`）の編集は、status によらず拒否する。ほかのファイルの編集は止めない |
| PostToolUse | 編集されたファイルが出力なら、`format` で自動で直してから、その中身を検査する（`stage: finish` の検査は除く）。直したときは、読み直すよう伝える |
| Stop | 出力全体を検査し、応答の終了を差し戻す。指摘が無くても、finish を実行するよう差し戻す。差し戻しが `max_stop_blocks` 回を超えたら status を `failed` にして止めるのをやめる。バックグラウンドの作業を待つときは止めない。`done` と `waiting` のときは、提示した成果物を版として保存する（収集） |
| UserPromptSubmit | `waiting` を `active` に戻す。成果物を提示した後の発言は、原文を記録し、分類の方法を additionalContext で伝える（収集）。ユーザーの発言は止めない |

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
- <restart したときは回数、前の実行が中断なら status と理由、前の実行の後に契約が変わったこと>

## 補足
- <notes.md の項目。無ければ「なし」>
```

## 5. 置き場所と hooks の登録（`install.py`）

| 使い方 | すること |
|---|---|
| `install.py --project <ルート>` | `targets` に従い置き場所を作り、hooks を登録する |
| `--check` | 置き場所と hooks が揃っているかを確かめるだけにする。もう一方の置き場が本体へのリンクでなければ問題にする（`--mode copy` を付けると、複製でもよい） |
| `--mode copy` | シンボリックリンクの代わりに写す（`dev/` は写さない） |
| `--no-hooks` | hooks を登録しない（収集も登録しない） |
| `--no-feedback` | 利用中の指摘の収集を外し、出力の検査の hooks だけを登録する（登録の文字列に `--no-feedback` が付く） |
| `--features check,feedback` | 登録する機能を選ぶ。既定は両方。`feedback` だけなら、PostToolUse を除いた3つを `--no-check` 付きで登録する |
| `--uninstall` | このスキルの hooks の項目を外す |
| `--dry-run` | 変更せずに、することを表示する |

契約の `control.feedback` が `false` なら、`--features` の指定によらず収集を登録しない。収集を付け外ししても、検査だけの登録の文字列は前と同じなので、Codex の信頼は外れない（[platforms.md](platforms.md)）。

利用者が自分で登録するときは `setup.py` を使う。SKILL.md の手順からは呼ばない（利用者が自分で行う準備のため）。ターミナルで実行すると、製品・機能・登録先を選ぶ画面が開き、書く前に、各ファイルに足す・外す項目を差分で見せる。書き込みは `install.py` の処理（`plan_hooks`、`apply_hooks`、`place`）をそのまま使い、書いた後に `--check` と同じ検査をする。プラグインの hooks が有効なら（Claude Code の `enabledPlugins`、Codex の `config.toml` の `[plugins."<名前>@<マーケットプレイス>"]`）、二重に動くことを画面に出す。

同じ画面で、ユーザーの設定（`settings/user-setting.yaml`）も選んで作れる。値の候補は、`inputs` が契約の `inputs`（毎回聞く入力と、ほかの入力から決まる入力は除く）、ほかの欄が `assets/settings.schema.json` の定義から作る。`assets/settings.schema.json` は skill-foundation だけが持ち、収束テストの動かし方（`convergence`）を定義する。上書きの前の内容は `settings/user-setting.yaml.bak` に残し、書いた後に `load_settings` で読み直して、定義に合わない値が無いかを確かめる。

| 使い方 | すること |
|---|---|
| `setup.py [--project <ルート>] [--plain]` | 対話の画面を開く。矢印キーとスペースで選ぶ（curses）。curses が使えないときと `--plain` では番号で選ぶ。最初のメニュー（「終わる」で抜ける）のほかは、どの画面でも「戻る」と「中止（何も書かない）」を選べる |
| `--status` | 今の hooks の登録、プラグインの hooks、ユーザーの設定の値と出どころを表示する |
| `--hooks claude,codex --features check,feedback` | hooks を登録する製品と機能を選ぶ（非対話）。`--hooks none` なら今の登録を外す |
| `--set <欄>.<項目>=<値>` | ユーザーの設定の値を選ぶ（非対話。例 `inputs.measure=run`、`convergence.agents=1`。`null` で値なし） |
| `--yes` | 非対話で書く。無ければ書く前の差分を見せるだけにする |

TTY が無いとき（AI のツール実行、CI など）に引数なしで実行すると、画面を開かずに、同じことを行う引数を示して終了コード2で止まる。AI は引数の形を使う。

## 6. 利用中の指摘の収集（`feedback.py`）

スキルを使った後に「ここが違う」と言われた内容を、指摘の原文、修正前と修正後の成果物、ユーザーの承認の組で `.skill-feedback/<name>/` に残す。hooks が提供する追加機能で、SKILL.md と `run.py` からは呼ばない。`skill_lint.py` は、SKILL.md と `references/decisions.md` に収集の指示が無いことを確かめる。

| 部品 | 役目 |
|---|---|
| `hook.py` | Stop で版を保存し、UserPromptSubmit で発言を記録して AI に分類の方法を伝え、PreToolUse で記録の直接の編集を拒否する。`feedback.py` の例外はすべて捨て、検査と完了を止めない |
| `feedback.py` | AI が分類と確認に使うコマンド（`feedback`、`ignore`、`context`、`review`、`status`、`validate`） |
| `feedback_review.py` | 修正前と修正後を並べて見せ、ユーザーがボタンで承認する確認画面（`127.0.0.1` だけで待ち受ける） |

集める時機、記録の形、承認の検査、止め方は [feedback.md](feedback.md) に書いた。
