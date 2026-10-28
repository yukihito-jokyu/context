# 収束テスト（フェーズ6）

フェーズ5までで、ルールを機械で守らせる仕組みはできている。しかし、仕組みが揃っていても、別の AI が同じ依頼から同じ出力を作るとは限らない。決めていない軸が残っていたり、手順が読み違えられたりするからである。収束テストでは、作成に関わっていない独立エージェントに同じ依頼を解かせ、出力の違い（ばらつき）を測る。ばらつきが見つかれば、原因を分類してルールや仕組みを締め込み、もう一度測る。

この章は次の順に読む。1章で課題を作り、2章で実行するかを決め、3章で実行し（エージェントの動きの AI の分析を含む）、4章で結果を読み、5章でばらつきと動きの指摘を分類して締め込み、6章で次のラウンドを決め、7章で記録する。段 review のルール（人や AI が読んで確かめるルール）は、出力を比べても見落としが分からないので、最終ラウンドでレビューの検出率も測る（3章の終わりと4章）。

## 1. 課題（`dev/evals.json`）

```json
{"tasks": [
  {"id": "T1-typical", "kind": "typical", "prompt": "ABC-12 のコミットメッセージを書いて",
   "fixture": "dev/fixtures/basic", "setup": ["git add -A"], "expect_status": "done"}
]}
```

| 項目 | 書くこと |
|---|---|
| `id` | 課題の ID |
| `kind` | `typical`（最もよくある依頼）、`default`（既定値で補う入力を書かない依頼）、`edge`（場合分けの境目に当たる依頼）、`holdout`（上と違う種類の依頼。最後のラウンドまで使わない） |
| `prompt` | ユーザーが実際に書く依頼文。聞くべき入力は依頼文に含める（独立エージェントは質問に答えてもらえない） |
| `fixture`、`setup` | 一時プロジェクトの元にするディレクトリと、準備のコマンド。fixture を写し、スキルを置き、git の初回コミットを作ってから `setup` を実行する。`setup` で `git commit` はしない（[control-ladder.md](control-ladder.md) の7章） |
| `invoke` | `explicit` なら、依頼文の前に Claude Code は `/<name>`、Codex は `$<name>` を付ける。省けば付けない（自動の起動も測る） |
| `expect_status` | 全員がこの status になることを期待する。既定は `done`。対象外の依頼なら `aborted` か `unused`（start しない） |

課題は次の規則で作る。`skill_lint.py --final` が確かめる。

- holdout 以外を3つ以上、holdout を1つ以上作る
- `fixture` は `dev/fixtures/basic` の1つだけにし、課題ごとの違い（ファイルの追加、ステージする変更）は `setup` のコマンドで作る。`dev/fixtures/` の下に `basic` のほかのディレクトリやスクリプトを置かない。fixture の数と名前が作る AI ごとに分かれないようにするためである
- `prompt` に、スキルの名前、ルールID（`OUT-02` の形）、`scripts/`、`run.py`、`SKILL.md` を書かない。ユーザーはこれらを知らずに依頼する。書くと、スキルが自分で起動するか、手順を自分で読み取れるかを測れない
- `invoke: explicit` は、`triggers.implicit` が `false` のスキルだけに使う。`implicit` が `false` のスキルでは、`expect_status` が `done` の課題に `invoke: explicit` を付ける（付けないと Claude Code ではスキルが起動しない）

## 2. 実行するか（入力 `measure`）

収束テストは、課題の数 × runner の数 × 人数（既定 2）の回数だけ、エージェントのセッションを起動する。起動には費用がかかるので、skill-foundation の入力 `measure` で扱いを決める（STEP-02）。

| `measure` | 扱い |
|---|---|
| `ask` | `convergence.py prepare` が出したセッションの回数を示し、`run.py wait --question` を実行してから、実行してよいかを聞く。答えが「はい」なら実行する。それ以外なら `skip` と同じにする |
| `run` | 聞かずに実行する |
| `skip` | 実行しない。`convergence.py prepare` も実行しない。spec の `convergence.skip_reason` に「利用者が収束テストを省くと指定した」と書く |
| 上のどれでもない | `ask` と同じにする |

