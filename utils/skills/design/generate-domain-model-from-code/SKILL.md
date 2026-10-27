---
name: generate-domain-model-from-code
description: "ローカルリポジトリのコードを調査し、根拠付きの業務概念と関係からMermaid原本・PNG・HTMLカタログを生成する。「コードからドメインモデル図を作成するスキルを使って」、「このリポジトリの業務概念と関係を図にして」、「コードからMermaidのドメインモデルを作って」、「ドメインモデルをPNGにしてHTMLカタログで見たい」、「実装の根拠を辿れる業務モデル図を生成してください」と頼まれたときに使う。DBテーブルと外部キーだけをER図にするには使わない（代わりにarchify-jpのer図を使う）。コードを読まずに構想中のモデルを描くには使わない（代わりにarchify-jpのclass図を使う）。"
---

# コードから根拠付きのドメインモデル図を作る

<!-- BEGIN GENERATED:purpose -->
ローカルリポジトリのコードを調査し、根拠付きの業務概念と関係からMermaid原本・PNG・HTMLカタログを生成する
<!-- END GENERATED:purpose -->

## 1. 使う場面

<!-- BEGIN GENERATED:triggers -->
次のような依頼で使う。

- 「コードからドメインモデル図を作成するスキルを使って」
- 「このリポジトリの業務概念と関係を図にして」
- 「コードからMermaidのドメインモデルを作って」
- 「ドメインモデルをPNGにしてHTMLカタログで見たい」
- 「実装の根拠を辿れる業務モデル図を生成してください」

次の場合は使わない。

- DBテーブルと外部キーだけをER図にする → 代わりに: archify-jpのer図
- コードを読まずに構想中のモデルを描く → 代わりに: archify-jpのclass図

依頼の内容から自動で選ばれる。明示して呼ぶときは Claude Code では `/generate-domain-model-from-code`、Codex では `$generate-domain-model-from-code` と書く。
<!-- END GENERATED:triggers -->

## 2. 手順

このファイルのディレクトリを `<skill>` と呼ぶ。モデル情報の形と判断の基準は [references/model-format.md](references/model-format.md) にある。

1. CTL-03・IN-01・OUT-05：依頼の対象コードと調査範囲を確認する。入力にない値は「3. 入力」の既定値を使う。同名の出力が存在すればstartの前に別のnameを聞く。
2. CTL-01・STEP-01：`python3 <skill>/scripts/run.py start --set repo=<対象> --set name=<名前> --set scope=<範囲> "<依頼文>"` を実行する。以降、出力は `.skill-runs/generate-domain-model-from-code/out/<名前>/` に作る。
3. IN-02：`python3 <skill>/scripts/catalog.py inspect --state .skill-runs/generate-domain-model-from-code/state.json` を実行する。列挙されたコードとREADME・AGENTS.mdを読み、未読範囲を記録する。対象コードが0件なら理由を示してabortする。
4. OUT-02・OUT-03・OUT-08：`assets/examples/model.json` を形の見本とし、調査したコードに基づくmodel.jsonを出力ディレクトリへ書く。概念・属性・関係の根拠を記録し、断定できない分類と多重度を確認事項へ残す。
5. STEP-02・STEP-03・STEP-04・STEP-05・OUT-04：`python3 <skill>/scripts/catalog.py build --state .skill-runs/generate-domain-model-from-code/state.json` を実行する。同じ実行内でモデルを修正した場合だけ --replace を付ける。変換失敗時はエラーを示してabortする。古い画像を成功の根拠にしない。
6. OUT-01・OUT-06・OUT-07・STEP-06：`python3 <skill>/scripts/run.py check` を実行する。PNGとHTMLを開き、日本語、関係、読みやすさ、検索、領域選択、拡大、Mermaid原本取得を確認する。未確認の項目は実行記録のnotes.mdへ箇条書きで書く。
7. CTL-01：`python3 <skill>/scripts/run.py finish` を実行する。出力先の指定があれば、検査済みのカタログ全体を指定先へコピーして渡す。最終の返答はfinishの本文をそのまま使う。

