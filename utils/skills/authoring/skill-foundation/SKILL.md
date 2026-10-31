---
name: skill-foundation
description: "作りたいスキルの依頼から、ユーザーと確かめた価値の Eval、ルール・出力の契約・hooks とスクリプトによる制御・違反例・収束テストを備え、Claude Code と Codex のどちらでも同じ結果になるスキルを作る。「スキルを作って」、「コミットメッセージを書くスキルを作って」、「誰が使っても同じ結果になるスキルにしたい」、「Codex でも Claude Code でも使えるスキルを作成して」、「hooks とスクリプトで出力を縛るスキルを作って」、「この作業手順を SKILL.md にまとめてスキル化して」、「この既存のスキルを、誰が使っても同じ結果になるように作り直して」、「Create a skill that gives the same result on any AI」と頼まれたときに使う。リポジトリ全体の規約・lint・ディレクトリ構造を作る依頼には使わない（代わりにpattern-foundationを使う）。skill-foundation で作ったスキルのルールや契約の小さな修正には使わない（代わりにそのスキルの dev/spec.json の修正と render_skill.pyを使う）。"
---

# 誰が使っても同じ結果になるスキルを作る

<!-- BEGIN GENERATED:purpose -->
作りたいスキルの依頼から、ユーザーと確かめた価値の Eval、ルール・出力の契約・hooks とスクリプトによる制御・違反例・収束テストを備え、Claude Code と Codex のどちらでも同じ結果になるスキルを作る
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
- skill-foundation で作ったスキルのルールや契約の小さな修正 → 代わりに: そのスキルの dev/spec.json の修正と render_skill.py

依頼の内容から自動で選ばれる。明示して呼ぶときは Claude Code では `/skill-foundation`、Codex では `$skill-foundation` と書く。
<!-- END GENERATED:triggers -->

## 2. 手順

このファイルがあるディレクトリを `<skill>` と呼ぶ。スクリプトは Python 3.9 以上の標準ライブラリだけで動く。手順は番号の順に行い、飛ばさない。

