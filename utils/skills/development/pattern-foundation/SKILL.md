---
name: pattern-foundation
description: 任意の分野・技術スタック・ツール指定から、「誰が書いても同じ書き方になる」ことを目標にルールを機械で強制する開発基盤一式（ディレクトリ構造、formatter・linter・構造検査の設定、参照実装、AGENTS.md/CLAUDE.md、実装用・レビュー用スキル、設計ドキュメント）を1つのディレクトリに作り、履歴を持たない独立エージェントに同じ課題を解かせて書き方が揃うまでルールを締め込む。「〇〇と△△を使ったアーキテクチャの基盤を作って」「ルールをガチガチにして誰が書いても同じにしたい」「AIが書いてもブレない規約とlint」「impl/reviewスキルも作って」「テンプレートリポジトリ・スターター・ボイラープレートを作って」「既存リポジトリに規約・lint・エージェント用スキルを後付けして書き方を揃えたい」といった依頼では、フロントエンド・バックエンド・IaC・データ基盤・モバイル・CLI・ライブラリ・技術文書のどの分野でも、技術名やスキル名が明示されていなくても必ず使う。
---

# pattern-foundation

## ゴール

ルールを書くこと自体はゴールではない。**同じ依頼を受けた別々の作者（人・エージェント）が、同じものを書く状態**を作ることがゴールである。そのために次の3つを組み合わせる。

1. **決める**：書き方が作者によって分かれうる点（以下「揺れの軸」）を洗い出し、軸ごとに答えを1つに決める
2. **縛る**：決めた答えを、できるだけ機械（型・formatter・linter・構造検査・テスト・生成器）で強制する。機械で縛れない分だけをレビュースキルと文書に回す
3. **測る**：履歴を持たない独立エージェントN人に同じ課題を解かせ、出力の違い（残った揺れ）を計測し、原因ごとにルールや仕組みを足して再計測する

「十分に厳しくなった」と自己評価で判断しない。ルールを書いた本人には行間が見えているため、独立した作者が同じものを書くかどうかは測るまで分からない。**測定（収束テスト）の結果を完了条件にする。**

## 原則

判断に迷ったらこの表に戻る。

| 原則 | 理由 |
|---|---|
| 調べてから決める（公式の推奨、最新の安定版、出典） | エージェントは公式ドキュメントの書き方を多く学習しているため、公式に沿ったルールほど守られる。記憶にあるバージョンや設定キーは古い可能性がある |
| 1つの軸に答えは1つ | 「どちらでもよい」「場合による」が残ると、作者ごとに選択が分かれる。条件で答えが変わるなら「条件 → 答え」の決定表にする |
| 機械で縛れるものは機械で縛る | 文書だけのルールは読み飛ばされ、忘れられる。違反を書いたら落ちる仕組みだけが確実に効く |
| 縛ったことを証明する | 設定を書いても効いていないことがある。違反例（probe）を実際に流し、検査が落ちることを確かめる |
| 見本は規則より強い | 作者は一番近くにある既存コードを真似る。参照実装に全ルールを体現させ、新規追加は生成器やひな形から始めさせる |
| 変更が局所に収まる構造にする | 変更に強いとは、1つの変更で触るファイルが少なく、どこを触るか予測できることである。依存の向き・公開面・機能単位の閉じ込めを先に決める |
| 抜け道を塞ぐ | 抑止コメント、設定の緩和、テストの skip で検査を通せるなら、そのルールは無いのと同じである |
| ディレクトリの中で完結させる | バージョンを固定し、全検査を1コマンドにまとめ、文書・スキル・検査用スクリプトをすべてその中に置く |

## 入力の扱い