`skip` のときも、`dev/evals.json`（1章の課題）は書く（`skill_lint.py --final` が求める）。`dev/convergence-report.md` は、ひな形の表の節を消し、「## 結論」に省いた理由だけを書く。`convergence.py prepare` は、`skip_reason` があると止まる（一時プロジェクトを作らない）。

`skip_reason` を書いてよいのは、上の表で `skip` になったときと、3章の表で runner が無いときだけである。書いたときは、skill-foundation の最終報告の「## 収束テスト」に、`report_skill.py` がその理由を出す（RPT-02）。

## 3. 実行

```bash
python3 <skill>/scripts/convergence.py prepare <作るスキル> --round <R> [--include-holdout]
python3 <skill>/scripts/convergence.py run --workdir <prepare が出した作業場所> --round <R>
python3 <skill>/scripts/convergence.py diff --workdir <作業場所> --round <R>
```

- `prepare` は、課題 × runner × 人数の分だけ一時プロジェクトを作り、スキルを写して hooks を登録する。holdout は `--include-holdout` を付けたときだけ含める（6章の最終ラウンド）。ラウンド2からは、前のラウンドの AI の分析と、その指摘を分類した「## 動きの指摘」の表（5章・7章）が揃っていないと止まる
- `run` は各プロジェクトで runner を起動する（[platforms.md](platforms.md) の3章）。runner `subagent` は起動せず、保存された最終の返答を集める
- `diff` は結果を比べ、`<作るスキル>/dev/results/convergence/round-<R>/` に `report.json`、`report.md`、エージェントごとの `.patch` を書く

runner は次の表で決める（STEP-03）。起動できるかは、`claude --version` と `codex --version` が終了コード0で終わるか、`run` の最初の1件が起動できたかで判断する。

| 状況 | runner |
|---|---|
| `claude` と `codex` のどちらも起動できる | spec の `convergence.runners`（既定 `claude`、`codex`） |
| 片方だけ起動できる（コマンドが無い、起動が拒否された） | 起動できる方だけ（`prepare --runners claude` など） |
| どちらも起動できず、Agent ツールがある | `subagent`（`prepare --runners subagent`） |
| 上のどれでもない | 実行しない。`convergence.skip_reason` に「独立エージェントを起動できない」と書く |

runner `subagent` は、`claude -p` や `codex exec` を起動できない環境（権限の設定、自動モードの安全判定で拒否されるなど）での代わりの方法である。手順は次のとおり。

```bash
python3 <skill>/scripts/convergence.py prepare <作るスキル> --round <R> --runners subagent
python3 <skill>/scripts/convergence.py prompts --workdir <作業場所> --round <R>
# prompts が示した各プロンプトファイルの中身を、Agent ツールで skill-foundation-tester のエージェントにそのまま渡し、最終の返答を保存先に書く
python3 <skill>/scripts/convergence.py run --workdir <作業場所> --round <R>
python3 <skill>/scripts/convergence.py diff --workdir <作業場所> --round <R>
```

- エージェントは、専用のエージェント型 `skill-foundation-tester`（Agent ツールの subagent_type）で起動する。`prepare` が `.claude/agents/` に置く。会話の文脈を引き継がず、fence.py（作業ディレクトリの外への操作を止める仕組み）が働く。fork のように文脈を引き継ぐ種類や、ほかの型で代わりに動かさない。作成の経緯を知るエージェントでは独立に解いたことにならず、fence.py の働かないエージェントは作業ディレクトリの外に触れる
- Codex のサブエージェントで動かしたときも、`trace` は Codex の記録から操作を集める（7章の表）。専用のエージェント型が無いので、fence.py は働かない（下の表）
- `.claude/agents/` をセッションの途中で初めて作ったときは、Claude Code を再起動してから起動する（Claude Code は、セッションを始めたときにあった `.claude/agents/` だけを読み直す）
- プロンプトの前後に説明を足さない。prompts が作るプロンプトには、作業ディレクトリの縛りと、スキルの置き場と説明文が入っている
- エージェントの最終の返答は、そのまま保存先（`_results/<実行ID>.last.txt`）に書く。要約しない
- 複数のエージェントを並べて起動してよい

runner `subagent` には、`claude` や `codex` と比べて次の限界がある。`diff` の report.md と、skill-foundation の最終報告の「確かめていないこと」に、この限界が出る。

