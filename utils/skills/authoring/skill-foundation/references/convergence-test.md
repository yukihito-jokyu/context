# 収束テスト（フェーズ6）

フェーズ5までで、決定を機械で守らせる仕組みはできている。しかし、仕組みが揃っていても、別の AI が同じ依頼から同じ出力を作るとは限らない。決めていない軸が残っていたり、手順が読み違えられたりするからである。収束テストでは、作成に関わっていない独立エージェントに同じ依頼を解かせ、出力の違い（揺れ）を測る。揺れが見つかれば、原因を分類して決定や仕組みを締め込み、もう一度測る。

この章は次の順に読む。1章で課題を作り、2章で実行するかを決め、3章で実行し、4章で結果を読み、5章で揺れを分類して締め込み、6章で次のラウンドを決め、7章で記録する。段 review の決定（人や AI が読んで確かめる決定）は、出力を比べても見落としが分からないので、最終ラウンドでレビューの検出率も測る（3章の終わりと4章）。

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
| `kind` | `typical`（最もよくある依頼）、`default`（既定値で補う入力を書かない依頼）、`edge`（決定表の境目に当たる依頼）、`holdout`（上と違う種類の依頼。最後のラウンドまで使わない） |
| `prompt` | ユーザーが実際に書く依頼文。聞くべき入力は依頼文に含める（独立エージェントは質問に答えてもらえない） |
| `fixture`、`setup` | 一時プロジェクトの元にするディレクトリと、準備のコマンド |
| `invoke` | `explicit` なら、依頼文の前に Claude Code は `/<name>`、Codex は `$<name>` を付ける。省けば付けない（自動の起動も測る） |
| `expect_status` | 全員がこの status になることを期待する。既定は `done`。対象外の依頼なら `aborted` か `unused`（start しない） |

課題は次の規則で作る。`skill_lint.py --final` が確かめる。

- holdout 以外を3つ以上、holdout を1つ以上作る
- `fixture` は `dev/fixtures/basic` の1つだけにし、課題ごとの違い（ファイルの追加、ステージする変更）は `setup` のコマンドで作る。`dev/fixtures/` の下に `basic` のほかのディレクトリやスクリプトを置かない。fixture の数と名前が作る AI ごとに分かれないようにするためである
- `prompt` に、スキルの名前、決定の ID（`OUT-02` の形）、`scripts/`、`run.py`、`SKILL.md` を書かない。ユーザーはこれらを知らずに依頼する。書くと、スキルが自分で起動するか、手順を自分で読み取れるかを測れない
- `invoke: explicit` は、`triggers.implicit` が `false` のスキルだけに使う。`implicit` が `false` のスキルでは、`expect_status` が `done` の課題に `invoke: explicit` を付ける（付けないと Claude Code ではスキルが起動しない）

## 2. 実行するか（入力 `measure`）

収束テストは、課題の数 × runner の数 × 人数（既定 2）の回数だけ、エージェントのセッションを起動する。起動には費用がかかるので、skill-foundation の入力 `measure` で扱いを決める（STEP-02）。

| `measure` | 扱い |
|---|---|
| `ask` | `convergence.py prepare` が出したセッションの回数を示し、`run.py wait --question` を実行してから、実行してよいかを聞く。答えが「はい」なら実行する。それ以外なら `skip` と同じにする |
| `run` | 聞かずに実行する |
| `skip` | 実行しない。spec の `convergence.skip_reason` に「利用者が収束テストを省くと指定した」と書く |
| 上のどれでもない | `ask` と同じにする |

`skip_reason` を書いてよいのは、上の表で `skip` になったときと、3章の表で runner が無いときだけである。書いたときは、skill-foundation の最終報告の「## 収束テスト」に、`report_skill.py` がその理由を出す（RPT-02）。

## 3. 実行

```bash
python3 <skill>/scripts/convergence.py prepare <作るスキル> --round <R> [--include-holdout]
python3 <skill>/scripts/convergence.py run --workdir <prepare が出した作業場所> --round <R>
python3 <skill>/scripts/convergence.py diff --workdir <作業場所> --round <R>
```

