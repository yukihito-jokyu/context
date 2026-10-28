# skill-foundation 収束テストの記録

このスキルの作成に関わっていない独立エージェントに同じ依頼を解かせ、出力の違い（ばらつき）を測った記録である。生データは `dev/results/convergence/round-<R>/` にある。

## 条件

| 項目 | 値 |
|---|---|
| runner | subagent（Agent ツールの general-purpose）。spec の `convergence.runners` は利用者の指定で `claude` だけにしたが、`claude -p` の起動が auto mode の安全判定で拒否された。起動できる runner が無くなったので、STEP-03 の表の「どちらも起動できず、Agent ツールがある」の行で subagent を選んだ |
| runner の限界 | 一時プロジェクトの hooks は働かず、`run.py check` と `finish` だけで検査された。自動の起動は、スキルの説明文を前置きで渡した近似である。subagent は呼び出し元の設定（グローバルの CLAUDE.md）を引き継ぐ（[references/convergence-test.md](../references/convergence-test.md) の3章） |
| 1 runner あたりの人数 | 2 |
| 課題 | `dev/evals.json`（T1-typical、T2-default、T3-edge。最後のラウンドは H1-holdout を足した） |
| 比べるファイルから外したもの | なし（`convergence.ignore` は空） |
| 合格基準 | status が全員、課題の expect_status と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェント（失格）がいない。files ≥ 1.0、structure ≥ 1.0、names ≥ 0.8。最後のラウンドのレビューの検出率が全見本で 1.0。V1〜V7 の未対処が0件 |

## ラウンドの一覧

| ラウンド | 課題 | status | files | structure | names | content | check | 失格 | V1〜V7 の未対処 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | T1-typical | done（全員） | 0.535 | 0.391 | 0.212 | 0.644 | 全員通過 | なし | 4 |
| 1 | T2-default | done（全員） | 0.500 | 0.429 | 0.163 | 0.622 | 全員通過 | なし | 2 |
| 1 | T3-edge | done（全員） | 0.054 | 1.000 | 0.176 | 0.500 | 全員通過 | なし | 3 |
| 2 | T1-typical | done（全員） | 0.875 | 0.429 | 0.223 | 0.711 | 全員通過 | なし | 2 |
| 2 | T2-default | done（全員） | 0.629 | 0.318 | 0.173 | 0.599 | 全員通過 | なし | 1 |
| 2 | T3-edge | done（全員） | 0.677 | 0.429 | 0.244 | 0.577 | 全員通過 | なし | 1 |
| 3 | T1-typical | done（全員） | 0.760 | 0.421 | 0.139 | 0.658 | 全員通過 | なし | 4 |
| 3 | T2-default | done（全員） | 0.440 | 0.364 | 0.178 | 0.610 | 全員通過 | なし | 4 |
| 3 | T3-edge | done（全員） | 0.667 | 0.400 | 0.202 | 0.644 | 全員通過 | なし | 3 |
| 3 | H1-holdout | unused（全員） | 1.000 | 1.000 | 1.000 | — | — | なし | 0 |

files の値は、試験の材料（`dev/fixtures/` の中身）と実行記録の置き場（`.skill-runs/`）の違い（V8）も含む。参考として、それらを除いて数え直すと、files は次のとおりである（基準の判定には使わない）。

| ラウンド | T1-typical | T2-default | T3-edge |
|---|---|---|---|
| 2 | 0.895 | 1.000 | 0.889 |
| 3 | 0.850 | 1.000 | 0.889 |

ラウンド3で除いた後に残る違いは、T1 と T3 のスクリプトの数と名前（ラウンド3の #1）だけである。names も、fixture・違反例・調査記録に出る語（チケットIDの例、製品名）を含んで数えている。

## レビューの検出率（最後のラウンド）

| 見本 | ルール | 検出率 | 余計な指摘 | 一致 |
|---|---|---|---|---|
| OUT-03-r1 | OUT-03 | 1.000 | なし | はい |

## ラウンド 1

### ばらつきと分類

