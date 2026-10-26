# skill-foundation 収束テストの記録

このスキルの作成に関わっていない独立エージェントに同じ依頼を解かせ、出力の違い（揺れ）を測った記録である。生データは `dev/results/convergence/round-<R>/` にある。

## 条件

| 項目 | 値 |
|---|---|
| runner | subagent（Agent ツールの general-purpose）。spec の `convergence.runners` は利用者の指定で `claude` だけにしたが、`claude -p` の起動が auto mode の安全判定で拒否された。起動できる runner が無くなったので、STEP-03 の表の「どちらも起動できず、Agent ツールがある」の行で subagent を選んだ |
| runner の制約 | 一時プロジェクトの hooks は働かず、`run.py check` と `finish` だけで検査された。自動の起動は、スキルの説明文を前置きで渡した近似である。subagent は呼び出し元の設定（グローバルの CLAUDE.md）を引き継ぐ（[references/convergence-test.md](../references/convergence-test.md) の3章） |
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

| 見本 | 決定 | 検出率 | 余計な指摘 | 一致 |
|---|---|---|---|---|
| OUT-03-r1 | OUT-03 | 1.000 | なし | はい |

## ラウンド 1

### 揺れと分類

| # | 課題 | 揺れ | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T3 | 動詞が convert と analyze に分かれ、名前と全ファイルの置き場が変わった | V2 | intake.md 2章の動詞の表を、出力の中身の作り方で選ぶ定義にし、例を足した。skill-profiles.json の label も合わせた |
| 2 | T3 | Codex だけのスキルに、install.py が Claude Code 側の置き場と hooks も作った（2人とも手で外した） | V7 | 契約に targets を入れ、install.py の `--targets` の既定を契約の targets にした |
| 3 | T3 | Codex だけのスキルの「1. 使う場面」「8. 制御の仕組み」に、Claude Code の呼び方と設定ファイルが出た | V7 | render_skill.py が、対象の製品の分だけ書く |
| 4 | T2 | CHANGELOG.md を直接書き換えるか、`{run}/out/` に書くだけかが分かれた | V2 | control-ladder.md 4章に、出力の置き場の決定表を足した |
| 5 | T1・T2 | 部品のモジュール（`_changes.py`、`_changelog.py`）を作るかが分かれた | V1 | control-ladder.md 5章に規則を足し、skill_lint.py が `_` で始まるスクリプトをエラーにする |
| 6 | T1・T2 | dev/fixtures の数と名前が分かれた（basic、change、english、stage_*.sh） | V1 | fixture は `dev/fixtures/basic` の1つにし、違いは setup に書く。skill_lint.py --final が確かめる。skill-foundation 自身の fixture も project から basic にした |
| 7 | T1 | 出力の path が `{run}/out/commit-message.txt` と `{run}/out/*` に分かれた | V2 | count の max が 1 ならファイル名まで書く。skill_lint.py が確かめる |
| 8 | T1・T2・T3 | 軸のまとめ方が分かれ、決定の数と ID がずれた（P1・P5 をまとめるか、対象外にするか） | V2 | 未対処。1決定1軸の規則は、見本の決定の ID の振り直しを伴うので、利用者に提案する |
| 9 | T1・T2・T3 | 依頼に無い値（文末の形、文字数・件数の上限、basis）の選び方が分かれた | V6 | 未対処。依頼に情報が無く、basis の順で選んでも答えが1つに決まらない |
| 10 | T1・T2・T3 | fixture のコード、違反例、課題の依頼文、調査記録の中身 | V8 | 締め込まない。試験の材料で、作ったスキルの振る舞いに影響しない |
| 11 | T1 | subagent-1 が `.skill-runs/skill-foundation/tmp/` に試しのファイルを残した | V8 | 締め込まない。実行記録の置き場で、CTL-05 が許す |
| 12 | T3 | subagent-2 が finish の本文の前後に、呼び出し元への説明を足した | V7 | 未対処。runner subagent は呼び出し元に報告する立場で動く |
| 13 | T1 | subagent-2 が、グローバルの CLAUDE.md の指示（`{TICKET-ID} {日本語の説明}`）に合わせた | V7 | 未対処。subagent は呼び出し元の設定を引き継ぐ（convergence-test.md 3章の制約） |
| 14 | T1 | subagent-1 が、一時プロジェクトの git にコミットを作って取り消した | V3 | 未対処。CTL-05 は作業ツリーだけを比べ、履歴の変更を見ない |

ほかに、names の数え方を直した（base64 の長い語が混ざっていたので、3〜40文字の語に限った）。

## ラウンド 2

### 揺れと分類

