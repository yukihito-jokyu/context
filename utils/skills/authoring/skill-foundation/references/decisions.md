<!-- このファイルは render_skill.py が dev/spec.json から生成する。手で編集しない。 -->

# 誰が使っても同じ結果になるスキルを作る のルール

## IN-01 対象外の依頼では start せずに代わりを示す

- 軸: I3
- ルール: 依頼が次の表の「対象外」に当たるときは、`run.py start` を実行せず、ファイルも作らずに、代わりに使うものを返答する。
- 理由: 対象外の依頼でスキルを作り始めると、AI ごとに違う形の成果物が残る。
- 決め方: AI の判断と覚える概念が少ない答え
- 守らせ方: doc: SKILL.md の手順1と references/intake.md の6章
- 機械化しない理由: 痕跡が残らない：判定は start の前に行い、検査する出力が無い

場合分け:

| 依頼 | 扱い |
|---|---|
| リポジトリ全体の規約、lint、ディレクトリ構造を作る | 対象外。pattern-foundation を示す |
| 1回限りの作業をしてほしい（繰り返し使う手順ではない） | 対象外。その作業を直接行うよう示す |
| skill-foundation で作ったスキルのルールや契約の小さな修正 | 対象外。そのスキルの `dev/spec.json` を直し、`render_skill.py` と `skill_lint.py` を実行するよう示す |
| skill-foundation で作っていない既存のスキルを、誰が使っても同じ結果になるようにしたい | 対象。spec の `mode` を `retrofit` にして手順2に進む（OUT-06） |
| 上のどれでもない | 対象。手順2に進む |

- 良い例:

  ```text
  「lint とディレクトリ構造を決めたい」には pattern-foundation を示して終える
  ```
- 悪い例:

  ```text
  規約の依頼から、規約を書くだけのスキルを作り始める
  ```

## IN-02 手順ごとに決めた references だけを読み、ほかのスキル作成スキルを使わない

- 軸: I4
- ルール: 手順3の Eval 作成と各フェーズでは、次の表のファイルだけを読む。ほかのスキル作成スキル（my-skill-creator、my-skill-creater、anthropic-skills:skill-creator、Codex の skill-creator）のファイルを読まず、呼び出さない。
- 理由: 読む資料が AI ごとに違うと、作るスキルの形が分かれる。ほかのスキル作成スキルは別の構成と規則を持つため、混ざると収束しない。
- 決め方: 依頼の指定
- 守らせ方: doc: SKILL.md の手順（手順3の Eval 作成と各フェーズで読むファイルを示す）
- 機械化しない理由: 痕跡が残らない：読んだファイルと呼び出したスキルは、出力に残らない

場合分け:

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

- 良い例:

  ```text
  フェーズ3で variance-axes.md と writing.md を読んでルールを書く
  ```
- 悪い例:

  ```text
  my-skill-creator を呼び出して SKILL.md の下書きを作らせる
  ```

## STEP-01 手順3の Eval 作成とフェーズ0〜7を順に進め、生成と検査はスクリプトに任せ、一緒に変えるファイルを揃える

- 軸: P1, P3, O7
- ルール: SKILL.md の「2. 手順」を番号の順に行う（手順3の Eval 作成の後に、フェーズ0〜7）。骨組みは `init_skill.py`、生成部分は `render_skill.py` で作り、手で書かない。`dev/spec.json` を変えたら、同じ変更の中で `render_skill.py` を実行し、ルールID を変えたなら `dev/probes.json` の違反例と `dev/research.md` の「使ったルール」も合わせる（一緒に変えるファイルの組）。各フェーズの終わりに `skill_lint.py` を実行し、エラーが0件になってから次のフェーズに進む。
- 理由: フェーズを飛ばしたり、生成部分を手で書いたり、spec だけを変えたりすると、spec と SKILL.md・違反例・調査の記録が食い違い、読む AI ごとに従う内容が変わる。
- 決め方: 機械で守らせられる答え
- 守らせ方: script, validate: scripts/init_skill.py、scripts/render_skill.py、scripts/skill_lint.py。契約の command 検査が、finish の前に `skill_lint.py --final --project` を実行する
- 良い例:

  ```text
  ルールを足したら `render_skill.py` を実行して SKILL.md の「4. ルール」を作り直す
  ```