| # | 課題 | ばらつき | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T3 | 動詞が convert と analyze に分かれ、名前と全ファイルの置き場が変わった | V2 | intake.md 2章の動詞の表を、出力の中身の作り方で選ぶ定義にし、例を足した。skill-profiles.json の label も合わせた |
| 2 | T3 | Codex だけのスキルに、install.py が Claude Code 側の置き場と hooks も作った（2人とも手で外した） | V7 | 契約に targets を入れ、install.py の `--targets` の既定を契約の targets にした |
| 3 | T3 | Codex だけのスキルの「1. 使う場面」「8. 制御の仕組み」に、Claude Code の呼び方と設定ファイルが出た | V7 | render_skill.py が、対象の製品の分だけ書く |
| 4 | T2 | CHANGELOG.md を直接書き換えるか、`{run}/out/` に書くだけかが分かれた | V2 | control-ladder.md 4章に、出力の置き場の場合分けを足した |
| 5 | T1・T2 | 部品のモジュール（`_changes.py`、`_changelog.py`）を作るかが分かれた | V1 | control-ladder.md 5章に規則を足し、skill_lint.py が `_` で始まるスクリプトをエラーにする |
| 6 | T1・T2 | dev/fixtures の数と名前が分かれた（basic、change、english、stage_*.sh） | V1 | fixture は `dev/fixtures/basic` の1つにし、違いは setup に書く。skill_lint.py --final が確かめる。skill-foundation 自身の fixture も project から basic にした |
| 7 | T1 | 出力の path が `{run}/out/commit-message.txt` と `{run}/out/*` に分かれた | V2 | count の max が 1 ならファイル名まで書く。skill_lint.py が確かめる |
| 8 | T1・T2・T3 | 軸のまとめ方が分かれ、ルールの数と ID がずれた（P1・P5 をまとめるか、対象外にするか） | V2 | 未対処。1ルール1軸の規則は、見本のルールID の振り直しを伴うので、利用者に提案する |
| 9 | T1・T2・T3 | 依頼に無い値（文末の形、文字数・件数の上限、basis）の選び方が分かれた | V6 | 未対処。依頼に情報が無く、basis の順で選んでも答えが1つに決まらない |
| 10 | T1・T2・T3 | fixture のコード、違反例、課題の依頼文、調査記録の中身 | V8 | 締め込まない。試験の材料で、作ったスキルの振る舞いに影響しない |
| 11 | T1 | subagent-1 が `.skill-runs/skill-foundation/tmp/` に試しのファイルを残した | V8 | 締め込まない。実行記録の置き場で、CTL-05 が許す |
| 12 | T3 | subagent-2 が finish の本文の前後に、呼び出し元への説明を足した | V7 | 未対処。runner subagent は呼び出し元に報告する立場で動く |
| 13 | T1 | subagent-2 が、グローバルの CLAUDE.md の指示に合わせた | V7 | 未対処。subagent は呼び出し元の設定を引き継ぐ（convergence-test.md 3章の限界） |
| 14 | T1 | subagent-1 が、一時プロジェクトの git にコミットを作って取り消した | V3 | 未対処。CTL-05 は作業ツリーだけを比べ、履歴の変更を見ない |

ほかに、names の数え方を直した（base64 の長い語が混ざっていたので、3〜40文字の語に限った）。

## ラウンド 2

### ばらつきと分類

| # | 課題 | ばらつき | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T2・T3 | 出力の ID（entry と changelog-entry）とファイル名（todo-list.md と todo-comments.md）が分かれた | V2 | 出力が1つなら、id は名前の目的語、`{run}/out/` のファイル名は `<目的語>.<拡張子>` にし、見本も同じ名前にする。skill_lint.py が確かめる。見本の出力 id も message から commit-message にした |
| 2 | T1 | スクリプトの名前が分かれた（staged_changes.py と staged_files.py） | V2 | 未対処。名前の規則は見本の2本のスクリプトの作り直しを伴うので、利用者に提案する |
| 3 | T1・T2・T3 | 対象外にする軸（P1・P2・P5・O5・O6）とルールの数が分かれた | V2 | 未対処（ラウンド1の #8 と同じ） |
| 4 | T1・T2・T3 | fixture の中のファイル、`.skill-runs/skill-foundation/work/` の試しのファイル | V8 | 締め込まない |

ラウンド1の締め込みのうち、次が効いた。部品のモジュールの禁止で、全員がスクリプトを1つにした。T3 の動詞は2人とも analyze になった。T2 の置き場は2人とも `{run}/out/` だけになった。install の targets で、手で外す操作が無くなった。

## ラウンド 3

### ばらつきと分類

