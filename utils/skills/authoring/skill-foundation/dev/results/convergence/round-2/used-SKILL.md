---
name: skill-foundation
description: "作りたいスキルの依頼から、決定表・出力の契約・hooks とスクリプトによる制御・違反例・収束テストを備え、Claude Code と Codex のどちらでも同じ結果になるスキルを作る。「スキルを作って」、「コミットメッセージを書くスキルを作って」、「誰が使っても同じ結果になるスキルにしたい」、「Codex でも Claude Code でも使えるスキルを作成して」、「hooks とスクリプトで出力を縛るスキルを作って」、「この作業手順を SKILL.md にまとめてスキル化して」、「この既存のスキルを、誰が使っても同じ結果になるように作り直して」、「Create a skill that gives the same result on any AI」と頼まれたときに使う。リポジトリ全体の規約・lint・ディレクトリ構造を作る依頼には使わない（代わりにpattern-foundationを使う）。skill-foundation で作ったスキルの決定や契約の小さな修正には使わない（代わりにそのスキルの dev/spec.json の修正と render_skill.pyを使う）。"
---

# 誰が使っても同じ結果になるスキルを作る

<!-- BEGIN GENERATED:purpose -->
作りたいスキルの依頼から、決定表・出力の契約・hooks とスクリプトによる制御・違反例・収束テストを備え、Claude Code と Codex のどちらでも同じ結果になるスキルを作る
<!-- END GENERATED:purpose -->

## 1. 使う場面

<!-- BEGIN GENERATED:triggers -->
次のような依頼で使う。

- 「スキルを作って」
- 「コミットメッセージを書くスキルを作って」
- 「誰が使っても同じ結果になるスキルにしたい」
- 「Codex でも Claude Code でも使えるスキルを作成して」
- 「hooks とスクリプトで出力を縛るスキルを作って」
- 「この作業手順を SKILL.md にまとめてスキル化して」
- 「この既存のスキルを、誰が使っても同じ結果になるように作り直して」
- 「Create a skill that gives the same result on any AI」

次の場合は使わない。

- リポジトリ全体の規約・lint・ディレクトリ構造を作る依頼 → 代わりに: pattern-foundation
- skill-foundation で作ったスキルの決定や契約の小さな修正 → 代わりに: そのスキルの dev/spec.json の修正と render_skill.py

依頼の内容から自動で選ばれる。明示して呼ぶときは Claude Code では `/skill-foundation`、Codex では `$skill-foundation` と書く。
<!-- END GENERATED:triggers -->

## 2. 手順

このファイルがあるディレクトリを `<skill>` と呼ぶ。スクリプトは Python 3.9 以上の標準ライブラリだけで動く。手順は番号の順に行い、飛ばさない。