- 悪い例:

  ```text
  SKILL.md の「4. ルール」に直接行を書き足す
  ```

## STEP-02 収束テストの実行は入力 measure で決め、省くのは決めた場合だけにする

- 軸: P2, O8
- ルール: フェーズ6の収束テストは、入力 `measure` に従って次の表のとおり扱う。収束テストを省く `convergence.skip_reason` は検査を止める記法なので、書いてよいのは、表で実行しないことになったときと、STEP-03 の表で runner が無いときだけである。
- 理由: 収束テストは費用がかかる。実行するかどうかを AI ごとに判断させると、測ったスキルと測っていないスキルが混ざる。
- 決め方: AI の判断と覚える概念が少ない答え
- 守らせ方: validate, doc: `skill_lint.py --final` が、収束テストの結果（各ラウンドの、今の記録を読んだ AI の分析を含む）か `convergence.skip_reason` を求める。`convergence.py prepare` は、`skip_reason` があると止まる

場合分け:

| measure | 扱い |
|---|---|
| ask | `convergence.py prepare` が出したセッションの回数を示し、`run.py wait --question` の後に実行してよいかを聞く。答えが「はい」なら実行する。それ以外なら実行せず、`skip_reason` に「利用者が収束テストを省くと答えた」と書く |
| run | 聞かずに実行する |
| skip | 実行せず（`convergence.py prepare` も実行しない）、`skip_reason` に「利用者が収束テストを省くと指定した」と書く |
| 上のどれでもない | ask と同じに扱う |

- 良い例:

  ```text
  measure が ask なので、「課題 4 件 × runner 2 種 × 2 人 = 16 回」を示して実行してよいかを聞く
  ```
- 悪い例:

  ```text
  measure が ask なのに、聞かずに skip_reason を書いて収束テストを省く
  ```

## STEP-03 使う道具は python3、git、skill-foundation のスクリプト、収束テストの runner に限る

- 軸: P4
- ルール: 使うコマンドは `python3`（skill-foundation の `scripts/` と、作るスキルの `scripts/`）、`git`、収束テストの runner だけにする。パッケージを追加で入れない。収束テストの runner は次の表で決める。`convergence.py prepare` は、`--runners` が無ければ、作るスキルの spec の `convergence.runners`、`settings/user-setting.yaml`、`settings/skill-setting.yaml` の順に、null でない最初の値を使う。エージェントのモデルと推論エフォートも同じ順の `convergence.model`・`convergence.effort` に従い、prepare が runner の起動コマンドに足す（runner `subagent` は、`convergence.py prompts` が示す値で Agent ツールを起動する）。
- 理由: 道具が AI ごとに違うと、生成物の形と検査の結果が変わる。追加のパッケージは利用者の環境に残る。runner を AI が選ぶと、同じスキルでも測り方が実行ごとに変わる。
- 決め方: 道具・スクリプト・入力を増やさない答え
- 守らせ方: doc: SKILL.md の手順10と references/convergence-test.md の3章
- 機械化しない理由: 痕跡が残らない：実行したコマンドと入れたパッケージは、作ったスキルのファイルに残らない

場合分け:

| 状況 | runner |
|---|---|
| `claude` と `codex` のどちらも起動できる | `convergence.py prepare` が上の順で決めた runner（`--runners` を渡さない） |
| 片方だけ起動できる（コマンドが無い、起動が拒否された） | 起動できる方だけ（`--runners` に渡す） |
| どちらも起動できず、Agent ツールがある | `subagent`。`convergence.py prompts` が出したプロンプトを、専用のエージェント型 `skill-foundation-tester`（prepare が `.claude/agents/` に置く。fence.py（作業ディレクトリの外への操作を止める仕組み）が働く）の新しいエージェントにそのまま渡し、最終の返答を保存先に書く |
| 上のどれでもない | 実行しない。`convergence.skip_reason` に「独立エージェントを起動できない」と書く |

- 良い例:

  ```text
  `claude -p` の起動が権限で拒否され、`codex` も無いので、`prepare --runners subagent` で準備し、prompts のプロンプトを新しいエージェントに渡す
  ```