| # | 課題 | ばらつき | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T1・T3 | スクリプトの数と名前が分かれた（T1: `collect_diff.py`＋`check_message.py` と `commit_message.py`、T3: `collect_todo.py` と `todo_comment.py`）。T2 は2人とも `changelog_entry.py` の1本で、サブコマンドで分けた | V2 | 未対処。「スキル固有のスクリプトは1本、名前は出力の id を snake_case にした `<id>.py`、処理はサブコマンドで分ける」を提案する（6人中4人がこの形）。T1 の subagent-1 は見本の2本（`collect_diff.py`、`check_body.py`）に倣っており、見本の作り直しを伴う |
| 2 | T1・T2・T3 | 対象外にした軸とルールの数が分かれた（T1: O6・O7・X1 の3軸と P1・P2・P5・O6・O7 の5軸、T2: 軸は2人とも O7 でルールの数が 15 と 16、T3: 3軸と5軸。スキル固有のルールの数は 10〜16） | V2 | 未対処（ラウンド1の #8、ラウンド2の #3 と同じ） |
| 3 | T1・T2 | 入力の候補 `language` を入力にするか除くかが分かれた（T1: 入力にした人と ja に固定した人、T2: 除いた人と入力にした人） | V2 | 未対処。skill-profiles.json の入力の候補ごとに、入れるか除くかの既定を決める規則を提案する |
| 4 | T1・T2・T3 | 依頼に無い値が分かれた（チケットIDの形を検査するか、項目の上限、1行の文字数の上限、ディレクトリにまとめる境目、調べる範囲を git の ls-files で決めるか、ディレクトリを辿って `.` で始まるものを除くか） | V6 | 未対処（ラウンド1の #9 と同じ） |
| 5 | T2 | subagent-2 が、入力 measure が skip なのに `convergence.py prepare` を実行し、作業場所の外（OS の一時ディレクトリ）に一時プロジェクトを残した | V3 | 未対処。STEP-02 の表は「実行しない」と決めているが、`convergence.py prepare` は実行の入力を見ない。prepare が実行記録の measure を読んで止める仕組みを提案する |
| 6 | T1・T2・T3 | fixture の中のファイル、`.skill-runs/skill-foundation/work/` の試しのファイル | V8 | 締め込まない |

ラウンド1の #12（finish の本文の前後に説明を足す）と #14（一時プロジェクトにコミットする）は、ラウンド3では起きなかった。T1〜T3 の全員の返答が finish の本文（`## 結果` から）だけで、一時プロジェクトのコミットは全員 base の1件だけだった。ただし締め込んだ結果ではないので、未対処のまま扱う。

## 動きの指摘

各エージェントの動きを別の AI が分析した指摘（`dev/results/convergence/round-<R>/analysis.md`）を、操作の記録（`traces.json`）で確かめて分類した。分析は全ラウンドの後（2026-10-28）に作ったので、当時の締め込みには使っていない。対処の「未対処」はそのためで、案は次に直すときの候補である。分析役は、各ラウンドで使った手順ではなく、分析した時点の SKILL.md と比べている。

3ラウンドとも出た指摘は次の4つである。

- 手順7の `skill_lint.py --phase 4` が、手順8で書く `probes.json` の違反例を先に求め、手順7と8を行き来した（V2。ラウンド3は6人全員）
- spec の checks・置き換え・probe の setup の書き方を references で引けず、スクリプトの中身を読んだ（V1）
- 固有のスクリプトを、probe の外の一時の場所で手で試した（V1）
- measure が skip のとき、手順9の文面と STEP-02 が食い違い、`prepare` を実行するかが分かれた（V2）

この4つと、2ラウンド以上で出た手順5・9の指摘は、分析の後（2026-10-28）に直した。直した行は「対処」に何を変えたかを書いた。直した後のラウンドは実行していないので、効いたかはまだ測っていない。

