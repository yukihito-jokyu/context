# ラウンド 1 のエージェントの動きの指摘（AI の推定）

`convergence.py analysis-collect` が、同じ場所の analysis.json から作る。締め込み（convergence-test.md の5章）の材料である。指摘は AI の推定なので、#番号の操作を traces.json（カタログの「エージェントの動き」）で確かめてから、dev/convergence-report.md の「## 動きの指摘」の表に、分類（V1〜V8。記録と合わなければ推定違い）と対処を書く。基準を満たした課題の指摘も分類する。

## 流れの評価

| エージェント | 流れの評価 | 操作 | 要る | 寄り道 | 無駄 | 誤り |
|---|---|---|---|---|---|---|
| T1-typical/subagent-1 | 寄り道・無駄あり | 92 | 64 | 26 | 1 | 1 |
| T1-typical/subagent-2 | 寄り道・無駄あり | 73 | 43 | 29 | 1 | 0 |
| T2-default/subagent-1 | 寄り道・無駄あり | 80 | 51 | 27 | 2 | 0 |
| T2-default/subagent-2 | 寄り道・無駄あり | 84 | 50 | 34 | 0 | 0 |
| T3-edge/subagent-1 | 寄り道・無駄あり | 72 | 47 | 24 | 1 | 0 |
| T3-edge/subagent-2 | 寄り道・無駄あり | 86 | 59 | 27 | 0 | 0 |

## 手順ごとの指摘

指摘の最初の「#番号」の操作がいた手順（番号が無ければ、文に出る「手順 N」）でまとめ、指摘したエージェントが多い手順から並べる。操作の当てはまりは、その手順にいた操作を全エージェント分数えたもの。

### 手順 7: フェーズ4（縛る）（指摘したエージェント 5 人。操作の当てはまり: 要る 47、寄り道 12）

問題だった点:

- T1-typical/subagent-1: #64 手順7の lint --phase 4 が、手順8で書く probes.json の違反例と baseline を求めたため、手順7→8→7 の往復になった（subagent-2 も同じ往復をしている）
- T1-typical/subagent-2: #52 phase 4 の lint が17件失敗した。主に決定に挙げた probe が probes.json に無いためで、手順 8 の作業（#53 の probes.json）を手順 7 の中で先にした
- T2-default/subagent-1: #55 phase 4 の lint が、手順 8 で書く probes.json の違反例と baseline を求めてエラー 18 件になり、#56 で手順 8 の作業を先に行った。手順 7 と 8 を行き来した
- T2-default/subagent-2: #47 で lint の phase 4 が、手順8で書く違反例（probes.json）が無いことをエラーにしたため、#48〜#55 で手順8の作業を先に行い、手順7と8が入り混じった
- T3-edge/subagent-2: #61 手順7の lint --phase 4 が dev/probes.json の違反例の無さをエラーにしたため、手順8で書くはずの probes.json を #64 で先に書いた
- T3-edge/subagent-2: #53〜#56、#81 で、スキルのディレクトリの中に dev/lab と dev/e2e の試しのプロジェクトを作って消した。保護ファイルの指紋への影響を #82 で確かめる手間も生じた

直し方の案:

- T1-typical/subagent-1: SKILL.md の手順7に「lint --phase 4 の前に dev/probes.json の baseline と違反例のIDを書く」と書くか、skill_lint.py の probes の検査を --phase 5 に移す
- T1-typical/subagent-2: SKILL.md の手順 7 に、決定の probes に挙げた ID は phase 4 の lint で probes.json に要ると書く。または skill_lint.py のこの検査を --phase 5 に移す
- T2-default/subagent-1: SKILL.md の手順 7 に「phase 4 の lint は dev/probes.json の違反例と baseline の from も確かめる」と書くか、skill_lint.py の違反例の有無の検査を --phase 5 に移す
- T2-default/subagent-2: skill_lint.py の --phase 4 から違反例の有無の検査を外して --phase 5 に移すか、SKILL.md の手順7に「decisions の probes に挙げた違反例は phase 4 の lint でも確かめる」と書く
- T3-edge/subagent-2: 手順7（フェーズ4）に dev/probes.json の違反例も書くと明記するか、skill_lint.py --phase 4 から probe の有無の検査を外して --phase 5 に回す