- 悪い例:

  ```text
  `pip install pyyaml` を実行して YAML を書く
  ```

## STEP-04 検査に落ちたら作るスキルの側を直し、残ったばらつきは結論に書く

- 軸: P5
- ルール: `skill_lint.py` か `probe.py` が失敗したら、作るスキルの `dev/spec.json`、`scripts/`、SKILL.md の「2. 手順」を直してやり直す。収束テストの各ラウンドでは、`convergence.py analysis-collect` が書く `analysis.md` の指摘を、基準を満たした課題のものも記録で確かめ、V1〜V8 か推定違いに分類して、`dev/convergence-report.md` の「## 動きの指摘」の表に書いてから次のラウンドへ進む。収束テストがラウンドの上限（`convergence.py prepare` が示す `max_rounds`。STEP-03 と同じ順で決まる）で基準を満たさなかったら、`run.py wait --question` を実行してから、残った課題ごとにばらつきの分類（V1〜V8）を示し、ラウンドを足して続けるかを聞く。続けるなら、作るスキルの spec の `convergence.max_rounds` に今の上限より1つ大きい値を書いて締め込む。続けないなら、残った課題の ID、分類、残した理由を `dev/convergence-report.md` の「結論」に1課題1行で書く。
- 理由: 検査や skill-foundation を緩めて通すと、検査が無いのと同じになる。ラウンドを足し続けるかを AI が決めると、費用と作るスキルの重さが AI ごとに変わる。残ったばらつきを書かないと、利用者が限界を知らずに使う。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, doc: `skill_lint.py --final` が、基準を満たさない課題が「結論」に書かれているかと、AI の分析に指摘のあるエージェントが「## 動きの指摘」の表にあるかを確かめる。次のラウンドの `convergence.py prepare` も、前のラウンドの表が揃うまで止まる
- 良い例:

  ```text
  上限のラウンドで T3-edge が残ったので、分類 V2 と締め込み案を示して続けるかを聞き、「続けない」と答えられたので結論に「- T3-edge: V2。ユーザーが続けないと答えた」と書く
  ```
- 悪い例:

  ```text
  上限のラウンドで基準を満たさないまま、聞かずに結論に「おおむね収束した」と書く
  ```

## STEP-05 廃止

- 廃止（ID は再利用しない）: ユーザーによる微修正を妨げる変更制限と変更後の特別な検査手順を廃止した。

## STEP-06 受付の前に、ユーザーと確かめた価値から Eval を作り、Eval 自体を検証し、収束テストの題材を確かめる

- 軸: P1, P2, O8
- ルール: SKILL.md の手順3では、受付の前に Eval を作る。作るかは次の表で決める。作るときは references/eval.md の順に、材料（利用場面、今の不満や失敗、望む結果、許容できない結果）から価値仮説を立て、ユーザーとの対話で確定した価値を、外から確かめられる振る舞い、成功と失敗の事例、正解の根拠、判定方法に落として `<base>/<name>/dev/eval/eval.json` に書く。ユーザーに聞くことは eval.json の `questions` に書き、カタログの「Eval 作成」タブで答えてもらい、チャット欄に貼られた回答を `eval_check.py --answer` で `dialog` に記録する。Eval を作り、入力 `measure` が `skip` でなければ、続けて収束テストの題材（`<base>/<name>/dev/evals.json`）の案を書き、同じ聞き方でユーザーと確かめる。作らないときは `skip_reason` だけを書く。`skip_reason` は Eval の検査を止める記法なので、書いてよいのは表で作らないことになったときだけである。どちらのときも `eval_check.py` のエラーを0件にしてから受付に進む。
- 理由: 価値を確かめずにルールを決めると、誰が使っても同じ出力になっても、その出力がユーザーの役に立つとは限らない。価値を AI だけで決めると、AI の思い込みが正しさの基準になる。Eval 自体を検証しないと、何でも通す判定方法や、許容できない結果を見逃す事例が残る。収束テストの題材をユーザーが知らないまま測ると、揃った結果が、ユーザーの使い方でも揃うのかが分からない。
- 決め方: 依頼の指定
- 守らせ方: script, validate, doc: scripts/eval_check.py が Eval 自体を検証し、結果を dev/results/eval-check.json に書く。答えを待っている質問（questions）があるあいだは、そのことを指摘して止める。`--answer` が貼られた回答を言い換えずに dialog に記録する。scripts/catalog.py が、質問を「Eval 作成」タブに1枚ずつ削って開くカードで出し、回答をチャット欄に貼る文にまとめる。収束テストの題材は、同じタブに最後の回答の時の版との違いのラベルを付けて載せる（合意した後に変えても止めない）。`skill_lint.py --final` が、今の Eval が eval_check.py の検査に通っていることか、`skip_reason` を求める

