<!-- このファイルは render_skill.py が dev/spec.json から生成する。手で編集しない。 -->

# 誰が使っても同じ結果になるスキルを作る の決定

## IN-01 対象外の依頼では start せずに代わりを示す

- 軸: I3
- 決定: 依頼が次の表の「対象外」に当たるときは、`run.py start` を実行せず、ファイルも作らずに、代わりに使うものを返答する。
- 理由: 対象外の依頼でスキルを作り始めると、AI ごとに違う形の成果物が残る。
- 決め方: AI の判断と覚える概念が少ない答え
- 守らせ方: doc: SKILL.md の手順1と references/intake.md の6章
- 機械化しない理由: 痕跡が残らない：判定は start の前に行い、検査する出力が無い

決定表:

| 依頼 | 扱い |
|---|---|
| リポジトリ全体の規約、lint、ディレクトリ構造を作る | 対象外。pattern-foundation を示す |
| 1回限りの作業をしてほしい（繰り返し使う手順ではない） | 対象外。その作業を直接行うよう示す |
| skill-foundation で作ったスキルの決定や契約の小さな修正 | 対象外。そのスキルの `dev/spec.json` を直し、`render_skill.py` と `skill_lint.py` を実行するよう示す |
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

## IN-02 フェーズごとに決めた references だけを読み、ほかのスキル作成スキルを使わない

- 軸: I4
- 決定: 各フェーズでは次の表のファイルだけを読む。ほかのスキル作成スキル（my-skill-creator、my-skill-creater、anthropic-skills:skill-creator、Codex の skill-creator）のファイルを読まず、呼び出さない。
- 理由: 読む資料が AI ごとに違うと、作るスキルの形が分かれる。ほかのスキル作成スキルは別の構成と規則を持つため、混ざると収束しない。
- 決め方: 依頼の指定
- 守らせ方: doc: SKILL.md の手順（各フェーズで読むファイルを示す）
- 機械化しない理由: 痕跡が残らない：読んだファイルと呼び出したスキルは、出力に残らない

決定表:

| フェーズ | 読むファイル |
|---|---|
| 0 受付 | `references/intake.md`、`references/skill-profiles.md` の種類の節 |
| 1 骨組み、2 調査 | `references/runtime.md`、`references/platforms.md`、`references/research.md`、`references/skill-profiles.md` の種類の節（調べる先） |
| 3 決める | `references/variance-axes.md`、`references/writing.md`、`references/control-ladder.md` の3章、`references/skill-profiles.md` の種類の節 |
| 4 縛る、5 証明する | `references/control-ladder.md`、`references/skill-profiles.md` の種類の節 |
| 6 測る | `references/convergence-test.md`、`references/skill-profiles.md` の種類の節 |
| 7 仕上げ | 読まない |
| 上のどれでもない | 読まない |

- 良い例:

  ```text
  フェーズ3で variance-axes.md と writing.md を読んで決定を書く
  ```
- 悪い例:

  ```text
  my-skill-creator を呼び出して SKILL.md の下書きを作らせる
  ```

## STEP-01 フェーズ0〜7を順に進め、生成と検査はスクリプトに任せ、一緒に変えるファイルを揃える

- 軸: P1, P3, O7
- 決定: SKILL.md の「2. 手順」のフェーズ0〜7を番号の順に行う。骨組みは `init_skill.py`、生成部分は `render_skill.py` で作り、手で書かない。`dev/spec.json` を変えたら、同じ変更の中で `render_skill.py` を実行し、決定の ID を変えたなら `dev/probes.json` の違反例と `dev/research.md` の「使った決定」も合わせる（一緒に変えるファイルの組）。各フェーズの終わりに `skill_lint.py` を実行し、エラーが0件になってから次のフェーズに進む。
- 理由: フェーズを飛ばしたり、生成部分を手で書いたり、spec だけを変えたりすると、spec と SKILL.md・違反例・調査の記録が食い違い、読む AI ごとに従う内容が変わる。
- 決め方: 機械で守らせられる答え
- 守らせ方: script, validate: scripts/init_skill.py、scripts/render_skill.py、scripts/skill_lint.py。契約の command 検査が、finish の前に `skill_lint.py --final --project` を実行する
- 良い例:

  ```text
  決定を足したら `render_skill.py` を実行して SKILL.md の「4. 決定表」を作り直す
  ```
- 悪い例:

  ```text
  SKILL.md の「4. 決定表」に直接行を書き足す
  ```

