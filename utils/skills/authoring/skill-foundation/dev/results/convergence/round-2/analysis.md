# ラウンド 2 のエージェントの動きの指摘（AI の推定）

`convergence.py analysis-collect` が、同じ場所の analysis.json から作る。締め込み（convergence-test.md の5章）の材料である。指摘は AI の推定なので、#番号の操作を traces.json（カタログの「エージェントの動き」）で確かめてから、dev/convergence-report.md の「## 動きの指摘」の表に、分類（V1〜V8。記録と合わなければ推定違い）と対処を書く。基準を満たした課題の指摘も分類する。

## 流れの評価

| エージェント | 流れの評価 | 操作 | 要る | 寄り道 | 無駄 | 誤り |
|---|---|---|---|---|---|---|
| T1-typical/subagent-1 | 寄り道・無駄あり | 79 | 50 | 29 | 0 | 0 |
| T1-typical/subagent-2 | 寄り道・無駄あり | 81 | 47 | 34 | 0 | 0 |
| T2-default/subagent-1 | 寄り道・無駄あり | 65 | 44 | 21 | 0 | 0 |
| T2-default/subagent-2 | 寄り道・無駄あり | 86 | 52 | 33 | 1 | 0 |
| T3-edge/subagent-1 | 寄り道・無駄あり | 76 | 52 | 23 | 1 | 0 |
| T3-edge/subagent-2 | 寄り道・無駄あり | 75 | 46 | 28 | 1 | 0 |

## 手順ごとの指摘

指摘の最初の「#番号」の操作がいた手順（番号が無ければ、文に出る「手順 N」）でまとめ、指摘したエージェントが多い手順から並べる。操作の当てはまりは、その手順にいた操作を全エージェント分数えたもの。

### 手順 7: フェーズ4（縛る）（指摘したエージェント 6 人。操作の当てはまり: 要る 42、寄り道 16、無駄 1）

問題だった点:

- T1-typical/subagent-1: #62 手順 7 の --phase 4 の lint が probes.json の違反例と baseline を求めてエラー 15 件になり、#63 #64 で手順 8 の probes.json を先に書いた。手順が 7→8→7→8 と戻った
- T1-typical/subagent-1: #56 #57 プロジェクト内の .skill-runs/skill-foundation/lab-test に一時の git リポジトリを作り、固有のスクリプトを手で試した。手順に無く、#57 では一時ファイルの書き込み先を誤るコマンドもあった
- T1-typical/subagent-2: #59 フェーズ4の lint が probes.json の違反例と baseline の見本を求めて 16 件のエラーになり、#60 で手順 8 の probes.json を手順 7 の中で先に書いた。手順の順番と検査の範囲がずれている
- T2-default/subagent-1: #49 手順7の skill_lint.py --phase 4 が、手順8で書くはずの dev/probes.json の違反例と baseline を求めて20件のエラーを出した。#50〜#53 で手順8の作業を前倒しした
- T2-default/subagent-2: #57 --phase 4 の lint が、手順8で書くはずの違反例が probes.json に無いことを21件のエラーにし、違反例をフェーズ4の中で書くことになった（#63）
- T2-default/subagent-2: #61 長すぎる項目の違反例の文が91字で100字に届かず assert で止まり、#62〜#63 で書き直した
- T3-edge/subagent-1: #57 手順7（フェーズ4）の lint が、手順8（フェーズ5）で書く dev/probes.json の違反例が無いことを10件のエラーにした。違反例を先に書くことになり、手順7と8を行き来した
- T3-edge/subagent-1: #52〜#53 違反例が止まるかを probe.py の前に手で試しており、#62 の probe.py と同じことを2度確かめた
- T3-edge/subagent-2: #48 で対象を . にすると dev/fixtures や skill-foundation の雛形の TODO まで一覧に入ると分かったが、除外せず notes に書くだけにした（#72）
- T3-edge/subagent-2: #47 で dev/fixtures/basic に .gitignore を置き、ホストのリポジトリで commit すると src/generated/schema.py が git に入らない問題を残した（#72 の notes）

直し方の案:

- T1-typical/subagent-1: scripts/skill_lint.py の --phase 4 で行う probes.json（違反例の有無と baseline の from）の検査を --phase 5 に移すか、SKILL.md 手順 7 に probes.json も書くと明記し、手順の行き来を無くす
- T1-typical/subagent-2: skill_lint.py の --phase 4 から probes.json の違反例と baseline の検査を --phase 5 に移すか、SKILL.md の手順 7 に「decisions の probes に挙げた ID の違反例と baseline もここで書く」と書く
- T2-default/subagent-1: skill_lint.py の --phase 4 から dev/probes.json の検査（probe の有無、baseline の from）を --phase 5 へ移す。移さないなら SKILL.md の手順7に「probes.json もここで書く」と書く
- T2-default/subagent-2: skill_lint.py の違反例の有無の検査を --phase 5 に移すか、SKILL.md の手順7に「違反例の ID と骨組みも probes.json に書く」と書く（#57）
- T3-edge/subagent-1: SKILL.md の手順7に「phase 4 の lint は決定の probes の ID が dev/probes.json にあるかを確かめるので、先に違反例を書く」と書くか、skill_lint.py のこの検査を phase 5 に移す

### 手順 3: フェーズ0（受付）（指摘したエージェント 3 人。操作の当てはまり: 要る 28、寄り道 13）

問題だった点:

- T1-typical/subagent-2: #13・#36〜#40・#50〜#52 で skill-foundation と作ったスキルのスクリプトの中身を 9 回読んだ。spec の書き方を references から引けなかったためとみられ、#35 から #47 まで約 450 秒かかった
- T2-default/subagent-1: #13・#30〜#34・#41〜#42 で init_skill.py、_skillrt.py、skill_lint.py、probe.py の中身を読み、#29〜#43 の間に約7分かかった。references だけでは検査や報告の節の書き方が分からなかったとみられる
- T2-default/subagent-1: #12 で見本 write-commit-message を読み、STEP-02 の境目（5件と6件の間）を調べずに写した。#64 の補足で本人も「調査で決めた数ではない」と書いている
- T3-edge/subagent-2: #10 で triggers に FIXME や TODO.md を作る例文を入れ、#41 で決定 IN-01（TODO だけを集め、リポジトリにファイルを作らない）と食い違うため書き直した

### 手順 5: フェーズ2（調査）（指摘したエージェント 3 人。操作の当てはまり: 要る 65、寄り道 5）

問題だった点:

- T1-typical/subagent-1: #27 #28 同じ Pro Git のページを2回 WebFetch した。1回で要点と見本の原文の両方を求めれば済んだ
- T1-typical/subagent-2: #32 で #31 と同じページを取り直し、#41・#42 で調べた CI スキップの記法は最終の返答に現れない。決定に使ったかは記録からは分からない
- T2-default/subagent-1: #24 で #21 と同じ keepachangelog.com/en/1.1.0/ を取り直した。別の部分を抜き出すためとみられ、1回の問いにまとめられた

### 手順 8: フェーズ5（証明する）（指摘したエージェント 3 人。操作の当てはまり: 要る 33、寄り道 33）

問題だった点:

- T2-default/subagent-1: #54 で zsh では空になる ${PIPESTATUS[0]} を使い、probe.py の終了コードが出ていない（exit= が空）。出力の「失敗 0 件」で成否を判断した
- T2-default/subagent-2: #39〜#43 フィクスチャ、固有スクリプト changelog_entry.py、見本を、調査の記録（#44）と決定（#49〜#51）より先に作り、手順5→6→7の順が前後した
- T2-default/subagent-2: #34〜#38、#72〜#74 skill-foundation のスクリプト（_skillrt.py、probe.py、convergence.py、skill_lint.py、_lib.py）のソースを読み、references に無い検査の種類や setup の扱いを調べた
- T3-edge/subagent-2: #31〜#38 と #53・#54 で skill-foundation の _skillrt.py・probe.py・skill_lint.py の中身を読み、command 検査の置き換えや実行場所、validate の判定を調べた。references だけでは足りなかったとみられる

直し方の案:

- T2-default/subagent-2: SKILL.md の手順5〜7に「固有スクリプト・見本・フィクスチャは、手順6の --phase 3 の lint が通ってから作る」と書く（#39〜#43）
- T2-default/subagent-2: references/control-ladder.md の出力の章（3〜5章）に、契約で使える検査の種類と command 検査の置換子（{file}、{root}、{in:キー}）の一覧を書く（#34〜#38）

### 手順 6: フェーズ3（決める）（指摘したエージェント 2 人。操作の当てはまり: 要る 45、寄り道 47）

問題だった点:

- T1-typical/subagent-1: #35 #36 #39〜#44 #48 spec の書き方（rules、impact、basis の値、fixture の扱い）を知るため、skill-foundation のスクリプト本体を9回読んだ。references だけでは書き方が決まらなかったと見られる
- T3-edge/subagent-1: #33〜#39 契約の置き換え（{in:キー}）、検査の種類、違反例の書き方を知るため、skill-foundation の _skillrt.py・probe.py・skill_lint.py を約250秒読んだ。references だけでは足りなかったとみられる
- T3-edge/subagent-1: #47 入力 source の impact を、skill-profiles.md の analyze の目安 target ではなく reversible にした。notes.md に理由はあるが、目安から外れた判断はエージェントごとに揺れうる

直し方の案:

- T1-typical/subagent-1: scripts/skill_lint.py の「ほか」の警告を、列挙の後に付く「ほか」だけに絞る。#49 では「〜のほかに」に警告が出て、#50 で書き直しが要った
- T1-typical/subagent-2: control-ladder.md（または spec.example.json の注記）に、checks・format の type ごとのキーと report.sections・inputs の書き方を表で載せ、SKILL.md の手順 6・7 からその章を名指しする
- T3-edge/subagent-2: SKILL.md の手順6の終わりに、決定を書いた後で triggers の use_when が対象外にした依頼（ほかの印、ファイルへの書き出し）を含まないかを見直す、と書く

### 手順 9: フェーズ6（測る）（指摘したエージェント 2 人。操作の当てはまり: 要る 22、寄り道 5）

問題だった点:

- T1-typical/subagent-2: #70〜#73 で収束テストを省くのに evals.json と convergence-report.md を書いたが、手順 9 にある convergence.py prepare は実行していない。STEP-02 の中身が記録に無く、省いてよかったかは分からない
- T2-default/subagent-2: #75〜#77 dev/fixtures に置いた basic.patch を外へ移し、probes の setup を差分の埋め込みに書き換えて probe.py を流し直す手戻りがあった

直し方の案:

- T1-typical/subagent-1: SKILL.md 手順 9 に、measure が skip のときにすること（spec の skip_reason、evals.json と convergence-report.md を書くかどうか）を直接書き、--final は手順 10 で流すと添える
- T1-typical/subagent-2: SKILL.md の手順 9 に、measure=skip のときに書くもの（evals.json、convergence-report.md、spec の convergence.skip_reason）と、convergence.py prepare を実行するかを書く
- T2-default/subagent-2: references/convergence-test.md の1章に、課題の setup で dev/ の下のファイル（差分など）を使えるかと、使えないときに差分を setup に埋める見本を書く（#72〜#76）

### 手順 1: 依頼が references/intake.md の6章の対象外に当たるかを確か（指摘したエージェント 1 人。操作の当てはまり: 要る 6、寄り道 7）

問題だった点:

- T1-typical/subagent-2: #5 の grep は zsh のグロブで失敗して #6 でやり直し、#64 は zsh に無い PIPESTATUS で probe.py の終了コードを取れず、#65 で結果の JSON を読んで補った

### 手順 10: フェーズ7（仕上げ）（指摘したエージェント 1 人。操作の当てはまり: 要る 10、寄り道 5）

問題だった点:

- T1-typical/subagent-1: #71 手順 10 で status を ready にする前に --final の lint を流し、予想できるエラー（status と hooks の未登録）を出した

### 手順 12: 決めきれなかったことがあれば .skill-runs/skill-foundat（指摘したエージェント 1 人。操作の当てはまり: 要る 13、寄り道 4、無駄 2）

問題だった点:

- T3-edge/subagent-2: #72 の notes に書いたとおり、入力 source の impact を skill-profiles の目安（target＝聞く）ではなく reversible（既定値 .）にした。種類の目安から外れ、ほかのエージェントと揺れる元になる

### 手順の外（手順を始める前か、手順を特定できない）（指摘したエージェント 0 人。操作の当てはまり: 要る 7、寄り道 13）

直し方の案:

- T1-typical/subagent-1: references/control-ladder.md か assets/templates/spec.example.json に、spec の欄（checks の rules、inputs の case・impact、decisions の basis）の取りうる値と例を載せ、スクリプトを読まずに書けるようにする
- T1-typical/subagent-1: references/control-ladder.md の7章に、git の状態を前提にする probe の fixture と setup の書き方の例（fixture が git のリポジトリとしてどう用意されるか）を書く
- T1-typical/subagent-2: references/research.md の 2 章に、調べるのは決定・検査・スクリプトが使う事実に限り、「使った決定」を付けられない調べものはしないと書く
- T2-default/subagent-1: references/runtime.md に、契約の command 検査と report.sections（run、stage、timeout、{in:…} の置き換え）の書き方を例付きで書き、スクリプトの中身を読まずに済むようにする
- T2-default/subagent-1: references/convergence-test.md の1章に、課題の fixture は git init と base のコミットだけがされ user.name などの設定が無いので、setup の git commit には -c を付けると書く
- T2-default/subagent-1: references/variance-axes.md の2章に、assets/example の見本の数値（STEP-02 の境目など）を写すときは、basis と dev/research.md に写した理由を書くと足す
- T3-edge/subagent-1: control-ladder.md の3〜5章に、契約のパスとコマンドで使える置き換え（{run}・{in:キー}・{file} など）と検査の種類の一覧を例付きで書き、スクリプトを読まずに済むようにする
- T3-edge/subagent-1: control-ladder.md の7章に、probes.json の files の mode（sub・delete など）と、置き換えが0件なら失敗することを書く
- T3-edge/subagent-1: skill-profiles.md の analyze の「入力の候補」で、範囲の入力の impact を固定するか、目安から外してよい条件を書く
- T3-edge/subagent-2: control-ladder.md の出力の検査の章に、command 検査の実行場所（cwd）、shell での実行、{in:キー} の置き換え、probe の一時プロジェクトが git init 済みかを書き、validate のエラー文で checks の rules を案内する
- T3-edge/subagent-2: skill-profiles.md の analyze の節の「入力の候補」で source の impact を固定し、目安と違う impact を選んだら skill_lint.py --phase 3 が警告する
- T3-edge/subagent-2: skill-profiles.md の analyze の節に、対象をプロジェクト全体にできるときは、スキルの置き場（.agents/skills、.claude/skills）を除くかを決定に書く、と足す
- T3-edge/subagent-2: convergence-test.md の1章に、fixture の .gitignore は evals.json の setup で作ると書き、skill_lint.py が dev/fixtures の下の .gitignore を警告する

## 前のラウンドの動きの指摘（dev/convergence-report.md のラウンド 1）

前のラウンドで締め込んだ指摘が上に再び出ていれば、その締め込みは効いていない。締め込み方を変える。