| 限界 | 理由 | 補うもの |
|---|---|---|
| スキルの hooks が働かない | エージェントは呼び出し元のセッションの設定で動き、一時プロジェクトの `.claude/settings.json` を読まない | 出力の検査は `run.py` の check と finish で行われる。hooks の働きは `probe.py` の hooks の動作の確認で確かめている。fence.py は、専用のエージェント型の frontmatter の hooks で働く |
| 自動の起動は近似になる | エージェントは一時プロジェクトのスキルの一覧を見ない。prompts がスキルの説明文を前置きで渡す | `invoke` が `explicit` の課題は、スキルの SKILL.md の場所を直接渡す |
| runner の違い（Claude Code と Codex）を測れない | 呼び出し元と同じ製品・同じモデルで動く | 測れなかったことを最終報告に書く |
| 呼び出し元の指示ファイル（CLAUDE.md など）が混ざることがある | エージェントは呼び出し元のセッションの設定を引き継ぐ | なし。最終報告に書く |
| Codex のサブエージェントでは、fence.py が働かない | fence.py は専用のエージェント型（Claude Code の仕組み）の frontmatter に登録する | 外に触れた操作は、カタログの「作業ディレクトリの外に触れた操作」のカードで確かめる |

### 作業ディレクトリの外への操作の停止（`fence.py`）

`fence.py` は、独立エージェントが作業ディレクトリ（一時プロジェクト）の外に触れる操作を、PreToolUse の hook で止める。プロンプトの縛り（このディレクトリの外は読まず、変えない）だけでは、Claude Code の「一時ファイルは scratchpad に置く」という指示や、スクリプトが既定の置き場（OS の一時ディレクトリ）に書くことを止められなかったため。`prepare` が各一時プロジェクトに印（`.skill-runs/_fence/lab.json`）を置き、runner ごとに次のように登録する。

| runner | fence.py の登録先 | 入力にパスが出ない一時ファイル |
|---|---|---|
| `claude` | 一時プロジェクトの `.claude/settings.json`（全道具） | `run` が環境変数 `TMPDIR` を `.skill-runs/_fence/tmp` に向ける |
| `codex` | 一時プロジェクトの `.codex/hooks.json`（Bash と apply_patch） | 同上。さらにサンドボックスの書き込み先から `/tmp` と `$TMPDIR` を外す |
| `subagent` | 専用のエージェント型 `skill-foundation-tester` の frontmatter（全道具）。最初に触れた一時プロジェクトにエージェントを結びつける | `fence.py` が Bash の先頭に `export TMPDIR=<作業ディレクトリ>/.skill-runs/_fence/tmp/ &&` を足す |

- 止める操作: 作業ディレクトリの外のパス（道具のパスと、Bash のコマンドに出る `/…`・`~`・`$HOME`・外へ出る `..`）と、ほかのエージェントの作業ディレクトリ。runner `subagent` では、`cd <作業ディレクトリ> && ` で始まらない Bash、path の無い Glob・Grep、Skill の道具も止める（どれも呼び出し元のプロジェクトで動く）
- 通す操作: システムのパス（`/usr`・`/bin`・`/dev` など）と、Claude Code が長い出力を逃がした tool-results
- 止めた理由はエージェントに返り、エージェントは作業ディレクトリの中でやり直せる。止めた操作は `.skill-runs/_fence/log.jsonl` に残り、`diff`・`trace` が `traces.json` の操作に `fenced` の印を付ける。カタログは、止めた操作を外に触れた操作に数えず、カードに別に載せる
- `.skill-runs/_fence/` は、`diff` の変わったファイルに数えない。runner `claude`・`codex` で fence.py の登録が外されたら、スキル自身や hooks の登録を変えたときと同じく、その課題は基準を満たさない
- 判定に失敗したときも止める（Codex は hook が失敗すると操作を進めるため）
- fence.py にも抜けがある。スクリプトの中で開くファイルはコマンドの文字列に出ないので見えない。書き込みは `TMPDIR` と Codex のサンドボックスで抑えるが、読み取りは抑えられない。抜けた操作は、カタログの「作業ディレクトリの外に触れた操作」のカードで確かめる