## STEP-02 収束テストの実行は入力 measure で決め、省くのは決めた場合だけにする

- 軸: P2, O8
- 決定: フェーズ6の収束テストは、入力 `measure` に従って次の表のとおり扱う。収束テストを省く `convergence.skip_reason` は検査を止める記法なので、書いてよいのは、表で実行しないことになったときと、STEP-03 の表で runner が無いときだけである。
- 理由: 収束テストは費用がかかる。実行するかどうかを AI ごとに判断させると、測ったスキルと測っていないスキルが混ざる。
- 決め方: AI の判断と覚える概念が少ない答え
- 守らせ方: validate, doc: `skill_lint.py --final` が、収束テストの結果か `convergence.skip_reason` を求める

決定表:

| measure | 扱い |
|---|---|
| ask | `convergence.py prepare` が出したセッションの回数を示し、`run.py wait --question` の後に実行してよいかを聞く。答えが「はい」なら実行する。それ以外なら実行せず、`skip_reason` に「利用者が収束テストを省くと答えた」と書く |
| run | 聞かずに実行する |
| skip | 実行せず、`skip_reason` に「利用者が収束テストを省くと指定した」と書く |
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
- 決定: 使うコマンドは `python3`（skill-foundation の `scripts/` と、作るスキルの `scripts/`）、`git`、収束テストの runner だけにする。パッケージを追加で入れない。収束テストの runner は次の表で決め、`convergence.py prepare --runners` に渡す。
- 理由: 道具が AI ごとに違うと、生成物の形と検査の結果が変わる。追加のパッケージは利用者の環境に残る。runner を AI が選ぶと、同じスキルでも測り方が実行ごとに変わる。
- 決め方: 道具・スクリプト・入力を増やさない答え
- 守らせ方: doc: SKILL.md の手順9と references/convergence-test.md の3章
- 機械化しない理由: 痕跡が残らない：実行したコマンドと入れたパッケージは、作ったスキルのファイルに残らない

決定表:

| 状況 | runner |
|---|---|
| `claude` と `codex` のどちらも起動できる | spec の `convergence.runners`（既定 `claude`、`codex`） |
| 片方だけ起動できる（コマンドが無い、起動が拒否された） | 起動できる方だけ |
| どちらも起動できず、Agent ツールがある | `subagent`。`convergence.py prompts` が出したプロンプトを、会話の文脈を引き継がない新しいエージェントにそのまま渡し、最終の返答を保存先に書く |
| 上のどれでもない | 実行しない。`convergence.skip_reason` に「独立エージェントを起動できない」と書く |

- 良い例:

  ```text
  `claude -p` の起動が権限で拒否され、`codex` も無いので、`prepare --runners subagent` で準備し、prompts のプロンプトを新しいエージェントに渡す
  ```
- 悪い例:

  ```text
  `pip install pyyaml` を実行して YAML を書く
  ```

## STEP-04 検査に落ちたら作るスキルの側を直し、残った揺れは結論に書く

- 軸: P5
- 決定: `skill_lint.py` か `probe.py` が失敗したら、作るスキルの `dev/spec.json`、`scripts/`、SKILL.md の「2. 手順」を直してやり直す。skill-foundation のファイルは変えない。収束テストが `convergence.max_rounds` のラウンドで基準を満たさなかったら、`run.py wait --question` を実行してから、残った課題ごとに揺れの分類（V1〜V8）を示し、ラウンドを足して続けるかを聞く。続けるなら `convergence.max_rounds` を1つ増やして締め込む。続けないなら、残った課題の ID、分類、残した理由を `dev/convergence-report.md` の「結論」に1課題1行で書く。
- 理由: 検査や skill-foundation を緩めて通すと、検査が無いのと同じになる。ラウンドを足し続けるかを AI が決めると、費用と作るスキルの重さが AI ごとに変わる。残った揺れを書かないと、利用者が限界を知らずに使う。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, doc: `skill_lint.py --final` が、基準を満たさない課題が「結論」に書かれているかを確かめる。skill-foundation のファイルは CTL-02 で守る
- 良い例:

  ```text
  上限のラウンドで T3-edge が残ったので、分類 V2 と締め込み案を示して続けるかを聞き、「続けない」と答えられたので結論に「- T3-edge: V2。ユーザーが続けないと答えた」と書く
  ```
- 悪い例:

  ```text
  上限のラウンドで基準を満たさないまま、聞かずに結論に「おおむね収束した」と書く
  ```

