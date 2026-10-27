---
name: generate-domain-model
description: "業務説明・仕様・指定されたコード・classDiagramからMermaid原本とPNGを生成し、HTMLカタログで一覧・検索・拡大する。「業務の概念と関係を表すドメインモデル図を作って」、「仕様からMermaidのドメインモデル図を作って」、「ドメインモデルをPNGとHTMLカタログにして」、「このリポジトリの業務概念を図で整理して」、「複数のclassDiagramをカタログで見たい」と頼まれたときに使う。DBのテーブルと外部キーをER図にするには使わない（代わりにarchify-jpのer図を使う）。ソースコードの全クラスとメソッドを列挙するには使わない（代わりにarchify-jpのclass図を使う）。"
---

# 業務の概念と関係を図とカタログにする

<!-- BEGIN GENERATED:purpose -->
業務説明・仕様・指定されたコード・classDiagramからMermaid原本とPNGを生成し、HTMLカタログで一覧・検索・拡大する
<!-- END GENERATED:purpose -->

## 1. 使う場面

<!-- BEGIN GENERATED:triggers -->
次のような依頼で使う。

- 「業務の概念と関係を表すドメインモデル図を作って」
- 「仕様からMermaidのドメインモデル図を作って」
- 「ドメインモデルをPNGとHTMLカタログにして」
- 「このリポジトリの業務概念を図で整理して」
- 「複数のclassDiagramをカタログで見たい」

次の場合は使わない。

- DBのテーブルと外部キーをER図にする → 代わりに: archify-jpのer図
- ソースコードの全クラスとメソッドを列挙する → 代わりに: archify-jpのclass図

依頼の内容から自動で選ばれる。明示して呼ぶときは Claude Code では `/generate-domain-model`、Codex では `$generate-domain-model` と書く。
<!-- END GENERATED:triggers -->

## 2. 手順

このファイルがあるディレクトリを `<skill>` と呼ぶ。Python 3.9以上の標準ライブラリと、既に導入されたMermaid CLIを使う。