1. 依頼が [references/intake.md](references/intake.md) の6章の対象外に当たるかを確かめる。当たれば start せず、ファイルも作らずに、代わりに使うものを返答して終える（IN-01）。当たらなければ、同じファイルの1章の表で「聞く」とある項目が依頼に無いかを確かめ、無ければここでまとめてユーザーに聞く（CTL-03）
2. 名前を intake.md の2章（OUT-04）で、依頼文の言語を3章の表で決め、`python3 <skill>/scripts/run.py start --set name=<名前> --guess language=<依頼文の言語> "<依頼文>"` を実行する。`targets`、`language`、`base`、`measure`、`eval` は、依頼に指定があるときだけ `--set <キー>=<値>` で足す（intake.md の1章）。指定の無い値は、start が `<skill>/settings/user-setting.yaml`（ユーザーの設定）、`<skill>/settings/skill-setting.yaml`（スキルの設定）、`--guess`、既定値の順に補い、出どころを出力する（置き場は4章の表で `targets` から決まる。OUT-01）。終了コード3なら、出力された質問をユーザーに聞き、答えを `--set` で渡してやり直す（CTL-01）
3. Eval 作成: `<base>/<name>/` の状態を OUT-06 の場合分けで確かめ、`mode` を `new` か `retrofit`（後付け）に決める。[references/eval.md](references/eval.md) を読み、STEP-06 の場合分けで Eval を作るかを決める。作らないなら、`<base>/<name>/dev/eval/eval.json` に `skip_reason` だけを書く。作るなら、`<skill>/assets/templates/eval.example.json` を `<base>/<name>/dev/eval/eval.json` に写す。ユーザーに聞くことは eval.md の2章の聞き方で聞く。聞くことを eval.json の `questions` に書き、`python3 <skill>/scripts/eval_check.py <base>/<name>` と `python3 <skill>/scripts/catalog.py --project .` を実行し、`run.py wait --question` を実行してから、カタログの `.skill-runs/catalog/<name>.html` の「Eval 作成」タブで答えて回答の文をチャット欄に貼るよう、ユーザーに伝える。貼られた文は言い換えずに `python3 <skill>/scripts/eval_check.py <base>/<name> --answer -` の標準入力に渡す。こうして聞いた材料（利用場面、今の不満や失敗、望む結果、許容できない結果）から、eval.md の順に、価値仮説、ユーザーと確定した価値、外から確かめられる振る舞い、成功と失敗の事例、正解の根拠、判定方法を書き、事例の出力の見本を `<base>/<name>/dev/eval/cases/` に置く。Eval を作り、入力 `measure` が `skip` でなければ、続けて eval.md の8章に従い、`<skill>/assets/templates/evals.example.json` を `<base>/<name>/dev/evals.json` に写して収束テストの題材の案を書き、同じ聞き方でユーザーと確かめる。どちらのときも `python3 <skill>/scripts/eval_check.py <base>/<name>` のエラーを0件にしてから次の手順に進む（STEP-06）
4. フェーズ0（受付）: `<skill>/assets/templates/spec.example.json` を `<base>/<name>/dev/spec.json` に写し、受付の項目（`name`、`kind`、`mode`、`language`、`targets`、`title`、`purpose`、`triggers`）を intake.md に従って埋める（手順3で既存の spec から続けると決めたときは写さない）。`mode` は手順3で決めた値にする。Eval を作ったなら、`purpose` は `dev/eval/eval.json` の確定した価値から、`triggers.use_when` は利用場面から書く。`kind` は名前の動詞にし、[references/skill-profiles.md](references/skill-profiles.md) のその種類の節を読む（OUT-05）
5. フェーズ1（骨組み）: `python3 <skill>/scripts/init_skill.py --dir <base>/<name>` を実行し、`python3 <skill>/scripts/skill_lint.py <base>/<name> --phase 1` のエラーを0件にする（STEP-01、OUT-02）
6. フェーズ2（調査）: [references/runtime.md](references/runtime.md)、[references/platforms.md](references/platforms.md)、[references/research.md](references/research.md) を読む。作るスキルが前提にする事実（コマンドの引数、ファイルの形式、製品の仕様）を、research.md の1章の順の情報源と、skill-profiles.md の種類の節の「調べる先」で確かめ、`<base>/<name>/dev/research.md` に出典、確かめた日付、確認の状態を付けて書く。プロジェクトに既にある書き方に合わせるルールは、決まりを書いた場所を「- 決まり：」の行に、数えた結果を「- 分布：」の行に書く（research.md の3章）。後付けなら、元の SKILL.md（`dev/original/SKILL.md`）を「## 既存のスキル」に書く（IN-02）。「使ったルール」の行は、ルールID が決まる手順7で埋めるので、ここでは空けておく。固有のスクリプト、見本、fixture はまだ作らない（手順8・9で作る）。この手順の `skill_lint.py` は無く、次の手順7で一緒に確かめる
7. フェーズ3（決める）: [references/variance-axes.md](references/variance-axes.md)、[references/writing.md](references/writing.md)、[references/control-ladder.md](references/control-ladder.md) の3章、skill-profiles.md の種類の節の「軸の読み替え」を読み、軸（種類の追加の軸を含む）ごとに spec の `decisions` と `excluded_axes` を書く。ルールごとに決めた根拠（`basis`）を variance-axes.md の2章の順で選ぶ。skill-profiles.md の種類の節の「入力の候補」は、`inputs` に同じ key で入れるか、`excluded_inputs` に key と理由を書く。入力ごとに、既定値で進めたときの影響（`impact`）から `ask` か `default` を決めて `inputs` を書く。決めたルールID を、根拠にした `dev/research.md` の項目の「使ったルール」の行に書いてから、`python3 <skill>/scripts/skill_lint.py <base>/<name> --phase 3` のエラーを0件にする（OUT-03、OUT-04）
8. フェーズ4（縛る）: [references/control-ladder.md](references/control-ladder.md) を読み、ルールごとの段（`control`）と機械にしない理由（`why_not_machine`）を control-ladder.md の1章の順で決め、spec の `outputs`（`checks` と自動で直す `format`）、一緒に変える出力の組（`together`）、スキル固有の `scripts/`、検査に通る出力の見本（`<base>/<name>/assets/examples/` と、見本が体現するルールID を挙げた spec の `examples`）、`<base>/<name>/SKILL.md` の「2. 手順」を書く。契約の検査は、skill-profiles.md の種類の節の「検査の候補」から選ぶ。Eval を作ったなら、[references/eval.md](references/eval.md) の7章を読み、`<base>/<name>/dev/eval/eval.json` の code と model の振る舞いに、判定するファイルの場所（`target`）を書く（STEP-07）。`python3 <skill>/scripts/render_skill.py --dir <base>/<name>` を実行し、`python3 <skill>/scripts/skill_lint.py <base>/<name> --phase 4` のエラーを0件にする（STEP-01、OUT-02）
9. フェーズ5（証明する）: `<base>/<name>/dev/probes.json` に baseline と違反例を書く。baseline の `files` の1つ以上は `from` で見本にし、違反例は1つにつき1つのルールだけを破る。段 format のルールの違反例には、直した後に消えるはずの正規表現を `fixed` に書く。段 review のルールには、違反を入れた見本を `reviews` に書く（control-ladder.md の7章）。`python3 <skill>/scripts/probe.py <base>/<name>` をすべて成功させ、`python3 <skill>/scripts/skill_lint.py <base>/<name> --phase 5` のエラーを0件にする。失敗したら STEP-04 に従い、作るスキルの側を直す
10. フェーズ6（測る）: [references/convergence-test.md](references/convergence-test.md) を読む。`<base>/<name>/dev/evals.json` の題材は手順3でユーザーと確かめたものを使い、ここでは fixture（`dev/fixtures/basic`）の中身と `setup` を仕上げる。手順3で題材を書いていなければ（Eval か収束テストを省いたとき）、skill-profiles.md の種類の節の「課題の例」に沿って書く。evals.json の検査は手順11の `--final` が行い、この手順の `skill_lint.py` は無い。入力 `measure` が `skip` なら、`convergence.py` は1つも実行せず、spec の `convergence.skip_reason` を書き、`<base>/<name>/dev/convergence-report.md` をひな形の表の節を消して「## 結論」に省いた理由だけを書いた形にして、手順11へ進む（STEP-02）。それ以外なら、STEP-03 の表で runner を決め、`python3 <skill>/scripts/convergence.py prepare <base>/<name> --round 1` を実行する（片方だけ起動できるときは `--runners <runner>` を、依頼にモデルや推論エフォートの指定があれば `--model <runner>=<値>`・`--effort <runner>=<値>` を足す）。prepare が表示した runner、人数、ラウンドの上限、モデルで測り、STEP-02 の場合分けで `run` と `diff` を実行するかを決める。`run` はバックグラウンドで実行し、終了を待ってから `diff` を実行する。runner が `subagent` なら、`run` の前に `convergence.py prompts` のプロンプトを Agent ツールの新しいエージェント（subagent_type は `skill-foundation-tester`。prompts が model・effort を示したら、それも指定する）に渡す。`diff` の後に、`convergence.py analysis-prepare`、`prompts --kind analysis`（runner `subagent`）か `run --kind analysis`、`analysis-collect` で、各エージェントの動きを別の AI に分析させる（同じファイルの3章）。Eval を作ったなら、`diff` が code の判定を、`analysis-collect` が分析役の model の判定を各エージェントの出力に当てる。Eval に落ちた判定と、Eval で確かめていない動きの指摘を、eval.md の7章の表で分類して `<base>/<name>/dev/convergence-report.md` の「## Eval の採点」の表に書き、Eval の疑いか抜けがあれば、`run.py wait --question` を実行してからユーザーとすり合わせて Eval を直し、`eval_check.py` のエラーを0件にしてから次のラウンドに進む（STEP-07）。ばらつきと、`analysis-collect` が書く `analysis.md` の動きの指摘（基準を満たした課題のものも）を V1〜V8 に分類して締め込み、同じファイルの6章の表で次のラウンドを決め、`<base>/<name>/dev/convergence-report.md` に書く（動きの指摘は「## 動きの指摘」の表。同じファイルの5章・7章）。最終ラウンドでは、`reviews` があれば `convergence.py review-prepare`、`run --kind review`、`review-score` でレビューの検出率も測る（同じファイルの3章）。上限のラウンドで基準を満たさない課題が残ったら、続けるかをユーザーに聞く（STEP-04）
11. フェーズ7（仕上げ）: spec の `status` を `ready` にし、`python3 <base>/<name>/scripts/install.py --project .` を実行して、`python3 <skill>/scripts/skill_lint.py <base>/<name> --final --project .` のエラーを0件にする（OUT-01）
12. `python3 <skill>/scripts/run.py check` を実行する。指摘があれば、ルールIDを「4. ルール」で引いて作るスキルの側を直す。
13. 決めきれなかったことがあれば `.skill-runs/skill-foundation/notes.md` に「- 」の箇条書きで書き、`python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら手順12に戻る。終了コード0なら、出力された本文をそのまま返答する（RPT-01、RPT-02）

利用中の指摘を基に既存のスキルを改善するときは、先に [references/feedback.md](references/feedback.md) の3章で承認済みの収集記録とスキルの作業用コピーを準備し、そのコピーで Eval 作成と収束テストを進める。成果物の承認を、一般化した評価条件への承認として扱わない。

## 3. 入力

<!-- BEGIN GENERATED:inputs -->
| 項目 | キー | 受け付ける書き方 | 無いとき |
|---|---|---|---|
| 作るスキルの名前 | `name` | 英小文字・数字・`-` に変換。別名: スキル名、名前、skill、skill name | start の前に聞く: 何を受け取り、何を出力するスキルですか（名前はこの答えから references/intake.md の2章の規則で決める） |
| 対象の製品 | `targets` | 一覧（`,`・`、`・改行で区切る）。別名: 対象、製品、platform、platforms | 既定値 `["claude", "codex"]` |
| 言語 | `language` | `ja`、`en` のどれか（日本語→`ja`、japanese→`ja`、英語→`en`、english→`en`）。別名: lang | 既定値 `ja` |
| 本体の置き場 | `base` | `.claude/skills`、`.agents/skills` のどれか。別名: 置き場、place | `targets` が `codex` なら `.agents/skills`。ほかは既定値 `.claude/skills` |
| 収束テストの実行 | `measure` | `ask`、`run`、`skip` のどれか（確認→`ask`、聞く→`ask`、実行→`run`、する→`run`、省く→`skip`、しない→`skip`）。別名: 収束テスト、convergence | 既定値 `ask` |
| Eval の作成 | `eval` | `make`、`skip` のどれか（作る→`make`、する→`make`、省く→`skip`、しない→`skip`）。別名: 評価、evaluation | 既定値 `make` |

入力は `run.py start --set <キー>=<値>` で渡す。キーは表のキー・項目名・別名のどれでもよく、全角と半角、大文字と小文字、`-`・`_`・空白の違いは吸収される。契約に無いキーは無視して記録する。依頼文そのものは最後の引数に渡す。依頼文の中の「キー: 値」の行も読む。

依頼に指定の無い入力は、`settings/user-setting.yaml`（ユーザーの設定）、`settings/skill-setting.yaml`（このスキルの設定）の `inputs` の順に、null でない最初の値で補い、どちらにも無ければ表の「無いとき」に従う。依頼文から推した値は `--guess <キー>=<値>` で渡し、設定より弱く、表の既定値より強い。どこから補ったかは start の出力と報告の「既定値で決めた値」に出る。
<!-- END GENERATED:inputs -->

## 4. ルール

<!-- BEGIN GENERATED:decisions -->
| ID | ルール | 守らせ方 |
|---|---|---|
| IN-01 | 依頼が次の表の「対象外」に当たるときは、`run.py start` を実行せず、ファイルも作らずに、代わりに使うものを返答する。 | doc: SKILL.md の手順1と references/intake.md の6章 |
| IN-02 | 手順3の Eval 作成と各フェーズでは、次の表のファイルだけを読む。ほかのスキル作成スキル（my-skill-creator、my-skill-creater、anthropic-skills:skill-creator、Codex の skill-creator）のファイルを読まず、呼び出さない。 | doc: SKILL.md の手順（手順3の Eval 作成と各フェーズで読むファイルを示す） |
| STEP-01 | SKILL.md の「2. 手順」を番号の順に行う（手順3の Eval 作成の後に、フェーズ0〜7）。骨組みは `init_skill.py`、生成部分は `render_skill.py` で作り、手で書かない。`dev/spec.json` を変えたら、同じ変更の中で `render_skill.py` を実行し、ルールID を変えたなら `dev/probes.json` の違反例と `dev/research.md` の「使ったルール」も合わせる（一緒に変えるファイルの組）。各フェーズの終わりに `skill_lint.py` を実行し、エラーが0件になってから次のフェーズに進む。 | script, validate: scripts/init_skill.py、scripts/render_skill.py、scripts/skill_lint.py。契約の command 検査が、finish の前に `skill_lint.py --final --project` を実行する |
| STEP-02 | フェーズ6の収束テストは、入力 `measure` に従って次の表のとおり扱う。収束テストを省く `convergence.skip_reason` は検査を止める記法なので、書いてよいのは、表で実行しないことになったときと、STEP-03 の表で runner が無いときだけである。 | validate, doc: `skill_lint.py --final` が、収束テストの結果（各ラウンドの、今の記録を読んだ AI の分析を含む）か `convergence.skip_reason` を求める。`convergence.py prepare` は、`skip_reason` があると止まる |
| STEP-03 | 使うコマンドは `python3`（skill-foundation の `scripts/` と、作るスキルの `scripts/`）、`git`、収束テストの runner だけにする。パッケージを追加で入れない。収束テストの runner は次の表で決める。`convergence.py prepare` は、`--runners` が無ければ、作るスキルの spec の `convergence.runners`、`settings/user-setting.yaml`、`settings/skill-setting.yaml` の順に、null でない最初の値を使う。エージェントのモデルと推論エフォートも同じ順の `convergence.model`・`convergence.effort` に従い、prepare が runner の起動コマンドに足す（runner `subagent` は、`convergence.py prompts` が示す値で Agent ツールを起動する）。 | doc: SKILL.md の手順10と references/convergence-test.md の3章 |
| STEP-04 | `skill_lint.py` か `probe.py` が失敗したら、作るスキルの `dev/spec.json`、`scripts/`、SKILL.md の「2. 手順」を直してやり直す。収束テストの各ラウンドでは、`convergence.py analysis-collect` が書く `analysis.md` の指摘を、基準を満たした課題のものも記録で確かめ、V1〜V8 か推定違いに分類して、`dev/convergence-report.md` の「## 動きの指摘」の表に書いてから次のラウンドへ進む。収束テストがラウンドの上限（`convergence.py prepare` が示す `max_rounds`。STEP-03 と同じ順で決まる）で基準を満たさなかったら、`run.py wait --question` を実行してから、残った課題ごとにばらつきの分類（V1〜V8）を示し、ラウンドを足して続けるかを聞く。続けるなら、作るスキルの spec の `convergence.max_rounds` に今の上限より1つ大きい値を書いて締め込む。続けないなら、残った課題の ID、分類、残した理由を `dev/convergence-report.md` の「結論」に1課題1行で書く。 | validate, doc: `skill_lint.py --final` が、基準を満たさない課題が「結論」に書かれているかと、AI の分析に指摘のあるエージェントが「## 動きの指摘」の表にあるかを確かめる。次のラウンドの `convergence.py prepare` も、前のラウンドの表が揃うまで止まる |
| STEP-06 | SKILL.md の手順3では、受付の前に Eval を作る。作るかは次の表で決める。作るときは references/eval.md の順に、材料（利用場面、今の不満や失敗、望む結果、許容できない結果）から価値仮説を立て、ユーザーとの対話で確定した価値を、外から確かめられる振る舞い、成功と失敗の事例、正解の根拠、判定方法に落として `<base>/<name>/dev/eval/eval.json` に書く。ユーザーに聞くことは eval.json の `questions` に書き、カタログの「Eval 作成」タブで答えてもらい、チャット欄に貼られた回答を `eval_check.py --answer` で `dialog` に記録する。Eval を作り、入力 `measure` が `skip` でなければ、続けて収束テストの題材（`<base>/<name>/dev/evals.json`）の案を書き、同じ聞き方でユーザーと確かめる。作らないときは `skip_reason` だけを書く。`skip_reason` は Eval の検査を止める記法なので、書いてよいのは表で作らないことになったときだけである。どちらのときも `eval_check.py` のエラーを0件にしてから受付に進む。 | script, validate, doc: scripts/eval_check.py が Eval 自体を検証し、結果を dev/results/eval-check.json に書く。答えを待っている質問（questions）があるあいだは、そのことを指摘して止める。`--answer` が貼られた回答を言い換えずに dialog に記録する。scripts/catalog.py が、質問を「Eval 作成」タブに1枚ずつ削って開くカードで出し、回答をチャット欄に貼る文にまとめる。収束テストの題材は、同じタブに最後の回答の時の版との違いのラベルを付けて載せる（合意した後に変えても止めない）。`skill_lint.py --final` が、今の Eval が eval_check.py の検査に通っていることか、`skip_reason` を求める |
| STEP-07 | Eval を作ったときは、フェーズ4で、code と model の振る舞いに判定するファイルの場所（`target`。出力の契約の置き場と同じ書き方で、`#<要素の id>` を付けると HTML のその要素だけを判定する）を書く。収束テストの各ラウンドでは、`convergence.py diff` が code の判定を当て、`analysis-collect` が分析役の model の判定を取り込む。Eval に落ちた出力がある課題は、基準を満たさない。締め込みでは、落ちた判定と、`analysis.md` の指摘のうち Eval のどの振る舞いも確かめていない問題を、次の表で分類し、`dev/convergence-report.md` の「## Eval の採点」の表に、ラウンド、課題/エージェント、振る舞い、分類、対処を書く。Eval の疑いか抜けがあれば、次のラウンドに進む前に、`run.py wait --question` を実行してからユーザーとすり合わせ、対話を `dialog` に足して `dev/eval/eval.json` を直し、`eval_check.py` のエラーを0件にする。そのラウンドで収束テストを終えるとき（STEP-04 で続けないと決めたとき、または最終ラウンドで全課題が基準を満たしたとき）は、Eval を直さず、疑いと抜けの振る舞い（抜けは価値）の ID、分類、残した理由を `dev/convergence-report.md` の「結論」に1件1行で書く。直すのは次にラウンドを足すときで、そのときは `convergence.py prepare` が直すまで止まる。 | script, validate, doc: scripts/convergence.py の diff が code の判定を report.json に書き、analysis-prepare が model の判定を分析役に頼み、analysis-collect が取り込んで課題の基準を決め直す。scripts/skill_lint.py の `--phase 4` が target を、次のラウンドの `convergence.py prepare` と `skill_lint.py --final` が、判定待ち、「## Eval の採点」の表の分類と対処、Eval の疑いか抜けの後に Eval を直したか（`skill_lint.py --final` は、最後のラウンドなら「結論」に残したかでもよい）、最後のラウンドを今の Eval で採点したかを確かめる |
| OUT-01 | 作るスキルの本体は、入力 `targets` から次の表で決めた `base` の下の `<base>/<name>/` に置き、`install.py --project <ルート>` で置き場所と hooks を揃える。共通正本を管理する場合は、プロジェクト内の `utils/skills/.../<name>/` に本体を保持し、対象製品すべての標準の置き場を本体へのリンクにしてよい（references/platforms.md の1章）。ユーザーのホームには置かない。 | validate, script: scripts/install.py。契約の outputs.skill-entry の path と count、`skill_lint.py --final --project` の本体の場所と `install.py --check`（対象製品の置き場が本体か、本体へのリンクか） |
| OUT-02 | スキルの直下には `SKILL.md`、`references/`、`assets/`、`scripts/`、`dev/` だけを置く。既定値を設定で変えられるスキルは、`settings/` に `skill-setting.yaml`（スキルの設定）と `user-setting.yaml`（ユーザーの設定）だけを置いてよい。SKILL.md の節は「1. 使う場面」から「8. 制御の仕組み」の8つで、手で書くのは「2. 手順」だけにする。`assets/examples/` には、検査に通る出力の見本を1つ以上置く。見本は `dev/probes.json` の baseline から `from` で使い、出力を書く手順で示す。 | script, validate: scripts/init_skill.py が構成を作り、`skill_lint.py` が直下の名前・必須のファイル・節の並び・frontmatter と、settings/ の2つのファイルの形（入力の key と type、収束テストの項目）を確かめる。見本は `skill_lint.py` が置き場・baseline の from・手順の記載を確かめ、probe.py が baseline として検査に通す |
| OUT-03 | SKILL.md、ルール、references は spec の `language` で書き、references/writing.md の書き方に従う。references/variance-axes.md の5章の語を使わない。 | validate, review: `skill_lint.py` がルールと手順のあいまいな語を検出する |
| OUT-04 | スキルの名前は references/intake.md の2章の表で `<動詞>-<目的語>` に決める。ルールID は references/variance-axes.md の4章の規則（接頭辞ごとに 01 から、軸の順）で振る。 | validate, doc: `skill_lint.py` が名前の形と、ID の形・接頭辞・番号の連続と順序を確かめる |
| OUT-05 | `triggers.use_when` は5つ以上、SKILL.md の手順は5つ以上、SKILL.md は 500 行以下、description は 1024 文字以下、`dev/evals.json` の課題は holdout 以外を3つ以上と holdout を1つ以上にする。 | validate: `skill_lint.py` が数を確かめる |
| OUT-06 | `<base>/<name>/` が既にあるときは、次の表に従う。 | script, validate, doc: scripts/init_skill.py は既にあるファイルを上書きしない。skill-foundation の形でない SKILL.md は、mode が retrofit のときだけ dev/original/SKILL.md に移し、そうでなければ止まる。skill_lint.py が、後付けのスキルに dev/original/SKILL.md と dev/research.md の「## 既存のスキル」を求める |
| RPT-01 | 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。 | runtime, validate, review: scripts/run.py の finish と abort が本文を組み立て、.skill-runs/<name>/report.md にも保存する。check と finish が notes.md の形を検査する |
| RPT-02 | 最終報告の「## 作ったスキル」から「## プロジェクトに置いたもの」までは、契約の `report.sections` に登録した `report_skill.py` の出力をそのまま使う。収束テストは、`dev/results/convergence/round-*/report.json` から作った表と、基準を満たさない課題の「結論」の行で示す。省いたときは `convergence.skip_reason` を示す。「## カタログ」は `catalog.py` の出力をそのまま使う。`catalog.py` は、finish が検査に通った後に、プロジェクトのスキルのワークフロー図と検証の記録を `.skill-runs/catalog.html` に作り直す。これらの節を書き足したり言い換えたりしない。 | runtime: scripts/report_skill.py と scripts/catalog.py。scripts/run.py の finish が契約の report.sections から実行し、出力を本文に入れる（catalog.py は stage: finish） |
| CTL-01 | 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。 | runtime, validate: scripts/run.py。finish は契約の検査に通らないと終了コード1で終わる |
| CTL-03 | ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。 | runtime, doc: scripts/run.py の start は、聞くべき入力が無いと終了コード3で止まり、質問を出力する。wait は hooks の強制を止める |
| CTL-04 | hooks は実行中（status: active）に、編集の後と応答を終える前に出力を検査する。実行記録への直接の編集は拒否する。ユーザーの発言を止めたり書き換えたりしない。hooks が無くても run.py check と finish で同じ出力の検査を行う。 | runtime: scripts/hook.py。install.py が Claude Code（.claude/settings.json）と Codex（.codex/hooks.json）に登録する |