### 手順 8: フェーズ5（証明する）（指摘したエージェント 5 人。操作の当てはまり: 要る 65、寄り道 38、無駄 3、誤り 1）

問題だった点:

- T1-typical/subagent-1: #41 プロジェクト内の .skill-runs/skill-foundation/tmp で「リポジトリの中でなければ init」としたため外側のリポジトリを使い、git add -A と commit で利用者のリポジトリにコミットを作った。#43 の git reset で戻した
- T1-typical/subagent-2: #49 は #47 で書いた正規表現の文字の範囲を、意味を変えずにエスケープの書き方に直しただけで、最初からそう書けば要らなかった
- T2-default/subagent-1: #63 probe.py を --keep-temp で流したが、残した一時プロジェクトを見ないまま #64 で別の確かめ方に移り、作業ディレクトリの外に一時ディレクトリを残した
- T2-default/subagent-2: #58・#59 で違反例を通した後にスクリプトを直し、#61 で spec も変えたが、#62 の lint の phase 5 は結果の古さを指摘せずに通った。#72 の --final で初めて分かり、#73 で流し直した
- T2-default/subagent-2: #48 で baseline の準備に git add と commit を書いたが、probe.py が fixture を先にコミットしているため失敗した。この前提を文書から読み取れなかったと推定
- T3-edge/subagent-1: #38〜#45 で collect_todo.py・フィクスチャ・見本を、調査の記録（#46）と決定（#50）より先に作った。手順は番号順と定めており、フェーズ2・3 を後から合わせる形になった
- T3-edge/subagent-1: #30〜#37 で約4分、_skillrt.py・render_skill.py・skill_lint.py の中身を読んだ。{in:キー}、path 型、出力の件数の数え方など、references で分からない仕様を確かめるためと推定
- T3-edge/subagent-1: #41 でプロジェクトの中のフィクスチャに collect_todo.py を当てると0件になり、#42・#62 で .skill-runs/skill-foundation/work に写して git init する回り道をした。0件の理由は記録からは分からない

### 手順 6: フェーズ3（決める）（指摘したエージェント 4 人。操作の当てはまり: 要る 38、寄り道 27）

問題だった点:

- T1-typical/subagent-2: #34 phase 3 の lint が4件失敗した。#23 で research.md の「使った決定」を TODO のまま残し、決定を書いた後に埋める手順が無いため、#36 で埋め直した
- T1-typical/subagent-2: #28・#29・#32・#40〜#42・#60 で skill-foundation のスクリプトの中身を読んだ。checks の任意の項目、probe の setup、収束テストを省くときの要件が references から読み取れなかったとみられる
- T2-default/subagent-1: #31〜#33 で手順 6 の参照を読んだ後に、#38 で手順 5 の research.md を書いた。手順 5 を終えてから手順 6 に進む順と少しずれる（結果への害は見えない）
- T2-default/subagent-2: #30 で research.md を、手順6の variance-axes.md などを読んだ後に書いた。調査の項目に「使った決定」の ID を書く欄があり、決定より先には書けないためと推定
- T3-edge/subagent-2: #32、#33、#35、#36、#44〜#46、#51、#65 で、ランタイム、probe.py、skill_lint.py のソースを読んだ。入力の読み方や probe の動きが references に足りないためと推定

直し方の案:

- T1-typical/subagent-1: SKILL.md の手順6に「basis が official の決定を書いたら、dev/research.md の該当の項目の「使った決定」にそのIDを書く」と書く
- T1-typical/subagent-2: SKILL.md の手順 6 に、決定を書いた後、phase 3 の lint の前に dev/research.md の「使った決定」の TODO を決定IDで埋めると書く

