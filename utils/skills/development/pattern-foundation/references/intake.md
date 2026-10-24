# 受付：指示を分解して manifest にする

フェーズ0で読む。目的は、以降のフェーズ・スクリプト・生成するスキルがすべて同じ前提を参照できるよう、指示を1つの機械可読なファイル（`.foundation/manifest.json`）に固定することである。あわせて [domain-profiles.md](domain-profiles.md) の該当する分野の節を読む。分野名、基盤名の語尾、聞くべき事項の例がそこにあるからである。

## 1. 指示から抜き出すもの

| 項目 | manifest のキー | 決め方 |
|---|---|---|
| 基盤名（ディレクトリ名） | `name` | 指示にあればそれ。無ければ2章の命名規則 |
| 状態 | `status` | `building`。フェーズ5の終わりに `ready` にする |
| モード | `mode` | 対象ディレクトリが無い・空 → `new`。既存コードがある → `retrofit` |
| 分野 | `domain`（配列） | [domain-profiles.md](domain-profiles.md) の見出しから最も近いもの。1つでも配列で書く（例：`["frontend"]`、フルスタックなら `["frontend", "backend"]`） |
| 主な技術 | `stack[]` | `version` はフェーズ2で確かめてから埋める（それまでは空文字）。指示で名指しされた技術は `"pinned": true`。名指しされた技術を動かすのに欠かせない部品（DB のアダプタ、ルーターのビルドプラグインなど）は、フェーズ2で `"pinned": false` で追記する。それ以外の周辺ライブラリは足さない |
| 道具 | `tools[]` | 役割ごとに1要素。`role` は `runtime`、`package-manager`、`formatter`、`linter`、`typecheck`、`test`、`structure`、`build`、`other` のどれか。言語が複数なら、同じ役割を言語ごとに別の要素にして `language` で分ける。名指しされたものは `"pinned": true` |
| 生成するスキル名 | `skills.impl`、`skills.review` | 指示にあればそれを使う。無ければ `impl`、`review` |
| 文書の言語 | `language` | ユーザーとの会話の言語 |
| コマンド | `commands.check`、`commands.fix` | 3章の表で決める。フェーズ4で中身を作る |
| 保護するファイル | `protected[]` | 検査の設定ファイル、依存の一覧ファイルと lockfile、check を定義するファイル（`Makefile` など。Node.js では package.json が兼ねる）、構造検査スクリプト、`.claude/settings.json`、`.foundation/**`、`docs/design/rules.md`、`docs/design/enforcement-matrix.md` |
| 抑止コメントの禁止パターン | `guard.suppressions[]` | フェーズ2で使うツールの抑止記法を調べ、`{"pattern", "rule"}` の形で入れる。`rule` はフェーズ3でルールIDが決まってから埋める（それまでは空文字） |
| コピーの扱い | `copy.link_dirs[]`、`copy.skip_dirs[]` | 依存のディレクトリ（コピーせずリンクする）と、ビルド成果物（コピーしない）。主なものは既定で入っているので、既定に無いものだけ書く。名前だけを書くとどの深さでも、`/` で始めるとルートからのパスだけに一致する（例：`/out`） |
| 収束テストの設定 | `convergence` | 例の値のまま。`runner` の `--allowedTools` は3章の表で埋める（[convergence-test.md](convergence-test.md)） |

書式は [../assets/templates/manifest.example.json](../assets/templates/manifest.example.json) を写し、`<…>` をすべて実際の値に置き換える。空文字の値（`version`、`guard.suppressions` の `rule`）は後のフェーズで埋める。埋め忘れは `rules_check.py` が検出する（rule はフェーズ4、version は `--final`）。キーの名前を変えない。スクリプトがキー名で読むためである。使わない役割の `tools` 要素は消してよい。

## 2. 基盤名の命名規則

同じ指示からは同じ名前になるように、次の手順で機械的に決める。

