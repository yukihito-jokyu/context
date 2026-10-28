# ラウンド 3 のエージェントの動きの指摘（AI の推定）

`convergence.py analysis-collect` が、同じ場所の analysis.json から作る。締め込み（convergence-test.md の5章）の材料である。指摘は AI の推定なので、#番号の操作を traces.json（カタログの「エージェントの動き」）で確かめてから、dev/convergence-report.md の「## 動きの指摘」の表に、分類（V1〜V8。記録と合わなければ推定違い）と対処を書く。基準を満たした課題の指摘も分類する。

## 流れの評価

| エージェント | 流れの評価 | 操作 | 要る | 寄り道 | 無駄 | 誤り |
|---|---|---|---|---|---|---|
| H1-holdout/subagent-1 | 妥当 | 4 | 3 | 1 | 0 | 0 |
| H1-holdout/subagent-2 | 寄り道・無駄あり | 6 | 3 | 3 | 0 | 0 |
| T1-typical/subagent-1 | 寄り道・無駄あり | 60 | 40 | 18 | 2 | 0 |
| T1-typical/subagent-2 | 寄り道・無駄あり | 86 | 51 | 34 | 1 | 0 |
| T2-default/subagent-1 | 寄り道・無駄あり | 81 | 47 | 32 | 2 | 0 |
| T2-default/subagent-2 | 寄り道・無駄あり | 81 | 49 | 31 | 0 | 1 |
| T3-edge/subagent-1 | 寄り道・無駄あり | 67 | 40 | 27 | 0 | 0 |
| T3-edge/subagent-2 | 寄り道・無駄あり | 86 | 48 | 38 | 0 | 0 |

## 手順ごとの指摘

指摘の最初の「#番号」の操作がいた手順（番号が無ければ、文に出る「手順 N」）でまとめ、指摘したエージェントが多い手順から並べる。操作の当てはまりは、その手順にいた操作を全エージェント分数えたもの。

### 手順 7: フェーズ4（縛る）（指摘したエージェント 6 人。操作の当てはまり: 要る 37、寄り道 21、無駄 2）

問題だった点:

- T1-typical/subagent-1: #45 で phase 4 の lint が、違反例が dev/probes.json に無いとして 16 件のエラーを出し、手順 8 の違反例を先に書いて（#46）通した
- T1-typical/subagent-2: #62：phase 4 の lint でエラー 18 件。多くは手順8で書くはずの probes.json の違反例が無いためで、手順7の中で probes.json を書いた（#67）
- T2-default/subagent-1: #58 phase 4 の lint が、手順8で書くはずの dev/probes.json に違反例の ID が無いことを 18 件のエラーにした。手順7の中で probes.json を先に書いて（#60）通すしかなかった
- T2-default/subagent-1: #62 macOS に無い timeout コマンドを付けて probe.py を回し、実行されずにやり直した
- T2-default/subagent-2: #49 手順7の skill_lint.py --phase 4 が、手順8で書く dev/probes.json の違反例を18件のエラーとして求めた。そのため #53 で probes.json を先に書き、手順7と8を行き来した
- T3-edge/subagent-1: #50 の --phase 4 の lint が、手順8で書くはずの違反例と baseline の不足でエラーを 10 件出した。#51 で手順8の内容を手順7の中で前倒しして書いた
- T3-edge/subagent-2: #58 フェーズ4の lint が、手順8で書く違反例（probes.json）が無いことをエラーに含めたため、#63 で違反例を先に書くことになり、手順7と8を行き来した

直し方の案:

- T1-typical/subagent-1: SKILL.md の手順 7 に「phase 4 の lint は、決定の probes が dev/probes.json にあるかも確かめる」と書くか、skill_lint.py のその検査を phase 5 に移す
- T1-typical/subagent-2: skill_lint.py の --phase 4 が決定の probes の実在を求めるので、手順7の中で probes.json を書くことになる。この検査を --phase 5 に移すか、手順7に先に書くと明記する（#62）
- T2-default/subagent-1: skill_lint.py の phase 4 にある「決定の probes の ID が dev/probes.json にある」検査を phase 5 に移すか、SKILL.md の手順7に「先に probes.json に違反例の ID を書く」と書く
- T2-default/subagent-2: skill_lint.py の --phase 4 から probes.json の違反例の有無の検査を外して --phase 5 に回すか、SKILL.md の手順7に「phase 4 の lint は手順8の probes.json の違反例も求める」と書く
- T3-edge/subagent-1: scripts/skill_lint.py の --phase 4 から probes.json の検査（違反例の id と baseline の from）を外して --phase 5 に移すか、SKILL.md の手順7に「違反例の id を probes.json に先に書く」と足す
- T3-edge/subagent-1: references/control-ladder.md に、command の run で使える置き換え（{skill}、{file}、{root}、{in:キー}）と、baseline の fixture の写され方を例付きで書き、手順7からその章を指す
- T3-edge/subagent-2: skill_lint.py の --phase 4 では違反例（probes.json）の有無を問わず、--phase 5 で問うようにする。または SKILL.md の手順7に「違反例のエラーは手順8で消える」と書く

### 手順 6: フェーズ3（決める）（指摘したエージェント 5 人。操作の当てはまり: 要る 49、寄り道 38）

問題だった点:

- T1-typical/subagent-1: #18・#28〜#33 で手順 6〜8 の資料と probe.py を先に読み、手順 5 の調査の記録（#35）が遅れた。#19〜#21 も control-ladder.md（#28）より前に読んでいた
- T1-typical/subagent-2: #28〜#41：手順5の調査を書く（#42）前に、手順6・7の参照と skill-foundation のスクリプトの内部を読み進め、手順の順から外れた。結果には響いていない
- T2-default/subagent-1: #29〜#30、#39〜#44 報告の節（report.sections）や検査の型 command の書き方、追加の軸の扱いを、references ではなく skill_lint.py・_skillrt.py のコードから調べた。references に書かれていないためと推定
- T2-default/subagent-1: #25〜#27 dev/research.md を書く（#35）前に手順6の references を読み進め、手順5と6が入り混じった。結果への害は無い
- T3-edge/subagent-1: dev/research.md を書いた操作が記録に見えない。#38 のスクリプトの中身が残っておらず、手順5の記録がいつ書かれたかは記録からは分からない（#62 の --final は通っている）
- T3-edge/subagent-2: #43〜#47、#59〜#61 で共通ランタイムと skill_lint.py のソースを読み、契約の検査の型やエラーの条件を調べた。references だけでは分からなかったとみられる

### 手順 8: フェーズ5（証明する）（指摘したエージェント 5 人。操作の当てはまり: 要る 38、寄り道 35、無駄 2）

問題だった点:

- T1-typical/subagent-1: #36 で存在しない skill_lint.py --phase 2 を実行して引数エラーになった。#49 の後片付けは cd の後に相対パスで rm したため効かず、一時リポジトリが残ったとみられる
- T1-typical/subagent-2: #31〜#40、#46、#74：契約の書き方、probe の baseline、lint の要件を確かめるため、_skillrt.py・probe.py・skill_lint.py の本体を 10 回以上読んだ
- T1-typical/subagent-2: #70：zsh では ${PIPESTATUS[0]} が空になり、probe.py の終了コードを取れていない。出力の「失敗 0 件」で成否を判断した
- T1-typical/subagent-2: #71〜#72：OUT-07 の決定文の書き方が SKILL.md の中でリンクと読まれ、phase 5 の lint が1件失敗し、決定文を書き換えた
- T2-default/subagent-1: #65 自作スクリプトを試す一時の場所を rm -rf で消そうとして、権限の判定で止められた。#59・#66・#67 の手での試しは probe の外で行い、違反例には足していない
- T2-default/subagent-2: #32〜#34、#51〜#52、#62〜#63 で probe.py・_lib.py・convergence.py の本文を読み、baseline の setup・commands と課題の fixture・setup の動きを確かめた。references の説明だけでは決めきれなかったとみられる
- T3-edge/subagent-2: #74 git でない場所の試しを外側の git リポジトリの中で行い、終了コード0（期待は4）が出たのを追わずに、#83 の補足に「git でない場所では終了コード4で中断する」と書いた