| ラウンド | エージェントと操作 | 指摘 | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T1-typical/subagent-1 #64、T1-typical/subagent-2 #52、T2-default/subagent-1 #55、T2-default/subagent-2 #47、T3-edge/subagent-2 #61 | 手順7の lint --phase 4 が、手順8で書く probes.json の違反例と baseline を求めてエラーになり、手順8を先にして手順7と8を行き来した | V2 | ラウンドの後（2026-10-28）に直した。probes.json の検査を skill_lint.py の phase 4 から phase 5 に移し、手順7の lint は違反例を求めない。測り直していない |
| 1 | T1-typical/subagent-1 #32・#57・#59、T1-typical/subagent-2 #23・#34・#36、T2-default/subagent-1 #31〜#33・#38、T2-default/subagent-2 #26・#27・#30 | 手順5の research.md の「使った決定」が手順6の決定 ID を求めるため、TODO で残して phase 3 の lint で埋めるか、手順6の資料を先に読んだ | V2 | ラウンドの後（2026-10-28）に直した。SKILL.md の手順5に「使ったルール」は手順6で埋めると書き、手順6に lint の前に書くと足し、research.md の雛形にも書いた。測り直していない |
| 1 | T1-typical/subagent-2 #28・#29・#32・#40〜#42・#60、T2-default/subagent-2 #48、T3-edge/subagent-1 #30〜#37、T3-edge/subagent-2 #32・#33・#35・#36・#44〜#46・#51・#65 | checks の項目と置き換え、probe の setup の動きが references に無く、スクリプトを読んだ（知らずに setup の commit が失敗した例も） | V1 | ラウンドの後（2026-10-28）に直した。control-ladder.md の4章に command 検査の動き（シェル、作業ディレクトリ、指摘になる行、rules）と report.sections を、7章に一時プロジェクトの作られ方（初回コミットの後に setup、setup で commit しない、sub が当たらないと止まる）を書き、convergence-test.md の1章の表にも setup の順を書いた。測り直していない |
| 1 | T2-default/subagent-1 #63・#64、T3-edge/subagent-1 #41・#42・#62、T3-edge/subagent-2 #53〜#56・#81・#82 | 固有のスクリプトを手で試す場所の決まりが無く、スキルの dev/ や .skill-runs に試しのプロジェクトを作った。外に一時ディレクトリを残した例も | V1 | ラウンドの後（2026-10-28）に直した。control-ladder.md の5章に、試しのプロジェクトを手で作らず、分かれ道ごとに違反例を作って probe.py で流す（中を見るなら --keep-temp で残し、見終えたら消す）と書いた。測り直していない |
| 1 | T1-typical/subagent-1 #41・#43 | 試しの git 操作が作業中のプロジェクトのリポジトリを使い、git add -A と commit でコミットを作って、#43 の git reset で戻した | V3 | 未対処（分析はラウンドの後に作った。ばらつきの表 #14 も未対処）。案: run.py start で HEAD を記録し、check と finish で HEAD が変わっていれば CTL-05 の指摘にする |
| 1 | T2-default/subagent-1 #68〜#71、T2-default/subagent-2 #66〜#70 | 手順9の文面（prepare を先に実行）と STEP-02 の skip が食い違い、省く人と、evals.json を作り setup まで試す人に分かれた | V2 | ラウンドの後（2026-10-28）に直した。手順9に skip の場合分け（convergence.py を1つも実行しない）を書き、convergence.py の prepare と review-prepare が skip_reason を見て止まるようにした（selftest で確かめた）。測り直していない |
| 1 | T3-edge/subagent-1 #63〜#67、T3-edge/subagent-2 #75〜#78 | targets が codex なのに、手順10の install.py --project . が Claude Code 側の置き場と hooks も作り、手で外した | V7 | ラウンド1の締め込みで、契約に targets を入れ、install.py の --targets の既定を契約の targets にした（ばらつきの表 #2）。ラウンド2・3では起きていない |
| 1 | T2-default/subagent-2 #58・#59・#61・#62・#72・#73 | 違反例を通した後にスクリプトと spec を変えたが、phase 5 の lint は probe の結果の古さを指摘せず、--final で初めて分かった | V3 | 未対処（分析はラウンドの後に作った）。案: skill_lint.py の --phase 5 でも、--final と同じく probe-results.json が spec・契約・スクリプトを変えた後の結果かを確かめる |
| 1 | T3-edge/subagent-1 #38〜#45 | 固有のスクリプト・fixture・見本を、調査の記録（#46）と決定（#50）より先に作った。番号の順に行う決まりはあるが、止める仕組みが無い | V3 | 一部を直した（2026-10-28）。SKILL.md の手順5に、固有のスクリプト・見本・fixture は手順7・8で作ると書いた。機械で止める検査は足していない。作り直しや後付けではスクリプトが既にあるのが正しく、誤った警告になるため。測り直していない |
| 1 | T3-edge/subagent-1 #69 | not_for の instead を動詞句（「その修正を直接行う」）で書き、説明文の「代わりに〜を使う」に合わず、check の後に直してやり直した | V2 | 未対処（分析はラウンドの後に作った）。案: intake.md 5章に「instead は『を使う』に続く名詞句で書く」と足し、skill_lint.py --phase 1 が「する」「行う」で終わる instead をエラーにする |
| 1 | T3-edge/subagent-2 #83 | 名前の動詞を analyze にしたが write や convert とも読めると迷い、同じ課題の subagent-1 は convert を選んで名前が揃わなかった | V2 | ラウンド1の締め込みで、intake.md 2章の動詞の表を出力の中身の作り方で選ぶ定義にし、例を足した（ばらつきの表 #1）。ラウンド2・3の T3 は2人とも analyze |
| 1 | T1-typical/subagent-2 #36・#71 | 区切りと日本語の説明を利用者のグローバルの指示に合わせたと補足に書いたが、research.md の「プロジェクトの決まり」は「使った決定：なし」で、根拠が記録に無い | V7 | 未対処（分析はラウンドの後に作った。ばらつきの表 #13 と同じく、subagent が呼び出し元の設定を引き継ぐ限界）。案: research.md の3章に、プロジェクトの外の指示に合わせたときの書き方と basis を書く |
| 1 | T1-typical/subagent-1 #2〜#4・#21・#22 | 複数のファイルを1つのコマンドで読んで出力が切れたり、zsh が「=====」を展開して失敗したりして、読み直した | V8 | 締め込まない。エージェントのシェルの使い方の誤りで、出力に影響しない |
| 1 | T1-typical/subagent-2 #47・#49 | #47 で書いた正規表現の文字の範囲を、意味を変えずにエスケープの書き方へ直した | V8 | 締め込まない。同じ意味の書き直しで、出力に影響しない |
| 1 | T2-default/subagent-1 #9・#15 | #9 で表示した spec.example.json と同じ中身を、写した後の spec.json で読み直した | V8 | 締め込まない。読み直しの1操作で、出力に影響しない |
| 2 | T1-typical/subagent-1 #62〜#64、T1-typical/subagent-2 #59・#60、T2-default/subagent-1 #49〜#53、T2-default/subagent-2 #57・#63、T3-edge/subagent-1 #57・#58 | 手順7の lint --phase 4 が probes.json の違反例と baseline を求め、手順8の probes.json を先に書いた（ラウンド1と同じ） | V2 | ラウンドの後（2026-10-28）に直した。probes.json の検査を skill_lint.py の phase 4 から phase 5 に移し、手順7の lint は違反例を求めない。測り直していない |
| 2 | T1-typical/subagent-1 #35・#36・#39〜#44・#48、T1-typical/subagent-2 #13・#36〜#40・#50〜#52、T2-default/subagent-1 #13・#30〜#34・#41・#42、T2-default/subagent-2 #34〜#38・#72〜#74、T3-edge/subagent-1 #33〜#39、T3-edge/subagent-2 #31〜#38・#53・#54 | spec（checks、置き換え、report.sections）と probe の setup の書き方を references で引けず、スクリプトを読んだ（ラウンド1と同じ） | V1 | ラウンドの後（2026-10-28）に直した。control-ladder.md の4章に command 検査の動き（シェル、作業ディレクトリ、指摘になる行、rules）と report.sections を、7章に一時プロジェクトの作られ方（初回コミットの後に setup、setup で commit しない、sub が当たらないと止まる）を書き、convergence-test.md の1章の表にも setup の順を書いた。測り直していない |
| 2 | T1-typical/subagent-1 #56・#57、T3-edge/subagent-1 #52・#53 | 固有のスクリプトを .skill-runs の一時の git リポジトリで手で試し、probe.py と同じことを2度確かめた（ラウンド1と同じ） | V1 | ラウンドの後（2026-10-28）に直した。control-ladder.md の5章に、試しのプロジェクトを手で作らず、分かれ道ごとに違反例を作って probe.py で流す（中を見るなら --keep-temp で残し、見終えたら消す）と書いた。測り直していない |
| 2 | T2-default/subagent-2 #39〜#43 | fixture・固有のスクリプト・見本を、調査の記録（#44）と決定（#49・#50）より先に作った（ラウンド1と同じ） | V3 | 一部を直した（2026-10-28）。SKILL.md の手順5に、固有のスクリプト・見本・fixture は手順7・8で作ると書いた。機械で止める検査は足していない。作り直しや後付けではスクリプトが既にあるのが正しく、誤った警告になるため。測り直していない |
| 2 | T1-typical/subagent-2 #70〜#73 | measure=skip で、手順9の文面にある prepare を実行しなかった。省いてよいかが手順から読めない（ラウンド1と同じ） | V2 | ラウンドの後（2026-10-28）に直した。手順9に skip の場合分け（convergence.py を1つも実行しない）を書き、convergence.py の prepare と review-prepare が skip_reason を見て止まるようにした（selftest で確かめた）。測り直していない |
| 2 | T1-typical/subagent-1 #71 | lint の無い手順9で evals.json を確かめようと、手順10の --final を先に流し、予想できるエラー（status と hooks の未登録）を出した | V1 | ラウンドの後（2026-10-28）に直した。SKILL.md の手順5と手順9に、その手順の skill_lint.py は無いと書き、evals.json は手順10の --final が確かめると書いた。測り直していない |
| 2 | T3-edge/subagent-1 #47、T3-edge/subagent-2 #72 | 入力 source の impact を、analyze の目安（target）ではなく reversible にした。2人とも skill-profiles.md の目安から外れた | V2 | 未対処（分析はラウンドの後に作った）。案: skill-profiles.md の analyze の「入力の候補」で source の impact を決め直すか外してよい条件を書き、lint の --phase 3 で外れを警告する |
| 2 | T3-edge/subagent-2 #10・#41 | 手順3で書いた triggers の例文に、後の決定 IN-01 で対象外にした依頼（FIXME も集める、TODO.md を作る）が入り、#41 で書き直した | V1 | 未対処（分析はラウンドの後に作った）。案: SKILL.md の手順6の終わりに、決定を書いた後で triggers の use_when が対象外にした依頼を含まないかを見直すと書く |
| 2 | T3-edge/subagent-2 #48・#72 | 対象を . にすると dev/fixtures や skill-foundation の雛形の TODO まで一覧に入ると分かったが、除くかを決めずに補足に書くだけにした | V1 | 未対処（分析はラウンドの後に作った）。案: skill-profiles.md の analyze の節に、対象がプロジェクト全体のとき、スキルの置き場（.agents/skills、.claude/skills）を除くかを決定に書くと足す |
| 2 | T3-edge/subagent-2 #47・#72 | dev/fixtures/basic に .gitignore を置き、ホストのリポジトリで commit すると fixture の一部が git に入らない問題を残した | V1 | 未対処（分析はラウンドの後に作った）。案: convergence-test.md 1章に「fixture の .gitignore は setup で作る」と書き、skill_lint.py で警告する |
| 2 | T2-default/subagent-2 #40・#75〜#77 | 差分 basic.patch を dev/fixtures に置いて setup から使ったが、後で外へ移し、setup に差分を埋め込んで probe を流し直した | V2 | 未対処（分析はラウンドの後に作った）。ラウンド1の締め込み（fixture は basic の1つ）の後、差分の置き場が書かれていない。案: convergence-test.md の1章に、差分を setup に埋め込む見本を書く |
| 2 | T2-default/subagent-1 #12・#64 | STEP-02 の境目（5件と6件の間）を、調べずに見本 write-commit-message から写した。本人も補足に「調査で決めた数ではない」と書いた | V6 | 未対処（分析はラウンドの後に作った。ばらつきの表 #9 の依頼に無い値と同じ原因）。案: variance-axes.md の2章に、見本の値を写すときの basis と、research.md に写した理由を書くことを足す |
| 2 | T1-typical/subagent-2 #5・#6・#64・#65、T2-default/subagent-1 #54 | zsh のグロブで grep が失敗し、zsh で空になる ${PIPESTATUS[0]} で probe.py の終了コードを取れなかった（ラウンド1と同じ） | V8 | 締め込まない。シェルの使い方の誤りで、出力に影響しない（probe はどちらも失敗0件） |
| 2 | T1-typical/subagent-1 #27・#28、T1-typical/subagent-2 #31・#32、T2-default/subagent-1 #21・#24 | 同じページを WebFetch で2回取り直した。1回の問いにまとめられた | V8 | 締め込まない。別の部分を抜き出すための取り直しで、出力に影響しない |
| 2 | T1-typical/subagent-2 #41・#42 | #41・#42 で調べた CI スキップの記法を決定に使ったかは、記録から分からない | 推定違い | 記録では、#57 で OUT-07 の forbid（[skip ci]、skip-checks: の検査）に、#60 で違反例 OUT-07-a に使っている |
| 2 | T2-default/subagent-2 #61〜#63 | 長すぎる項目の違反例の文が91字で100字に届かず、自分で書いた assert で止まって書き直した | V8 | 締め込まない。作業用スクリプトの中の確かめで、出力に影響しない |
| 3 | T1-typical/subagent-1 #45・#46、T1-typical/subagent-2 #62・#67、T2-default/subagent-1 #58・#60、T2-default/subagent-2 #49・#53、T3-edge/subagent-1 #50・#51、T3-edge/subagent-2 #58・#63 | 手順7の lint --phase 4 が probes.json の違反例を求め、6人全員が手順8の probes.json を先に書いた（ラウンド1・2と同じ） | V2 | ラウンドの後（2026-10-28）に直した。probes.json の検査を skill_lint.py の phase 4 から phase 5 に移し、手順7の lint は違反例を求めない。測り直していない |
| 3 | T1-typical/subagent-1 #7・#14・#19〜#21・#29・#31〜#33・#41・#52、T1-typical/subagent-2 #31〜#40・#46・#74、T2-default/subagent-1 #29・#30・#39〜#44、T2-default/subagent-2 #32〜#34・#51・#52・#62・#63、T3-edge/subagent-1 #12・#29〜#35・#40、T3-edge/subagent-2 #43〜#47・#59〜#61 | checks の型と置き換え、report.sections、fixture と setup の動きを references で引けず、スクリプトを読んだ（ラウンド1・2と同じ） | V1 | ラウンドの後（2026-10-28）に直した。control-ladder.md の4章に command 検査の動き（シェル、作業ディレクトリ、指摘になる行、rules）と report.sections を、7章に一時プロジェクトの作られ方（初回コミットの後に setup、setup で commit しない、sub が当たらないと止まる）を書き、convergence-test.md の1章の表にも setup の順を書いた。測り直していない |
| 3 | T1-typical/subagent-1 #18・#28〜#33・#35、T1-typical/subagent-2 #28〜#41・#42、T2-default/subagent-1 #25〜#27・#35 | research.md（手順5）を書く前に手順6〜8の資料を読み進めた。T1 の subagent-1 は決定より先に決定 ID を書いた（ラウンド1と同じ） | V2 | ラウンドの後（2026-10-28）に直した。SKILL.md の手順5に「使ったルール」は手順6で埋めると書き、手順6に lint の前に書くと足し、research.md の雛形にも書いた。測り直していない |
| 3 | T2-default/subagent-2 #66〜#69、T3-edge/subagent-1 #59 | measure=skip なのに、片方は文面どおり prepare を実行して作業場所の外に一時プロジェクトを残し、片方は省いた（ラウンド1・2と同じ） | V2・V3 | ラウンドの後（2026-10-28）に直した。手順9に skip の場合分け（convergence.py を1つも実行しない）を書き、convergence.py の prepare と review-prepare が skip_reason を見て止まるようにした（selftest で確かめた）。測り直していない |
| 3 | T2-default/subagent-1 #59・#65〜#67 | 固有のスクリプトを probe の外の一時の場所で手で試し、片付けの rm -rf が権限で止められ、試した分かれ道を違反例に足さなかった（ラウンド1・2と同じ） | V1 | ラウンドの後（2026-10-28）に直した。control-ladder.md の5章に、試しのプロジェクトを手で作らず、分かれ道ごとに違反例を作って probe.py で流す（中を見るなら --keep-temp で残し、見終えたら消す）と書いた。測り直していない |
| 3 | T3-edge/subagent-2 #74・#83 | git でない場所の試しを外側の git の中で行い、終了コード0（期待は4）を追わずに、補足に「終了コード4で中断する」と書いた | V1 | 未対処（分析はラウンドの後に作った）。案: control-ladder.md の7章に、終了コードで中断する決定は、その状況を作る fixture と違反例で終了コードを確かめると書く |
| 3 | T1-typical/subagent-1 #49 | 試しの一時リポジトリを cd の後に相対パスで rm したため消えず、残ったとみられる | 推定違い | rm が cd 先で空振りする書き方なのは記録どおり。ただし最後の差分（round-3 の subagent-1.patch）に一時リポジトリのファイルは無く、残った跡は記録に無い |
| 3 | T1-typical/subagent-1 #36 | 手順5の終わりに、存在しない skill_lint.py --phase 2 を実行して引数エラーになった（ラウンド2と同じ） | V1 | ラウンドの後（2026-10-28）に直した。SKILL.md の手順5と手順9に、その手順の skill_lint.py は無いと書き、evals.json は手順10の --final が確かめると書いた。測り直していない |
| 3 | T3-edge/subagent-1 #8・#13、T3-edge/subagent-2 #16 | run.py start の出力の「書いたら check」に従い、骨組みを作る前に check を実行して、SKILL.md が無いという分かりきった指摘を得た | V2 | 未対処（分析はラウンドの後に作った）。案: run.py start が出す「次:」を、skill-foundation では「check は手順11で実行する」にするか、手順3に「ここでは check を実行しない」と書く |
| 3 | T1-typical/subagent-1 #2〜#4、T1-typical/subagent-2 #70、T2-default/subagent-1 #62・#63 | 1つのコマンドで大きな出力を読んで切れたり、zsh で空になる PIPESTATUS や macOS に無い timeout を使ったりした（ラウンド1・2と同じ） | V8 | 締め込まない。シェルの使い方の誤りで、出力に影響しない。3ラウンド続いたので、直すなら SKILL.md の手順8に probe.py の終了コードの取り方を書く |
| 3 | T1-typical/subagent-2 #71・#72、T3-edge/subagent-2 #81・#82 | 決定文の書き損じ（リンクと読まれる「](」、二重のバッククォート）を、phase 5 の lint や目視で見つけて直し、render からやり直した | V8 | 締め込まない。エージェントの書き損じを自分で直した。直すなら skill_lint.py のリンクのエラーに行番号を添え、二重のバッククォートを警告する |
| 3 | H1-holdout/subagent-2 #1・#2・#5 | SKILL.md を読む前に find と cat でプロジェクト全体を見回し、判定の後に git status と ls -a で変更が無いことを確かめた（手順に無い） | V8 | 締め込まない。status は期待どおり unused で、出力に影響しない。#1・#2 は SKILL.md を読む前の操作で、スキルの側では防げない |
| 3 | T2-default/subagent-2 #8・#10 | 手順2の run.py start（#10）より前に、手順3で読む skill-profiles.md を読んだ | V8 | 締め込まない。読む順の違いで、出力に影響しない |
| 3 | T3-edge/subagent-1 #38 | research.md を書いた操作が記録に無く、#38 のスクリプトの中身も残っていないので、手順5の記録をいつ書いたかが分からない | V8 | 締め込まない。記録の抜けで、動きの問題とは言えない。#38 の phase3.py は作業場所の外（呼び出し元の scratchpad、#37〜#39・#44・#45）にあり、research.md は書いていない |