1. 指示に出てきた順に、名指しされた技術を並べる
2. 各技術を、指示に書かれた表記（読み替えた場合は公式の名前）を小文字にしてから、次の規則の最初に当たる1つで短い名前にする
   - スコープ付き（`@tanstack/react-router`）→ スコープ名（`tanstack`）
   - ハイフンかドットで区切られている（`tanstack-router`、`dbt-core`、`next.js`）→ 先頭の語（`tanstack`、`dbt`、`next`）
   - それ以外 → そのまま（`react`、`zustand`）
3. 同じ短い名前が2回以上出たら、最初の1つだけを残す（`tanstack-router` と `tanstack-query` → `tanstack`）
4. 先頭から2つを取り、[domain-profiles.md](domain-profiles.md) の分野の語尾を付ける（例：`react-tanstack-web`、`dbt-duckdb-data`、`go-chi-api`）
5. 指示が技術を1つしか名指ししていなければ、`<技術>-<語尾>` にする

## 3. コマンドと runner の決め方

| 生態系 | `commands.check` / `commands.fix` | runner の `--allowedTools` に足すもの |
|---|---|---|
| Node.js（npm、pnpm、yarn） | package.json の scripts の `check` / `fix`（例：`npm run check`） | `Bash(npm run *)`、`Bash(npx *)`（パッケージマネージャに合わせて置き換える） |
| 上記以外（Python、Go、Rust、Terraform、dbt など） | `Makefile` の `check` / `fix` ターゲット（`make check`、`make fix`） | `Bash(make *)` と、ファイル単位の検査を起動する手段（`Bash(uv run *)`、`Bash(go *)`、`Bash(cargo *)` など） |

どの生態系でも `Skill`、`Bash(git diff *)`、`Bash(git status *)` は入れる。タスクの実行手段を1つに決めるのは、作者が検査の呼び方を迷わないようにするためである。

## 4. 指示に無い事項をどう決めるか

指示に無い事項は、次の2種類に分けて扱う。分けるのは、何でも聞くとユーザーの負担が大きく、何でも勝手に決めると取り返しのつかない選択を誤るからである。

| 種類 | 例 | 扱い |
|---|---|---|
| 後から変えやすい・業界の定番がある | テストランナー、import の並び順、ファイル名のケース、ディレクトリの切り方 | フェーズ2の調査で公式の推奨に従って決め、ADR に理由を書く。聞かない |
| 後から変えにくい・費用やデータに響く・指示と衝突する | 実行環境、DB やクラウドの種類、ライセンス、課金が発生するサービス、指示されたツールが廃止済み。分野ごとの例は domain-profiles.md の「聞くべき事項」 | ユーザーに聞く。聞けない状況なら、保守的な既定値（公式の推奨、無料、可逆、依存が少ないもの）で決め、最終報告の「判断してほしいこと」に載せる |

**指示の語が2通り以上に読める場合**（例：「Python 部分は ruff」が、変換処理を Python で書くことを指すのか、補助スクリプトだけを指すのか）は、どちらを選ぶかで構造が変わるなら「後から変えにくい」に分類する。聞けない状況では、作るものが少ない方の読み方を既定にして ADR に書く。

推測で決めた値は、後から辿れるように必ず ADR か最終報告に「既定値で決めた」と明記する。

## 5. モードの判定と retrofit の追加作業

`retrofit` の場合は、フェーズ2の前に既存コードの実態を測る。

1. 言語・フレームワーク・既存の検査ツールとその設定を一覧にする
2. [variance-axes.md](variance-axes.md) の軸ごとに、既存コードでの書き方の分布を数える（例：default export と named export の件数、ファイル名ケースの内訳）。数えられるものは grep やスクリプトで数え、目視で済ませない
3. 結果を `docs/design/research.md` の「現状」節に書く。フェーズ3では、この分布の多数派を初期値にする

書き換えは、指示された範囲とユーザーの承認の範囲に限る。

## 6. 完了条件

- manifest に `<…>` が残っていない（`init_foundation.py` が name、status、mode、stack、tools の形を検査する）
- 指定された技術・ツールに `"pinned": true` が付いている
- 聞くべき事項を聞いたか、既定値で決めた理由を記録した