- ユーザーの指示を最優先する。指定された技術・ツール・名前（スキル名など）は必ず使い、より良いと思っても置き換えない
- 指定の名前が綴りの揺れや旧称で実在しない場合（例：「oxformat」）は、レジストリで確かめて公式の名前に読み替え、ADR に書く。候補が2つ以上あるなら聞く。指定の名前が実在していても、よく知られた名前と1〜2字しか違わず利用者が少ない場合は、別物（なりすましのパッケージを含む）の可能性があるので、使う前に確かめる
- 指定が公式に非推奨・廃止になっているなど問題がある場合は、作る前に伝えて判断を仰ぐ。聞けない状況なら指定どおりに作り、リスクを ADR と最終報告に書く
- 指示に無い周辺ライブラリは足さない選択を既定にし、名指しされた技術を動かすのに欠かせない部品だけを足す。足すほど作者ごとの選択が分かれ、覚えることも増えるからである
- 基盤は、指示に場所が無ければ `<作業ディレクトリ>/<基盤名>/` に作る。retrofit モードでは既存のリポジトリのルートが `<root>` になる
- 指示に無い事項の決め方、新規作成か既存への後付けかの判定は [references/intake.md](references/intake.md) に従う

## 全体の流れ

フェーズは順に進め、通過条件を満たしてから次へ進む。各フェーズでは、表の「読むもの」をそのとき読めばよく、最初に全部を読む必要はない。`<skill>` はこの SKILL.md があるディレクトリ、`<root>` は作る基盤のディレクトリを指す。

| # | フェーズ | 読むもの | 主な成果物 | 通過条件 |
|---|---|---|---|---|
| 0 | 受付 | [intake.md](references/intake.md)、[domain-profiles.md](references/domain-profiles.md) の該当分野 | `<root>/.foundation/manifest.json`（status: building） | 基盤名、モード、技術、指定ツール、スキル名、コマンド名が埋まっている |
| 1 | 骨組み | — | 文書・スキル・検査スクリプトの骨組み | `init_foundation.py` が成功している |
| 2 | 調査 | [research.md](references/research.md) | `docs/design/research.md` | 全技術のバージョンと、使うルール名をコマンドで確認し、採用する推奨に出典がある |
| 3 | 揺れを決める | [variance-axes.md](references/variance-axes.md)、[enforcement-ladder.md](references/enforcement-ladder.md) の1〜2章、[design-doc.md](references/design-doc.md) の2〜3章 | `docs/design/rules.md`、`architecture.md`、`adr/` | `rules_check.py --phase 3` が通る（全軸に答えか対象外の理由がある） |
| 4 | 作って縛る | [enforcement-ladder.md](references/enforcement-ladder.md) | ソース、設定、構造検査、参照実装、生成器、`probes.json` | check が通り、probe が全件落ち、`rules_check.py --phase 4` が通る |
| 5 | エージェント向けの入口 | [agent-surface.md](references/agent-surface.md) | `AGENTS.md`、`CLAUDE.md`、実装用・レビュー用スキル、hooks、manifest の status: ready | `rules_check.py` が通る（review・doc のルールがスキルや AGENTS.md に載っている） |
| 6 | 収束テスト | [convergence-test.md](references/convergence-test.md) | `.foundation/convergence/`、`docs/design/convergence-report.md` | 合格基準を満たす。上限回数に達した場合は残差をすべて分類している |
| 7 | 仕上げと報告 | [design-doc.md](references/design-doc.md) | `docs/design/*`、`README.md`、最終報告 | `rules_check.py --final`、check、probe の全件が通る |

### 0. 受付

指示を分解して `<root>/.foundation/manifest.json` に書く。書式は [assets/templates/manifest.example.json](assets/templates/manifest.example.json) を写し、`<…>` をすべて実際の値に置き換える。基盤名は [intake.md](references/intake.md) の命名規則で決める。同じ名前のディレクトリが既にあり中身が空でない場合は、上書きせず、後付けモードとして扱うかをユーザーに確かめる。

`status` は `building` にしておく。`building` の間は、保護ファイルを編集する前の確認（hooks）が働かない。作者自身が設定やルールを作る段階だからである。

### 1. 骨組み

```bash
python3 <skill>/scripts/init_foundation.py --root <root>
```

manifest から次の骨組みを作る。既にあるファイルは上書きしない。

- `AGENTS.md`、`CLAUDE.md`
- `docs/design/`
- 実装用・レビュー用スキルのひな形
- `.claude/settings.json`（hooks）
- `.foundation/bin/`（検査用スクリプトの写し）

ひな形の中の `TODO(pattern-foundation)` は、以降のフェーズで埋める箇所の目印である。最後に `rules_check.py --final` で、目印が残っていないことを確かめる。