#### IN-01 の場合分け

| 依頼 | 扱い |
|---|---|
| リポジトリ全体の規約、lint、ディレクトリ構造を作る | 対象外。pattern-foundation を示す |
| 1回限りの作業をしてほしい（繰り返し使う手順ではない） | 対象外。その作業を直接行うよう示す |
| skill-foundation で作ったスキルのルールや契約の小さな修正 | 対象外。そのスキルの `dev/spec.json` を直し、`render_skill.py` と `skill_lint.py` を実行するよう示す |
| skill-foundation で作っていない既存のスキルを、誰が使っても同じ結果になるようにしたい | 対象。spec の `mode` を `retrofit` にして手順2に進む（OUT-06） |
| 上のどれでもない | 対象。手順2に進む |

#### IN-02 の場合分け

| 手順 | 読むファイル |
|---|---|
| Eval 作成（手順3） | `references/eval.md`、`assets/templates/eval.example.json`。収束テストの題材を書くときは、`assets/templates/evals.example.json`、`references/convergence-test.md` の1章、`references/skill-profiles.md` の種類の節（課題の例）。後付けなら元の `<base>/<name>/SKILL.md` |
| 0 受付 | `references/intake.md`、`references/skill-profiles.md` の種類の節 |
| 1 骨組み、2 調査 | `references/runtime.md`、`references/platforms.md`、`references/research.md`、`references/skill-profiles.md` の種類の節（調べる先） |
| 3 決める | `references/variance-axes.md`、`references/writing.md`、`references/control-ladder.md` の3章、`references/skill-profiles.md` の種類の節 |
| 4 縛る、5 証明する | `references/control-ladder.md`、`references/skill-profiles.md` の種類の節。Eval を作ったなら `references/eval.md` の7章 |
| 6 測る | `references/convergence-test.md`、`references/skill-profiles.md` の種類の節。Eval を作ったなら `references/eval.md` の7章 |
| 7 仕上げ | 読まない |
| 上のどれでもない | 読まない |