| # | 課題 | 揺れ | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T2・T3 | 出力の ID（entry と changelog-entry）とファイル名（todo-list.md と todo-comments.md）が分かれた | V2 | 出力が1つなら、id は名前の目的語、`{run}/out/` のファイル名は `<目的語>.<拡張子>` にし、見本も同じ名前にする。skill_lint.py が確かめる。見本の出力 id も message から commit-message にした |
| 2 | T1 | スクリプトの名前が分かれた（staged_changes.py と staged_files.py） | V2 | 未対処。名前の規則は見本の2本のスクリプトの作り直しを伴うので、利用者に提案する |
| 3 | T1・T2・T3 | 対象外にする軸（P1・P2・P5・O5・O6）と決定の数が分かれた | V2 | 未対処（ラウンド1の #8 と同じ） |
| 4 | T1・T2・T3 | fixture の中のファイル、`.skill-runs/skill-foundation/work/` の試しのファイル | V8 | 締め込まない |

ラウンド1の締め込みのうち、次が効いた。部品のモジュールの禁止で、全員がスクリプトを1つにした。T3 の動詞は2人とも analyze になった。T2 の置き場は2人とも `{run}/out/` だけになった。install の targets で、手で外す操作が無くなった。

## ラウンド 3

### 揺れと分類

| # | 課題 | 揺れ | 分類 | 対処 |
|---|---|---|---|---|
| 1 | T1・T3 | スクリプトの数と名前が分かれた（T1: `collect_diff.py`＋`check_message.py` と `commit_message.py`、T3: `collect_todo.py` と `todo_comment.py`）。T2 は2人とも `changelog_entry.py` の1本で、サブコマンドで分けた | V2 | 未対処。「スキル固有のスクリプトは1本、名前は出力の id を snake_case にした `<id>.py`、処理はサブコマンドで分ける」を提案する（6人中4人がこの形）。T1 の subagent-1 は見本の2本（`collect_diff.py`、`check_body.py`）に倣っており、見本の作り直しを伴う |
| 2 | T1・T2・T3 | 対象外にした軸と決定の数が分かれた（T1: O6・O7・X1 の3軸と P1・P2・P5・O6・O7 の5軸、T2: 軸は2人とも O7 で決定の数が 15 と 16、T3: 3軸と5軸。スキル固有の決定の数は 10〜16） | V2 | 未対処（ラウンド1の #8、ラウンド2の #3 と同じ） |
| 3 | T1・T2 | 入力の候補 `language` を入力にするか除くかが分かれた（T1: 入力にした人と ja に固定した人、T2: 除いた人と入力にした人） | V2 | 未対処。skill-profiles.json の入力の候補ごとに、入れるか除くかの既定を決める規則を提案する |
| 4 | T1・T2・T3 | 依頼に無い値が分かれた（チケットIDの形を検査するか、項目の上限、1行の文字数の上限、ディレクトリにまとめる境目、調べる範囲を git の ls-files で決めるか、ディレクトリを辿って `.` で始まるものを除くか） | V6 | 未対処（ラウンド1の #9 と同じ） |
| 5 | T2 | subagent-2 が、入力 measure が skip なのに `convergence.py prepare` を実行し、作業場所の外（OS の一時ディレクトリ）に一時プロジェクトを残した | V3 | 未対処。STEP-02 の表は「実行しない」と決めているが、`convergence.py prepare` は実行の入力を見ない。prepare が実行記録の measure を読んで止める仕組みを提案する |
| 6 | T1・T2・T3 | fixture の中のファイル、`.skill-runs/skill-foundation/work/` の試しのファイル | V8 | 締め込まない |

ラウンド1の #12（finish の本文の前後に説明を足す）と #14（一時プロジェクトにコミットする）は、ラウンド3では起きなかった。T1〜T3 の全員の返答が finish の本文（`## 結果` から）だけで、一時プロジェクトのコミットは全員 base の1件だけだった。ただし締め込んだ結果ではないので、未対処のまま扱う。

## 結論

合格基準を満たさなかった。status、check、失格、holdout（H1-holdout は2人とも unused）、レビューの検出率（OUT-03-r1 は 1.000）は満たした。満たさなかったのは、T1〜T3 の files・structure・names と、V1〜V7 の未対処0件である。上限の3ラウンドに達したので、ここで止める。締め込みを続けるかは利用者が決める（STEP-04）。

- T1-typical: V2（スクリプトの数と名前、対象外にした軸と決定の数、入力の候補 language の扱い）と V6（依頼に無い値）。締め込みは、見本 write-commit-message のスクリプトの1本化と決定の ID の振り直しを伴うため、上限のラウンドで止めた。続けるかは利用者の判断を待つ
- T2-default: V2（対象外にした軸と決定の数、入力の候補 language の扱い）、V3（measure が skip のときの prepare の実行）、V6（依頼に無い値）。fixture と実行記録の置き場（V8）を除くと files は 1.000 で、作ったスキルのファイルの構成は揃っている。上限のラウンドで止めた。続けるかは利用者の判断を待つ
- T3-edge: V2（スクリプトの名前、対象外にした軸と決定の数）と V6（調べる範囲の決め方）。上限のラウンドで止めた。続けるかは利用者の判断を待つ

names は3ラウンドとも 0.14〜0.24 で、基準の 0.8 から遠い。fixture・違反例・調査記録に出る語（V8）を含めて数えているためで、V2 を締め込んでも、この数え方のままでは届かない見込みである。