- `prepare` は、課題 × runner × 人数の分だけ一時プロジェクトを作り、スキルを写して hooks を登録する。holdout は `--include-holdout` を付けたときだけ含める（6章の最終ラウンド）
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
# prompts が示した各プロンプトファイルの中身を、Agent ツールで新しいエージェントにそのまま渡し、最終の返答を保存先に書く
python3 <skill>/scripts/convergence.py run --workdir <作業場所> --round <R>
python3 <skill>/scripts/convergence.py diff --workdir <作業場所> --round <R>
```

- エージェントは、会話の文脈を引き継がない種類（Claude Code の general-purpose など）を使う。fork のように文脈を引き継ぐ種類は使わない。作成の経緯を知るエージェントでは、独立に解いたことにならない
- プロンプトの前後に説明を足さない。prompts が作るプロンプトには、作業ディレクトリの縛りと、スキルの置き場と説明文が入っている
- エージェントの最終の返答は、そのまま保存先（`_results/<実行ID>.last.txt`）に書く。要約しない
- 複数のエージェントを並べて起動してよい

runner `subagent` には、`claude` や `codex` と比べて次の制約がある。`diff` の report.md と、skill-foundation の最終報告の「確かめていないこと」に、この制約が出る。

| 制約 | 理由 | 補うもの |
|---|---|---|
| 一時プロジェクトの hooks が働かない | エージェントは呼び出し元のセッションの設定で動き、一時プロジェクトの `.claude/settings.json` を読まない | 出力の検査は `run.py` の check と finish で行われる。hooks の働きは `probe.py` の配線で確かめている |
| 自動の起動は近似になる | エージェントは一時プロジェクトのスキルの一覧を見ない。prompts がスキルの説明文を前置きで渡す | `invoke` が `explicit` の課題は、スキルの SKILL.md の場所を直接渡す |
| runner の違い（Claude Code と Codex）を測れない | 呼び出し元と同じ製品・同じモデルで動く | 測れなかったことを最終報告に書く |
| 呼び出し元の指示ファイル（CLAUDE.md など）が混ざることがある | エージェントは呼び出し元のセッションの設定を引き継ぐ | なし。最終報告に書く |

最終ラウンドでは、課題の `diff` の後に、レビューの検出率を測る。`dev/probes.json` の `reviews`（段 review の決定の、違反を入れた見本）ごとに、独立エージェントに「完了前チェックリストで出力を確かめ、違反した決定の ID を挙げて」と頼み、違反の ID を挙げたかを数える。

```bash
python3 <skill>/scripts/convergence.py review-prepare <作るスキル> --round <R> --runners <runner> --workdir <作業場所>
python3 <skill>/scripts/convergence.py run --workdir <作業場所> --round <R> --kind review   # subagent なら先に prompts --kind review
python3 <skill>/scripts/convergence.py review-score --workdir <作業場所> --round <R> --out <作るスキル>/dev/results/convergence/round-<R>
```

- `review-prepare` は、見本 × runner × 人数の分だけ一時プロジェクトを作る。baseline の出力を置いた後に、見本の `files` で違反を入れる
- `review-score` は、`review.json` と `review.md` を書く。見本ごとの検出率（違反の ID を挙げたエージェントの割合）、余計な指摘（見本に無い決定の ID）、エージェント同士の一致、ファイルを変えたエージェントが出る

`run` は1ラウンドに最長で「セッションの回数 ÷ 並列数（既定 3）× 1件の上限（既定 1800 秒）」かかる。Claude Code の Bash ツールは前景の実行を最大 10 分で打ち切るので、`run` はバックグラウンドで実行し、終了の通知を待ってから `diff` を実行する。バックグラウンドで実行できない環境では、`--only <実行ID,…>`（実行ID は `<課題ID>/<runner>-<番号>`）で、1回の実行が時間の上限に収まるように分ける。

## 4. 指標と基準

| 指標 | 意味 |
|---|---|
| status | エージェントごとの実行の状態。`unused` は start しなかった（スキルが起動しなかった） |
| files | 作った・変えたファイルの集合の一致度（2人ずつの Jaccard の平均） |
| structure | 共通のファイルの骨格（見出しや行の種類の並び、JSON のキーと型）が一致する割合 |
| names | 作業で新しく作った名前（英字の識別子）の集合の一致度（2人ずつの Jaccard の平均）。課題の前からある名前は数えない。名前の付け方が揃っているかを測る |
| content | 共通のファイルの中身の一致度。参考値で、基準には使わない |
| 検出率 | 最終ラウンドのレビューで、見本ごとに違反の決定の ID を挙げたエージェントの割合（`review.json`） |
| check | `done` のエージェントの出力を、改めて `run.py check` で検査した結果 |

課題ごとに、次のすべてを満たせば基準を満たす。

- status が全員 `expect_status` と同じ
- check が全員通過
- スキル自身（`<base>/<name>/` の下のファイル）を変えたエージェントと、このスキルの hooks の登録を外した・変えたエージェント（`install.py --check` が失敗する）がいない。いれば失格にし、`report.md` の「スキル自身や hooks の登録を変えたエージェント（失格）」に載せる。検査を緩めて通した結果は、揃っていても測れていないからである
- files と structure が spec の `convergence.thresholds`（既定 1.0）以上、names が `convergence.thresholds.names`（既定 0.8）以上。names は、出力に識別子が無い課題（新しい名前が誰にも無い）では 1.0 になる

レビューの見本は、検出率が 1.0（全員が見つける）なら基準を満たす。満たさない見本は、課題と同じく5章で分類して締め込む（多くは V2：チェックリストの書き方があいまい、か V3：機械で守らせる段に上げられる）。

比べるファイルから外すものは、spec の `convergence.ignore`（glob の配列。既定は空）に書く。外してよいのは、実行ごとに必ず中身が変わるファイル（日時を含むログなど）だけである。外したら、その理由を `dev/convergence-report.md` の「条件」に書く。揺れているファイルを外して基準を満たしたことにしない。

## 5. 揺れの分類と締め込み

基準を満たさない課題は、`report.md` の「一部のエージェントだけが作った・変えたファイル」と「中身の違い」から揺れを拾い、次の表で分類する。表の上から順に当てはめ、最初に当たった行を使う。

| 分類 | 揺れの原因 | 締め込み方 |
|---|---|---|
| V1 | 揺れた点に答える決定が無い | 軸を決め、決定を足す（[variance-axes.md](variance-axes.md)） |
| V2 | 決定はあるが、書き方があいまいで解釈が分かれた | 決定を数、値、決定表で書き直す |
| V3 | 決定はあるが、機械で守らせていない | 段を上げる（[control-ladder.md](control-ladder.md) の1章）。validate なら違反例を足す |
| V4 | スキルが起動しなかった、または手順を飛ばした | triggers を足す。手順に決定の ID とコマンドを足す |
| V5 | 良い例が無く、形が分かれた | `good` を足す。ひな形（template）を足す |
| V6 | 依頼文に情報が足りなかった | 入力に `default` か `ask` を足す。課題の依頼文の不備なら課題を直す |
| V7 | 製品（Claude Code と Codex）の違いで分かれた | スクリプトで吸収する。吸収できなければ決定に製品ごとの行を足す |
| V8 | 結果に影響しない揺れ（言い回しの違い） | 締め込まない。記録に理由を書く |

締め込んだら、フェーズ4・5の検査（`skill_lint.py --phase 5`、`probe.py`）をやり直してから、6章で次のラウンドを決める。

## 6. 次のラウンドの決め方

「最終ラウンド」は、holdout を含む全課題で実行するラウンドである（`prepare --include-holdout`）。ラウンドは1から数え、上限は spec の `convergence.max_rounds`（既定 3）である。最終ラウンドも上限の回数に含める。ラウンド1は、上限が1なら最終ラウンド、それ以外なら通常のラウンドにする。

ラウンド R の `diff` の後、次の表を上から順に当てはめ、最初に当たった行に従う。

| 状況 | 次にすること |
|---|---|
| R が通常のラウンドで、全課題が基準を満たした | R+1 を最終ラウンドにする |
| R が通常のラウンドで、基準を満たさない課題があり、R+1 が上限 | 締め込み、R+1 を最終ラウンドにする |
| R が通常のラウンドで、基準を満たさない課題があり、R+1 が上限より前 | 締め込み、R+1 を通常のラウンドにする |
| R が最終ラウンドで、全課題が基準を満たした | 終える（7章の記録へ） |
| R が最終ラウンドで、基準を満たさない課題があり、R が上限より前 | 締め込み、R+1 を再び最終ラウンドにする。holdout が既に見た課題になったことを記録に書く |
| 上のどれでもない（上限のラウンドで基準を満たさない課題が残った） | 止める。下の手順でユーザーに続けるかを聞く |

上限で止めたときは、`python3 <skill>/scripts/run.py wait --question "<質問>"` を実行してから、残った課題ごとに、揺れの分類（V1〜V8）と、締め込むなら何をするかを示し、ラウンドを足して続けるかを聞く（STEP-04）。ルールを足すほど作るスキルが重くなり、費用もかかるので、続けるかはユーザーが決める。

| 答え | 次にすること |
|---|---|
| 続ける | `run.py resume` を実行し、spec の `convergence.max_rounds` を1つ増やして締め込み、R+1 を最終ラウンドにする |
| 上のどれでもない | `run.py resume` を実行し、残った課題を7章の「結論」に書いて終える |

## 7. 記録（`dev/convergence-report.md`）

ラウンドごとに、指標と、揺れ・分類・締め込みの表を書く。最後に「## 結論」の節を書き、基準を満たしたかを書く。最後のラウンドで基準を満たさなかった課題と、検出率が 1.0 に届かなかったレビューの見本は、1つにつき1行で、課題の ID、揺れの分類、残した理由（V8 である、またはユーザーが続けないと答えた）を「結論」に書く（例：`- T3-edge: V8。本文の動詞の言い回しだけが違う`）。`skill_lint.py --final` が、残った課題と見本の ID が「結論」にあるかと、`reviews` があるのに最後のラウンドに `review.json` が無くないかを確かめる。

skill-foundation の最終報告の「## 収束テスト」は、`report_skill.py` が `dev/results/convergence/round-*/report.json` と「結論」から作る（RPT-02）。ラウンドごと・課題ごとの指標の表（names を含む）と、最後のラウンドの合格数、レビューの検出率が出る。残った課題には、「結論」のうちその課題の ID を含む行がそのまま出る。