#### STEP-02 の場合分け

| measure | 扱い |
|---|---|
| ask | `convergence.py prepare` が出したセッションの回数を示し、`run.py wait --question` の後に実行してよいかを聞く。答えが「はい」なら実行する。それ以外なら実行せず、`skip_reason` に「利用者が収束テストを省くと答えた」と書く |
| run | 聞かずに実行する |
| skip | 実行せず（`convergence.py prepare` も実行しない）、`skip_reason` に「利用者が収束テストを省くと指定した」と書く |
| 上のどれでもない | ask と同じに扱う |

#### STEP-03 の場合分け

| 状況 | runner |
|---|---|
| `claude` と `codex` のどちらも起動できる | `convergence.py prepare` が上の順で決めた runner（`--runners` を渡さない） |
| 片方だけ起動できる（コマンドが無い、起動が拒否された） | 起動できる方だけ（`--runners` に渡す） |
| どちらも起動できず、Agent ツールがある | `subagent`。`convergence.py prompts` が出したプロンプトを、専用のエージェント型 `skill-foundation-tester`（prepare が `.claude/agents/` に置く。fence.py（作業ディレクトリの外への操作を止める仕組み）が働く）の新しいエージェントにそのまま渡し、最終の返答を保存先に書く |
| 上のどれでもない | 実行しない。`convergence.skip_reason` に「独立エージェントを起動できない」と書く |

