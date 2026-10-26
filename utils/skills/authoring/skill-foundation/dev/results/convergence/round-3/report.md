# 収束テスト ラウンド 3

convergence.py diff が生成する。揺れの分類（V1〜V8）と対処は dev/convergence-report.md に書く。

基準: status が全員、課題の expect_status（既定 done）と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェントがいない。files ≥ 1.0、structure ≥ 1.0、names ≥ 0.8

runner subagent は Agent ツールで実行した。一時プロジェクトの hooks は働かず、run.py の check と finish だけで検査された。自動の起動は、スキルの説明文を前置きで渡した近似である（convergence-test.md の3章）。

## 指標

| 課題 | status | files | structure | names | content | check | runner 別 files | 基準 |
|---|---|---|---|---|---|---|---|---|
| T1-typical | done | 0.760 | 0.421 | 0.139 | 0.658 | 全員通過 | subagent 0.760 | 満たさない |
| T2-default | done | 0.440 | 0.364 | 0.178 | 0.610 | 全員通過 | subagent 0.440 | 満たさない |
| T3-edge | done | 0.667 | 0.400 | 0.202 | 0.644 | 全員通過 | subagent 0.667 | 満たさない |
| H1-holdout | unused | 1.000 | 1.000 | 1.000 | — | — | subagent 1.000 | 満たす |

## T1-typical

### 実行の状態（期待: done）

- subagent-1: done
- subagent-2: done

### 新しく作った名前（names。先頭 40 件）

- subagent-1: `Apple`, `Assistant`, `COMMIT_EDITMSG`, `CTL-02-builtin-hooks-claude`, `CTL-02-builtin-hooks-codex`, `Co-Authored-By`, `DIFF`, `Git-155`, `JA_CHARS`, `JA_ENDING`, `KINDS`, `OUT-02-c`, `OUT-03-b`, `PER_FILE_LINES`, `R100`, `STEP-02-c`, `STEP-02-d`, `TOTAL_LINES`, `abc-13-sub`, `begin`, `check_message`, `duplicated`, `eval`, `feature`, `file_diff`, `guide`, `literal-pathspecs`, `nCo-Authored-By`, `no-color`, `no-ext-diff`, `no-textconv`, `noreply`, `npython3`, `obsolete`, `old`, `old-guide`, `ordered`, `post-image`, `read_lines`, `renames`
- subagent-2: `A-Z0-9_`, `Apple`, `Atlassian`, `Backlog`, `CHANGELOG`, `COMMIT_EDITMSG`, `CTL-02-builtin-hooks-claude`, `CTL-02-builtin-hooks-codex`, `DESCRIPTION`, `DIR`, `EXAMPLE-1`, `Exception`, `FORMAT`, `GIT`, `Git-155`, `GitError`, `GitLab`, `HTTP`, `IDs`, `IN-01-a`, `Jira`, `KINDS`, `NUL`, `Namespace`, `OPTIONS`, `OUT-02-c`, `OUT-03-b`, `OUT-03-c`, `OUT-07`, `OUT-07-a`, `OUTPUT`, `PROJ-123`, `PROJ-7`, `R100`, `RAW`, `Redmine`, `STEP-01-a`, `Same`, `Signed-off-by`, `Support`

### 一部のエージェントだけが作った・変えたファイル

- `.claude/skills/write-commit-message/dev/fixtures/basic/README.md`: subagent-2
- `.claude/skills/write-commit-message/dev/fixtures/basic/src/calc.py`: subagent-2
- `.claude/skills/write-commit-message/dev/fixtures/basic/src/helpers.py`: subagent-2
- `.claude/skills/write-commit-message/scripts/check_message.py`: subagent-1
- `.claude/skills/write-commit-message/scripts/collect_diff.py`: subagent-1
- `.claude/skills/write-commit-message/scripts/commit_message.py`: subagent-2

### 中身の違い（抜粋）

#### `.claude/skills/write-commit-message/SKILL.md`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-commit-message/SKILL.md
+++ subagent-2/.claude/skills/write-commit-message/SKILL.md
@@ -1,12 +1,12 @@
 ---
 name: write-commit-message
-description: "ステージ済みの差分とチケットIDから、チケットIDで始まる1行目と変更ファイルごとの箇条書きの本文からなるコミットメッセージを1つ書く。「コミットメッセージを書いて。チケットIDで始まる1行目と、変更ファイルごとの箇条書きの本文にして」、「ステージした変更のコミットメッセージを作って」、「ABC-12 のコミットメッセージをお願いします」、「この差分に合うコミットメッセージを考えてくれる？」、「commit message 書いて」と頼まれたときに使う。コミットの実行やプッシュには使わない（代わりにgit コマンドを使う）。プルリクエストの説明文を書くには使わない（代わりにプルリクエスト用のスキルを使う）。"
+description: "ステージした変更の差分とチケットIDを受け取り、チケットIDで始まる1行目と、変更ファイルごとの箇条書きの本文からなるコミットメッセージを書く。「コミットメッセージを書いて。チケットIDで始まる1行目と、変更ファイルごとの箇条書きの本文にしたい」、「ステージした変更のコミットメッセージを作ってください」、「この差分でコミットメッセージ考えて」、「PROJ-123 の変更のコミットメッセージをお願いします」、「変更したファイルごとに何をしたかを箇条書きにしたコミットメッセージがほしい」、「Write a commit message for the staged changes」と頼まれたときに使う。複数のコミットから変更履歴（CHANGELOG）やリリースノートを書くには使わない（代わりに変更履歴を書くスキルか、直接の依頼を使う）。プルリクエストのタイトルや説明文を書くには使わない（代わりにプルリクエストの説明を書くスキルか、直接の依頼を使う）。"
 ---
 
 # コミットメッセージを書く
 
 <!-- BEGIN GENERATED:purpose -->
-ステージ済みの差分とチケットIDから、チケットIDで始まる1行目と変更ファイルごとの箇条書きの本文からなるコミットメッセージを1つ書く
+ステージした変更の差分とチケットIDを受け取り、チケットIDで始まる1行目と、変更ファイルごとの箇条書きの本文からなるコミットメッセージを書く
 <!-- END GENERATED:purpose -->
 
 ## 1. 使う場面
@@ -14,16 +14,17 @@
 <!-- BEGIN GENERATED:triggers -->
 次のような依頼で使う。
 
-- 「コミットメッセージを書いて。チケットIDで始まる1行目と、変更ファイルごとの箇条書きの本文にして」
-- 「ステージした変更のコミットメッセージを作って」
-- 「ABC-12 のコミットメッセージをお願いします」
-- 「この差分に合うコミットメッセージを考えてくれる？」
-- 「commit message 書いて」
+- 「コミットメッセージを書いて。チケットIDで始まる1行目と、変更ファイルごとの箇条書きの本文にしたい」
+- 「ステージした変更のコミットメッセージを作ってください」
+- 「この差分でコミットメッセージ考えて」
+- 「PROJ-123 の変更のコミットメッセージをお願いします」
+- 「変更したファイルごとに何をしたかを箇条書きにしたコミットメッセージがほしい」
+- 「Write a commit message for the staged changes」
 
 次の場合は使わない。
 
-- コミットの実行やプッシュ → 代わりに: git コマンド
-- プルリクエストの説明文を書く → 代わりに: プルリクエスト用のスキル
+- 複数のコミットから変更履歴（CHANGELOG）やリリースノートを書く → 代わりに: 変更履歴を書くスキルか、直接の依頼
+- プルリクエストのタイトルや説明文を書く → 代わりに: プルリクエストの説明を書くスキルか、直接の依頼
 
 依頼の内容から自動で選ばれる。明示して呼ぶときは Claude Code では `/write-commit-message`、Codex では `$write-commit-message` と書く。
 <!-- END GENERATED:triggers -->
@@ -32,21 +33,20 @@
 
 このファイルがあるディレクトリを `<skill>` と呼ぶ。スクリプトは Python 3.9 以上の標準ライブラリだけで動く。手順は番号の順に行い、飛ばさない。
 