場合分け:

| 状況 | 扱い |
|---|---|
| `eval` が `make` で、ユーザーに質問できる | 作る。質問の前に `run.py wait --question` を実行する（CTL-03） |
| `eval` が `skip` | 作らず、`skip_reason` に「利用者が Eval を省くと指定した」と書く |
| ユーザーに質問できない（依頼文だけで動く独立エージェントとして実行している） | 作らず、`skip_reason` に「利用者に価値を確かめられない」と書く |
| 上のどれでもない | `make` と同じに扱う |

- 良い例:

  ```text
  材料の4種類を1つの `questions` で聞き、カタログで答えてもらった回答を `eval_check.py --answer` で記録し、仮説を同じ聞き方で確かめて確定させ、振る舞いごとに成功と失敗の事例を書いて `eval_check.py` を通してから受付に進む
  ```
- 悪い例:

  ```text
  ユーザーに聞かずに依頼文だけから価値と事例を書き、成功の事例だけを置く
  ```

## STEP-07 収束テストの各ラウンドで、各エージェントの出力を Eval で採点し、Eval の問題をユーザーとすり合わせてから次のラウンドに進む

- 軸: P1, P5
- ルール: Eval を作ったときは、フェーズ4で、code と model の振る舞いに判定するファイルの場所（`target`。出力の契約の置き場と同じ書き方で、`#<要素の id>` を付けると HTML のその要素だけを判定する）を書く。収束テストの各ラウンドでは、`convergence.py diff` が code の判定を当て、`analysis-collect` が分析役の model の判定を取り込む。Eval に落ちた出力がある課題は、基準を満たさない。締め込みでは、落ちた判定と、`analysis.md` の指摘のうち Eval のどの振る舞いも確かめていない問題を、次の表で分類し、`dev/convergence-report.md` の「## Eval の採点」の表に、ラウンド、課題/エージェント、振る舞い、分類、対処を書く。Eval の疑いか抜けがあれば、次のラウンドに進む前に、`run.py wait --question` を実行してからユーザーとすり合わせ、対話を `dialog` に足して `dev/eval/eval.json` を直し、`eval_check.py` のエラーを0件にする。そのラウンドで収束テストを終えるとき（STEP-04 で続けないと決めたとき、または最終ラウンドで全課題が基準を満たしたとき）は、Eval を直さず、疑いと抜けの振る舞い（抜けは価値）の ID、分類、残した理由を `dev/convergence-report.md` の「結論」に1件1行で書く。直すのは次にラウンドを足すときで、そのときは `convergence.py prepare` が直すまで止まる。
- 理由: ばらつきだけを測ると、全員が同じ誤りをしても基準を満たす。Eval で採点すれば、出力が価値を満たすかも測れる。Eval は手順3でユーザーと決めた基準なので、実際の出力に当てると判定のずれが見つかることがある。落ちた判定を AI だけで Eval の誤りと決めて直すと、価値の基準を AI の都合で緩めることになる。収束テストを終えるラウンドで Eval を直しても、直した Eval で採点するラウンドが無く、確かめられないまま残るだけなので、直すのは次にラウンドを足すときにする。
- 決め方: 依頼の指定
- 守らせ方: script, validate, doc: scripts/convergence.py の diff が code の判定を report.json に書き、analysis-prepare が model の判定を分析役に頼み、analysis-collect が取り込んで課題の基準を決め直す。scripts/skill_lint.py の `--phase 4` が target を、次のラウンドの `convergence.py prepare` と `skill_lint.py --final` が、判定待ち、「## Eval の採点」の表の分類と対処、Eval の疑いか抜けの後に Eval を直したか（`skill_lint.py --final` は、最後のラウンドなら「結論」に残したかでもよい）、最後のラウンドを今の Eval で採点したかを確かめる
- 分けた理由: STEP-06 は手順3で Eval を作るときに破られ、STEP-07 は収束テストの各ラウンドで破られる。Eval を正しく作っても、target を書かない、落ちた判定を分類しない、Eval の疑いをユーザーとすり合わせずに次のラウンドへ進む、という違反は STEP-06 を守ったまま起きる