#### STEP-06 の場合分け

| 状況 | 扱い |
|---|---|
| `eval` が `make` で、ユーザーに質問できる | 作る。質問の前に `run.py wait --question` を実行する（CTL-03） |
| `eval` が `skip` | 作らず、`skip_reason` に「利用者が Eval を省くと指定した」と書く |
| ユーザーに質問できない（依頼文だけで動く独立エージェントとして実行している） | 作らず、`skip_reason` に「利用者に価値を確かめられない」と書く |
| 上のどれでもない | `make` と同じに扱う |

#### STEP-07 の場合分け

| 状況 | 分類と扱い |
|---|---|
| 落ちた出力が、確定した価値を満たしていない（判定が正しい） | 出力の誤り。ばらつきと同じく、作るスキルの側を直す |
| 落ちた出力が、確定した価値を満たしている。または判定が課題の状況に合わない | Eval の疑い。ユーザーとすり合わせて、振る舞い・判定方法・事例を直す |
| `analysis.md` の指摘の問題を、Eval のどの振る舞いも確かめていない | Eval の抜け。ユーザーとすり合わせて、振る舞いと事例を足す |
| 上のどれでもない | 出力の誤りと同じに扱う |

#### OUT-01 の場合分け

| targets | base |
|---|---|
| claude と codex | `.claude/skills`（`.agents/skills/<name>` は本体へのシンボリックリンク） |
| claude だけ | `.claude/skills` |
| codex だけ | `.agents/skills` |
| 上のどれでもない | `.claude/skills` |