最終ラウンドでは、課題の `diff` の後に、レビューの検出率を測る。`dev/probes.json` の `reviews`（段 review のルールの、違反を入れた見本）ごとに、独立エージェントに「完了前チェックリストで出力を確かめ、違反したルールID を挙げて」と頼み、違反の ID を挙げたかを数える。

```bash
python3 <skill>/scripts/convergence.py review-prepare <作るスキル> --round <R> --runners <runner> --workdir <作業場所>
python3 <skill>/scripts/convergence.py run --workdir <作業場所> --round <R> --kind review   # subagent なら先に prompts --kind review
python3 <skill>/scripts/convergence.py review-score --workdir <作業場所> --round <R> --out <作るスキル>/dev/results/convergence/round-<R>
```

- `review-prepare` は、見本 × runner × 人数の分だけ一時プロジェクトを作る。baseline の出力を置いた後に、見本の `files` で違反を入れる
- `review-score` は、`review.json` と `review.md` を書く。見本ごとの検出率（違反の ID を挙げたエージェントの割合）、余計な指摘（見本に無いルールID）、エージェント同士の一致、ファイルを変えたエージェントが出る

### エージェントの動きの分析（AI の推定）

各ラウンドの `diff` の後、締め込み（5章）の前に、エージェントごとの記録（`traces.json`）を別の AI に読ませ、各操作をした理由と、流れが妥当かを分析させる。エージェント自身の考えは記録に残らない（Codex は暗号化され、Claude Code は空になる）ので、操作の入力・出力・成否と手順を突き合わせて推し量る。カタログの「エージェントの動き」が、機械の照合（手順との照合）と並べて「AI の推定」として出す。

```bash
python3 <skill>/scripts/convergence.py analysis-prepare <作るスキル> --round <R> [--runner <runner>]
python3 <skill>/scripts/convergence.py prompts --workdir <作業場所> --round <R> --kind analysis   # runner subagent
python3 <skill>/scripts/convergence.py run --workdir <作業場所> --round <R> --kind analysis       # runner claude・codex
python3 <skill>/scripts/convergence.py analysis-collect --workdir <作業場所> --round <R>
```

- `analysis-prepare` は、操作の記録があるエージェント1人につき1件、分析役の作業ディレクトリ（`analysis-<R>/<課題ID>/<エージェント>/`）を作り、`record.md` を置く。`record.md` には、SKILL.md の手順（そのラウンドでエージェントが読んだもの。下の `used-SKILL.md`）、依頼、操作ごとの入力・出力の抜粋・成否・手順との照合、最終の返答、同じ課題のほかのエージェントの流れと、書き方の決まりが入る
- runner は STEP-03 の表で決める（`--runner`。既定は spec の `convergence.runners` の先頭）。runner `subagent` は、prompts のプロンプトを `skill-foundation-tester` のエージェントにそのまま渡す。分析役は `record.md` を読み、同じディレクトリの `analysis.json` に自分で書く。最終の返答は保存しなくてよい
- 分析役のモデルと推論エフォートは、`analysis-collect` が次から読む。Agent ツールの分析役は Agent ツールの記録（プロンプトの全文で突き合わせる）、Codex のサブエージェントの分析役は Codex の記録（`trace` と同じく、作業ディレクトリで突き合わせる）、runner `claude`・`codex` は `run` の実行の結果
- `analysis-collect` は、各 `analysis.json` が決まり（操作の全件に理由と当てはまり、流れの評価、問題だった点、直し方の案、ほかのエージェントとの違い）に合うかを確かめ、`<作るスキル>/dev/results/convergence/round-<R>/analysis.json` に集める。合わないものと無いものを挙げて終了コード1で終わるので、その分析役だけ `--only <課題ID>/<エージェント>` でやり直す。合ったものは残る
- `analysis-collect` は、同じ場所に、ラウンドのまとめ `analysis.md` も書く。全エージェントの問題だった点と直し方の案を、手順ごとに集めたものである（指摘の最初の「#番号」の操作がいた手順でまとめ、指摘したエージェントが多い手順から並べる）。末尾には、前のラウンドの「## 動きの指摘」の表（7章）を写す
- 分析は、読んだ記録の操作のハッシュ（`based_on`）を持つ。記録を `trace` で取り直して操作が変わったら、その分析はカタログに出ず、`skill_lint.py --final` が分析のやり直しを求める
- 分析は推定であり、収束テストの指標には数えない。分析の指摘は、締め込み（5章の「動きの指摘」）で確かめて分類する