| エージェントと操作 | 指摘 | 分類 | 対処 |
|---|---|---|---|
| T1-typical/subagent-1 #64、T1-typical/subagent-2 #52、T2-default/subagent-1 #55、T2-default/subagent-2 #47、T3-edge/subagent-2 #61 | 手順7の lint --phase 4 が、手順8で書く probes.json の違反例と baseline を求めてエラーになり、手順8を先にして手順7と8を行き来した | V2 | 未対処（分析はラウンドの後に作った）。案: skill_lint.py --phase 4 の probes.json の検査（違反例と baseline の from）を --phase 5 に移すか、手順7に違反例の ID を先に書くと足す |
| T1-typical/subagent-1 #32・#57・#59、T1-typical/subagent-2 #23・#34・#36、T2-default/subagent-1 #31〜#33・#38、T2-default/subagent-2 #26・#27・#30 | 手順5の research.md の「使った決定」が手順6の決定 ID を求めるため、TODO で残して phase 3 の lint で埋めるか、手順6の資料を先に読んだ | V2 | 未対処（分析はラウンドの後に作った）。案: SKILL.md の手順6に、決定を書いた後、phase 3 の lint の前に research.md の「使った決定」を埋めると書き、手順5では空けてよいと雛形に書く |
| T1-typical/subagent-2 #28・#29・#32・#40〜#42・#60、T2-default/subagent-2 #48、T3-edge/subagent-1 #30〜#37、T3-edge/subagent-2 #32・#33・#35・#36・#44〜#46・#51・#65 | checks の項目と置き換え、probe の setup の動きが references に無く、スクリプトを読んだ（知らずに setup の commit が失敗した例も） | V1 | 未対処（分析はラウンドの後に作った）。案: control-ladder.md の3〜5章と7章に、checks の型と項目、置き換え（{skill}・{file}・{in:キー}）、probe の一時プロジェクトがコミット済みであることを書く |
| T2-default/subagent-1 #63・#64、T3-edge/subagent-1 #41・#42・#62、T3-edge/subagent-2 #53〜#56・#81・#82 | 固有のスクリプトを手で試す場所の決まりが無く、スキルの dev/ や .skill-runs に試しのプロジェクトを作った。外に一時ディレクトリを残した例も | V1 | 未対処（分析はラウンドの後に作った）。案: control-ladder.md の5章に、固有のスクリプトは違反例と probe.py で試すと書き、probe.py --keep-temp の help に使い終えたら消すと書く |
| T1-typical/subagent-1 #41・#43 | 試しの git 操作が作業中のプロジェクトのリポジトリを使い、git add -A と commit でコミットを作って、#43 の git reset で戻した | V3 | 未対処（分析はラウンドの後に作った。ばらつきの表 #14 も未対処）。案: run.py start で HEAD を記録し、check と finish で HEAD が変わっていれば CTL-05 の指摘にする |
| T2-default/subagent-1 #68〜#71、T2-default/subagent-2 #66〜#70 | 手順9の文面（prepare を先に実行）と STEP-02 の skip が食い違い、省く人と、evals.json を作り setup まで試す人に分かれた | V2 | 未対処（分析はラウンドの後に作った）。案: 手順9に measure=skip の場合分け（prepare 以降を実行しない、evals.json・skip_reason・convergence-report.md に書くもの）を書く |
| T3-edge/subagent-1 #63〜#67、T3-edge/subagent-2 #75〜#78 | targets が codex なのに、手順10の install.py --project . が Claude Code 側の置き場と hooks も作り、手で外した | V7 | ラウンド1の締め込みで、契約に targets を入れ、install.py の --targets の既定を契約の targets にした（ばらつきの表 #2）。ラウンド2・3では起きていない |
| T2-default/subagent-2 #58・#59・#61・#62・#72・#73 | 違反例を通した後にスクリプトと spec を変えたが、phase 5 の lint は probe の結果の古さを指摘せず、--final で初めて分かった | V3 | 未対処（分析はラウンドの後に作った）。案: skill_lint.py の --phase 5 でも、--final と同じく probe-results.json が spec・契約・スクリプトを変えた後の結果かを確かめる |
| T3-edge/subagent-1 #38〜#45 | 固有のスクリプト・fixture・見本を、調査の記録（#46）と決定（#50）より先に作った。番号の順に行う決まりはあるが、止める仕組みが無い | V3 | 未対処（分析はラウンドの後に作った）。案: SKILL.md の手順5に「スクリプト・見本・fixture は手順7で作る」と書き、skill_lint.py --phase 3 が固有のスクリプトや見本が既にあれば警告する |
| T3-edge/subagent-1 #69 | not_for の instead を動詞句（「その修正を直接行う」）で書き、説明文の「代わりに〜を使う」に合わず、check の後に直してやり直した | V2 | 未対処（分析はラウンドの後に作った）。案: intake.md 5章に「instead は『を使う』に続く名詞句で書く」と足し、skill_lint.py --phase 1 が「する」「行う」で終わる instead をエラーにする |
| T3-edge/subagent-2 #83 | 名前の動詞を analyze にしたが write や convert とも読めると迷い、同じ課題の subagent-1 は convert を選んで名前が揃わなかった | V2 | ラウンド1の締め込みで、intake.md 2章の動詞の表を出力の中身の作り方で選ぶ定義にし、例を足した（ばらつきの表 #1）。ラウンド2・3の T3 は2人とも analyze |
| T1-typical/subagent-2 #36・#71 | 区切りと日本語の説明を利用者のグローバルの指示に合わせたと補足に書いたが、research.md の「プロジェクトの決まり」は「使った決定：なし」で、根拠が記録に無い | V7 | 未対処（分析はラウンドの後に作った。ばらつきの表 #13 と同じく、subagent が呼び出し元の設定を引き継ぐ限界）。案: research.md の3章に、プロジェクトの外の指示に合わせたときの書き方と basis を書く |
| T1-typical/subagent-1 #2〜#4・#21・#22 | 複数のファイルを1つのコマンドで読んで出力が切れたり、zsh が「=====」を展開して失敗したりして、読み直した | V8 | 締め込まない。エージェントのシェルの使い方の誤りで、出力に影響しない |
| T1-typical/subagent-2 #47・#49 | #47 で書いた正規表現の文字の範囲を、意味を変えずにエスケープの書き方へ直した | V8 | 締め込まない。同じ意味の書き直しで、出力に影響しない |
| T2-default/subagent-1 #9・#15 | #9 で表示した spec.example.json と同じ中身を、写した後の spec.json で読み直した | V8 | 締め込まない。読み直しの1操作で、出力に影響しない |