ひな形は日本語で書いてある。manifest の `language` が `ja` 以外なら、埋めるときに見出しも含めてその言語に訳す。ただし、スクリプトが文字列で読む次の語は訳さない。

- rules.md のルールの項目名（`状態`、`軸`、`決定`、`理由`、`出典`、`強制`、`機械化しない理由`、`probe`、`良い例`、`悪い例`）、値の `廃止`、節の名前（「追加した軸」「対象外とした軸」）：`rules_check.py` が読む
- research.md の `確認の状態` と、その値の `確認済み`・`未確認`：`rules_check.py --final` が読む
- レビュー用スキルの判定の語 `承認`・`差し戻し`：`convergence.py review-score` が読む

### 2. 調査

公式ドキュメント・公式テンプレート・パッケージレジストリを一次情報として調べ、`docs/design/research.md` に出典付きで記録する。技術が3つ以上あるときは、技術ごとにサブエージェントへ並列で調べさせる。バージョン、設定キー、ルール名は記憶で書かず、必ずコマンドかドキュメントで確かめる。ルール名は、フェーズ3で使う前に、ツールを一時実行して一覧を取って確かめる（依存を入れるのはフェーズ4だが、ルール名はフェーズ3で必要になるため）。

### 3. 揺れを決める

[variance-axes.md](references/variance-axes.md) の軸と、[domain-profiles.md](references/domain-profiles.md) がその分野に定める「軸の読み替え」と「追加の軸（X）」を1つずつ見る。揺れる軸すべてに答えを1つ決め、`docs/design/rules.md` にルールとして書く。ルールの粒度と番号の振り方は variance-axes.md の2章に従う。

ルールの書式は rules.md のひな形どおりにし、ルールID、決定、理由、強制、probe、例をそろえる。強制の段は enforcement-ladder.md の2章の質問で選ぶ。probe の欄には、フェーズ4で作る予定の ID（`<ルールID>-a` など）を書く。実在はフェーズ4の検査で確かめられる。「なるべく」「適切に」などのあいまいな語は `rules_check.py` がエラーにするので、条件と答えで書く。

変更に強い構造の決め方（依存の向き、公開面、変更シナリオ）は `architecture.md` に書き、ツールや構造の選択理由は ADR に残す。最後に `python3 <root>/.foundation/bin/rules_check.py --root <root> --phase 3` を通す。

### 4. 作って縛る

依存を入れ、設定を書き、参照実装（全ルールを体現する見本機能）を作る。各ルールは [enforcement-ladder.md](references/enforcement-ladder.md) の順位でできるだけ上の段に載せる。機械で縛るルールには、違反例を `.foundation/probes.json` に書く。そのうえで次の3つを通す。

```bash
python3 .foundation/bin/rules_check.py --root . --phase 4  # ルール・強制・probe の対応を検査する
<check コマンド>                                           # 全検査が通る
python3 .foundation/bin/violation_probe.py --root .        # 違反例が全件、検査で落ち、各検査が check に組み込まれている
```

check コマンドには、プロジェクト自身の format・lint・型・構造検査・テストに加え、`guard.py --root .`（抑止コメントの検出）と `rules_check.py --root . --no-write`（ルールの対応の検査。ファイルは書き換えない）を含める。こうすると、ルールの仕組み自体が壊れたときも check で気づける。probe は時間がかかるので check には含めず、ルールや設定を変えたときと最終確認で回す。

### 5. エージェント向けの入口

[agent-surface.md](references/agent-surface.md) に従い、次を仕上げる。

- `AGENTS.md`（人とエージェント共通の入口）。`CLAUDE.md` は `@AGENTS.md` の1行だけにする
- 実装用スキル（依頼の振り分け表、既定値表、作る順序、完了前チェックリスト）
- レビュー用スキル（ルールIDごとの確認項目と、固定の出力形式）
- hooks（編集直後の自動整形・lint、保護ファイルを編集する前の確認）

仕上げたら manifest の `status` を `ready` にし、`rules_check.py`（フェーズ5の検査。`enforcement-matrix.md` を生成する）を通す。`ready` にすると hooks が保護ファイルを守り始める。収束テストの独立エージェントが、設定を緩めて検査を通すことを防ぐためである。