`run` は1ラウンドに最長で「セッションの回数 ÷ 並列数（既定 3）× 1件の上限（既定 1800 秒）」かかる。Claude Code の Bash ツールは前景の実行を最大 10 分で打ち切るので、`run` はバックグラウンドで実行し、終了の通知を待ってから `diff` を実行する。バックグラウンドで実行できない環境では、`--only <実行ID,…>`（実行ID は `<課題ID>/<runner>-<番号>`）で、1回の実行が時間の上限に収まるように分ける。

## 4. 指標と基準

| 指標 | 意味 |
|---|---|
| status | エージェントごとの実行の状態。`unused` は start しなかった（スキルが起動しなかった） |
| files | 作った・変えたファイルの集合の一致度（2人ずつの Jaccard の平均） |
| structure | 共通のファイルの骨格（見出しや行の種類の並び、JSON のキーと型）が一致する割合 |
| names | 作業で新しく作った名前（英字の識別子）の集合の一致度（2人ずつの Jaccard の平均）。課題の前からある名前は数えない。名前の付け方が揃っているかを測る |
| content | 共通のファイルの中身の一致度。参考値で、基準には使わない |
| 検出率 | 最終ラウンドのレビューで、見本ごとに違反のルールID を挙げたエージェントの割合（`review.json`） |
| check | `done` のエージェントの出力を、改めて `run.py check` で検査した結果 |

課題ごとに、次のすべてを満たせば基準を満たす。

- status が全員 `expect_status` と同じ
- check が全員通過
- スキル自身（`<base>/<name>/` の下のファイル）を変えたエージェントと、このスキルの hooks の登録を外した・変えたエージェント（`install.py --check` が失敗する）がいない。いれば失格にし、`report.md` の「スキル自身や hooks の登録を変えたエージェント（失格）」に載せる。検査を緩めて通した結果は、揃っていても測れていないからである
- files と structure が spec の `convergence.thresholds`（既定 1.0）以上、names が `convergence.thresholds.names`（既定 0.8）以上。names は、出力に識別子が無い課題（新しい名前が誰にも無い）では 1.0 になる

レビューの見本は、検出率が 1.0（全員が見つける）なら基準を満たす。満たさない見本は、課題と同じく5章で分類して締め込む（多くは V2：チェックリストの書き方があいまい、か V3：機械で守らせる段に上げられる）。

比べるファイルから外すものは、spec の `convergence.ignore`（glob の配列。既定は空）に書く。外してよいのは、実行ごとに必ず中身が変わるファイル（日時を含むログなど）だけである。外したら、その理由を `dev/convergence-report.md` の「条件」に書く。ばらついているファイルを外して基準を満たしたことにしない。

## 5. ばらつきの分類と締め込み

基準を満たさない課題は、`report.md` の「一部のエージェントだけが作った・変えたファイル」と「中身の違い」からばらつきを拾い、次の表で分類する。表の上から順に当てはめ、最初に当たった行を使う。

| 分類 | ばらつきの原因 | 締め込み方 |
|---|---|---|
| V1 | ばらついた点に答えるルールが無い | 軸を決め、ルールを足す（[variance-axes.md](variance-axes.md)） |
| V2 | ルールはあるが、書き方があいまいで解釈が分かれた | ルールを数、値、場合分けで書き直す |
| V3 | ルールはあるが、機械で守らせていない | 段を上げる（[control-ladder.md](control-ladder.md) の1章）。validate なら違反例を足す |
| V4 | スキルが起動しなかった、または手順を飛ばした | triggers を足す。手順にルールID とコマンドを足す |
| V5 | 良い例が無く、形が分かれた | `good` を足す。ひな形（template）を足す |
| V6 | 依頼文に情報が足りなかった | 入力に `default` か `ask` を足す。課題の依頼文の不備なら課題を直す |
| V7 | 製品（Claude Code と Codex）の違いで分かれた | スクリプトで吸収する。吸収できなければルールに製品ごとの行を足す |
| V8 | 結果に影響しないばらつき（言い回しの違い） | 締め込まない。記録に理由を書く |