### 手順 9: フェーズ6（測る）（指摘したエージェント 2 人。操作の当てはまり: 要る 16、寄り道 13）

問題だった点:

- T2-default/subagent-1: 手順 9（#68〜#71）で convergence.py prepare を実行していない。手順の文面は prepare の後に STEP-02 で run を決める順で、subagent-2 は実行した。measure=skip のとき省いてよいかは記録からは分からない
- T2-default/subagent-2: #66〜#70 で measure=skip なのに convergence.py の help を読み、fixture と evals.json を作って準備のコマンドまで試した。skip のときに evals.json が要るかを手順から読み取れない

直し方の案:

- T1-typical/subagent-2: SKILL.md の手順 9 に、measure=skip のときに書くもの（evals.json、convergence.skip_reason、convergence-report.md）と、prepare 以降を実行しないことを書く
- T2-default/subagent-1: SKILL.md の手順 9 に、measure=skip のときに convergence.py prepare を実行するかと、しないなら convergence-report.md に何を書くかを明記する
- T2-default/subagent-2: SKILL.md の手順9と convergence-test.md の2章に、measure=skip のときに evals.json を書くかどうかを場合分けで明記する

### 手順 10: フェーズ7（仕上げ）（指摘したエージェント 2 人。操作の当てはまり: 要る 13、寄り道 14）

問題だった点:

- T3-edge/subagent-1: #63 で手順10どおり install.py --project . を実行すると、targets が codex なのに Claude Code 側のリンクと hooks も入り、#64〜#67 で調べて外す手戻りになった
- T3-edge/subagent-1: #69 で run.py check（#68）の後に not_for の instead を書き直し、render と probe と lint をやり直した。description の「代わりに<instead>を使う」に動詞句が入っていたためと推定
- T3-edge/subagent-2: #75 手順10の `install.py --project .` が既定の targets（claude,codex）で .claude にも置き、#76〜#78 で外す後始末が要った。lint --final はこの余分な置き場を指摘しなかった

直し方の案:

- T3-edge/subagent-1: SKILL.md の手順10 に install.py へ --targets <spec の targets> を渡すと書くか、install.py が既定で contract.json の targets を読むようにする

### 手順 3: フェーズ0（受付）（指摘したエージェント 1 人。操作の当てはまり: 要る 26、寄り道 19、無駄 1）

問題だった点:

- T2-default/subagent-1: #15 #9 で表示した spec.example.json と同じ中身を読み直した

### 手順 5: フェーズ2（調査）（指摘したエージェント 1 人。操作の当てはまり: 要る 58、寄り道 5）

問題だった点:

- T1-typical/subagent-1: #32・#57 research.md の「使った決定」を TODO のまま残し、#38 で取った出典も書き足さず、lint --phase 3 のエラーを受けて #59 で初めて埋めた

直し方の案:

- T1-typical/subagent-1: SKILL.md の手順5と references/research.md に「git を試す一時リポジトリはプロジェクトの外（mktemp -d）に作り、git init の後に rev-parse --show-toplevel で切り離しを確かめる」と書く
- T2-default/subagent-2: research.md の雛形と SKILL.md の手順5に、「使った決定」は手順6で決定を書いた後に埋めてよいと書く（または手順6の終わりに research.md を見直す一文を足す）

### 手順 11: run.py check を実行する（指摘したエージェント 1 人。操作の当てはまり: 要る 9）

問題だった点:

- T3-edge/subagent-2: #83 の notes で、名前の動詞を analyze にしたが write や convert とも読めると迷いを書いている。同じ課題の subagent-1 は convert を選び、名前が揃わなかった

### 手順 12: 決めきれなかったことがあれば .skill-runs/skill-foundat（指摘したエージェント 1 人。操作の当てはまり: 要る 13、寄り道 7）

問題だった点:

- T1-typical/subagent-2: #71 の補足で区切りと日本語の説明を利用者のグローバルの指示に合わせたと書いたが、research.md の「プロジェクトの決まり」は「使った決定：なし」（#36）で、この根拠は調査の記録に無い

### 手順の外（手順を始める前か、手順を特定できない）（指摘したエージェント 1 人。操作の当てはまり: 要る 10、寄り道 12、無駄 1）

問題だった点:

- T1-typical/subagent-1: #2・#21 複数のファイルを1つのコマンドで読んで出力が切れたり、zsh が「=====」を展開して失敗したりして、#3・#4・#22 で読み直した

直し方の案:

- T1-typical/subagent-1: scripts/run.py の start で HEAD を記録し、check と finish で HEAD が変わっていれば CTL-05 の指摘にする。作業ツリーだけで判定すると、コミットした変更を見逃す
- T1-typical/subagent-2: control-ladder.md の3〜5章に、checks の任意の項目（lines、name_pattern、{in:キー}）と probe の fixture・setup の動きを表で書き、スクリプトを読まずに済むようにする
- T1-typical/subagent-2: references/research.md の3章に、プロジェクトの外にある利用者の指示（グローバルの CLAUDE.md など）に合わせるときの書き方と basis の選び方を書く
- T2-default/subagent-1: skill-profiles.md の write の節の「入力の候補」か軸の読み替えに、出力を対象のファイル（CHANGELOG.md など）へ直接書くか、別のファイルに出すかを入れ、作り手ごとの設計の違いを減らす
- T2-default/subagent-1: probe.py の --keep-temp の help に、残した一時ディレクトリの場所と、使い終えたら消すことを書く
- T2-default/subagent-2: skill_lint.py の --phase 5 でも --final と同じく、probe-results.json が spec・契約・スクリプトを変えた後の結果かを確かめる
- T2-default/subagent-2: control-ladder.md の7章と probe.py の --help に、baseline.setup の前に fixture はコミット済みであり、setup で commit しないことを書く
- T3-edge/subagent-1: references/intake.md の triggers の説明に「not_for の instead は『〜を使う』に続く名詞句で書く」と書き、skill_lint.py --phase 1 で「する」「行う」で終わる instead をエラーにする
- T3-edge/subagent-1: references/control-ladder.md の3〜5章に、契約のパスの {in:キー}、path 型の入力、前回と同じ中身の出力は件数に数えないことを書き、ランタイムのコードを読まずに済むようにする
- T3-edge/subagent-1: SKILL.md の手順の冒頭に「スクリプトと見本はフェーズ4で作る。フェーズ2で試すなら dev/ の下で試す」と書き、決定より先に作るのを防ぐ
- T3-edge/subagent-1: probe.py に、フィクスチャを一時ディレクトリに写して git init し、スキル固有のスクリプトを試す使い方を足し、control-ladder.md の7章に書く
- T3-edge/subagent-2: scripts/install.py（共通ランタイム）の --targets の既定を契約の targets にし、skill_lint.py --final で targets に無い製品の置き場と hooks をエラーにする
- T3-edge/subagent-2: control-ladder.md の5章に、スキル固有のスクリプトが _skillrt.py で入力（state.json）とプロジェクトのルートを読む関数と、書き方の見本を載せる
- T3-edge/subagent-2: control-ladder.md の5章に、スクリプトを試すときは probe.py --keep-temp の一時プロジェクトを使い、スキルのディレクトリの中に試しのプロジェクトを作らないと書く
- T3-edge/subagent-2: intake.md の2章の動詞の表に、「集めて一覧の文書にする」（TODO、課題、依存の一覧など）が analyze か convert かを決める行を足す

## 前のラウンドの動きの指摘（dev/convergence-report.md のラウンド 0）

前のラウンドで締め込んだ指摘が上に再び出ていれば、その締め込みは効いていない。締め込み方を変える。

（表に前のラウンドの行が無い）