-1. 依頼から「3. 入力」の項目を読み取る。表で「start の前に聞く」とある項目が依頼に無ければ、ここでまとめてユーザーに聞く（CTL-03）
-2. `python3 <skill>/scripts/run.py start --set ticket=<チケットID> --set language=<ja・en> "<依頼文>"` を実行する。`language` は依頼に指定が無ければ渡さない。終了コード3なら、出力された質問をユーザーに聞き、答えを `--set` で渡してやり直す（CTL-01、OUT-04）
-3. `python3 <skill>/scripts/collect_diff.py` を実行する。終了コード4なら IN-01、終了コード2なら STEP-04 に従い、出力を書かずに `python3 <skill>/scripts/run.py abort --reason "<理由>"` を実行して、abort の本文をそのまま返答する。材料は collect_diff.py の出力だけにし、差分が「省きました」と出たファイルは `python3 <skill>/scripts/collect_diff.py --path <パス>` で読む。git はこの2つのスクリプトの中だけで使い、`git add`・`git commit`・`git push`・`git stash` を実行しない（IN-01、IN-02、STEP-01、STEP-03、STEP-04）
-4. 1行目を `<チケットID> <要約>` の形で、50文字以内に書く。チケットIDは start が出した `ticket` の値をそのまま使う。要約は start が出した `language` に従い、OUT-03 の決定表の形にする。Conventional Commits の接頭辞（`feat:` の類）と、`[skip ci]` のような CI を止める記法は書かない（OUT-02、OUT-03、OUT-04、OUT-05、OUT-06）
-5. 2行目を空行にし、3行目から、collect_diff.py が出した「本文に書くパス」を出た順に1つずつ「- `<パス>`: <変更の要約>」の形で書く。ファイルが1つでも本文を書き、ディレクトリでまとめない。変更の要約も OUT-03 の形にする。形は見本 `assets/examples/commit-message.txt` と同じにする。書いたものを `.skill-runs/write-commit-message/out/commit-message.txt` に保存する（OUT-01、OUT-02、STEP-02）
-6. `python3 <skill>/scripts/run.py check` を実行する。「整形」で始まる行は check が契約の format で自動で直した記録なので、ファイルを読み直す。指摘があれば、ルールIDを「4. 決定表」で引いて出力を直す。検査や契約を変えて通さない（CTL-02）
-7. 決めきれなかったことがあれば `.skill-runs/write-commit-message/notes.md` に「- 」の箇条書きで書き、`python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら手順6に戻る。終了コード0なら、出力された本文をそのまま返答する。コミットは利用者に任せる（RPT-01、STEP-03）
+1. 依頼からチケットID（入力 `ticket`）を読み取る。依頼に無ければ、ここでユーザーに聞く（CTL-03）
+2. `python3 <skill>/scripts/run.py start --set ticket=<チケットID> "<依頼文>"` を実行する。終了コード3なら、出力された質問をユーザーに聞き、答えを `--set` で渡してやり直す（CTL-01）
+3. プロジェクトのルートで `python3 <skill>/scripts/commit_message.py list --ticket <チケットID>` を実行する。終了コードが0でなければ、IN-01 の表のとおり中断するか聞き直し、メッセージを書かない（IN-01）
+4. list の「変更の種類と、差分を読むコマンド」の各行のコマンドで差分を読む。未ステージの変更、追跡していないファイル、`git log` は読まない（IN-02）。`git add`、`git reset`、`git commit` を実行しない（STEP-02）
+5. 見本 `assets/examples/commit-message.txt` を写す元にして、`.skill-runs/write-commit-message/out/commit-message.txt` に丸ごと書く（OUT-01）。1行目は list の「1行目の形」、2行目は空行、3行目からは list の「本文の行」をその順のまま写して `<説明>` を埋める（STEP-01、OUT-02、OUT-04）。要約と説明は日本語の動詞の現在形で終え（OUT-03）、50文字以内にし（OUT-05）、CI を止める記法と URL を書かない（OUT-06、OUT-07）
+6. `python3 <skill>/scripts/run.py check` を実行する。指摘があれば、ルールIDを「4. 決定表」で引いて出力を直す。検査や契約を変えて通さない（CTL-02）
+7. 決めきれなかったことがあれば `.skill-runs/write-commit-message/notes.md` に「- 」の箇条書きで書き、`python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら手順6に戻る。終了コード0なら、出力された本文をそのまま返答する（RPT-01）
```

#### `.claude/skills/write-commit-message/assets/contract.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-commit-message/assets/contract.json
+++ subagent-2/.claude/skills/write-commit-message/assets/contract.json
@@ -11,41 +11,20 @@
     {
       "key": "ticket",
       "label": "チケットID",
-      "impact": "target",
       "type": "string",
       "case": "upper",
       "aliases": [
         "チケット",
+        "チケット番号",
+        "課題キー",
         "課題",
-        "課題キー",
         "issue",
-        "ticket id",
+        "issue_key",
         "ticket_id"
       ],
+      "impact": "target",
       "ask": true,
-      "question": "1行目の先頭に書くチケットID（例: ABC-123）は何ですか"
-    },
-    {
-      "key": "language",
-      "label": "出力の言語",
-      "impact": "reversible",
-      "type": "enum",
-      "enum": [
-        "ja",
-        "en"
-      ],
-      "enum_aliases": {
-        "日本語": "ja",
-        "japanese": "ja",
-        "英語": "en",
-        "english": "en"
-      },
-      "aliases": [
-        "言語",
-        "lang",
-        "メッセージの言語"
-      ],
-      "default": "ja"
+      "question": "1行目の先頭に付けるチケットID（例：PROJ-123）を教えてください"
     }
   ],
   "outputs": [
@@ -58,72 +37,101 @@
         "min": 1,
         "max": 1
       },