場合分け:

| 状況 | 分類と扱い |
|---|---|
| 落ちた出力が、確定した価値を満たしていない（判定が正しい） | 出力の誤り。ばらつきと同じく、作るスキルの側を直す |
| 落ちた出力が、確定した価値を満たしている。または判定が課題の状況に合わない | Eval の疑い。ユーザーとすり合わせて、振る舞い・判定方法・事例を直す |
| `analysis.md` の指摘の問題を、Eval のどの振る舞いも確かめていない | Eval の抜け。ユーザーとすり合わせて、振る舞いと事例を足す |
| 上のどれでもない | 出力の誤りと同じに扱う |

- 良い例:

  ```text
  落ちた判定ごとに出力を開き、価値を満たしていなければ出力の誤りとしてスキルを直し、判定がずれていればユーザーに示して Eval を直してから次のラウンドに進む
  ```
- 悪い例:

  ```text
  Eval に落ちた出力を見て、判定が厳しすぎると AI だけで決め、Eval の検査を緩めて次のラウンドに進む
  ```

## OUT-01 作るスキルは対象の製品から決めた置き場に1つ置く

- 軸: O1
- ルール: 作るスキルの本体は、入力 `targets` から次の表で決めた `base` の下の `<base>/<name>/` に置き、`install.py --project <ルート>` で置き場所と hooks を揃える。ユーザーのホームには置かない。
- 理由: 置き場が AI ごとに違うと、製品がスキルを見つけられない。
- 決め方: 出力を使う道具や形式の公式の決まり
- 守らせ方: validate, script: scripts/install.py。契約の outputs.skill-entry の path と count、`skill_lint.py --final --project` の本体の場所と `install.py --check`（もう一方の置き場が本体へのリンクか）

場合分け:

| targets | base |
|---|---|
| claude と codex | `.claude/skills`（`.agents/skills/<name>` は本体へのシンボリックリンク） |
| claude だけ | `.claude/skills` |
| codex だけ | `.agents/skills` |
| 上のどれでもない | `.claude/skills` |

- 良い例:

  ```text
  `.claude/skills/write-commit-message/SKILL.md` と、`.agents/skills/write-commit-message` へのリンク
  ```
- 悪い例:

  ```text
  `~/.claude/skills/write-commit-message/` に置く
  ```

## OUT-02 スキルの構成は init_skill.py が作る形だけにする

- 軸: O2
- ルール: スキルの直下には `SKILL.md`、`references/`、`assets/`、`scripts/`、`dev/` だけを置く。既定値を設定で変えられるスキルは、`settings/` に `skill-setting.yaml`（スキルの設定）と `user-setting.yaml`（ユーザーの設定）だけを置いてよい。SKILL.md の節は「1. 使う場面」から「8. 制御の仕組み」の8つで、手で書くのは「2. 手順」だけにする。`assets/examples/` には、検査に通る出力の見本を1つ以上置く。見本は `dev/probes.json` の baseline から `from` で使い、出力を書く手順で示す。
- 理由: 構成が揃うと、読む AI が同じ場所で同じ情報を探せる。見本があると、AI はルールの文から形を想像せずに、検査に通った実物を写せる。
- 決め方: 出力を使う道具や形式の公式の決まり
- 守らせ方: script, validate: scripts/init_skill.py が構成を作り、`skill_lint.py` が直下の名前・必須のファイル・節の並び・frontmatter と、settings/ の2つのファイルの形（入力の key と type、収束テストの項目）を確かめる。見本は `skill_lint.py` が置き場・baseline の from・手順の記載を確かめ、probe.py が baseline として検査に通す
- 良い例:

  ```text
  作業メモは `dev/research.md` に書く
  ```