## 3. 入力

<!-- BEGIN GENERATED:inputs -->
| 項目 | キー | 受け付ける書き方 | 無いとき |
|---|---|---|---|
| 出力の名前 | `name` | 英小文字・数字・`-` に変換。別名: 名前、catalog | 既定値 `domain-model` |
| 対象リポジトリ | `repo` | パス。別名: repository、リポジトリ | 既定値 `.` |
| 調査範囲 | `scope` | 一覧（`,`・`、`・改行で区切る）。別名: 対象範囲 | 既定値 `["."]` |

入力は `run.py start --set <キー>=<値>` で渡す。キーは表のキー・項目名・別名のどれでもよく、全角と半角、大文字と小文字、`-`・`_`・空白の違いは吸収される。契約に無いキーは無視して記録する。依頼文そのものは最後の引数に渡す。依頼文の中の「キー: 値」の行も読む。
<!-- END GENERATED:inputs -->

## 4. 決定表

<!-- BEGIN GENERATED:decisions -->
| ID | 決定 | 守らせ方 |
|---|---|---|
| IN-01 | コードが読めない、対象ファイルが0件、概念が0件のいずれかなら理由を示して中断する。構想図だけの依頼はarchify-jpへ案内する。 | doc: references/model-format.md |
| IN-02 | catalog.py inspectが列挙したファイルとルートのREADME・AGENTS.mdを読む。依存パッケージ・生成物・symlinkは除外する。未読のコードはunreadにパスと理由を書く。 | doc: references/model-format.md |
| STEP-01 | 受付、start、inspect、コードの読解、model.jsonの作成、build、check、画像とHTMLの確認、finishの順に進める。 | doc: references/model-format.md |
| STEP-02 | 全概念を置いたoverviewを1つ作り、領域が2つ以上なら領域別の図も作る。領域は概念の宣言元ファイルの親ディレクトリとする。領域を跨ぐ関係は両端の概念を図へ残す。 | validate, script: scripts/catalog.py のverifyが図の集合とMermaidを再計算する。 |
| STEP-03 | AIはmodel.jsonを作る。Mermaid、PNG、HTML、manifest.jsonはcatalog.py buildで生成し、手で書き換えない。 | validate, script: scripts/catalog.py のverifyがMermaidとHTMLを再生成して比較する。 |
| STEP-04 | Python 3.9以上、git、インストール済みMermaid CLIとブラウザーを使う。MMDCでCLI、PUPPETEER_EXECUTABLE_PATHでブラウザーを指定する。CLIがなければ中断し、導入が必要と伝える。自動ダウンロードは行わない。 | doc: references/model-format.md |
| STEP-05 | 変換失敗、画像不正、根拠の不一致では中断する。全図の変換と検査の成功後に出力を置き換える。古い画像と仮の画像で成功を代替しない。 | doc: references/model-format.md |
| STEP-06 | checkとfinishでPNGのCRCと圧縮データを検査する。画像とHTMLを開いて文字・関係・検索・絞り込み・拡大・原本取得も確認する。 | validate, script: scripts/catalog.py のverifyがPNGを検査する。 |
| OUT-01 | 出力は実行記録のout/name配下に置く。inventory.json、model.json、index.html、manifest.jsonとdiagrams配下のmmd・pngを保存する。 | validate: 出力契約と scripts/catalog.py のverifyがファイル集合を検査する。 |
| OUT-02 | model.jsonはschema_version・title・domains・concepts・relations・questions・unreadを持つ。references/model-format.mdに従い、型・キー・参照先とコードの行・抜粋を検査する。 | validate, template: assets/examples/model.json と scripts/catalog.py のvalidateが型・キー・参照・抜粋を検査する。 |
| OUT-03 | 説明は日本語で書く。symbolとコードの抜粋は実装の表記を保持する。名称を翻訳してもコード識別子を変えない。 | review: references/model-format.md |
| OUT-04 | 概念の表示名はsymbol、領域の表示名はpath（.はルート）、関係名はコードのmember（継承は継承）に固定する。確認事項は改行区切りの文字列にする。conceptのIDはkeyのSHA-256先頭12桁にC_を付ける。relationのIDはsource・target・kind・固定した関係名のJSON配列のSHA-256先頭12桁にR_を付ける。domainsはpath、conceptsはkey、relationsはIDで並べる。 | validate, script: scripts/catalog.py のnormalizeとverifyがIDと順序を再計算する。 |
| OUT-05 | 受付時に同名の出力があれば別のnameを聞く。buildは既存の生成結果を拒否する。同じ実行内の修正はgenerate-domain-model-from-codeが生成した出力に限り--replaceで再生成する。 | doc: references/model-format.md |
| OUT-06 | コード、model、Mermaid、PNG、HTMLのハッシュをmanifestに記録し、checkとfinishで比較する。コードまたはモデルが変わったらinspectとbuildからやり直す。 | validate, script: scripts/catalog.py のverifyがmanifestと実ファイルを比較する。 |
| OUT-07 | model.jsonのskip_validation、no_verify、ignore_errors、disable_checksを拒否する。許可していないキーを追加して検査を止めない。 | validate: scripts/catalog.py のvalidateが検査を省くキーを拒否する。 |
| OUT-08 | 分類の明示がないクラスはconceptにする。entityはEntity基底型かentity注釈、valueはValueObject基底型かvalue_object注釈、enumは列挙宣言かリテラルの選択型のコードを根拠にする。idという属性名やdataclassのfrozenだけで分類しない。参照メンバー・属性・関係種別・多重度の意味をレビューし、断定できない関係種別はassociation、多重度はnullにする。不明点はquestionsに書く。 | review: references/model-format.md |
| RPT-01 | 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。 | runtime, validate, review: scripts/run.py の finish と abort が本文を組み立て、.skill-runs/<name>/report.md にも保存する。check と finish が notes.md の形を検査する |
| CTL-01 | 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。 | runtime, validate: scripts/run.py。finish は契約の検査に通らないと終了コード1で終わる |
| CTL-02 | `run.py start` から `run.py finish` までの間、スキルの保護ファイル（`SKILL.md`、`scripts/`、`assets/`、`references/`）と、プロジェクトに登録したこのスキルの hooks を変えない。出力が契約に合わないときは、出力の方を直す。保護ファイルが封印（`assets/seal.json`）と違うと `run.py start` が終了コード1で止まるので、そのときは出力された指摘をユーザーに伝えて止まる。 | runtime, validate: scripts/run.py の start が保護ファイルのハッシュと hooks の登録を記録し、check と finish が比べる。`start --restart` は記録を最初の start から引き継ぐ。hooks が編集の前に止める。start は封印と保護ファイルを比べ、違えば始めない |
| CTL-03 | ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。 | runtime, doc: scripts/run.py の start は、聞くべき入力が無いと終了コード3で止まり、質問を出力する。wait は hooks の強制を止める |
| CTL-04 | hooks は、このスキルの実行中（status: active）に、編集の後の検査、応答を終える前の検査、保護ファイルの編集の停止の3つを行う。実行していないときは、封印したスキル（`assets/seal.json` がある）の保護ファイルの編集に、Claude Code で確認を求めることだけを行う。ユーザーの発言を止めたり書き換えたりしない。 | runtime: scripts/hook.py。install.py が Claude Code（.claude/settings.json）と Codex（.codex/hooks.json）に登録する |
| CTL-05 | `run.py start` から `run.py finish` までの間に作る・変えるファイルは、「5. 出力の契約」の出力と `control.allow_changes` に挙げたものだけにする。作業用のメモや一時ファイルも、出力の置き場の外に作らない。 | runtime, validate: scripts/run.py の start が git の作業ツリーの状態を記録し、check と finish が比べる。編集の直後には hooks が知らせる |