直し方の案:

- T1-typical/subagent-2: skill_lint.py の「リンク先 先 がありません」に行番号とその行を添え、references/writing.md に、決定文で角かっこの直後に丸かっこを続けないと書く（#71）
- T2-default/subagent-1: SKILL.md の手順8に、probe.py はそのまま実行し、timeout コマンドを付けない（macOS には無い）と書く
- T3-edge/subagent-2: control-ladder.md の7章に、終了コード4で中断する決定（IN-01）は、表の行ごとにその状況を作る fixture でスクリプトの終了コードを確かめると書く（#74）

### 手順 1: 依頼が references/intake.md の6章の対象外に当たるかを確か（指摘したエージェント 2 人。操作の当てはまり: 要る 10、寄り道 8）

問題だった点:

- H1-holdout/subagent-2: #5 何も書いていないのに git status と ls -a で変更が無いことを確かめた。返答の「確認したこと」の根拠にはなったが、手順には無い
- T1-typical/subagent-1: #7・#14・#19〜#21・#29・#31〜#33・#41・#52 の11回、skill-foundation のスクリプトの中身を読み、入力の正規化や checks の lines、baseline の扱いを確かめた

直し方の案:

- H1-holdout/subagent-2: SKILL.md の手順1に「対象外かの判定は依頼文だけで行う。プロジェクトの中を見る前に intake.md の6章を読む」と書く

### 手順 3: フェーズ0（受付）（指摘したエージェント 2 人。操作の当てはまり: 要る 23、寄り道 13）

問題だった点:

- T2-default/subagent-2: #8 で run.py start（#10）より前に skill-profiles.md を読み、手順の並びが 1 → 3 → 2 になった。読むだけなので結果への影響は無い
- T3-edge/subagent-1: #12、#29〜#35、#40 で init_skill.py・_skillrt.py・skill_lint.py・probe.py のソースを読んだ（10 操作）。契約の検査の置き換えや probe の動きを、references だけでは掴めなかったと推測

直し方の案:

- T1-typical/subagent-2: SKILL.md の手順7に、同梱の assets/example/write-commit-message を参考に読んでよいかを書く。今は手順からの参照が無く、読むかどうかがエージェントで分かれた（#12）

### 手順 9: フェーズ6（測る）（指摘したエージェント 2 人。操作の当てはまり: 要る 35、寄り道 15、誤り 1）

問題だった点:

- T2-default/subagent-2: #67 measure: skip で収束テストを走らせないのに convergence.py prepare を --workdir なしで実行し、作業ディレクトリの外（/var/folders/…）に一時プロジェクトを作った。#69 で消そうとして権限で拒否され、残ったまま終えた
- T3-edge/subagent-1: 手順9の本文は prepare を実行してから run と diff を決める流れだが、#59 では prepare を実行せず、evals.json と skip_reason だけを書いた。measure=skip でこれが正しいかは記録からは分からない

直し方の案:

- T1-typical/subagent-2: SKILL.md の手順9に、measure=skip のときに書くもの（evals.json、convergence.skip_reason、convergence-report.md の扱い）を書く（#73〜#75）
- T2-default/subagent-2: SKILL.md の手順9に「measure が skip なら prepare・run・diff を実行せず、spec の convergence.skip_reason と convergence-report.md だけを書く」と書く
- T3-edge/subagent-1: SKILL.md の手順9に measure=skip の場合分けを書く。prepare を実行するか、evals.json・convergence.skip_reason・convergence-report.md に何を書くかを明記する