- 悪い例:

  ```text
  スキルの直下に `notes.md` を作る
  ```

## OUT-03 文章は spec の言語で書き、あいまいな語を使わない

- 軸: O3
- ルール: SKILL.md、ルール、references は spec の `language` で書き、references/writing.md の書き方に従う。references/variance-axes.md の5章の語を使わない。
- 理由: あいまいな語は、読む AI ごとに解釈が分かれる。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, review: `skill_lint.py` がルールと手順のあいまいな語を検出する
- 良い例:

  ```text
  「ファイルが 6 つ以上ならディレクトリごとに1行」
  ```
- 悪い例:

  ```text
  「必要に応じてディレクトリごとにまとめる」
  ```

## OUT-04 名前と ID は決めた規則で振る

- 軸: O4
- ルール: スキルの名前は references/intake.md の2章の表で `<動詞>-<目的語>` に決める。ルールID は references/variance-axes.md の4章の規則（接頭辞ごとに 01 から、軸の順）で振る。
- 理由: 名前と ID の振り方が AI ごとに違うと、同じスキルが別の名前と別の番号で作られる。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, doc: `skill_lint.py` が名前の形と、ID の形・接頭辞・番号の連続と順序を確かめる
- 良い例:

  ```text
  コミットメッセージを書くスキルは `write-commit-message`、出力のルールは `OUT-01` から
  ```
- 悪い例:

  ```text
  `commit-helper` と名付け、ルールに `OUT-01`、`OUT-03` と番号を飛ばして振る
  ```

## OUT-05 量の下限と上限を数で守る

- 軸: O5
- ルール: `triggers.use_when` は5つ以上、SKILL.md の手順は5つ以上、SKILL.md は 500 行以下、description は 1024 文字以下、`dev/evals.json` の課題は holdout 以外を3つ以上と holdout を1つ以上にする。
- 理由: 量の感覚は AI ごとに違う。数で決めれば判定が割れない。
- 決め方: 出力を使う道具や形式の公式の決まり
- 守らせ方: validate: `skill_lint.py` が数を確かめる
- 良い例:

  ```text
  use_when に言い方の違う依頼を5つ書く
  ```
- 悪い例:

  ```text
  use_when に「スキルを作って」の1つだけを書く
  ```

## OUT-06 既にある置き場は状態で扱いを分ける

- 軸: O6
- ルール: `<base>/<name>/` が既にあるときは、次の表に従う。
- 理由: 既にあるスキルを上書きするかどうかが AI ごとに分かれると、利用者の作業が失われる。元の SKILL.md を残すと、後付けで何を変えたかを利用者が見比べられる。
- 決め方: AI の判断と覚える概念が少ない答え
- 守らせ方: script, validate, doc: scripts/init_skill.py は既にあるファイルを上書きしない。skill-foundation の形でない SKILL.md は、mode が retrofit のときだけ dev/original/SKILL.md に移し、そうでなければ止まる。skill_lint.py が、後付けのスキルに dev/original/SKILL.md と dev/research.md の「## 既存のスキル」を求める

場合分け:

| `<base>/<name>/` の状態 | 扱い |
|---|---|
| 無い | 作る（spec の `mode` は `new`） |
| あり、`dev/spec.json` がある | 既存の spec から続ける。`init_skill.py` は既にあるファイルを上書きしない |
| あり、`dev/spec.json` が無く、`SKILL.md` がある | `run.py wait --question` を実行し、そのスキルに後付けするか、別の名前で新しく作るかを聞く。後付けなら spec の `mode` を `retrofit` にする。`init_skill.py` が元の SKILL.md を `dev/original/SKILL.md` に移し、新しい骨組みを作る。別の名前なら、その名前で続ける。どちらでもない答えなら `run.py abort` |
| 上のどれでもない | 触らない。abort して状態をユーザーに伝える |

- 良い例:

  ```text
  spec の無い既存のスキルを見つけたので、wait を実行して後付けか別の名前かを聞き、後付けと答えられたので mode を retrofit にする
  ```
- 悪い例:

  ```text
  既存の SKILL.md を新しい内容で上書きする
  ```

## RPT-01 最終の返答は finish の本文をそのまま使う