理由・良い例・悪い例は [references/decisions.md](references/decisions.md) にある。
<!-- END GENERATED:decisions -->

## 5. 出力の契約

<!-- BEGIN GENERATED:contract -->
| 出力 | 置き場 | 件数 | 検査（ルールID） |
|---|---|---|---|
| model モデル情報 | `{run}/out/{in:name}/model.json` | 1〜1 件（OUT-01） | `^  "(?:skip_validation\|no_verify\|ignore_errors\|disable_checks)":` に一致する行が無い（OUT-07）。`python3 {skill}/scripts/catalog.py verify --state {run}/state.json --only-rule OUT-01` が通る（check・finish・応答を終える前だけ。編集の直後は検査しない）（OUT-01）。`python3 {skill}/scripts/catalog.py verify --state {run}/state.json --only-rule OUT-02` が通る（check・finish・応答を終える前だけ。編集の直後は検査しない）（OUT-02）。`python3 {skill}/scripts/catalog.py verify --state {run}/state.json --only-rule OUT-04` が通る（check・finish・応答を終える前だけ。編集の直後は検査しない）（OUT-04）。`python3 {skill}/scripts/catalog.py verify --state {run}/state.json --only-rule OUT-06` が通る（check・finish・応答を終える前だけ。編集の直後は検査しない）（OUT-06）。`python3 {skill}/scripts/catalog.py verify --state {run}/state.json --only-rule OUT-07` が通る（check・finish・応答を終える前だけ。編集の直後は検査しない）（OUT-07）。`python3 {skill}/scripts/catalog.py verify --state {run}/state.json --only-rule STEP-02` が通る（check・finish・応答を終える前だけ。編集の直後は検査しない）（STEP-02）。`python3 {skill}/scripts/catalog.py verify --state {run}/state.json --only-rule STEP-03` が通る（check・finish・応答を終える前だけ。編集の直後は検査しない）（STEP-03）。`python3 {skill}/scripts/catalog.py verify --state {run}/state.json --only-rule STEP-06` が通る（check・finish・応答を終える前だけ。編集の直後は検査しない）（STEP-06） |
| inventory コードのスナップショット | `{run}/out/{in:name}/inventory.json` | 1〜1 件（OUT-01） | — |
| catalog HTMLカタログ | `{run}/out/{in:name}/index.html` | 1〜1 件（OUT-01） | — |
| manifest 画像と派生物の検証記録 | `{run}/out/{in:name}/manifest.json` | 1〜1 件（OUT-01） | — |
| mermaid Mermaid原本 | `{run}/out/{in:name}/diagrams/*.mmd` | 1〜10000 件（OUT-01） | — |