### 6. 収束テスト

[convergence-test.md](references/convergence-test.md) に従い、次を繰り返す。

1. 課題（追加・変更・横断・ホールドアウト）を作る
2. 独立エージェントN人（既定3人）に同じ課題を解かせる
3. `convergence.py` で揺れを計測する
4. 揺れを原因別に分類し、ルール・仕組み・スキル・見本を足して再計測する

あわせて、レビュー用スキルに、違反を仕込んだ差分を渡して検出率を測る。既定の上限は3ラウンドである。上限に達した場合は、残った揺れをすべて分類して報告する。

### 7. 仕上げと報告

[design-doc.md](references/design-doc.md) に従って設計ドキュメントを完成させ、最終確認を回す。

```bash
<check コマンド> && python3 .foundation/bin/violation_probe.py --root . && python3 .foundation/bin/rules_check.py --root . --final
```

最終報告は次の順で書く。読み手はこの会話の途中経過を見ていない前提で、前提から結論へつながるように書く。

1. 作ったもの：基盤名、パス、モード、主な技術とバージョン
2. 構造の要点：依存の向き、ディレクトリの切り方、変更シナリオごとに触るファイル
3. 強制の内訳：`enforcement-matrix.md` の集計（段ごとの件数）と、文書だけで守らせているルールの一覧と理由
4. 収束テストの結果：ラウンドごとの指標、残った揺れの分類、レビューの検出率
5. 検証結果：check、probe、`rules_check --final` の出力の末尾
6. 決めきれなかったこと、ユーザーに判断してほしいこと

## 既存リポジトリへの後付け（retrofit モード）

流れは同じだが、次の点を変える。理由は、既存コードとチームの慣れを壊さずに揺れだけを止めるためである。

- **フェーズ3**：答えは既存コードで多数派の書き方を数えて決める。公式の推奨と食い違い、かつ変える価値が大きい場合だけ別の答えを提案する
- **フェーズ4**：既存の違反は一括で書き換えない。ツールに baseline 機能があればそれを使い、無ければ違反ファイルの一覧を除外設定として固定して、新しい違反だけを落とす（ラチェット）。書き換えはユーザーの承認を得てから、別の作業として行う
- **書き込み先**：ユーザーが指定した範囲のファイルだけを変更する。新しく置くのは `.foundation/`、`docs/design/`、`.claude/`、設定ファイル、ルートの `AGENTS.md`・`CLAUDE.md`・`README.md` に限る。`init_foundation.py` は既にあるファイルを上書きしない。既に `CLAUDE.md` があれば、先頭に `@AGENTS.md` の1行を足し、既存の内容は残す。既存の `README.md` は変えない

## スクリプト

すべて Python 3 の標準ライブラリだけで動く。`init_foundation.py` 以外は `<root>/.foundation/bin/` に写され、基盤の中から実行できる。`--help` で使い方を表示する。

| スクリプト | 役割 | 主に使うフェーズ |
|---|---|---|
| `init_foundation.py` | manifest から骨組みを生成する（上書きしない） | 1 |
| `rules_check.py` | rules.md を検査し、`enforcement-matrix.md` を生成する。`--phase 3/4/5` でフェーズに合わせて検査を絞り、`--final` では TODO の残り・probe の結果・status も検査する | 3〜7 |
| `violation_probe.py` | 一時コピーに違反例を1件ずつ入れて検査を回し、全件落ちることと、各検査が check に組み込まれていることを証明する | 4、7 |
| `guard.py` | 抑止コメント（lint 無効化、型無視など）の混入を、パターンごとのルールID付きで検出する | 4〜（check に含める） |
| `hooks.py` | Claude Code の hooks 本体。status が ready のとき保護ファイル編集前に確認を求め、編集後に整形・lint を回す | 5〜 |
| `convergence.py` | 収束テストの準備・実行・計測・レビュー検出率の採点 | 6 |

スクリプトの出力（`enforcement-matrix.md`、`probe-results.json`、収束テストのレポート）は生成物である。手で編集せず、入力（rules.md、probes.json、課題）を直して再生成する。