- 軸: R1
- ルール: 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- 理由: 報告の形と中身が AI ごとに分かれない。既定値で決めた値と検証の結果を、読み手が必ず見られる。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, validate, review: scripts/run.py の finish と abort が本文を組み立て、.skill-runs/<name>/report.md にも保存する。check と finish が notes.md の形を検査する
- 良い例:

  ```text
  決めきれなかった既定値を notes.md に「- 」で書き、finish の本文をそのまま返答する
  ```
- 悪い例:

  ```text
  finish の本文を要約し直し、最後に自由な文で補足を足して返答する
  ```

## RPT-02 作ったスキルの要約、収束テストの結果、カタログは report_skill.py と catalog.py が集計する

- 軸: R1
- ルール: 最終報告の「## 作ったスキル」から「## プロジェクトに置いたもの」までは、契約の `report.sections` に登録した `report_skill.py` の出力をそのまま使う。収束テストは、`dev/results/convergence/round-*/report.json` から作った表と、基準を満たさない課題の「結論」の行で示す。省いたときは `convergence.skip_reason` を示す。「## カタログ」は `catalog.py` の出力をそのまま使う。`catalog.py` は、finish が検査に通った後に、プロジェクトのスキルのワークフロー図と検証の記録を `.skill-runs/catalog.html` に作り直す。これらの節を書き足したり言い換えたりしない。
- 理由: ルールの数、検証の結果、収束テストの結果を AI が要約すると、載せる項目と数え方が AI ごとに変わり、測っていないことを測ったように書く余地が残る。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime: scripts/report_skill.py と scripts/catalog.py。scripts/run.py の finish が契約の report.sections から実行し、出力を本文に入れる（catalog.py は stage: finish）
- 良い例:

  ```text
  finish の本文の「## 収束テスト」に、ラウンドごとの表と残ったばらつきがそのまま出ている
  ```
- 悪い例:

  ```text
  収束テストの結果を「おおむね揃った」と自分の言葉でまとめて返答する
  ```

## CTL-01 実行は run.py で始めて終える

- 軸: C1
- ルール: 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。
- 理由: 始まりと終わりをスクリプトで区切ると、検査が必ず走り、hooks が実行中かどうかを判定できる。完了の基準が AI ごとに分かれない。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, validate: scripts/run.py。finish は契約の検査に通らないと終了コード1で終わる
- 良い例:

  ```text
  `run.py finish` が終了コード0で終わってから、その本文で返答する
  ```
- 悪い例:

  ```text
  出力を書いた直後に「完了しました」と返答する
  ```

## CTL-02 廃止

- 廃止（ID は再利用しない）: ユーザーによる微修正を妨げる変更制限と変更後の特別な検査手順を廃止した。

## CTL-03 質問は start の前に済ませる

- 軸: C3, I2
- ルール: ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。
- 理由: 実行の途中で質問するかどうかが AI ごとに分かれると、出力が揃わない。wait を挟むと、質問のために応答を終えることを hooks が止めない。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, doc: scripts/run.py の start は、聞くべき入力が無いと終了コード3で止まり、質問を出力する。wait は hooks の強制を止める
- 良い例:

  ```text
  start の終了コード3で出た質問をユーザーに聞き、答えを `--set` で渡して start をやり直す
  ```
- 悪い例:

  ```text
  出力を半分書いたところで、形式をユーザーに尋ねる
  ```

## CTL-04 hooks で出力を検査する

- 軸: C4
- ルール: hooks は実行中（status: active）に、編集の後と応答を終える前に出力を検査する。実行記録への直接の編集は拒否する。ユーザーの発言を止めたり書き換えたりしない。hooks が無くても run.py check と finish で同じ出力の検査を行う。
- 理由: スキルの微修正を妨げず、出力の検証結果と実行記録を揃える。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime: scripts/hook.py。install.py が Claude Code（.claude/settings.json）と Codex（.codex/hooks.json）に登録する
- 良い例:

  ```text
  Stop の hook が、検査に通るまで応答の終了を差し戻す
  ```
- 悪い例:

  ```text
  UserPromptSubmit の hook で、依頼文の書き方が違うと拒否する
  ```