`{run}` は実行記録の置き場 `.skill-runs/generate-domain-model-from-code` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。

- 保護ファイルが実行中に変わっていない（CTL-02）
- 上の出力と、変えてよいファイル `{run}/out/{in:name}/diagrams/*.png`のほかに、start の後に変わったファイルが無い（CTL-05。git の作業ツリーで判定し、git が無いときは検査しない）
<!-- END GENERATED:contract -->

## 6. 完了前チェックリスト

<!-- BEGIN GENERATED:checklist -->
- [ ] OUT-03 説明は日本語で書く。symbolとコードの抜粋は実装の表記を保持する。名称を翻訳してもコード識別子を変えない。
- [ ] OUT-08 分類の明示がないクラスはconceptにする。entityはEntity基底型かentity注釈、valueはValueObject基底型かvalue_object注釈、enumは列挙宣言かリテラルの選択型のコードを根拠にする。idという属性名やdataclassのfrozenだけで分類しない。参照メンバー・属性・関係種別・多重度の意味をレビューし、断定できない関係種別はassociation、多重度はnullにする。不明点はquestionsに書く。
- [ ] RPT-01 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- [ ] `python3 <skill>/scripts/run.py finish` が終了コード0で終わった
<!-- END GENERATED:checklist -->

## 7. 報告