### 手順 11: run.py check を実行する（指摘したエージェント 2 人。操作の当てはまり: 要る 10、寄り道 8）

問題だった点:

- T3-edge/subagent-1: #13 で spec.json を書いた直後に run.py check を実行し、SKILL.md が無いという指摘が1件出た。check は手順11の操作で、ここでは要らない。#8 の start の出力の「書いたら check」に従ったと推測
- T3-edge/subagent-2: #81〜#82 status を ready にして final の lint が通った後に、STEP-01 の決定文の二重のバッククォートを目で見つけ、render・probe・lint をやり直した
- T3-edge/subagent-2: #16 骨組みを作る前に run.py check を実行し、SKILL.md が無いという分かりきった指摘1件を得た（手順11の操作の先取り）

直し方の案:

- T3-edge/subagent-2: skill_lint.py に、spec の決定文の中の二重のバッククォート（``）を警告する検査を足す（#81〜#82）
- T3-edge/subagent-2: run.py start が skill-foundation で出す「次:」の案内を、「書いたら check」から「check は手順11で実行する」に変える（#16。subagent-1 の #13 も同じ動き）

### 手順の外（手順を始める前か、手順を特定できない）（指摘したエージェント 2 人。操作の当てはまり: 要る 9、寄り道 17、無駄 1）

問題だった点:

- H1-holdout/subagent-2: #1 #2 SKILL.md を読む前に find と cat でプロジェクト全体を見回し、settings.json や hooks.json の中身まで出した。手順1の判定は依頼文だけでできるので、判定には使っていない
- T1-typical/subagent-1: #2 で SKILL.md と設定類を1つのコマンドでまとめて読み、出力が大きすぎて先頭しか見えず、#3・#4 で読み直した

直し方の案:

- T1-typical/subagent-1: references/control-ladder.md に、checks の lines の値（first・all・行番号）とコマンドの置き換え（{file}・{skill}・{run}・{in:キー}）の一覧を載せる（無ければ）
- T1-typical/subagent-1: control-ladder.md の7章に、baseline の fixture と setup の動き（一時プロジェクトが git init 済みか、setup がいつ流れるか）を書き、probe.py を読まずに済むようにする
- T1-typical/subagent-1: control-ladder.md の3章（入力）に、start が別名・全角・大文字小文字をどう揃えるかを書き、_skillrt.py の normalize_input を読まずに inputs を書けるようにする（無ければ）
- T1-typical/subagent-2: references/control-ladder.md の4章と7章に、command の検査の run で使える置き換え（{skill}・{file}・{in:<key>}・{run}）と、probes.json の fixture・setup の書き方を書く
- T2-default/subagent-1: control-ladder.md の出力の契約の章（4章）に、検査の型 command の項目（run、rules、{file}・{root}・{skill} の置き換え）と spec の report.sections の書き方を表で載せる
- T2-default/subagent-1: control-ladder.md の7章に、スキル固有のスクリプトの分かれ道（終了コードごとの中断、単位の切り替え）は fixture と違反例で確かめ、手で作った一時の場所で試さないと書く
- T2-default/subagent-2: convergence.py prepare の --workdir の既定を、作業ディレクトリの外の一時ディレクトリではなく、プロジェクトの .skill-runs/skill-foundation/ の下にする
- T2-default/subagent-2: control-ladder.md の7章と convergence-test.md の1章に、baseline と課題の fixture・setup・commands がいつどのディレクトリで動くか（{skill}・{lab}・{root}、git の初期化）と、ステージ済みの状態を作る例（git apply --index）を書く
- T3-edge/subagent-2: control-ladder.md の4章に、checks の型（require、forbid、headings、command）と、command の rules で決定を契約に結ぶ書き方の早見を足す