#### OUT-06 の場合分け

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
| skill-entry 作ったスキルの SKILL.md | `{in:base}/{in:name}/SKILL.md` | 1〜1 件（OUT-01） | front matter に `name`、`description` がある（OUT-02）。`^\d+\. .*run\.py finish` に一致する行がある（「2. 手順」に `run.py finish` を実行する番号付きの行を残す。編集の直後に検査する）（OUT-02）。`python3 {skill}/scripts/skill_lint.py {root}/{in:base}/{in:name} --final --project {root} --rule STEP-01` が通る。OUT-01、OUT-03、OUT-04、OUT-05、STEP-02、STEP-04、OUT-06、STEP-06、STEP-07 の指摘も出す（check・finish・応答を終える前だけ。編集の直後は検査しない）（STEP-01） |

`{run}` は実行記録の置き場 `.skill-runs/skill-foundation` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。

<!-- END GENERATED:contract -->

## 6. 完了前チェックリスト

<!-- BEGIN GENERATED:checklist -->
- [ ] OUT-03 SKILL.md、ルール、references は spec の `language` で書き、references/writing.md の書き方に従う。references/variance-axes.md の5章の語を使わない。
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

<`python3 {skill}/scripts/catalog.py --project {root}` の出力>

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
| `scripts/run.py start` | 手順の始め | 入力を正規化し（表記ゆれ・全角・未知のキーを受け入れる）、既定値で補い、実行記録を作る |
| `scripts/run.py check` と `finish` | 出力を書いた後と最後 | 契約（`assets/contract.json`）の format で出力を直してから検査する。finish は通ったときだけ実行を終える |
| hooks の pre-tool | ファイルを編集する前 | 実行記録への直接の編集を拒否する。スキル自身のファイルは編集できる |
| hooks の post-tool | ファイルを編集した後 | 出力に当たるファイルを format で直し、検査し、指摘を返す |
| hooks の stop | 応答を終える前 | 実行中は出力全体を検査する（最大 3 回。超えると status: failed） |
| hooks の prompt | ユーザーが発言したとき | 質問待ちを解く。発言を止めたり書き換えたりしない |

出力の検査は実行中（`.skill-runs/skill-foundation/state.json` の status が active）に働く。hooks が無い環境でも、`run.py check` と `finish` が同じ検査をする。

hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（Claude Code は `.claude/settings.json`、Codex は `.codex/hooks.json` に追記する。Codex では、追記した hooks を `/hooks` で信頼するまで動かない）

<!-- END GENERATED:control -->