<!-- BEGIN GENERATED:report -->
最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。決めきれなかったことは、finish の前に `.skill-runs/generate-domain-model-from-code/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを「## 補足」に入れる。中断するときは `run.py abort --reason <理由>` を実行し、abort が出力した本文を同じようにそのまま使う。本文の形は次のとおり。

```text
## 結果

generate-domain-model-from-code: 完了（検証に合格）

## 出力

- `<パス>`（<出力ID> <出力の名前>）

## 既定値で決めた値

- <項目>（<キー>）: <値>（無ければ「- なし」）

## 入力で読めなかった値

- <内容>（無ければ「- なし」）

## 検証

- `run.py finish`: 指摘 0 件

## 補足

- <notes.md の箇条書き。無ければ「- なし」>
```
<!-- END GENERATED:report -->

## 8. 制御の仕組み

<!-- BEGIN GENERATED:control -->
| 仕組み | いつ働くか | 何をするか |
|---|---|---|
| `scripts/run.py start` | 手順の始め | 入力を正規化し（表記ゆれ・全角・未知のキーを受け入れる）、既定値で補い、保護ファイルのハッシュと git の作業ツリーの状態を記録する。保護ファイルが封印（`assets/seal.json`）と違えば始めない（終了コード1） |
| `scripts/run.py check` と `finish` | 出力を書いた後と最後 | 契約（`assets/contract.json`）の format で出力を直してから検査する。finish は通ったときだけ実行を終える |
| hooks の pre-tool | ファイルを編集する前 | 保護ファイルと実行記録の編集を止める（Claude Code は確認を求め、Codex は拒否する）。実行していないときも、封印したスキルの保護ファイルの編集に Claude Code で確認を求める |
| hooks の post-tool | ファイルを編集した後 | 出力に当たるファイルを format で直し、検査し、指摘を返す。出力でも変えてよいファイルでもなければ CTL-05 の指摘を返す |
| hooks の stop | 応答を終える前 | 出力全体を検査し、通るまで応答を終えさせない（最大 3 回。超えると status: failed） |
| hooks の prompt | ユーザーが発言したとき | 質問待ち（wait）を解くだけ。発言を止めたり書き換えたりしない |

hooks は、このスキルの実行中（`.skill-runs/generate-domain-model-from-code/state.json` の status が active）だけ出力を検査する。hooks が無い環境でも、`run.py check` と `finish` が同じ検査をする。

hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（Claude Code は `.claude/settings.json`、Codex は `.codex/hooks.json` に追記する。Codex では、追記した hooks を `/hooks` で信頼するまで動かない）

保護ファイル（スキルのディレクトリからの相対パス）: `SKILL.md`、`scripts/**`、`assets/**`、`references/**`

このスキル（決定、契約、手順、スクリプト）を変えるときは、次の順にする。保護ファイルだけを直接書き換えると、封印と違うため次の `run.py start` が止まる（CTL-02）。`<skill-foundation>` は skill-foundation のディレクトリを指す。

1. 実行中なら `python3 <skill>/scripts/run.py abort --reason <理由>` で止める
2. `dev/spec.json` を直す。手で書く部分（この SKILL.md の「2. 手順」、`scripts/` のスキル固有のスクリプト、`references/`、`assets/examples/`）は直接直す
3. `python3 <skill-foundation>/scripts/render_skill.py --dir <skill>` で生成した部分を作り直す
4. 決定や契約を変えたなら `dev/probes.json` の違反例も合わせ、`python3 <skill-foundation>/scripts/probe.py <skill>` を通す
5. `python3 <skill-foundation>/scripts/skill_lint.py <skill> --final --seal` を通す。通ると封印し直す
<!-- END GENERATED:control -->