### 動きの指摘（AI の分析）

出力を比べても、途中の動きの問題（手順の行き来、要らない操作、手順の読み違い）は見えない。この問題は、基準を満たした課題でも起きる。そこで、ばらつきに加えて、3章の `analysis.md` の指摘も、基準を満たした課題のものを含めて分類する。

1. `analysis.md` の「手順ごとの指摘」を上から読む。指摘したエージェントが多い手順ほど、エージェントではなくスキルの側に原因がある見込みが高い
2. 指摘ごとに、#番号の操作を `traces.json`（カタログの「エージェントの動き」）で確かめる。記録と合わない指摘は「推定違い」と分類し、締め込まない
3. 記録と合う指摘は、上の表の V1〜V8 で分類して締め込む。直し方の案は材料であり、そのまま採らなくてよい
4. `analysis.md` の末尾の「前のラウンドの動きの指摘」で締め込んだ指摘が、再び出ていたら、その締め込みは効いていない。指摘の列に「ラウンド <R-1> と同じ」と書き、締め込み方を変える
5. 7章の「## 動きの指摘」の表に、原因1つにつき1行で書く。分析に指摘があるエージェントは、どれかの行の「エージェントと操作」の列に入れる

動きの指摘は合格基準に数えない。ただし、次のラウンドの `convergence.py prepare` は、前のラウンドの分析が揃っていないか、指摘のあるエージェントが表に無いと止まる。`skill_lint.py --final` も、全ラウンドについて同じことを確かめる（STEP-04）。

締め込んだら、フェーズ4・5の検査（`skill_lint.py --phase 5`、`probe.py`）をやり直してから、6章で次のラウンドを決める。

## 6. 次のラウンドの決め方

「最終ラウンド」は、holdout を含む全課題で実行するラウンドである（`prepare --include-holdout`）。ラウンドは1から数え、上限は spec の `convergence.max_rounds`（既定 3）である。最終ラウンドも上限の回数に含める。ラウンド1は、上限が1なら最終ラウンド、それ以外なら通常のラウンドにする。

ラウンド R の `diff` と分析の後、次の表を上から順に当てはめ、最初に当たった行に従う。「締め込み」には、5章の動きの指摘の締め込みも入る。全課題が基準を満たした行でも、動きの指摘を締め込んでから次のラウンドへ進む。

| 状況 | 次にすること |
|---|---|
| R が通常のラウンドで、全課題が基準を満たした | R+1 を最終ラウンドにする |
| R が通常のラウンドで、基準を満たさない課題があり、R+1 が上限 | 締め込み、R+1 を最終ラウンドにする |
| R が通常のラウンドで、基準を満たさない課題があり、R+1 が上限より前 | 締め込み、R+1 を通常のラウンドにする |
| R が最終ラウンドで、全課題が基準を満たした | 終える（7章の記録へ） |
| R が最終ラウンドで、基準を満たさない課題があり、R が上限より前 | 締め込み、R+1 を再び最終ラウンドにする。holdout が既に見た課題になったことを記録に書く |
| 上のどれでもない（上限のラウンドで基準を満たさない課題が残った） | 止める。下の手順でユーザーに続けるかを聞く |

上限で止めたときは、`python3 <skill>/scripts/run.py wait --question "<質問>"` を実行してから、残った課題ごとに、ばらつきの分類（V1〜V8）と、締め込むなら何をするかを示し、ラウンドを足して続けるかを聞く（STEP-04）。ルールを足すほど作るスキルが重くなり、費用もかかるので、続けるかはユーザーが決める。

| 答え | 次にすること |
|---|---|
| 続ける | `run.py resume` を実行し、spec の `convergence.max_rounds` を1つ増やして締め込み、R+1 を最終ラウンドにする |
| 上のどれでもない | `run.py resume` を実行し、残った課題を7章の「結論」に書いて終える |

## 7. 記録（`dev/convergence-report.md`）

ラウンドごとに、指標と、ばらつき・分類・締め込みの表を書く。5章で分類した動きの指摘は、「## 動きの指摘」の節に、全ラウンド分を1つの表で書く。「ラウンド」の列には数字だけを書く。