1. 依頼が [references/intake.md](references/intake.md) の6章の対象外に当たるかを確かめる。当たれば start せず、ファイルも作らずに、代わりに使うものを返答して終える（IN-01）。当たらなければ、同じファイルの1章の表で「聞く」とある項目が依頼に無いかを確かめ、無ければここでまとめてユーザーに聞く（CTL-03）
2. 名前を intake.md の2章（OUT-04）、言語を3章、置き場を4章（OUT-01）で決め、`python3 <skill>/scripts/run.py start --set name=<名前> --set targets=<対象> --set language=<言語> --set base=<置き場> --set measure=<ask・run・skip> "<依頼文>"` を実行する。`measure` は依頼に指定が無ければ渡さない。終了コード3なら、出力された質問をユーザーに聞き、答えを `--set` で渡してやり直す（CTL-01）
3. フェーズ0（受付）: `<base>/<name>/` の状態を OUT-06 の決定表で確かめ、`mode` を `new` か `retrofit`（後付け）に決める。`<skill>/assets/templates/spec.example.json` を `<base>/<name>/dev/spec.json` に写し、受付の項目（`name`、`kind`、`mode`、`language`、`targets`、`title`、`purpose`、`triggers`）を intake.md に従って埋める。`kind` は名前の動詞にし、[references/skill-profiles.md](references/skill-profiles.md) のその種類の節を読む（OUT-05）
4. フェーズ1（骨組み）: `python3 <skill>/scripts/init_skill.py --dir <base>/<name>` を実行し、`python3 <skill>/scripts/skill_lint.py <base>/<name> --phase 1` のエラーを0件にする（STEP-01、OUT-02）
5. フェーズ2（調査）: [references/runtime.md](references/runtime.md)、[references/platforms.md](references/platforms.md)、[references/research.md](references/research.md) を読む。作るスキルが前提にする事実（コマンドの引数、ファイルの形式、製品の仕様）を、research.md の1章の順の情報源と、skill-profiles.md の種類の節の「調べる先」で確かめ、`<base>/<name>/dev/research.md` に出典、確かめた日付、確認の状態を付けて書く。プロジェクトに既にある書き方に合わせる決定は、決まりを書いた場所を「- 決まり：」の行に、数えた結果を「- 分布：」の行に書く（research.md の3章）。後付けなら、元の SKILL.md（`dev/original/SKILL.md`）を「## 既存のスキル」に書く（IN-02）
6. フェーズ3（決める）: [references/variance-axes.md](references/variance-axes.md)、[references/writing.md](references/writing.md)、[references/control-ladder.md](references/control-ladder.md) の3章、skill-profiles.md の種類の節の「軸の読み替え」を読み、軸（種類の追加の軸を含む）ごとに spec の `decisions` と `excluded_axes` を書く。決定ごとに答えの決め方（`basis`）を variance-axes.md の2章の順で選ぶ。skill-profiles.md の種類の節の「入力の候補」は、`inputs` に同じ key で入れるか、`excluded_inputs` に key と理由を書く。入力ごとに、既定値で進めたときの影響（`impact`）から `ask` か `default` を決めて `inputs` を書く。`python3 <skill>/scripts/skill_lint.py <base>/<name> --phase 3` のエラーを0件にする（OUT-03、OUT-04）
7. フェーズ4（縛る）: [references/control-ladder.md](references/control-ladder.md) を読み、決定ごとの段（`control`）と機械にしない理由（`why_not_machine`）を control-ladder.md の1章の順で決め、spec の `outputs`（`checks` と自動で直す `format`）、一緒に変える出力の組（`together`）、スキル固有の `scripts/`、検査に通る出力の見本（`<base>/<name>/assets/examples/` と、見本が体現する決定の ID を挙げた spec の `examples`）、`<base>/<name>/SKILL.md` の「2. 手順」を書く。契約の検査は、skill-profiles.md の種類の節の「検査の候補」から選ぶ。`python3 <skill>/scripts/render_skill.py --dir <base>/<name>` を実行し、`python3 <skill>/scripts/skill_lint.py <base>/<name> --phase 4` のエラーを0件にする（STEP-01、OUT-02）
8. フェーズ5（証明する）: `<base>/<name>/dev/probes.json` に baseline と違反例を書く。baseline の `files` の1つ以上は `from` で見本にし、違反例は1つにつき1つの決定だけを破る。段 format の決定の違反例には、直した後に消えるはずの正規表現を `fixed` に書く。段 review の決定には、違反を入れた見本を `reviews` に書く（control-ladder.md の7章）。`python3 <skill>/scripts/probe.py <base>/<name>` をすべて成功させ、`python3 <skill>/scripts/skill_lint.py <base>/<name> --phase 5` のエラーを0件にする。失敗したら STEP-04 に従い、作るスキルの側を直す
9. フェーズ6（測る）: [references/convergence-test.md](references/convergence-test.md) を読み、skill-profiles.md の種類の節の「課題の例」に沿って `<base>/<name>/dev/evals.json` を書く。STEP-03 の表で runner を決め、`python3 <skill>/scripts/convergence.py prepare <base>/<name> --round 1 --runners <runner>` を実行し、STEP-02 の決定表で `run` と `diff` を実行するかを決める。`run` はバックグラウンドで実行し、終了を待ってから `diff` を実行する。runner が `subagent` なら、`run` の前に `convergence.py prompts` のプロンプトを Agent ツールの新しいエージェントに渡す。揺れを V1〜V8 に分類して締め込み、同じファイルの6章の表で次のラウンドを決め、`<base>/<name>/dev/convergence-report.md` に書く。最終ラウンドでは、`reviews` があれば `convergence.py review-prepare`、`run --kind review`、`review-score` でレビューの検出率も測る（同じファイルの3章）。上限のラウンドで基準を満たさない課題が残ったら、続けるかをユーザーに聞く（STEP-04）
10. フェーズ7（仕上げ）: spec の `status` を `ready` にし、`python3 <base>/<name>/scripts/install.py --project .` を実行して、`python3 <skill>/scripts/skill_lint.py <base>/<name> --final --project .` のエラーを0件にする（OUT-01）
11. `python3 <skill>/scripts/run.py check` を実行する。指摘があれば、ルールIDを「4. 決定表」で引いて作るスキルの側を直す。skill-foundation のファイルを変えて通さない（CTL-02、CTL-05）
12. 決めきれなかったことがあれば `.skill-runs/skill-foundation/notes.md` に「- 」の箇条書きで書き、`python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら手順11に戻る。finish は検査に通った後に作ったスキルを封印する（STEP-05）。終了コード0なら、出力された本文をそのまま返答する（RPT-01、RPT-02）

## 3. 入力

<!-- BEGIN GENERATED:inputs -->
| 項目 | キー | 受け付ける書き方 | 無いとき |
|---|---|---|---|
| 作るスキルの名前 | `name` | 英小文字・数字・`-` に変換。別名: スキル名、名前、skill、skill name | start の前に聞く: 何を受け取り、何を出力するスキルですか（名前はこの答えから references/intake.md の2章の規則で決める） |
| 対象の製品 | `targets` | 一覧（`,`・`、`・改行で区切る）。別名: 対象、製品、platform、platforms | 既定値 `["claude", "codex"]` |
| 言語 | `language` | `ja`、`en` のどれか（日本語→`ja`、japanese→`ja`、英語→`en`、english→`en`）。別名: lang | 既定値 `ja` |
| 本体の置き場 | `base` | `.claude/skills`、`.agents/skills` のどれか。別名: 置き場、place | 既定値 `.claude/skills` |
| 収束テストの実行 | `measure` | `ask`、`run`、`skip` のどれか（確認→`ask`、聞く→`ask`、実行→`run`、する→`run`、省く→`skip`、しない→`skip`）。別名: 収束テスト、convergence | 既定値 `ask` |

入力は `run.py start --set <キー>=<値>` で渡す。キーは表のキー・項目名・別名のどれでもよく、全角と半角、大文字と小文字、`-`・`_`・空白の違いは吸収される。契約に無いキーは無視して記録する。依頼文そのものは最後の引数に渡す。依頼文の中の「キー: 値」の行も読む。
<!-- END GENERATED:inputs -->

## 4. 決定表

<!-- BEGIN GENERATED:decisions -->
| ID | 決定 | 守らせ方 |
|---|---|---|
| IN-01 | 依頼が次の表の「対象外」に当たるときは、`run.py start` を実行せず、ファイルも作らずに、代わりに使うものを返答する。 | doc: SKILL.md の手順1と references/intake.md の6章 |
| IN-02 | 各フェーズでは次の表のファイルだけを読む。ほかのスキル作成スキル（my-skill-creator、my-skill-creater、anthropic-skills:skill-creator、Codex の skill-creator）のファイルを読まず、呼び出さない。 | doc: SKILL.md の手順（各フェーズで読むファイルを示す） |
| STEP-01 | SKILL.md の「2. 手順」のフェーズ0〜7を番号の順に行う。骨組みは `init_skill.py`、生成部分は `render_skill.py` で作り、手で書かない。`dev/spec.json` を変えたら、同じ変更の中で `render_skill.py` を実行し、決定の ID を変えたなら `dev/probes.json` の違反例と `dev/research.md` の「使った決定」も合わせる（一緒に変えるファイルの組）。各フェーズの終わりに `skill_lint.py` を実行し、エラーが0件になってから次のフェーズに進む。 | script, validate: scripts/init_skill.py、scripts/render_skill.py、scripts/skill_lint.py。契約の command 検査が、finish の前に `skill_lint.py --final --project` を実行する |
| STEP-02 | フェーズ6の収束テストは、入力 `measure` に従って次の表のとおり扱う。収束テストを省く `convergence.skip_reason` は検査を止める記法なので、書いてよいのは、表で実行しないことになったときと、STEP-03 の表で runner が無いときだけである。 | validate, doc: `skill_lint.py --final` が、収束テストの結果か `convergence.skip_reason` を求める |
| STEP-03 | 使うコマンドは `python3`（skill-foundation の `scripts/` と、作るスキルの `scripts/`）、`git`、収束テストの runner だけにする。パッケージを追加で入れない。収束テストの runner は次の表で決め、`convergence.py prepare --runners` に渡す。 | doc: SKILL.md の手順9と references/convergence-test.md の3章 |
| STEP-04 | `skill_lint.py` か `probe.py` が失敗したら、作るスキルの `dev/spec.json`、`scripts/`、SKILL.md の「2. 手順」を直してやり直す。skill-foundation のファイルは変えない。収束テストが `convergence.max_rounds` のラウンドで基準を満たさなかったら、`run.py wait --question` を実行してから、残った課題ごとに揺れの分類（V1〜V8）を示し、ラウンドを足して続けるかを聞く。続けるなら `convergence.max_rounds` を1つ増やして締め込む。続けないなら、残った課題の ID、分類、残した理由を `dev/convergence-report.md` の「結論」に1課題1行で書く。 | validate, doc: `skill_lint.py --final` が、基準を満たさない課題が「結論」に書かれているかを確かめる。skill-foundation のファイルは CTL-02 で守る |
| STEP-05 | 作ったスキルは、skill-foundation の `run.py finish` が検査に通った後に `report_skill.py --seal` で封印する（`assets/seal.json`）。封印の後に作ったスキルを変えるときは、作ったスキルの SKILL.md の「8. 制御の仕組み」の変え方に従い、`skill_lint.py <作ったスキル> --final --seal` で封印し直す。 | runtime: 契約の report.sections に stage: finish で置いた `scripts/report_skill.py --seal` を、scripts/run.py の finish が検査に通った後だけ実行する。封印は skill_lint.py --final に通った状態だけに書く |
| OUT-01 | 作るスキルの本体は、入力 `targets` から次の表で決めた `base` の下の `<base>/<name>/` に置き、`install.py --project <ルート>` で置き場所と hooks を揃える。ユーザーのホームには置かない。 | validate, script: scripts/install.py。契約の outputs.skill-entry の path と count、`skill_lint.py --final --project` の `install.py --check` |
| OUT-02 | スキルの直下には `SKILL.md`、`references/`、`assets/`、`scripts/`、`dev/` だけを置く。SKILL.md の節は「1. 使う場面」から「8. 制御の仕組み」の8つで、手で書くのは「2. 手順」だけにする。`assets/examples/` には、検査に通る出力の見本を1つ以上置く。見本は `dev/probes.json` の baseline から `from` で使い、出力を書く手順で示す。 | script, validate: scripts/init_skill.py が構成を作り、`skill_lint.py` が直下の名前・必須のファイル・節の並び・frontmatter を確かめる。見本は `skill_lint.py` が置き場・baseline の from・手順の記載を確かめ、probe.py が baseline として検査に通す |
| OUT-03 | SKILL.md、決定、references は spec の `language` で書き、references/writing.md の書き方に従う。references/variance-axes.md の5章の語を使わない。 | validate, review: `skill_lint.py` が決定と手順のあいまいな語を検出する |
| OUT-04 | スキルの名前は references/intake.md の2章の表で `<動詞>-<目的語>` に決める。決定の ID は references/variance-axes.md の4章の規則（接頭辞ごとに 01 から、軸の順）で振る。 | validate, doc: `skill_lint.py` が名前の形と、ID の形・接頭辞・番号の連続と順序を確かめる |
| OUT-05 | `triggers.use_when` は5つ以上、SKILL.md の手順は5つ以上、SKILL.md は 500 行以下、description は 1024 文字以下、`dev/evals.json` の課題は holdout 以外を3つ以上と holdout を1つ以上にする。 | validate: `skill_lint.py` が数を確かめる |
| OUT-06 | `<base>/<name>/` が既にあるときは、次の表に従う。 | script, validate, doc: scripts/init_skill.py は既にあるファイルを上書きしない。skill-foundation の形でない SKILL.md は、mode が retrofit のときだけ dev/original/SKILL.md に移し、そうでなければ止まる。skill_lint.py が、後付けのスキルに dev/original/SKILL.md と dev/research.md の「## 既存のスキル」を求める |
| RPT-01 | 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。 | runtime, validate, review: scripts/run.py の finish と abort が本文を組み立て、.skill-runs/<name>/report.md にも保存する。check と finish が notes.md の形を検査する |
| RPT-02 | 最終報告の「## 作ったスキル」から「## プロジェクトに置いたもの」までは、契約の `report.sections` に登録した `report_skill.py` の出力をそのまま使う。収束テストは、`dev/results/convergence/round-*/report.json` から作った表と、基準を満たさない課題の「結論」の行で示す。省いたときは `convergence.skip_reason` を示す。これらの節を書き足したり言い換えたりしない。 | runtime: scripts/report_skill.py。scripts/run.py の finish が契約の report.sections から実行し、出力を本文に入れる |
| CTL-01 | 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。 | runtime, validate: scripts/run.py。finish は契約の検査に通らないと終了コード1で終わる |
| CTL-02 | `run.py start` から `run.py finish` までの間、スキルの保護ファイル（`SKILL.md`、`scripts/`、`assets/`、`references/`）と、プロジェクトに登録したこのスキルの hooks を変えない。出力が契約に合わないときは、出力の方を直す。保護ファイルが封印（`assets/seal.json`）と違うと `run.py start` が終了コード1で止まるので、そのときは出力された指摘をユーザーに伝えて止まる。 | runtime, validate: scripts/run.py の start が保護ファイルのハッシュと hooks の登録を記録し、check と finish が比べる。`start --restart` は記録を最初の start から引き継ぐ。hooks が編集の前に止める。start は封印と保護ファイルを比べ、違えば始めない |
| CTL-03 | ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。 | runtime, doc: scripts/run.py の start は、聞くべき入力が無いと終了コード3で止まり、質問を出力する。wait は hooks の強制を止める |
| CTL-04 | hooks は、このスキルの実行中（status: active）に、編集の後の検査、応答を終える前の検査、保護ファイルの編集の停止の3つを行う。実行していないときは、封印したスキル（`assets/seal.json` がある）の保護ファイルの編集に、Claude Code で確認を求めることだけを行う。ユーザーの発言を止めたり書き換えたりしない。 | runtime: scripts/hook.py。install.py が Claude Code（.claude/settings.json）と Codex（.codex/hooks.json）に登録する |
| CTL-05 | `run.py start` から `run.py finish` までの間に作る・変えるファイルは、「5. 出力の契約」の出力と `control.allow_changes` に挙げたものだけにする。作業用のメモや一時ファイルも、出力の置き場の外に作らない。 | runtime, validate: scripts/run.py の start が git の作業ツリーの状態を記録し、check と finish が比べる。編集の直後には hooks が知らせる |

#### IN-01 の決定表

| 依頼 | 扱い |
|---|---|
| リポジトリ全体の規約、lint、ディレクトリ構造を作る | 対象外。pattern-foundation を示す |
| 1回限りの作業をしてほしい（繰り返し使う手順ではない） | 対象外。その作業を直接行うよう示す |
| skill-foundation で作ったスキルの決定や契約の小さな修正 | 対象外。そのスキルの `dev/spec.json` を直し、`render_skill.py` と `skill_lint.py` を実行するよう示す |
| skill-foundation で作っていない既存のスキルを、誰が使っても同じ結果になるようにしたい | 対象。spec の `mode` を `retrofit` にして手順2に進む（OUT-06） |
| 上のどれでもない | 対象。手順2に進む |

#### IN-02 の決定表

| フェーズ | 読むファイル |
|---|---|
| 0 受付 | `references/intake.md`、`references/skill-profiles.md` の種類の節 |
| 1 骨組み、2 調査 | `references/runtime.md`、`references/platforms.md`、`references/research.md`、`references/skill-profiles.md` の種類の節（調べる先） |
| 3 決める | `references/variance-axes.md`、`references/writing.md`、`references/control-ladder.md` の3章、`references/skill-profiles.md` の種類の節 |
| 4 縛る、5 証明する | `references/control-ladder.md`、`references/skill-profiles.md` の種類の節 |
| 6 測る | `references/convergence-test.md`、`references/skill-profiles.md` の種類の節 |
| 7 仕上げ | 読まない |
| 上のどれでもない | 読まない |

#### STEP-02 の決定表

| measure | 扱い |
|---|---|
| ask | `convergence.py prepare` が出したセッションの回数を示し、`run.py wait --question` の後に実行してよいかを聞く。答えが「はい」なら実行する。それ以外なら実行せず、`skip_reason` に「利用者が収束テストを省くと答えた」と書く |
| run | 聞かずに実行する |
| skip | 実行せず、`skip_reason` に「利用者が収束テストを省くと指定した」と書く |
| 上のどれでもない | ask と同じに扱う |

#### STEP-03 の決定表

| 状況 | runner |
|---|---|
| `claude` と `codex` のどちらも起動できる | spec の `convergence.runners`（既定 `claude`、`codex`） |
| 片方だけ起動できる（コマンドが無い、起動が拒否された） | 起動できる方だけ |
| どちらも起動できず、Agent ツールがある | `subagent`。`convergence.py prompts` が出したプロンプトを、会話の文脈を引き継がない新しいエージェントにそのまま渡し、最終の返答を保存先に書く |
| 上のどれでもない | 実行しない。`convergence.skip_reason` に「独立エージェントを起動できない」と書く |

#### OUT-01 の決定表

| targets | base |
|---|---|
| claude と codex | `.claude/skills`（`.agents/skills/<name>` は本体へのシンボリックリンク） |
| claude だけ | `.claude/skills` |
| codex だけ | `.agents/skills` |
| 上のどれでもない | `.claude/skills` |

#### OUT-06 の決定表

| `<base>/<name>/` の状態 | 扱い |
|---|---|
| 無い | 作る（spec の `mode` は `new`） |
| あり、`dev/spec.json` がある | 既存の spec から続ける。`init_skill.py` は既にあるファイルを上書きしない |
| あり、`dev/spec.json` が無く、`SKILL.md` がある | `run.py wait --question` を実行し、そのスキルに後付けするか、別の名前で新しく作るかを聞く。後付けなら spec の `mode` を `retrofit` にする。`init_skill.py` が元の SKILL.md を `dev/original/SKILL.md` に移し、新しい骨組みを作る。別の名前なら、その名前で続ける。どちらでもない答えなら `run.py abort` |
| 上のどれでもない | 触らない。abort して状態をユーザーに伝える |

理由・良い例・悪い例は [references/decisions.md](references/decisions.md) にある。
<!-- END GENERATED:decisions -->

## 5. 出力の契約

<!-- BEGIN GENERATED:contract -->
| 出力 | 置き場 | 件数 | 検査（ルールID） |
|---|---|---|---|
| skill-entry 作ったスキルの SKILL.md | `{in:base}/{in:name}/SKILL.md` | 1〜1 件（OUT-01） | front matter に `name`、`description` がある（OUT-02）。`^\d+\. .*run\.py finish` に一致する行がある（「2. 手順」に `run.py finish` を実行する番号付きの行を残す。編集の直後に検査する）（OUT-02）。`python3 {skill}/scripts/skill_lint.py {root}/{in:base}/{in:name} --final --project {root} --rule STEP-01` が通る。OUT-01、OUT-03、OUT-04、OUT-05、STEP-02、STEP-04、OUT-06 の指摘も出す（check・finish・応答を終える前だけ。編集の直後は検査しない）（STEP-01） |

`{run}` は実行記録の置き場 `.skill-runs/skill-foundation` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。

- 保護ファイルが実行中に変わっていない（CTL-02）
- 上の出力と、変えてよいファイル `{in:base}/{in:name}/**`、`.agents/skills/{in:name}`、`.claude/skills/{in:name}`、`.claude/settings.json`、`.codex/hooks.json`のほかに、start の後に変わったファイルが無い（CTL-05。git の作業ツリーで判定し、git が無いときは検査しない）
<!-- END GENERATED:contract -->

## 6. 完了前チェックリスト

<!-- BEGIN GENERATED:checklist -->
- [ ] OUT-03 SKILL.md、決定、references は spec の `language` で書き、references/writing.md の書き方に従う。references/variance-axes.md の5章の語を使わない。
- [ ] RPT-01 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- [ ] `python3 <skill>/scripts/run.py finish` が終了コード0で終わった
<!-- END GENERATED:checklist -->

## 7. 報告

<!-- BEGIN GENERATED:report -->
最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。決めきれなかったことは、finish の前に `.skill-runs/skill-foundation/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを「## 補足」に入れる。中断するときは `run.py abort --reason <理由>` を実行し、abort が出力した本文を同じようにそのまま使う。本文の形は次のとおり。

```text
## 結果

skill-foundation: 完了（検証に合格）

<`python3 {skill}/scripts/report_skill.py {root}/{in:base}/{in:name} --project {root}` の出力>

<`python3 {skill}/scripts/report_skill.py {root}/{in:base}/{in:name} --project {root} --seal` の出力>

## 出力

- `<パス>`（<出力ID> <出力の名前>）

## 既定値で決めた値

- <項目>（<キー>）: <値>（無ければ「- なし」）

## 入力で読めなかった値

- <内容>（無ければ「- なし」）

## 検証

- `run.py finish`: 指摘 0 件

## 補足

- <notes.md の箇条書き。無ければ「- なし」>
```
<!-- END GENERATED:report -->

## 8. 制御の仕組み

<!-- BEGIN GENERATED:control -->
| 仕組み | いつ働くか | 何をするか |
|---|---|---|
| `scripts/run.py start` | 手順の始め | 入力を正規化し（表記ゆれ・全角・未知のキーを受け入れる）、既定値で補い、保護ファイルのハッシュと git の作業ツリーの状態を記録する。保護ファイルが封印（`assets/seal.json`）と違えば始めない（終了コード1） |
| `scripts/run.py check` と `finish` | 出力を書いた後と最後 | 契約（`assets/contract.json`）の format で出力を直してから検査する。finish は通ったときだけ実行を終える |
| hooks の pre-tool | ファイルを編集する前 | 保護ファイルと実行記録の編集を止める（Claude Code は確認を求め、Codex は拒否する）。実行していないときも、封印したスキルの保護ファイルの編集に Claude Code で確認を求める |
| hooks の post-tool | ファイルを編集した後 | 出力に当たるファイルを format で直し、検査し、指摘を返す。出力でも変えてよいファイルでもなければ CTL-05 の指摘を返す |
| hooks の stop | 応答を終える前 | 出力全体を検査し、通るまで応答を終えさせない（最大 3 回。超えると status: failed） |
| hooks の prompt | ユーザーが発言したとき | 質問待ち（wait）を解くだけ。発言を止めたり書き換えたりしない |

hooks は、このスキルの実行中（`.skill-runs/skill-foundation/state.json` の status が active）だけ出力を検査する。hooks が無い環境でも、`run.py check` と `finish` が同じ検査をする。

hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（Claude Code は `.claude/settings.json`、Codex は `.codex/hooks.json` に追記する。Codex では、追記した hooks を `/hooks` で信頼するまで動かない）

保護ファイル（スキルのディレクトリからの相対パス）: `SKILL.md`、`scripts/**`、`assets/**`、`references/**`

このスキル（決定、契約、手順、スクリプト）を変えるときは、次の順にする。保護ファイルだけを直接書き換えると、封印と違うため次の `run.py start` が止まる（CTL-02）。`<skill-foundation>` は skill-foundation のディレクトリを指す。

1. 実行中なら `python3 <skill>/scripts/run.py abort --reason <理由>` で止める
2. `dev/spec.json` を直す。手で書く部分（この SKILL.md の「2. 手順」、`scripts/` のスキル固有のスクリプト、`references/`、`assets/examples/`）は直接直す
3. `python3 <skill-foundation>/scripts/render_skill.py --dir <skill>` で生成した部分を作り直す
4. 決定や契約を変えたなら `dev/probes.json` の違反例も合わせ、`python3 <skill-foundation>/scripts/probe.py <skill>` を通す
5. `python3 <skill-foundation>/scripts/skill_lint.py <skill> --final --seal` を通す。通ると封印し直す
<!-- END GENERATED:control -->