## STEP-05 検査に通った作ったスキルは、finish が封印する

- 軸: P3
- 決定: 作ったスキルは、skill-foundation の `run.py finish` が検査に通った後に `report_skill.py --seal` で封印する（`assets/seal.json`）。封印の後に作ったスキルを変えるときは、作ったスキルの SKILL.md の「8. 制御の仕組み」の変え方に従い、`skill_lint.py <作ったスキル> --final --seal` で封印し直す。
- 理由: hooks は実行中しか働かないため、封印が無いと、作った後に検査を緩める変更が入っても次の実行が気づかない。封印を AI の判断に任せると、封印するスキルとしないスキルが混ざる。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime: 契約の report.sections に stage: finish で置いた `scripts/report_skill.py --seal` を、scripts/run.py の finish が検査に通った後だけ実行する。封印は skill_lint.py --final に通った状態だけに書く
- 良い例:

  ```text
  finish の本文の「## 封印」に、`assets/seal.json` に保護ファイルのハッシュを書いたと出ている
  ```
- 悪い例:

  ```text
  作り終えた後、封印せずに完了と返答し、後から契約の正規表現を緩めても誰も気づかない
  ```

## OUT-01 作るスキルは対象の製品から決めた置き場に1つ置く

- 軸: O1
- 決定: 作るスキルの本体は、入力 `targets` から次の表で決めた `base` の下の `<base>/<name>/` に置き、`install.py --project <ルート>` で置き場所と hooks を揃える。ユーザーのホームには置かない。
- 理由: 置き場が AI ごとに違うと、製品がスキルを見つけられない。
- 決め方: 出力を使う道具や形式の公式の決まり
- 守らせ方: validate, script: scripts/install.py。契約の outputs.skill-entry の path と count、`skill_lint.py --final --project` の `install.py --check`

決定表:

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
- 決定: スキルの直下には `SKILL.md`、`references/`、`assets/`、`scripts/`、`dev/` だけを置く。SKILL.md の節は「1. 使う場面」から「8. 制御の仕組み」の8つで、手で書くのは「2. 手順」だけにする。`assets/examples/` には、検査に通る出力の見本を1つ以上置く。見本は `dev/probes.json` の baseline から `from` で使い、出力を書く手順で示す。
- 理由: 構成が揃うと、読む AI が同じ場所で同じ情報を探せる。見本があると、AI は決定表の文から形を想像せずに、検査に通った実物を写せる。
- 決め方: 出力を使う道具や形式の公式の決まり
- 守らせ方: script, validate: scripts/init_skill.py が構成を作り、`skill_lint.py` が直下の名前・必須のファイル・節の並び・frontmatter を確かめる。見本は `skill_lint.py` が置き場・baseline の from・手順の記載を確かめ、probe.py が baseline として検査に通す
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
- 決定: SKILL.md、決定、references は spec の `language` で書き、references/writing.md の書き方に従う。references/variance-axes.md の5章の語を使わない。
- 理由: あいまいな語は、読む AI ごとに解釈が分かれる。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, review: `skill_lint.py` が決定と手順のあいまいな語を検出する
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
- 決定: スキルの名前は references/intake.md の2章の表で `<動詞>-<目的語>` に決める。決定の ID は references/variance-axes.md の4章の規則（接頭辞ごとに 01 から、軸の順）で振る。
- 理由: 名前と ID の振り方が AI ごとに違うと、同じスキルが別の名前と別の番号で作られる。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, doc: `skill_lint.py` が名前の形と、ID の形・接頭辞・番号の連続と順序を確かめる
- 良い例:

  ```text
  コミットメッセージを書くスキルは `write-commit-message`、出力の決定は `OUT-01` から
  ```
- 悪い例:

  ```text
  `commit-helper` と名付け、決定に `OUT-01`、`OUT-03` と番号を飛ばして振る
  ```

## OUT-05 量の下限と上限を数で守る

- 軸: O5
- 決定: `triggers.use_when` は5つ以上、SKILL.md の手順は5つ以上、SKILL.md は 500 行以下、description は 1024 文字以下、`dev/evals.json` の課題は holdout 以外を3つ以上と holdout を1つ以上にする。
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
- 決定: `<base>/<name>/` が既にあるときは、次の表に従う。
- 理由: 既にあるスキルを上書きするかどうかが AI ごとに分かれると、利用者の作業が失われる。元の SKILL.md を残すと、後付けで何を変えたかを利用者が見比べられる。
- 決め方: AI の判断と覚える概念が少ない答え
- 守らせ方: script, validate, doc: scripts/init_skill.py は既にあるファイルを上書きしない。skill-foundation の形でない SKILL.md は、mode が retrofit のときだけ dev/original/SKILL.md に移し、そうでなければ止まる。skill_lint.py が、後付けのスキルに dev/original/SKILL.md と dev/research.md の「## 既存のスキル」を求める