| ラウンド | エージェントと操作 | 指摘 | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T1-typical/subagent-1 #64、T2-default/subagent-1 #55 | 手順7の検査が、手順8で書く違反例を先に求め、手順7と8を行き来した | V2 | 手順7に、検査の前に違反例の ID を書くと足した |

「分類」の列は V1〜V8 か「推定違い」にする。締め込まなかった行は、「対処」の列に理由を書く。次のラウンドの `convergence.py prepare` と `skill_lint.py --final` が、指摘のあるエージェントがどれかの行にあるかと、「分類」と「対処」の列が埋まっているかを確かめる（STEP-04）。

最後に「## 結論」の節を書き、基準を満たしたかを書く。最後のラウンドで基準を満たさなかった課題と、検出率が 1.0 に届かなかったレビューの見本は、1つにつき1行で、課題の ID、ばらつきの分類、残した理由（V8 である、またはユーザーが続けないと答えた）を「結論」に書く（例：`- T3-edge: V8。本文の動詞の言い回しだけが違う`）。`skill_lint.py --final` が、残った課題と見本の ID が「結論」にあるかと、`reviews` があるのに最後のラウンドに `review.json` が無くないかを確かめる。

skill-foundation の最終報告の「## 収束テスト」は、`report_skill.py` が `dev/results/convergence/round-*/report.json` と「結論」から作る（RPT-02）。ラウンドごと・課題ごとの指標の表（names を含む）と、最後のラウンドの合格数、レビューの検出率が出る。残った課題には、「結論」のうちその課題の ID を含む行がそのまま出る。

`diff` は、各エージェントの動きを `traces.json` にも書く。実行の記録（start・check・finish）と、次の記録から、道具の呼び出しを時刻・道具・対象・成否・出力の抜粋（先頭 400 字と末尾 200 字）の列にする。runner claude では、実行の記録だけになる。`traces.json` の無いラウンドには、`convergence.py trace` で後から足す。`diff` と `trace` は、エージェントが読んだ SKILL.md の写しも `used-SKILL.md` として同じ場所に残す。締め込みで SKILL.md を変えた後に分析し直しても、分析と `analysis.md` はそのラウンドの手順と比べる。各エージェントの動きの AI の分析は、同じ場所の `analysis.json` に置く（3章）。

| runner | 道具の呼び出しの記録 | 実行との突き合わせ |
|---|---|---|
| `subagent`（Claude Code） | Agent ツールの記録（Claude Code が `~/.claude/projects/` に置く） | 最初のメッセージがプロンプトの全文と一致するもの |
| `subagent`（Codex） | Codex のサブエージェントの記録（Codex が `~/.codex/sessions/<年>/<月>/<日>/rollout-*.jsonl` に置く） | コマンドとファイルのパスに、その実行の作業ディレクトリが一番多く出るもの（依頼文は暗号化されて残るため） |
| `codex` | `run` が保存した `codex exec --json` の出力（`_results/<実行ID>.events.jsonl`。出来事に時刻が無いので、行ごとに届いた時刻を付ける） | 実行ごとのファイル |

記録は、plan を作った時刻（plan.json の `prepared_at`）より後のものだけを探す。Codex の記録の道具は、Claude Code の道具の名前（コマンドは Bash、ファイルの追加は Write、変更は Edit、画像を見たのは Read）にそろえて、カタログが同じに読む。

finish は、`catalog.py` でカタログも作り直す（RPT-02）。カタログは、一覧（`.skill-runs/catalog.html`）とスキルごとのページ（`.skill-runs/catalog/<名前>.html`）に分かれる。スキルのページには、作ったスキルのワークフロー図に、この記録（最後のラウンドで変わったファイルの揃い方、チェックポイント（run.py start・check・finish）を通った回数、手順ごとの操作の回数）を重ねて載せ、エージェントごとの動き（いた手順の時間の流れ、失敗した操作、作業ディレクトリの外に触れた操作、操作の一覧と、操作ごとの手順との照合・AI が推し量った理由、流れの評価）を描く。カタログはほかのファイルから作る図なので、収束テストの指標には数えない。