1. 図にする資料を読み取る。資料が無ければstartの前にまとめて聞く。ER図とコードクラスの列挙は案内して終える（CTL-03、IN-01）
2. カタログ名は指定値、指定が無ければ `domain` とし、資料の参照先か依頼文を `source` に渡して `python3 <skill>/scripts/run.py start --set name=<name> --set source=<資料> --set update=<true・false> "<依頼文>"` を実行する。名前は英小文字・数字・ハイフンにする。更新の依頼がある場合だけupdateをtrueにする（CTL-01、OUT-04）
3. `python3 <skill>/scripts/catalog.py inspect domain-models/<name>` で既存IDを読む。指定された資料と定義を読み、図ごとの業務領域・概念・属性・関係と根拠を整理する。材料が足りない関係・多重度は推測せず未確認事項にする（IN-02、OUT-03、OUT-06、STEP-01）
4. `assets/examples/catalog.json` と `assets/examples/sample/diagrams/order.mmd` を見本にし、`domain-models/<name>/catalog.json` と `diagrams/<id>.mmd` を書く。既存図を残し、同じ図のIDを維持する。catalog.jsonの構造は `assets/examples/catalog.json` と同じにし、nameと図の内容は資料に合わせる（OUT-01、OUT-02、OUT-04、OUT-05、OUT-08）
5. `python3 <skill>/scripts/catalog.py deps` でCLIの版を確認する。不足時は `references/setup.md` を示してabortする。`python3 <skill>/scripts/catalog.py build domain-models/<name>` でPNGとHTMLを生成する。更新の依頼がある場合だけ `--update` を付ける。固定のファイル名・並び順・画像設定と検証記録はスクリプトに任せる（STEP-02、OUT-06、OUT-07）
6. `python3 <skill>/scripts/catalog.py check domain-models/<name>` と `python3 <skill>/scripts/run.py check` を実行する。非0なら診断された入力か出力を直す。環境不足を直せないときは `python3 <skill>/scripts/run.py abort --reason "<実際の理由>"` を実行する。検査する側は変えない（STEP-03、CTL-02）
7. 完了前チェックリストで資料と図を照合し、生成したPNGとHTMLを表示して日本語・図の欠け・検索・拡大・原本参照を確認する。`.skill-runs/generate-domain-model/notes.md` は次の3行だけにする。`- 資料照合: 確認済み`、`- PNG表示: 確認済み`、`- HTML操作: 確認済み`。実施できなかった項目の値だけ `未実施（実際の理由）` に変える。理由は英字を含まない日本語で書く。パス・識別子はカタログ内の根拠を参照し、notesには書かない（OUT-03、STEP-04）
8. `python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら手順6へ戻る。0なら出力された本文をそのまま返答する（RPT-01）

## 3. 入力

<!-- BEGIN GENERATED:inputs -->
| 項目 | キー | 受け付ける書き方 | 無いとき |
|---|---|---|---|
| カタログ名 | `name` | 英小文字・数字・`-` に変換。別名: 名前、カタログ、catalog | 既定値 `domain` |
| 資料 | `source` | 文字列。別名: 入力、資料、対象 | start の前に聞く: 図にする業務説明・仕様・コードのパス・classDiagramを教えてください。 |
| 既存カタログの更新 | `update` | はい・いいえ（true/false、する/しない も可）。別名: 更新 | 既定値 `false` |

入力は `run.py start --set <キー>=<値>` で渡す。キーは表のキー・項目名・別名のどれでもよく、全角と半角、大文字と小文字、`-`・`_`・空白の違いは吸収される。契約に無いキーは無視して記録する。依頼文そのものは最後の引数に渡す。依頼文の中の「キー: 値」の行も読む。
<!-- END GENERATED:inputs -->

## 4. 決定表

<!-- BEGIN GENERATED:decisions -->
| ID | 決定 | 守らせ方 |
|---|---|---|
| IN-01 | 業務資料が無ければ start の前に資料を聞く。ER図または全コードクラスの列挙だけを求める依頼では start せず archify-jp を案内する。 | doc: SKILL.md の手順1 |
| IN-02 | 読む範囲は利用者が渡した業務説明、仕様、classDiagram、指定したパスとその用語を定義する参照先にする。各図の sources に参照先と実際の記述を残す。 | doc: SKILL.md の手順3 |
| STEP-01 | start → inspect → 資料を読む → catalog.json と .mmd を書く → build → check → finish の順にする。既存カタログは update=true のときだけ更新し、既存IDを維持して追加と内容修正を行う。 | script, doc: scripts/catalog.py の inspect、build、check。SKILL.md の手順2〜7 |
| STEP-02 | Python 3.9以上と既に導入された mmdc を使う。mmdc は引数 --mmdc、環境変数 DOMAIN_MODEL_MMDC、PATH の順に選ぶ。deps で版を確認する。不足時は references/setup.md の導入手順を提示し、インストールせず中断する。 | script, doc: scripts/catalog.py の deps と build。references/setup.md |
| STEP-03 | build または check が非0なら診断を読み、入力か生成対象を直して再実行する。環境不足を直せないときは run.py abort に実際の理由を渡す。既存の正常な画像とHTMLは全図の変換が成功してから置き換える。 | script, doc: scripts/catalog.py の build と check。SKILL.md の手順6 |
| STEP-04 | validation.json の status は passed、renderer.name は mermaid-cli、renderer.version は空でない文字列にする。各PNGの署名・CRC・寸法・IDAT・終端を検査する。生成したPNGとHTMLを表示して日本語と図の欠けを確認し、notes.md は「- 資料照合: 」「- PNG表示: 」「- HTML操作: 」の順で3行にする。値は「確認済み」または「未実施（実際の理由）」だけにし、理由は英字を含まない日本語で書き、参照パスや識別子は書かない。詳細な根拠と未確認事項はカタログに残す。 | validate, script: scripts/catalog.py の check と build、SKILL.md の手順7 |
| OUT-01 | 出力は domain-models/{name}/catalog.json、index.html、validation.json、diagrams/<id>.mmd、images/<id>.png に限定する。カタログには1図以上を載せ、図ごとに原本とPNGを1つずつ対応させる。 | validate, script: scripts/catalog.py の check と契約の出力パス |
| OUT-02 | catalog.json は schema_version、name、title、diagrams を持つ。図は id、title、description、terms、sources、unresolved を持つ。sources は path と quote を持つ。原本は classDiagram で始める。HTMLはオフラインの一覧・検索・拡大・原本参照を備える。PNGは破損していない画像にする。 | validate, script: scripts/catalog.py の check。assets/examples/catalog.json |
| OUT-03 | 業務概念・主な属性・関係名・資料にある多重度を図にする。ラベルは資料の用語を使う。コードのメソッドやDBの外部キーを業務概念に置き換えない。資料にない概念・属性・関係・多重度を断定せず、足りない情報を unresolved に書く。sources.quote の実際の記述と図・説明を照合する。入力で指定された業務領域を省略しない。 | review: 完了前チェックリストで sources.quote と図・説明を照合する |
| OUT-04 | name と図の id は英小文字・数字・ハイフンで、英小文字から始める。図は id の昇順、terms は重複なしの昇順にする。ファイル名は id と一致させ、JSONはキーの昇順・2空白で書く。既存IDは同じ図の更新で維持する。termsはMermaidに宣言した概念の表示名から生成し、表示名がない概念は概念IDを使う。同じファイルの引用は1件にまとめ、参照先の昇順に並べる。 プロジェクト内の資料パスはプロジェクトルートからの相対パスに統一する。プロジェクト外の資料とURLは入力の参照先を保つ。 | validate, script: scripts/catalog.py の check と build |
| OUT-05 | 図は1〜1000件にする。各図に空でない題名と説明と1件以上の sources を持たせる。terms と unresolved は配列にし、未確認事項が無ければ空配列にする。 | validate: scripts/catalog.py の check |
| OUT-06 | inspect で既存図のIDを読む。index.html があるときは update=true の依頼でだけ build --update を使う。依頼のない既存図は残す。build は前回 validation.json にあるIDの削除と同名の未知のファイルの置換を拒否する。 原本・変換版・設定と既存PNGのハッシュが前回の検証記録と一致する図はPNGを再利用し、未変更図の画像を維持する。 | script, doc: scripts/catalog.py の inspect と build。SKILL.md の手順3 |
| OUT-07 | check は全ファイルのSHA-256と validation.json の記録を照合し、metadata・Mermaid・PNG・HTMLの組が一致することを確認する。変更のない再実行でも report.sections が全カタログを検査する。 | validate, script: scripts/catalog.py の check と report、report.sections |
| OUT-08 | Mermaidとcatalog.jsonに skip ci、ci skip、eslint-disable、noqa、type: ignore、validation: false の記法を書かない。Mermaidの初期化ディレクティブとclick文は生成せず、変換設定はbuildが固定する。 | validate: scripts/catalog.py の check |
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
| catalog カタログ情報 | `domain-models/{in:name}/catalog.json` | 0〜1 件（OUT-01） | `python3 {skill}/scripts/catalog.py check {root}/domain-models/{in:name}` が通る。OUT-01、OUT-04、OUT-05、OUT-07、OUT-08、STEP-04 の指摘も出す（check・finish・応答を終える前だけ。編集の直後は検査しない）（OUT-02） |
| index HTMLカタログ | `domain-models/{in:name}/index.html` | 0〜1 件（OUT-01） | — |
| validation 変換検証結果 | `domain-models/{in:name}/validation.json` | 0〜1 件（OUT-01） | — |
| mermaid Mermaid原本 | `domain-models/{in:name}/diagrams/*.mmd` | 0〜1000 件（OUT-01） | 1 行目が `^classDiagram$` に一致する（原本の先頭行はclassDiagramにする）（OUT-02） |

`{run}` は実行記録の置き場 `.skill-runs/generate-domain-model` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。

- 保護ファイルが実行中に変わっていない（CTL-02）
- 上の出力と、変えてよいファイル `domain-models/{in:name}/images/*.png`のほかに、start の後に変わったファイルが無い（CTL-05。git の作業ツリーで判定し、git が無いときは検査しない）
<!-- END GENERATED:contract -->

## 6. 完了前チェックリスト

<!-- BEGIN GENERATED:checklist -->
- [ ] OUT-03 業務概念・主な属性・関係名・資料にある多重度を図にする。ラベルは資料の用語を使う。コードのメソッドやDBの外部キーを業務概念に置き換えない。資料にない概念・属性・関係・多重度を断定せず、足りない情報を unresolved に書く。sources.quote の実際の記述と図・説明を照合する。入力で指定された業務領域を省略しない。
- [ ] RPT-01 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- [ ] `python3 <skill>/scripts/run.py finish` が終了コード0で終わった
<!-- END GENERATED:checklist -->

## 7. 報告

<!-- BEGIN GENERATED:report -->
最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。決めきれなかったことは、finish の前に `.skill-runs/generate-domain-model/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを「## 補足」に入れる。中断するときは `run.py abort --reason <理由>` を実行し、abort が出力した本文を同じようにそのまま使う。本文の形は次のとおり。

```text
## 結果

generate-domain-model: 完了（検証に合格）

<`python3 {skill}/scripts/catalog.py report {root}/domain-models/{in:name}` の出力>

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

hooks は、このスキルの実行中（`.skill-runs/generate-domain-model/state.json` の status が active）だけ出力を検査する。hooks が無い環境でも、`run.py check` と `finish` が同じ検査をする。

hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（Claude Code は `.claude/settings.json`、Codex は `.codex/hooks.json` に追記する。Codex では、追記した hooks を `/hooks` で信頼するまで動かない）

保護ファイル（スキルのディレクトリからの相対パス）: `SKILL.md`、`scripts/**`、`assets/**`、`references/**`

このスキル（決定、契約、手順、スクリプト）を変えるときは、次の順にする。保護ファイルだけを直接書き換えると、封印と違うため次の `run.py start` が止まる（CTL-02）。`<skill-foundation>` は skill-foundation のディレクトリを指す。

1. 実行中なら `python3 <skill>/scripts/run.py abort --reason <理由>` で止める
2. `dev/spec.json` を直す。手で書く部分（この SKILL.md の「2. 手順」、`scripts/` のスキル固有のスクリプト、`references/`、`assets/examples/`）は直接直す
3. `python3 <skill-foundation>/scripts/render_skill.py --dir <skill>` で生成した部分を作り直す
4. 決定や契約を変えたなら `dev/probes.json` の違反例も合わせ、`python3 <skill-foundation>/scripts/probe.py <skill>` を通す
5. `python3 <skill-foundation>/scripts/skill_lint.py <skill> --final --seal` を通す。通ると封印し直す
<!-- END GENERATED:control -->