## 結論

合格基準を満たさなかった。status、check、失格、holdout（H1-holdout は2人とも unused）、レビューの検出率（OUT-03-r1 は 1.000）は満たした。満たさなかったのは、T1〜T3 の files・structure・names と、V1〜V7 の未対処0件である。上限の3ラウンドに達したので、ここで止める。締め込みを続けるかは利用者が決める（STEP-04）。

- T1-typical: V2（スクリプトの数と名前、対象外にした軸とルールの数、入力の候補 language の扱い）と V6（依頼に無い値）。締め込みは、見本 write-commit-message のスクリプトの1本化とルールID の振り直しを伴うため、上限のラウンドで止めた。続けるかは利用者の判断を待つ
- T2-default: V2（対象外にした軸とルールの数、入力の候補 language の扱い）、V3（measure が skip のときの prepare の実行）、V6（依頼に無い値）。fixture と実行記録の置き場（V8）を除くと files は 1.000 で、作ったスキルのファイルの構成は揃っている。上限のラウンドで止めた。続けるかは利用者の判断を待つ
- T3-edge: V2（スクリプトの名前、対象外にした軸とルールの数）と V6（調べる範囲の決め方）。上限のラウンドで止めた。続けるかは利用者の判断を待つ

names は3ラウンドとも 0.14〜0.24 で、基準の 0.8 から遠い。fixture・違反例・調査記録に出る語（V8）を含めて数えているためで、V2 を締め込んでも、この数え方のままでは届かない見込みである。