決定表:

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
- 決定: 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
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

## RPT-02 作ったスキルの要約と収束テストの結果は report_skill.py が集計する

- 軸: R1
- 決定: 最終報告の「## 作ったスキル」から「## プロジェクトに置いたもの」までは、契約の `report.sections` に登録した `report_skill.py` の出力をそのまま使う。収束テストは、`dev/results/convergence/round-*/report.json` から作った表と、基準を満たさない課題の「結論」の行で示す。省いたときは `convergence.skip_reason` を示す。これらの節を書き足したり言い換えたりしない。
- 理由: 決定の数、検証の結果、収束テストの結果を AI が要約すると、載せる項目と数え方が AI ごとに変わり、測っていないことを測ったように書く余地が残る。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime: scripts/report_skill.py。scripts/run.py の finish が契約の report.sections から実行し、出力を本文に入れる
- 良い例:

  ```text
  finish の本文の「## 収束テスト」に、ラウンドごとの表と残った揺れがそのまま出ている
  ```
- 悪い例:

  ```text
  収束テストの結果を「おおむね揃った」と自分の言葉でまとめて返答する
  ```

## CTL-01 実行は run.py で始めて終える

- 軸: C1
- 決定: 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。
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

## CTL-02 実行中はスキル自身のファイルを変えない

- 軸: C2
- 決定: `run.py start` から `run.py finish` までの間、スキルの保護ファイル（`SKILL.md`、`scripts/`、`assets/`、`references/`）と、プロジェクトに登録したこのスキルの hooks を変えない。出力が契約に合わないときは、出力の方を直す。保護ファイルが封印（`assets/seal.json`）と違うと `run.py start` が終了コード1で止まるので、そのときは出力された指摘をユーザーに伝えて止まる。
- 理由: 検査や契約を緩めて通すと、検査が無いのと同じになる。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, validate: scripts/run.py の start が保護ファイルのハッシュと hooks の登録を記録し、check と finish が比べる。`start --restart` は記録を最初の start から引き継ぐ。hooks が編集の前に止める。start は封印と保護ファイルを比べ、違えば始めない
- 良い例:

  ```text
  指摘されたルールIDを決定表で引き、出力のファイルを直す
  ```
- 悪い例:

  ```text
  検査に通すために `assets/contract.json` の正規表現を緩める
  ```

## CTL-03 質問は start の前に済ませる

- 軸: C3, I2
- 決定: ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。
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

## CTL-04 hooks は出力の検査だけに使い、入力を止めない

- 軸: C4
- 決定: hooks は、このスキルの実行中（status: active）に、編集の後の検査、応答を終える前の検査、保護ファイルの編集の停止の3つを行う。実行していないときは、封印したスキル（`assets/seal.json` がある）の保護ファイルの編集に、Claude Code で確認を求めることだけを行う。ユーザーの発言を止めたり書き換えたりしない。
- 理由: 縛る対象は AI の出力であり、ユーザーの入力ではない。このスキルを使っていないセッションの邪魔をしない。ただし、実行していない間にスキル自身が変わると、次の実行の検査が緩んだままになるので、封印したファイルの編集だけは人に確かめさせる。
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

## CTL-05 契約の出力のほかにファイルを変えない

- 軸: C5
- 決定: `run.py start` から `run.py finish` までの間に作る・変えるファイルは、「5. 出力の契約」の出力と `control.allow_changes` に挙げたものだけにする。作業用のメモや一時ファイルも、出力の置き場の外に作らない。
- 理由: 出力の外に作るファイル（メモ、控え、別名の写し）は AI ごとに違い、利用者のリポジトリに残る。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, validate: scripts/run.py の start が git の作業ツリーの状態を記録し、check と finish が比べる。編集の直後には hooks が知らせる
- 良い例:

  ```text
  下書きも出力の置き場（`.skill-runs/<name>/`）の中に書く
  ```
- 悪い例:

  ```text
  リポジトリの直下に `notes.md` を作って下書きする
  ```