### 手順 2: 名前を intake.md の2章、言語を3章、置き場を4章で決め、run.py（指摘したエージェント 0 人。操作の当てはまり: 要る 6、寄り道 9）

直し方の案:

- T3-edge/subagent-1: SKILL.md の手順3に「この時点では check を実行しない（手順11で実行する）」と書く。start の案内（#8 の出力）の「書いたら check」が、早い check を招いている

### 手順 5: フェーズ2（調査）（指摘したエージェント 0 人。操作の当てはまり: 要る 37、寄り道 2）

直し方の案:

- T1-typical/subagent-1: SKILL.md の手順 5 の終わりに「phase 2 の lint は無い」と書くか、skill_lint.py に research.md を確かめる --phase 2 を足す
- T3-edge/subagent-1: SKILL.md の手順5の終わりで research.md を書き終えることを求め、scripts/skill_lint.py に --phase 2 を足して、出典と確認の状態が埋まったかをその場で確かめる

## 前のラウンドの動きの指摘（dev/convergence-report.md のラウンド 2）

前のラウンドで締め込んだ指摘が上に再び出ていれば、その締め込みは効いていない。締め込み方を変える。

| エージェントと操作 | 指摘 | 分類 | 対処 |
|---|---|---|---|
| T1-typical/subagent-1 #62〜#64、T1-typical/subagent-2 #59・#60、T2-default/subagent-1 #49〜#53、T2-default/subagent-2 #57・#63、T3-edge/subagent-1 #57・#58 | 手順7の lint --phase 4 が probes.json の違反例と baseline を求め、手順8の probes.json を先に書いた（ラウンド1と同じ） | V2 | 未対処（分析はラウンドの後に作った）。案: ラウンド1の行と同じく、probes.json の検査を --phase 5 に移すか、SKILL.md の手順7に違反例の ID を先に書くと足す |
| T1-typical/subagent-1 #35・#36・#39〜#44・#48、T1-typical/subagent-2 #13・#36〜#40・#50〜#52、T2-default/subagent-1 #13・#30〜#34・#41・#42、T2-default/subagent-2 #34〜#38・#72〜#74、T3-edge/subagent-1 #33〜#39、T3-edge/subagent-2 #31〜#38・#53・#54 | spec（checks、置き換え、report.sections）と probe の setup の書き方を references で引けず、スクリプトを読んだ（ラウンド1と同じ） | V1 | 未対処（分析はラウンドの後に作った）。案: ラウンド1の行と同じく control-ladder.md に表を足し、spec.example.json に欄ごとの取りうる値と例を載せる |
| T1-typical/subagent-1 #56・#57、T3-edge/subagent-1 #52・#53 | 固有のスクリプトを .skill-runs の一時の git リポジトリで手で試し、probe.py と同じことを2度確かめた（ラウンド1と同じ） | V1 | 未対処（分析はラウンドの後に作った）。案: ラウンド1の行と同じく、control-ladder.md の5章に、固有のスクリプトは違反例と probe.py で試すと書く |
| T2-default/subagent-2 #39〜#43 | fixture・固有のスクリプト・見本を、調査の記録（#44）と決定（#49・#50）より先に作った（ラウンド1と同じ） | V3 | 未対処（分析はラウンドの後に作った）。案: ラウンド1の行と同じく、手順5に作る時期を書き、skill_lint.py --phase 3 が先に作ったスクリプトや見本を警告する |
| T1-typical/subagent-2 #70〜#73 | measure=skip で、手順9の文面にある prepare を実行しなかった。省いてよいかが手順から読めない（ラウンド1と同じ） | V2 | 未対処（分析はラウンドの後に作った）。案: ラウンド1の行と同じく、SKILL.md の手順9に measure=skip の場合分けを書く |
| T1-typical/subagent-1 #71 | lint の無い手順9で evals.json を確かめようと、手順10の --final を先に流し、予想できるエラー（status と hooks の未登録）を出した | V1 | 未対処（分析はラウンドの後に作った）。案: SKILL.md の手順9に「evals.json は手順10の --final で確かめる」と書くか、skill_lint.py に evals.json を確かめる --phase 6 を足す |
| T3-edge/subagent-1 #47、T3-edge/subagent-2 #72 | 入力 source の impact を、analyze の目安（target）ではなく reversible にした。2人とも skill-profiles.md の目安から外れた | V2 | 未対処（分析はラウンドの後に作った）。案: skill-profiles.md の analyze の「入力の候補」で source の impact を決め直すか外してよい条件を書き、lint の --phase 3 で外れを警告する |
| T3-edge/subagent-2 #10・#41 | 手順3で書いた triggers の例文に、後の決定 IN-01 で対象外にした依頼（FIXME も集める、TODO.md を作る）が入り、#41 で書き直した | V1 | 未対処（分析はラウンドの後に作った）。案: SKILL.md の手順6の終わりに、決定を書いた後で triggers の use_when が対象外にした依頼を含まないかを見直すと書く |
| T3-edge/subagent-2 #48・#72 | 対象を . にすると dev/fixtures や skill-foundation の雛形の TODO まで一覧に入ると分かったが、除くかを決めずに補足に書くだけにした | V1 | 未対処（分析はラウンドの後に作った）。案: skill-profiles.md の analyze の節に、対象がプロジェクト全体のとき、スキルの置き場（.agents/skills、.claude/skills）を除くかを決定に書くと足す |
| T3-edge/subagent-2 #47・#72 | dev/fixtures/basic に .gitignore を置き、ホストのリポジトリで commit すると fixture の一部が git に入らない問題を残した | V1 | 未対処（分析はラウンドの後に作った）。案: convergence-test.md 1章に「fixture の .gitignore は setup で作る」と書き、skill_lint.py で警告する |
| T2-default/subagent-2 #40・#75〜#77 | 差分 basic.patch を dev/fixtures に置いて setup から使ったが、後で外へ移し、setup に差分を埋め込んで probe を流し直した | V2 | 未対処（分析はラウンドの後に作った）。ラウンド1の締め込み（fixture は basic の1つ）の後、差分の置き場が書かれていない。案: convergence-test.md の1章に、差分を setup に埋め込む見本を書く |
| T2-default/subagent-1 #12・#64 | STEP-02 の境目（5件と6件の間）を、調べずに見本 write-commit-message から写した。本人も補足に「調査で決めた数ではない」と書いた | V6 | 未対処（分析はラウンドの後に作った。ばらつきの表 #9 の依頼に無い値と同じ原因）。案: variance-axes.md の2章に、見本の値を写すときの basis と、research.md に写した理由を書くことを足す |
| T1-typical/subagent-2 #5・#6・#64・#65、T2-default/subagent-1 #54 | zsh のグロブで grep が失敗し、zsh で空になる ${PIPESTATUS[0]} で probe.py の終了コードを取れなかった（ラウンド1と同じ） | V8 | 締め込まない。シェルの使い方の誤りで、出力に影響しない（probe はどちらも失敗0件） |
| T1-typical/subagent-1 #27・#28、T1-typical/subagent-2 #31・#32、T2-default/subagent-1 #21・#24 | 同じページを WebFetch で2回取り直した。1回の問いにまとめられた | V8 | 締め込まない。別の部分を抜き出すための取り直しで、出力に影響しない |
| T1-typical/subagent-2 #41・#42 | #41・#42 で調べた CI スキップの記法を決定に使ったかは、記録から分からない | 推定違い | 記録では、#57 で OUT-07 の forbid（[skip ci]、skip-checks: の検査）に、#60 で違反例 OUT-07-a に使っている |
| T2-default/subagent-2 #61〜#63 | 長すぎる項目の違反例の文が91字で100字に届かず、自分で書いた assert で止まって書き直した | V8 | 締め込まない。作業用スクリプトの中の確かめで、出力に影響しない |