+      "format": [
+        {
+          "type": "trailing_space",
+          "rule": "OUT-02"
+        },
+        {
+          "type": "final_newline",
```

#### `.claude/skills/write-commit-message/assets/examples/commit-message.txt`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-commit-message/assets/examples/commit-message.txt
+++ subagent-2/.claude/skills/write-commit-message/assets/examples/commit-message.txt
@@ -1,5 +1,6 @@
-ABC-12 引き算と使い方の表示を足す
+ABC-12 電卓に引き算を足す
 
-- `docs/guide.md`: 使い方の文書の名前を変える
-- `src/app.py`: 計算の結果を表示する
-- `src/calc.py`: 引き算の関数を足す
+- README.md: 引き算の使い方を足す
+- src/calc.py: 引き算の関数 subtract を足し、補助関数の読み込み先を変える
+- src/helpers.py -> src/util.py: 補助関数のファイル名を util.py に変える
+- tests/test_calc.py: subtract のテストを足す
```

#### `.claude/skills/write-commit-message/assets/seal.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-commit-message/assets/seal.json
+++ subagent-2/.claude/skills/write-commit-message/assets/seal.json
@@ -1,15 +1,14 @@
 {
   "runtime": "1.0.0",
   "files": {
-    "SKILL.md": "0cd01c1018cf77087d59a4555b74a2d0f0cade24fdef3d3ba9bb24a557fa065d",
-    "assets/contract.json": "4b74f586e0f9d0745e941dee892c146c79189c611779e6b28a75a013492467c3",
-    "assets/examples/commit-message.txt": "5c231c8ee4937a9cf8c8059845474835f71583372f5970b778cff1bca11109e7",
-    "references/decisions.md": "6b788f668cd14914e18c9932954ca09a050cd97155e35c35ca0455d8ac16f19e",
+    "SKILL.md": "18200ea1a1d62c3faec4a97df916a01d8a715e1e0f58868fd7487d375f12ac76",
+    "assets/contract.json": "c09808e2abbd28b3ca583dd65c53cd628231e44a66dd5c02f6ac76045e27299e",
+    "assets/examples/commit-message.txt": "b754a93a8032cd9617f5564e8def84a7108a05dac6a75bd58b264e4b19d7cfca",
+    "references/decisions.md": "b952d4c6003b28b33d1e94f65eee951151f34c3bea4f1a2386a512d15644ea25",
     "scripts/run.py": "fcced04ce88880bbe860dadc1d25481c464f13d733de4d4c7d9c5ccbde096b76",
     "scripts/_skillrt.py": "b76eceeda4fdcad10a4246a66a7d137d2400cec49cc62d95ec89fd463b784304",
     "scripts/hook.py": "b0ccd614d242fcbbd2499da75d759b33b4cb8f7c7357563954570f15c3a7ef55",
-    "scripts/collect_diff.py": "f63fa76c859e23a08bbbf9d88ccef755c74c1feee6fc901550a1dca3579ccf6e",
     "scripts/install.py": "286effaa9680fd4f8a03816b37252e36b62172301ef9d64c8debd4646d91ea19",
-    "scripts/check_message.py": "6f146ba7f36e5e034f034a4004ecb1f015c1decc76704f6e9767ff23d02f319c"
+    "scripts/commit_message.py": "d6f0f325ada54aa5b876bab3b21c49dcf4cb540defce15493b70ab8a84c671a5"
   }
 }
```

#### `.claude/skills/write-commit-message/dev/convergence-report.md`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-commit-message/dev/convergence-report.md
+++ subagent-2/.claude/skills/write-commit-message/dev/convergence-report.md
@@ -1,28 +1,28 @@
 # write-commit-message 収束テストの記録
 
-このスキルの作成に関わっていない独立エージェント（Claude Code と Codex。起動できないときは Agent ツールの subagent）に同じ依頼を解かせ、出力の違い（揺れ）を測るための記録である。今回は実行していない。
+このスキルの作成に関わっていない独立エージェント（Claude Code と Codex。起動できないときは Agent ツールの subagent）に同じ依頼を解かせ、出力の違い（揺れ）を測った記録である。生データは `dev/results/convergence/round-<R>/` にある。
 
 ## 条件
 
 | 項目 | 値 |
 |---|---|
-| runner | なし（実行していない） |
-| 1 runner あたりの人数 | なし |
-| 課題 | `dev/evals.json`（T1-typical、T2-default、T3-edge、H1-holdout） |
-| 合格基準 | 測っていない |
+| runner | なし。利用者が収束テストを省くと指定した（skill-foundation の入力 `measure` が `skip`。STEP-02 の表の skip の行） |
+| 1 runner あたりの人数 | 0（実行していない） |
+| 課題 | `dev/evals.json`（作ったが実行していない） |
+| 合格基準 | status が全員、課題の expect_status と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェント（失格）がいない。files・structure・names が基準以上。最後のラウンドのレビューの検出率が全見本で 1.0。V1〜V7 の未対処が0件 |
 
 ## ラウンドの一覧
 
 | ラウンド | 課題 | status | files | structure | names | content | check | 失格 | V1〜V7 の未対処 |
 |---|---|---|---|---|---|---|---|---|---|
-| なし | | | | | | | | | |
+| なし | 実行していない | | | | | | | | |
 
 ## レビューの検出率（最後のラウンド）
 
 | 見本 | 決定 | 検出率 | 余計な指摘 | 一致 |
 |---|---|---|---|---|
-| なし（`dev/probes.json` の reviews にある IN-02-r1、OUT-03-r1 は測っていない） | | | | |
+| なし（`dev/probes.json` の reviews が無い） | | | | |
 
 ## 結論
 
-収束テストは実行していない。利用者が収束テストを省くと指定したため、skill-foundation の STEP-02 の表の `skip` の行に従い、spec の `convergence.skip_reason` に「利用者が収束テストを省くと指定した」と書いた。測るときは、`dev/evals.json` の課題で skill-foundation の `convergence.py prepare` から始める。
+収束テストは実行していない。spec の `convergence.skip_reason` は「利用者が収束テストを省くと指定した」である。独立エージェントの間で出力が揃うかは測っておらず、確かめたのは `probe.py` の違反例 25 件と hooks の配線 20 件だけである。
```

#### `.claude/skills/write-commit-message/dev/evals.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-commit-message/dev/evals.json
+++ subagent-2/.claude/skills/write-commit-message/dev/evals.json
@@ -3,16 +3,13 @@
     {
       "id": "T1-typical",
       "kind": "typical",
-      "prompt": "ABC-12 のコミットメッセージを書いて。チケットIDで始まる1行目と、変更ファイルごとの箇条書きの本文にして",
-      "fixture": null,
+      "prompt": "ABC-12 のコミットメッセージを書いて。1行目はチケットIDから始めて、本文は変更したファイルごとの箇条書きにして",
+      "fixture": "dev/fixtures/basic",
       "setup": [
-        "mkdir -p src docs",
-        "printf 'def add(a, b):\\n    return a + b\\n' > src/calc.py",
-        "printf '# 使い方\\n\\npython3 src/app.py を実行する\\n' > docs/old-guide.md",
-        "git add -A && git -c user.name=eval -c user.email=eval@localhost -c commit.gpgsign=false -c core.hooksPath=/dev/null commit -q -m init",
-        "printf 'def add(a, b):\\n    return a + b\\n\\n\\ndef sub(a, b):\\n    return a - b\\n' > src/calc.py",
-        "printf 'from calc import add, sub\\n\\nprint(add(1, 2), sub(3, 1))\\n' > src/app.py",
-        "git mv docs/old-guide.md docs/guide.md",
+        "printf '%s\\n' '' '## 引き算' '' '`subtract(5, 3)` は 2 を返す。' >> README.md",
+        "printf '%s\\n' '\"\"\"小さな電卓。\"\"\"' '' 'from src.util import to_number' '' '' 'def add(a, b):' '    \"\"\"a と b の和を返す。\"\"\"' '    return to_number(a) + to_number(b)' '' '' 'def subtract(a, b):' '    \"\"\"a から b を引いた差を返す。\"\"\"' '    return to_number(a) - to_number(b)' > src/calc.py",
+        "git mv src/helpers.py src/util.py",
+        "mkdir -p tests && printf '%s\\n' 'from src.calc import subtract' '' '' 'def test_subtract():' '    assert subtract(5, 3) == 2' > tests/test_calc.py",
         "git add -A"
       ],
       "expect_status": "done"
@@ -20,47 +17,34 @@
     {
       "id": "T2-default",
       "kind": "default",
-      "prompt": "ステージした変更のコミットメッセージを作って。チケットは xyz-7",
-      "fixture": null,
+      "prompt": "PROJ-7 の対応をステージしたので、コミットメッセージをお願いします",
+      "fixture": "dev/fixtures/basic",
       "setup": [
-        "mkdir -p src",
-        "printf 'def add(a, b):\\n    return a + b\\n' > src/calc.py",
-        "git add -A && git -c user.name=eval -c user.email=eval@localhost -c commit.gpgsign=false -c core.hooksPath=/dev/null commit -q -m init",
-        "printf 'def add(a, b):\\n    return a + b\\n\\n\\ndef mul(a, b):\\n    return a * b\\n' > src/calc.py",
-        "git add src/calc.py"
+        "printf '%s\\n' '' '## 注意' '' '文字列の数も足せる。' >> README.md",
+        "git add README.md"
       ],
       "expect_status": "done"
     },
     {
       "id": "T3-edge",
       "kind": "edge",
-      "prompt": "チケット: ABC-30\nこの変更のコミットメッセージを考えて",
-      "fixture": null,
+      "prompt": "ABC-12 のコミットメッセージを書いて",
+      "fixture": "dev/fixtures/basic",
       "setup": [
-        "mkdir -p src docs tests",
-        "printf 'x = 1\\n' > src/config.py",
-        "printf 'obsolete\\n' > docs/old.md",
-        "git add -A && git -c user.name=eval -c user.email=eval@localhost -c commit.gpgsign=false -c core.hooksPath=/dev/null commit -q -m init",
-        "for f in a b c; do printf '# %s\\n' $f > docs/$f.md; done",
-        "printf '設定の説明\\n' > docs/設定.md",
-        "printf 'def test_add():\\n    assert True\\n' > tests/test_calc.py",
-        "printf 'x = 2\\n' > src/config.py",
```


## T2-default

### 実行の状態（期待: done）

- subagent-1: done
- subagent-2: done

### 新しく作った名前（names。先頭 40 件）

- subagent-1: `A-Za-z`, `Added`, `Apple`, `Broken`, `CATEGORIES`, `CHANGELOG`, `CHANGELOG_ENTRY`, `COMMENT`, `CSV`, `CTL-02-builtin-hooks-claude`, `CTL-02-builtin-hooks-codex`, `Changed`, `Configuration`, `Copied`, `DEPRECATION`, `DavidAnson`, `Deleted`, `Deprecated`, `DeprecationWarning`, `ENDINGS`, `Exception`, `FILE_UNIT_MAX`, `Git-155`, `GitError`, `HASH`, `ISO`, `JUDGED`, `LOG_NAME`, `LOOSE_BULLET`, `MD024`, `Modified`, `Multiple`, `NOTES`, `NUL`, `OUT-03-b`, `OUT-04-b`, `OUT-07`, `OUT-07-a`, `OUT-08`, `OUT-08-a`
- subagent-2: `ALICE`, `Added`, `Alice`, `All`, `Ann`, `Apple`, `CHANGELOG`, `COMMENT_LINE`, `CTL-02-builtin-hooks-claude`, `CTL-02-builtin-hooks-codex`, `Changed`, `Changelogs`, `DESCRIPTION`, `Deprecate`, `Deprecated`, `ENDING_JA`, `English`, `Fix`, `Git-155`, `Goodbye`, `HELLO`, `Hello`, `Issue`, `JA_CHAR`, `MD024`, `Mary`, `NAME`, `OUT-02-c`, `OUT-03-b`, `OUT-05-r1`, `OUT-06-b`, `OUT-07`, `OUT-08`, `OUT-08-a`, `OUT-09`, `OUT-09-a`, `OUT-09-b`, `OUT-09-r1`, `OUTPUT_REL`, `PATHSPEC`

### 一部のエージェントだけが作った・変えたファイル

- `.claude/skills/write-changelog-entry/dev/fixtures/basic/.fixture/basic.patch`: subagent-2
- `.claude/skills/write-changelog-entry/dev/fixtures/basic/.fixture/positional-name.patch`: subagent-2
- `.claude/skills/write-changelog-entry/dev/fixtures/basic/.fixture/tests-only.patch`: subagent-2
- `.claude/skills/write-changelog-entry/dev/fixtures/basic/src/app.py`: subagent-1
- `.claude/skills/write-changelog-entry/dev/fixtures/basic/src/calc.py`: subagent-1
- `.claude/skills/write-changelog-entry/dev/fixtures/basic/src/greet.py`: subagent-2
- `.claude/skills/write-changelog-entry/dev/fixtures/basic/tests/test_greet.py`: subagent-2
- `.skill-runs/skill-foundation/work/entry.md`: subagent-1
- `.skill-runs/skill-foundation/work/g1/add.txt`: subagent-1
- `.skill-runs/skill-foundation/work/g1/keep.txt`: subagent-1
- `.skill-runs/skill-foundation/work/g1/new.txt`: subagent-1
- `.skill-runs/skill-foundation/work/lab1/CHANGELOG.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab1/README.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab1/src/app.py`: subagent-1
- `.skill-runs/skill-foundation/work/lab1/src/calc.py`: subagent-1
- `.skill-runs/skill-foundation/work/lab1/src/report.py`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/CHANGELOG.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/NOTES.txt`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/README.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/docs/a.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/docs/b.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/docs/c.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/docs/d.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/docs/e.md`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/src/calc.py`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/src/main.py`: subagent-1
- `.skill-runs/skill-foundation/work/lab3/tests/test_calc.py`: subagent-1
- `.skill-runs/skill-foundation/work/probe.log`: subagent-1

### 中身の違い（抜粋）

#### `.claude/skills/write-changelog-entry/SKILL.md`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-changelog-entry/SKILL.md
+++ subagent-2/.claude/skills/write-changelog-entry/SKILL.md
@@ -1,12 +1,12 @@
 ---
 name: write-changelog-entry
-description: "ステージ済みの差分から、CHANGELOG.md に足す1節を Keep a Changelog の形で1つ書く。「変更履歴（CHANGELOG.md）に足す1節を、ステージ済みの差分から書いて」、「ステージした変更で CHANGELOG のエントリを作って」、「この変更を変更履歴に追記する文面を考えて」、「次のリリースに向けて、Unreleased に足す変更履歴を書いて」、「changelog entry 書いて」、「CHANGELOG.md に何を足せばいいか、差分から書き出して」と頼まれたときに使う。コミットメッセージを書くには使わない（代わりにコミットメッセージ用のスキルを使う）。過去のコミット履歴やタグの間から、リリース全体の変更履歴をまとめるには使わない（代わりにgit log を読む別の手順を使う）。版の番号と日付を付けたリリースの節を作る（Unreleased の節を版の節に移す）には使わない（代わりにリリースの手順を使う）。GitHub のリリースの作成や公開には使わない（代わりにgh release を使うリリースの手順を使う）。"
+description: "ステージ済みの差分（`git diff --cached`）を受け取り、CHANGELOG.md に足す `## [Unreleased]` の1節を Keep a Changelog の形で書く。「変更履歴（CHANGELOG.md）に足す1節を、ステージ済みの差分から書いて」、「ステージした変更の CHANGELOG エントリを書いて」、「git add した差分から CHANGELOG.md の Unreleased の節を作ってください」、「今回の変更を変更履歴に載せる文章にまとめて」、「Write a changelog entry for the staged changes」、「staged の diff から CHANGELOG に載せる項目を考えて」と頼まれたときに使う。ステージ済みの差分からコミットメッセージを書くには使わない（代わりにコミットメッセージを書くスキル（write-commit-message）を使う）。git log のコミット履歴全体から CHANGELOG.md を作り直すには使わない（代わりにその作業を直接行うを使う）。`## [Unreleased]` の項目を版の番号と日付の節に移す（リリースの作業）には使わない（代わりにその作業を直接行うを使う）。"
 ---
 
-# 変更履歴の1節を書く
+# ステージ済みの差分から CHANGELOG.md に足す1節を書く
 
 <!-- BEGIN GENERATED:purpose -->
-ステージ済みの差分から、CHANGELOG.md に足す1節を Keep a Changelog の形で1つ書く
+ステージ済みの差分（`git diff --cached`）を受け取り、CHANGELOG.md に足す `## [Unreleased]` の1節を Keep a Changelog の形で書く
 <!-- END GENERATED:purpose -->
 
 ## 1. 使う場面
@@ -15,18 +15,17 @@
 次のような依頼で使う。
 
 - 「変更履歴（CHANGELOG.md）に足す1節を、ステージ済みの差分から書いて」
-- 「ステージした変更で CHANGELOG のエントリを作って」
-- 「この変更を変更履歴に追記する文面を考えて」
-- 「次のリリースに向けて、Unreleased に足す変更履歴を書いて」
-- 「changelog entry 書いて」
-- 「CHANGELOG.md に何を足せばいいか、差分から書き出して」
+- 「ステージした変更の CHANGELOG エントリを書いて」
+- 「git add した差分から CHANGELOG.md の Unreleased の節を作ってください」
+- 「今回の変更を変更履歴に載せる文章にまとめて」
+- 「Write a changelog entry for the staged changes」
+- 「staged の diff から CHANGELOG に載せる項目を考えて」
 
 次の場合は使わない。
 
-- コミットメッセージを書く → 代わりに: コミットメッセージ用のスキル
-- 過去のコミット履歴やタグの間から、リリース全体の変更履歴をまとめる → 代わりに: git log を読む別の手順
-- 版の番号と日付を付けたリリースの節を作る（Unreleased の節を版の節に移す） → 代わりに: リリースの手順
-- GitHub のリリースの作成や公開 → 代わりに: gh release を使うリリースの手順
+- ステージ済みの差分からコミットメッセージを書く → 代わりに: コミットメッセージを書くスキル（write-commit-message）
+- git log のコミット履歴全体から CHANGELOG.md を作り直す → 代わりに: その作業を直接行う
+- `## [Unreleased]` の項目を版の番号と日付の節に移す（リリースの作業） → 代わりに: その作業を直接行う
 
 依頼の内容から自動で選ばれる。明示して呼ぶときは Claude Code では `/write-changelog-entry`、Codex では `$write-changelog-entry` と書く。
 <!-- END GENERATED:triggers -->
@@ -35,18 +34,22 @@
 
 このファイルがあるディレクトリを `<skill>` と呼ぶ。スクリプトは Python 3.9 以上の標準ライブラリだけで動く。手順は番号の順に行い、飛ばさない。
 
-1. 依頼を読む。このスキルには入力の項目が無い（「3. 入力」）ので、start の前にユーザーに聞くことは無い。依頼に版の番号や日付があっても、節の見出しには使わない（CTL-03、OUT-04）
-2. `python3 <skill>/scripts/run.py start "<依頼文>"` を実行する（CTL-01）
-3. `python3 <skill>/scripts/changelog_entry.py collect` を実行する。終了コード4か5なら IN-01 の表、終了コード2なら STEP-05 に従って、出力を書かずに `run.py abort` で中断する。出力の最後に「続きは」の行があれば、`--page` で最後のページまで出す。材料は collect の出力だけにし、未ステージの変更、`git log`、既存の `CHANGELOG.md` を読まない。git はこのスクリプトの中だけで使い、`git add`・`git commit` を実行しない（IN-02、STEP-01、STEP-04）
-4. collect の「単位」の行ごとに分類を決める。「分類」が `Added`・`Removed`・`Deprecated` ならそれを使う。「判断」なら、その単位の差分に STEP-03 の表を上から当てはめ、最初に当たった行の分類にする。単位を足したり、省いたり、まとめ直したりしない（STEP-02、STEP-03）
-5. 見本 `assets/examples/changelog-entry.md` と同じ形で節を書き、`.skill-runs/write-changelog-entry/out/changelog-entry.md` に保存する。1行目は `## [Unreleased]`、2行目は空行にし、分類は `Added`、`Changed`、`Deprecated`、`Removed`、`Fixed`、`Security` の順に、箇条書きのある分類だけを書く。各単位を「- `<単位のパス>`: <要約>」の1行にし、collect の単位の順に並べる。要約は、分類ごとの語（OUT-03 の表）で終わる40文字以内の日本語にする。`<!--`、URL、リンク、`#12` の形の番号、コミットのハッシュは書かない。`CHANGELOG.md` は書き換えない（OUT-01〜OUT-08）
-6. `python3 <skill>/scripts/run.py check` を実行する。「整形」で始まる行は check が契約の format で自動で直した記録なので、ファイルを読み直す。指摘があれば、ルールIDを「4. 決定表」で引いて出力を直す。検査や契約を変えて通さない（CTL-02）
-7. 「6. 完了前チェックリスト」を確かめる。決めきれなかったことがあれば `.skill-runs/write-changelog-entry/notes.md` に「- 」の箇条書きで書き、`python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら手順6に戻る。終了コード0なら、出力された本文をそのまま返答する。CHANGELOG.md への反映の仕方は、本文の「## CHANGELOG.md への反映」に入っている（RPT-01、OUT-06）
+1. 依頼から「3. 入力」の項目を読み取る。表で「start の前に聞く」とある項目が依頼に無ければ、ここでまとめてユーザーに聞く（CTL-03）
+2. `python3 <skill>/scripts/run.py start --set <キー>=<値> "<依頼文>"` を実行する。終了コード3なら、出力された質問をユーザーに聞き、答えを `--set` で渡してやり直す（CTL-01）
+3. `python3 <skill>/scripts/changelog_entry.py collect` を実行し、出力されたファイルの一覧と差分を読む（STEP-01、STEP-03）。終了コード4なら IN-01 の表に従い、`python3 <skill>/scripts/run.py abort --reason ステージされた変更が無い` を実行して、abort の本文をそのまま返答して終える。終了コード2なら STEP-05 の表に従う。差分のほかに読むものは IN-02 に、使うコマンドは STEP-04 に従い、CHANGELOG.md、`git diff`、`git log` は読まない
+4. 一覧の変更ごとに、STEP-02 の表で種類（`Added`、`Changed`、`Deprecated`、`Removed`、`Fixed`、`Security`、書かない）を決める。すべてが「書かない」になったら、IN-01 の表に従い `python3 <skill>/scripts/run.py abort --reason 利用者に見える変更が無い` を実行して、abort の本文をそのまま返答して終える。依頼に版の番号か日付があれば、IN-01 の表のとおり `.skill-runs/write-changelog-entry/notes.md` に書く
```

#### `.claude/skills/write-changelog-entry/assets/contract.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-changelog-entry/assets/contract.json
+++ subagent-2/.claude/skills/write-changelog-entry/assets/contract.json
@@ -7,52 +7,127 @@
     "claude",
     "codex"
   ],
-  "inputs": [],
+  "inputs": [
+    {
+      "key": "language",
+      "label": "項目の言語",
+      "type": "enum",
+      "enum": [
+        "ja",
+        "en"
+      ],
+      "enum_aliases": {
+        "日本語": "ja",
+        "japanese": "ja",
+        "英語": "en",
+        "english": "en"
+      },
+      "case": "lower",
+      "aliases": [
+        "言語",
+        "lang",
+        "出力の言語"
+      ],
+      "impact": "reversible",
+      "default": "ja"
+    }
+  ],
   "outputs": [
     {
       "id": "changelog-entry",
-      "label": "変更履歴の節",
+      "label": "CHANGELOG.md に足す節",
       "path": "{run}/out/changelog-entry.md",
       "rule": "OUT-01",
       "count": {
         "min": 1,
         "max": 1
       },
+      "name_pattern": "^changelog-entry\\.md$",
+      "format": [
+        {
+          "type": "trailing_space",
+          "rule": "OUT-02"
+        },
+        {
+          "type": "final_newline",
+          "rule": "OUT-02"
+        },
+        {
+          "type": "replace",
+          "pattern": "^[*+] ",
+          "with": "- ",
+          "rule": "OUT-02",
+          "message": "行頭の `* ` と `+ ` を `- ` にそろえた"
+        }
```

#### `.claude/skills/write-changelog-entry/assets/examples/changelog-entry.md`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-changelog-entry/assets/examples/changelog-entry.md
+++ subagent-2/.claude/skills/write-changelog-entry/assets/examples/changelog-entry.md
@@ -2,8 +2,9 @@
 
 ### Added
 
-- `src/report.py`: 計算の結果を表の行にする関数を追加
+- 別れの挨拶を表示する `farewell` コマンドを追加した。
+- `greet` コマンドに、挨拶を大文字で表示する `--shout` オプションを追加した。
 
 ### Fixed
 
-- `src/calc.py`: 割り算が掛け算の結果を返す誤りを修正
+- `greet` コマンドの `--name` に空白だけの文字列を渡すと、名前の無い挨拶を表示する不具合を修正した。
```

#### `.claude/skills/write-changelog-entry/assets/seal.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-changelog-entry/assets/seal.json
+++ subagent-2/.claude/skills/write-changelog-entry/assets/seal.json
@@ -1,14 +1,14 @@
 {
   "runtime": "1.0.0",
   "files": {
-    "SKILL.md": "4036772c1b535a2ecd6e8b8578546eb0cde30a1fee8417f711adddaaacd8bceb",
-    "assets/contract.json": "4940599ec1a65003adc1ff320352484e5d8e1a1a4d07a08d9de8a1dccf671cde",
-    "assets/examples/changelog-entry.md": "0a4f140baaf32ad90ea3914c4bb4e76a34a0f7877437fc2f468cdb65980f564c",
-    "references/decisions.md": "5e310e03fcbf312ff9287a6372fd4a9f4c6320f68a0889d3aedacc76a4aa3df6",
+    "SKILL.md": "b9872f0b48bc2ed3a4b46326774d0dfa62b3fe98fd6266316c703d80d54f7beb",
+    "assets/contract.json": "f298ccb78817f82e9a87e39c8f13d41411deeb7e49e27a6c2ebcd1ab7f79c657",
+    "assets/examples/changelog-entry.md": "43828260ca7ebe141992e9e853b0e46b1df9b41d741d6c8fc7cb5145cc1dc11e",
+    "references/decisions.md": "e46ff9902d17697ffdb1fe15253ae3ef60c700516fa85beb395ffbf1681a9bb6",
     "scripts/run.py": "fcced04ce88880bbe860dadc1d25481c464f13d733de4d4c7d9c5ccbde096b76",
     "scripts/_skillrt.py": "b76eceeda4fdcad10a4246a66a7d137d2400cec49cc62d95ec89fd463b784304",
     "scripts/hook.py": "b0ccd614d242fcbbd2499da75d759b33b4cb8f7c7357563954570f15c3a7ef55",
-    "scripts/changelog_entry.py": "a66a291335627ef58a8f73a5b0d6ff87c9279f6b1c1d362568185fdaf1456188",
+    "scripts/changelog_entry.py": "ddc8f9e14435f62b7eab13bb04292c89b6f4c1bd26941d122251b91da4fad217",
     "scripts/install.py": "286effaa9680fd4f8a03816b37252e36b62172301ef9d64c8debd4646d91ea19"
   }
 }
```

#### `.claude/skills/write-changelog-entry/dev/convergence-report.md`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-changelog-entry/dev/convergence-report.md
+++ subagent-2/.claude/skills/write-changelog-entry/dev/convergence-report.md
@@ -1,28 +1,29 @@
 # write-changelog-entry 収束テストの記録
 
-このスキルの作成に関わっていない独立エージェント（Claude Code と Codex。起動できないときは Agent ツールの subagent）に同じ依頼を解かせ、出力の違い（揺れ）を測るための記録である。今回は実行していない。
+このスキルの作成に関わっていない独立エージェント（Claude Code と Codex。起動できないときは Agent ツールの subagent）に同じ依頼を解かせ、出力の違い（揺れ）を測った記録である。生データは `dev/results/convergence/round-<R>/` にある。
 
 ## 条件
 
 | 項目 | 値 |
 |---|---|
-| runner | なし（実行していない） |
-| 1 runner あたりの人数 | 2（spec の `convergence.agents`。実行していない） |
-| 課題 | `dev/evals.json`（T1-typical、T2-default、T3-edge、T4-edge、H1-holdout） |
+| runner | `claude`（STEP-03 の表の「片方だけ起動できる」の行。`claude --version` は [observed version redacted] で終了コード0、`codex` は PATH に無く終了コード127） |
+| 1 runner あたりの人数 | 2（spec の `convergence.agents`） |
+| 課題 | `dev/evals.json`（T1-typical、T2-default、T3-edge、H1-holdout） |
 | 合格基準 | status が全員、課題の expect_status と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェント（失格）がいない。files・structure・names が基準以上。最後のラウンドのレビューの検出率が全見本で 1.0。V1〜V7 の未対処が0件 |
+| 実行 | 実行していない。skill-foundation の入力 `measure` が `skip` だったため（STEP-02）。`convergence.py prepare --round 1 --runners claude` は実行し、3課題の setup（`git apply --index .fixture/<パッチ>`）が通ることだけを確かめた |
 
 ## ラウンドの一覧
 
 | ラウンド | 課題 | status | files | structure | names | content | check | 失格 | V1〜V7 の未対処 |
 |---|---|---|---|---|---|---|---|---|---|
-| なし | | | | | | | | | |
+| なし | 実行していない | | | | | | | | |
 
 ## レビューの検出率（最後のラウンド）
 
 | 見本 | 決定 | 検出率 | 余計な指摘 | 一致 |
 |---|---|---|---|---|
-| 測っていない（`IN-02-r1`、`STEP-03-r1` は `dev/probes.json` にある） | | | | |
+| なし（実行していない。見本は `dev/probes.json` の STEP-02-r1、OUT-05-r1、OUT-09-r1） | | | | |
 
 ## 結論
 
-収束テストは実行していない。理由: 利用者が収束テストを省くと指定した（入力 `measure: skip`。spec の `convergence.skip_reason`）。決定を機械で守らせる仕組みは `probe.py`（違反例 14 件、レビューの見本 2 件、標準の確認と配線）で確かめた。
+収束テストは実行していない。利用者が収束テストを省くと指定した（`measure: skip`）ため、spec の `convergence.skip_reason` に理由を書いた。機械で守らせる決定は `probe.py` の違反例 13 件と標準の確認で確かめた。段 review の決定（STEP-02、OUT-05、OUT-09 の関数とクラスの名前）は、レビューの検出率を測っていない。
```

#### `.claude/skills/write-changelog-entry/dev/evals.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.claude/skills/write-changelog-entry/dev/evals.json
+++ subagent-2/.claude/skills/write-changelog-entry/dev/evals.json
@@ -3,65 +3,33 @@
     {
       "id": "T1-typical",
       "kind": "typical",
-      "prompt": "ステージした変更で CHANGELOG のエントリを作って",
+      "prompt": "変更履歴（CHANGELOG.md）に足す1節を、ステージ済みの差分から日本語で書いて",
       "fixture": "dev/fixtures/basic",
-      "setup": [
-        "printf 'def add(a, b):\\n    return a + b\\n\\n\\ndef div(a, b):\\n    return a / b\\n' > src/calc.py",
-        "printf 'def table(rows):\\n    return [f\"{a} | {b}\" for a, b in rows]\\n' > src/report.py",
-        "git add -A"
-      ],
+      "setup": ["git apply --index .fixture/basic.patch"],
       "expect_status": "done"
     },
     {
       "id": "T2-default",
       "kind": "default",
-      "prompt": "この変更を変更履歴に追記する文面を考えて",
+      "prompt": "git add した変更を CHANGELOG に載せたいので、その分の項目を書いておいて",
       "fixture": "dev/fixtures/basic",
-      "setup": [
-        "printf '# calc\\n\\n小さな計算機。足し算と割り算ができる。\\n' > README.md",
-        "printf 'tmp\\n' > notes.txt",
-        "git add README.md"
-      ],
+      "setup": ["git apply --index .fixture/basic.patch"],
       "expect_status": "done"
     },
     {
       "id": "T3-edge",
       "kind": "edge",
-      "prompt": "変更履歴（CHANGELOG.md）に足す1節を、ステージ済みの差分から書いて。1.1.0 として出す予定",
+      "prompt": "ステージした変更の CHANGELOG エントリを書いて",
       "fixture": "dev/fixtures/basic",
-      "setup": [
-        "mkdir -p docs tests",
-        "for f in install usage faq; do printf '# %s\\n' $f > docs/$f.md; done",
-        "printf 'from src.calc import add\\n\\n\\ndef test_add():\\n    assert add(1, 2) == 3\\n' > tests/test_calc.py",
-        "printf 'from src.calc import div\\n\\n\\ndef test_div():\\n    assert div(6, 3) == 2\\n' > tests/test_div.py",
-        "printf 'def add(a, b):\\n    return a + b\\n\\n\\ndef div(a, b):\\n    return a / b\\n' > src/calc.py",
-        "printf 'def table(rows):\\n    return [f\"{a} | {b}\" for a, b in rows]\\n' > src/report.py",
-        "printf 'x = 1\\n' > src/config.py",
-        "printf '# calc\\n\\n小さな計算機。\\n\\n使い方は docs/usage.md を読む。\\n' > README.md",
-        "git add -A"
-      ],
-      "expect_status": "done"
-    },
-    {
-      "id": "T4-edge",
-      "kind": "edge",
-      "prompt": "CHANGELOG.md に何を足せばいいか、差分から書き出して",
-      "fixture": "dev/fixtures/basic",
-      "setup": [
-        "printf '# calc\\n\\nまだステージしていない変更。\\n' > README.md"
-      ],
+      "setup": ["git apply --index .fixture/tests-only.patch"],
       "expect_status": "aborted"
```


## T3-edge

### 実行の状態（期待: done）

- subagent-1: done
- subagent-2: done

### 新しく作った名前（names。先頭 40 件）

- subagent-1: `API`, `Apple`, `CLOSERS`, `CTL-02-builtin-hooks-codex`, `ESLint`, `Exception`, `FIXME`, `Flavored`, `GENERAL`, `Git`, `Git-155`, `HACK`, `IN-02-a`, `Include`, `LABELS`, `MARKDOWN`, `MARKDOWN_EXT`, `NAME`, `NUL`, `Namespace`, `OUT-04-b`, `OUT_REL`, `ROW`, `Ruff`, `STATE_REL`, `STEP-01-a`, `Spec`, `TABLE_HEAD`, `TABLE_RULE`, `TAG`, `TD006`, `TITLE`, `TODOS`, `Tables`, `Terms`, `Unicode`, `XXX`, `admitted`, `alice`, `analyze-todo-comment`
- subagent-2: `Apple`, `CLOSERS`, `COUNT`, `CTL-02-builtin-hooks-codex`, `Codetags`, `Command`, `Comments`, `EMPTY`, `Exception`, `FIXME`, `Flavored`, `Git`, `Git-155`, `Google`, `Guide`, `HACK`, `IN-02-a`, `Include`, `Informal`, `JavaScript`, `Language`, `Last`, `Lexical`, `Lexical_grammar`, `MARKER`, `MDN`, `Math`, `NUL`, `OUT-03-b`, `PEP`, `PostgreSQL`, `ROW`, `Recognition`, `Reference`, `Rejected`, `SKIP_PREFIXES`, `SQL`, `STAR`, `STEP-01-a`, `STEP-01-b`

### 一部のエージェントだけが作った・変えたファイル

- `.agents/skills/analyze-todo-comment/dev/fixtures/basic/.github/workflows/ci.yml`: subagent-1
- `.agents/skills/analyze-todo-comment/dev/fixtures/basic/.gitignore`: subagent-2
- `.agents/skills/analyze-todo-comment/dev/fixtures/basic/build/gen.py`: subagent-2
- `.agents/skills/analyze-todo-comment/dev/fixtures/basic/docs/logo.png`: subagent-1
- `.agents/skills/analyze-todo-comment/dev/fixtures/basic/src/page.html`: subagent-2
- `.agents/skills/analyze-todo-comment/dev/fixtures/basic/src/util.js`: subagent-2
- `.agents/skills/analyze-todo-comment/dev/fixtures/basic/src/util.py`: subagent-1
- `.agents/skills/analyze-todo-comment/dev/fixtures/basic/src/web/index.js`: subagent-1
- `.agents/skills/analyze-todo-comment/scripts/collect_todo.py`: subagent-1
- `.agents/skills/analyze-todo-comment/scripts/todo_comment.py`: subagent-2

### 中身の違い（抜粋）

#### `.agents/skills/analyze-todo-comment/SKILL.md`（subagent-1 と subagent-2）

```diff
--- subagent-1/.agents/skills/analyze-todo-comment/SKILL.md
+++ subagent-2/.agents/skills/analyze-todo-comment/SKILL.md
@@ -1,12 +1,12 @@
 ---
 name: analyze-todo-comment
-description: "プロジェクトのソースコードから TODO コメントを集め、ファイルのパスと行番号の付いた一覧の Markdown を1つ書く。「ソースコードの TODO コメントを一覧の Markdown にして」、「このリポジトリに残っている TODO を洗い出して」、「src の下の TODO コメントを一覧にまとめて」、「TODO がどこに何件あるか Markdown で出して」、「list all TODO comments in this repo as markdown」と頼まれたときに使う。TODO コメントに書かれた作業を実装して解消するには使わない（代わりに通常のコードの修正の依頼を使う）。TODO を課題管理のチケットとして登録するには使わない（代わりに課題管理のツールを使う）。"
+description: "リポジトリのソースコードから TODO コメントを集め、ファイルと行番号を付けた Markdown の一覧を1つ書く。「ソースコードの TODO コメントを一覧の Markdown にして」、「このリポジトリに残っている TODO を全部洗い出して」、「TODO コメントの一覧を作ってください」、「src の下の TODO をファイルごとにまとめて」、「コードの中の TODO を Markdown の表にして」、「list all TODO comments in this repo」と頼まれたときに使う。TODO コメントの箇所のコードを直す、TODO を消すには使わない（代わりにコードを直接直す（fix の種類のスキル）を使う）。TODO を課題管理ツールのチケットに登録するには使わない（代わりに課題管理ツールの操作を使う）。"
 ---
 
 # ソースコードの TODO コメントを一覧にする
 
 <!-- BEGIN GENERATED:purpose -->
-プロジェクトのソースコードから TODO コメントを集め、ファイルのパスと行番号の付いた一覧の Markdown を1つ書く
+リポジトリのソースコードから TODO コメントを集め、ファイルと行番号を付けた Markdown の一覧を1つ書く
 <!-- END GENERATED:purpose -->
 
 ## 1. 使う場面
@@ -15,15 +15,16 @@
 次のような依頼で使う。
 
 - 「ソースコードの TODO コメントを一覧の Markdown にして」
-- 「このリポジトリに残っている TODO を洗い出して」
-- 「src の下の TODO コメントを一覧にまとめて」
-- 「TODO がどこに何件あるか Markdown で出して」
-- 「list all TODO comments in this repo as markdown」
+- 「このリポジトリに残っている TODO を全部洗い出して」
+- 「TODO コメントの一覧を作ってください」
+- 「src の下の TODO をファイルごとにまとめて」
+- 「コードの中の TODO を Markdown の表にして」
+- 「list all TODO comments in this repo」
 
 次の場合は使わない。
 
-- TODO コメントに書かれた作業を実装して解消する → 代わりに: 通常のコードの修正の依頼
-- TODO を課題管理のチケットとして登録する → 代わりに: 課題管理のツール
+- TODO コメントの箇所のコードを直す、TODO を消す → 代わりに: コードを直接直す（fix の種類のスキル）
+- TODO を課題管理ツールのチケットに登録する → 代わりに: 課題管理ツールの操作
 
 依頼の内容から自動で選ばれる。明示して呼ぶときは Codex では `$analyze-todo-comment` と書く。
 <!-- END GENERATED:triggers -->
@@ -32,11 +33,11 @@
 
 このファイルがあるディレクトリを `<skill>` と呼ぶ。スクリプトは Python 3.9 以上の標準ライブラリだけで動く。手順は番号の順に行い、飛ばさない。
 
-1. 依頼から「3. 入力」の項目を読み取る。依頼に調べる場所（ディレクトリかファイル）があれば、それを `source` にする。2つ以上なら `,` で区切って1つの値にする。「3. 入力」に start の前に聞く項目は無いので、ユーザーに質問せずに次へ進む（CTL-03）
-2. `python3 <skill>/scripts/run.py start --set source=<場所> "<依頼文>"` を実行する。依頼に場所が無ければ `--set` を付けない（既定値 `.` になる）。終了コード3なら、出力された質問をユーザーに聞き、答えを `--set` で渡してやり直す（CTL-01）
-3. 依頼を IN-01 の決定表に当てはめる。`TODO` 以外の印（`FIXME`、`XXX`、`HACK`）を頼まれたとき、別のファイルへの書き込みを頼まれたときは、決定表のとおり `.skill-runs/analyze-todo-comment/notes.md` に「- 」の行を書く（IN-01）
-4. `python3 <skill>/scripts/collect_todo.py write` を実行する。このスクリプトは start の入力 `source` を読み、`.skill-runs/analyze-todo-comment/out/todo-comment.md` に一覧を書く。一覧の形は見本 `assets/examples/todo-comment.md` と同じになる。一覧を手で書いたり書き換えたりしない。`rg`・`grep`・`git grep`・`find` で TODO を探さない（IN-02、STEP-01、STEP-02、STEP-03、OUT-01、OUT-02、OUT-03、OUT-04、OUT-05）。終了コード4なら IN-01、終了コード2なら STEP-04 に従い、出力を書かずに `python3 <skill>/scripts/run.py abort --reason "<スクリプトの出力の1行目>"` を実行し、abort が出力した本文をそのまま返答して終える
-5. `python3 <skill>/scripts/run.py check` を実行する。指摘があれば、出力を手で直さずに `python3 <skill>/scripts/collect_todo.py write` をもう一度実行し、check をやり直す。2回目の check でも指摘が残ったら `python3 <skill>/scripts/run.py abort --reason "check の指摘が消えない"` を実行し、abort が出力した本文をそのまま返答して終える。検査や契約を変えて通さない（STEP-04、CTL-02）
+1. 依頼から「3. 入力」の項目を読み取る。表で「start の前に聞く」とある項目が依頼に無ければ、ここでまとめてユーザーに聞く（CTL-03）
+2. `python3 <skill>/scripts/run.py start --set source=<調べるパス> "<依頼文>"` を実行する。依頼に調べるパスが無ければ `--set source` を渡さない（既定値 `.`）。終了コード3なら、出力された質問をユーザーに聞き、答えを `--set` で渡してやり直す（CTL-01）
+3. `python3 <skill>/scripts/todo_comment.py write --source <start が出した source の値> --out .skill-runs/analyze-todo-comment/out/todo-comment.md` を実行する。終了コード4なら IN-01、終了コード2なら STEP-04 に従って中断する。TODO を `grep`・`rg`・`git grep` で探したり、ソースのファイルを開いたりしない（IN-02、STEP-01、STEP-02、STEP-03）
+4. 書かれた一覧が、見本 `assets/examples/todo-comment.md` と同じ形（見出し、根拠の3行、表）であることを確かめる。一覧に行を足す、行を消す、内容を書き換える、並べ替える、要約を書き足すことをしない（OUT-01、OUT-02、OUT-03、OUT-04、STEP-01）
+5. `python3 <skill>/scripts/run.py check` を実行する。指摘があれば、一覧を手で直さず、手順3の `todo_comment.py write` を同じ引数でやり直してから check を実行する。検査や契約を変えて通さない（STEP-04、CTL-02）
 6. 決めきれなかったことがあれば `.skill-runs/analyze-todo-comment/notes.md` に「- 」の箇条書きで書き、`python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら手順5に戻る。終了コード0なら、出力された本文をそのまま返答する（RPT-01）
 
 ## 3. 入力
@@ -44,7 +45,7 @@
 <!-- BEGIN GENERATED:inputs -->
 | 項目 | キー | 受け付ける書き方 | 無いとき |
```

#### `.agents/skills/analyze-todo-comment/assets/contract.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.agents/skills/analyze-todo-comment/assets/contract.json
+++ subagent-2/.agents/skills/analyze-todo-comment/assets/contract.json
@@ -9,21 +9,18 @@
   "inputs": [
     {
       "key": "source",
-      "label": "調べる場所",
+      "label": "調べる範囲",
       "impact": "reversible",
-      "type": "string",
+      "type": "path",
       "aliases": [
-        "調べるデータ",
+        "範囲",
         "対象",
-        "範囲",
-        "場所",
         "ディレクトリ",
-        "フォルダ",
+        "パス",
         "path",
-        "paths",
         "dir",
         "directory",
-        "target"
+        "scope"
       ],
       "default": "."
     }
@@ -41,25 +38,70 @@
       "checks": [
         {
           "rule": "OUT-02",
+          "type": "require",
+          "lines": [
+            1
+          ],
+          "pattern": "^# TODO コメントの一覧$",
+          "message": "1行目は「# TODO コメントの一覧」"
+        },
+        {
+          "rule": "OUT-02",
+          "type": "forbid",
+          "lines": [
+            2,
+            6
+          ],
+          "pattern": "\\S",
+          "message": "2行目と6行目は空行"
+        },
+        {
+          "rule": "OUT-02",
+          "type": "require",
+          "lines": [
+            3
+          ],
+          "pattern": "^- 対象: ",
+          "message": "3行目は「- 対象: 」で始める"
+        },
+        {
```

#### `.agents/skills/analyze-todo-comment/assets/examples/todo-comment.md`（subagent-1 と subagent-2）

```diff
--- subagent-1/.agents/skills/analyze-todo-comment/assets/examples/todo-comment.md
+++ subagent-2/.agents/skills/analyze-todo-comment/assets/examples/todo-comment.md
@@ -1,14 +1,13 @@
 # TODO コメントの一覧
 
 - 対象: `.`
-- 調べたファイル: 5 件（テキストとして読めなかったファイル: 1 件）
-- TODO コメント: 5 件
-- 集めたコマンド: `python3 .agents/skills/analyze-todo-comment/scripts/collect_todo.py write --source .`
+- 件数: 5 件（3 ファイル）
+- 数えたコマンド: `python3 .agents/skills/analyze-todo-comment/scripts/todo_comment.py scan --source .`
 
-| 場所 | コメント |
-|---|---|
-| `README.md:5` | TODO: 使い方を書く |
-| `src/app.py:3` | TODO: 入力の検査を足す |
-| `src/app.py:4` | todo(alice): 結果の書式を決める |
-| `src/util.py:3` | TODO(bob): 0 のときに a \| b のどちらを返すかを決める |
-| `src/web/index.js:1` | TODO: 古い API を消す |
+| ファイル | 行 | 内容 |
+|---|---:|---|
+| `src/app.py` | 5 | TODO: 引数の検査を足す |
+| `src/app.py` | 7 | TODO(alice): 挨拶の文を設定から読む |
+| `src/page.html` | 4 | TODO: 目次を足す |
+| `src/util.js` | 1 | TODO: 丸めの桁を引数にする |
+| `src/util.js` | 4 | TODO: a \| b の両方を受ける |
```

#### `.agents/skills/analyze-todo-comment/assets/seal.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.agents/skills/analyze-todo-comment/assets/seal.json
+++ subagent-2/.agents/skills/analyze-todo-comment/assets/seal.json
@@ -1,14 +1,14 @@
 {
   "runtime": "1.0.0",
   "files": {
-    "SKILL.md": "bb2ec79cf544b8c7a97ad6a1a9fa62b739f84b2f10a8f1e9b9207bf3a1b366f0",
-    "assets/contract.json": "f0cc036da961ab349287de63fda2ab774fe02c1818c48b35b8b7bd6b429f5c2b",
-    "assets/examples/todo-comment.md": "39a97d935d3d9fb82c6fec31b2b0e191f25cdea1a4be1ccae54db9547f45e476",
-    "references/decisions.md": "c3807f4d14fcd904f5c3e6438362c7f1dccc0ab28ecf7a3304b8c16704da3a5b",
+    "SKILL.md": "02390388eebf314ea802e4633e484eb55fb00a6f9885237250eaaaeb0476adcd",
+    "assets/contract.json": "cb886e47a7950d7b571dc539e97d2771e395f07f990103f3c14f76dbb0258554",
+    "assets/examples/todo-comment.md": "cd5cd0c06bb25fc3cb86009ca18fa3f47cda0f8dce151b18875b75b160a79956",
+    "references/decisions.md": "54d91cfc323c6cc0470bdb4358ecb7b856dc523ce4c54601beaea4036538511a",
     "scripts/run.py": "fcced04ce88880bbe860dadc1d25481c464f13d733de4d4c7d9c5ccbde096b76",
     "scripts/_skillrt.py": "b76eceeda4fdcad10a4246a66a7d137d2400cec49cc62d95ec89fd463b784304",
     "scripts/hook.py": "b0ccd614d242fcbbd2499da75d759b33b4cb8f7c7357563954570f15c3a7ef55",
     "scripts/install.py": "286effaa9680fd4f8a03816b37252e36b62172301ef9d64c8debd4646d91ea19",
-    "scripts/collect_todo.py": "6796ffbdae30a30d504dc90973383621fcea828e91043b8368e1df30dc1b2db7"
+    "scripts/todo_comment.py": "699879380f6a95065e86cc36f840e6a14d536a88055e95eefd66b87745183229"
   }
 }
```

#### `.agents/skills/analyze-todo-comment/dev/convergence-report.md`（subagent-1 と subagent-2）

```diff
--- subagent-1/.agents/skills/analyze-todo-comment/dev/convergence-report.md
+++ subagent-2/.agents/skills/analyze-todo-comment/dev/convergence-report.md
@@ -6,17 +6,16 @@
 
 | 項目 | 値 |
 |---|---|
-| runner | なし（実行していない） |
+| runner | なし。skill-foundation の入力 `measure` が `skip` で、STEP-02 の表の「skip」の行に当たったため実行していない |
 | 1 runner あたりの人数 | なし |
-| 課題 | `dev/evals.json`（T1-typical、T2-default、T3-edge、H1-holdout） |
+| 課題 | `dev/evals.json`（T1-typical、T2-default、T3-edge、H1-holdout。実行していない） |
 | 合格基準 | status が全員、課題の expect_status と同じ。check が全員通過。スキル自身や hooks の登録を変えたエージェント（失格）がいない。files・structure・names が基準以上。V1〜V7 の未対処が0件 |
-| 実行しなかった理由 | 利用者が収束テストを省くと指定した（依頼の「収束テスト: しない」。spec の `convergence.skip_reason`） |
 
 ## ラウンドの一覧
 
 | ラウンド | 課題 | status | files | structure | names | content | check | 失格 | V1〜V7 の未対処 |
 |---|---|---|---|---|---|---|---|---|---|
-| なし | なし | | | | | | | | |
+| なし | なし | なし | なし | なし | なし | なし | なし | なし | なし |
 
 ## レビューの検出率（最後のラウンド）
 
@@ -26,4 +25,4 @@
 
 ## 結論
 
-収束テストは実行していないので、合格基準を満たしたかは確かめていない。決定を機械で守らせる仕組みは、`probe.py` の違反例 9 件と標準の確認・配線ですべて成功している（`dev/results/probe-results.json`）。
+収束テストは実行していない。spec の `convergence.skip_reason` は「利用者が収束テストを省くと指定した」である。決定を機械で守らせる仕組みは `probe.py` の違反例 9 件と標準の確認・配線で確かめたが、別の AI が同じ依頼から同じ一覧を作るかは測っていない。
```

#### `.agents/skills/analyze-todo-comment/dev/evals.json`（subagent-1 と subagent-2）

```diff
--- subagent-1/.agents/skills/analyze-todo-comment/dev/evals.json
+++ subagent-2/.agents/skills/analyze-todo-comment/dev/evals.json
@@ -3,41 +3,37 @@
     {
       "id": "T1-typical",
       "kind": "typical",
-      "prompt": "このリポジトリのソースコードの TODO コメントを一覧の Markdown にして",
+      "prompt": "このリポジトリに残っている TODO コメントを全部洗い出して、Markdown の一覧にして",
       "fixture": "dev/fixtures/basic",
-      "setup": [],
-      "expect_status": "done"
+      "setup": []
     },
     {
       "id": "T2-default",
       "kind": "default",
-      "prompt": "TODO を洗い出して",
+      "prompt": "TODO コメントの一覧を作ってください",
       "fixture": "dev/fixtures/basic",
-      "setup": [],
-      "expect_status": "done"
+      "setup": []
     },
     {
       "id": "T3-edge",
       "kind": "edge",
-      "prompt": "lib ディレクトリの TODO コメントを Markdown の一覧にまとめて",
+      "prompt": "docs の下にある TODO コメントを一覧の Markdown にして",
       "fixture": "dev/fixtures/basic",
       "setup": [
-        "mkdir -p lib",
-        "printf 'x = 1\\n' > lib/config.py"
+        "mkdir -p docs",
+        "printf '# 使い方\\n\\nsrc/app.py を実行する。\\n' > docs/guide.md"
       ],
       "expect_status": "done"
     },
     {
       "id": "H1-holdout",
       "kind": "holdout",
-      "prompt": "list all TODO comments under web and tests as markdown",
+      "prompt": "db ディレクトリの SQL に残ってる TODO を表にまとめてほしい",
       "fixture": "dev/fixtures/basic",
       "setup": [
-        "mkdir -p web/src tests",
-        "printf '// TODO: ルーティングを足す\\nexport const x = 1;\\n' > web/src/main.ts",
-        "printf 'def test_div():\\n    # TODO: 0 で割る場合を試す\\n    assert True\\n' > tests/test_util.py"
-      ],
-      "expect_status": "done"
+        "mkdir -p db",
+        "printf -- '-- TODO: 索引を足す\\nCREATE TABLE users (id int);\\n/*\\n * TODO: 外部キーを足す\\n */\\n' > db/schema.sql"
+      ]
     }
   ]
 }
```


## H1-holdout

### 実行の状態（期待: unused）

- subagent-1: unused
- subagent-2: unused

### 新しく作った名前（names。先頭 40 件）

- subagent-1: なし
- subagent-2: なし

### 一部のエージェントだけが作った・変えたファイル

なし

### 中身の違い（抜粋）

なし
