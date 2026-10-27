---
name: generate-usecase-diagram
description: "要件文または既存のMermaidからユースケース図の原本とPNGを生成し、ローカルで閲覧できるHTMLカタログにまとめる。「Mermaidでユースケース図を作成し、PNGに変換してHTMLでカタログとして見たい」、「要件からアクターとユースケースを整理して図にして」、「ユースケース図をPNGとMermaid原本で保存して」、「複数のユースケース図をHTMLで一覧にして」、「既存のusecase-betaを画像とカタログに変換して」、「Generate use case diagrams and an HTML catalog」と頼まれたときに使う。シーケンス図、ER図、状態遷移図を作成するには使わない（代わりにarchify-jpを使う）。Webへカタログを公開するには使わない（代わりに公開先を指定した公開手順を使う）。"
---

# ユースケース図をPNGとHTMLカタログにする

<!-- BEGIN GENERATED:purpose -->
要件文または既存のMermaidからユースケース図の原本とPNGを生成し、ローカルで閲覧できるHTMLカタログにまとめる
<!-- END GENERATED:purpose -->

## 1. 使う場面

<!-- BEGIN GENERATED:triggers -->
次のような依頼で使う。

- 「Mermaidでユースケース図を作成し、PNGに変換してHTMLでカタログとして見たい」
- 「要件からアクターとユースケースを整理して図にして」
- 「ユースケース図をPNGとMermaid原本で保存して」
- 「複数のユースケース図をHTMLで一覧にして」
- 「既存のusecase-betaを画像とカタログに変換して」
- 「Generate use case diagrams and an HTML catalog」

次の場合は使わない。

- シーケンス図、ER図、状態遷移図を作成する → 代わりに: archify-jp
- Webへカタログを公開する → 代わりに: 公開先を指定した公開手順

依頼の内容から自動で選ばれる。明示して呼ぶときは Claude Code では `/generate-usecase-diagram`、Codex では `$generate-usecase-diagram` と書く。
<!-- END GENERATED:triggers -->

## 2. 手順

このファイルがあるディレクトリを `<skill>` と呼ぶ。スクリプトは Python 3.9 以上の標準ライブラリだけで動く。手順は番号の順に行い、飛ばさない。

1. 対象システムとアクター・機能を依頼から読み取り、不明な場合はstartの前にまとめて確認する。対象外の図は対応するスキルへ案内する（CTL-03、IN-01、STEP-01）。
2. 指定された入力、[作図手順](references/authoring.md)、見本 `assets/examples/request.json` を読み、`python3 <skill>/scripts/catalog.py preflight` で既存の描画環境を確認する（IN-02、STEP-04）。
3. `python3 <skill>/scripts/run.py start --set system="<対象システム>" "<依頼文>"` を実行する。カタログ名の指定が無い場合と「お任せ」の場合はnameを渡さず既定値catalogを使う。指定された場合だけ `--set name=<名前>`、入力ファイルがある場合は `--set source=<パス>` を付ける。終了コード3なら質問へ回答を得てから再実行する（CTL-01）。
4. `assets/examples/request.json` の構造を使い、利用者の要件から `.skill-runs/generate-usecase-diagram/source/request.json` を作る。既存Mermaidはsourceで指定する。新規作図と関係の判断はSTEP-02、IDと分割はOUT-04・OUT-05に従う。アクターと境界のメタデータを手入力しない（STEP-03）。
5. `python3 <skill>/scripts/catalog.py build --request .skill-runs/generate-usecase-diagram/source/request.json --name <カタログ名>` を実行する。更新の依頼がある場合だけ `--replace` を付ける。失敗時は指摘された原本を直して再実行し、以前の正常な出力を保持する（OUT-06、STEP-05）。
6. `python3 <skill>/scripts/catalog.py preview --catalog <出力>/catalog.json --out .skill-runs/generate-usecase-diagram/preview.png` を実行する。保存した画面と出力の全PNGを開き、日本語、境界、関係線、一覧・検索・拡大・原本取得を確認する。確認できた範囲だけ `catalog.py review --catalog <出力>/catalog.json --notes "<確認内容>"` で記録する。入力と図の意味も照合する（STEP-06、OUT-03）。
7. `python3 <skill>/scripts/run.py check` を実行し、指摘された出力を直す。原本を変えた場合は手順5から再生成する（CTL-02、OUT-07、OUT-08）。
8. 未確認の範囲を `.skill-runs/generate-usecase-diagram/notes.md` に箇条書きで残す。未確認が無い場合も「- なし」を保存する。その後、`python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら指摘を直して再実行し、終了コード0の本文をそのまま返答する。短い報告への書き直しも行わない（RPT-01）。

## 3. 入力

<!-- BEGIN GENERATED:inputs -->
| 項目 | キー | 受け付ける書き方 | 無いとき |
|---|---|---|---|
| 対象システム | `system` | 文字列。別名: 対象、システム | start の前に聞く: 図にする対象システムとアクター・機能を教えてください。 |
| カタログ名 | `name` | 英小文字・数字・`-` に変換。別名: 名前、カタログ名 | 既定値 `catalog` |
| 要件またはMermaidの入力ファイル | `source` | パス。別名: 入力ファイル、原本 | 空のまま |

入力は `run.py start --set <キー>=<値>` で渡す。キーは表のキー・項目名・別名のどれでもよく、全角と半角、大文字と小文字、`-`・`_`・空白の違いは吸収される。契約に無いキーは無視して記録する。依頼文そのものは最後の引数に渡す。依頼文の中の「キー: 値」の行も読む。
<!-- END GENERATED:inputs -->

## 4. 決定表

<!-- BEGIN GENERATED:decisions -->
| ID | 決定 | 守らせ方 |
|---|---|---|
| IN-01 | 対象システム・アクター・機能が分からないときはstartの前に確認する。シーケンス図・ER図・状態遷移図の依頼はarchify-jpへ案内し、Web公開の依頼は公開先を確認する。 | doc: SKILL.mdの手順1、references/authoring.md。 |
| IN-02 | 指定された入力ファイルと依頼文、references/authoring.md、assets/examples/request.jsonを読む。入力が参照するリポジトリを調べるときは対象機能の根拠を読む。無関係な機能から要件を補わない。 | doc: SKILL.mdの手順2、references/authoring.md。 |
| STEP-01 | 質問を済ませ、run.py start、入力の整理、catalog.py build、PNGとHTMLの目視、run.py check、run.py finishの順に実行する。 | doc: SKILL.mdの手順1〜8。 |
| STEP-02 | 要件文からは明示されたアクター・機能・関係をMermaidにする。既存Mermaidは原本を保持して検査する。includeは必須処理、extendは条件付き追加、汎化は明示された継承関係がある場合だけ使う。 | doc: SKILL.mdの手順3、references/authoring.md。 |
| STEP-03 | scripts/catalog.py buildがMermaidからPNG・HTMLを生成する。scripts/render_diagram.pyがMermaidの構文解析結果からアクター・境界・関係を取得する。catalog.jsonへこれらの情報を手入力しない。 | script, validate: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonのcommand検査。 |
| STEP-04 | Python 3.9以上の標準ライブラリ、Mermaid 12の完全版mermaid.min.js、ChromeのCDP pipeを使う。catalog.py preflightで版とパスを確認する。追加のパッケージを導入しない。描画中のHTTP・HTTPS接続を遮断する。 | script, doc: scripts/catalog.py、scripts/render_diagram.py。SKILL.mdの手順2。 |
| STEP-05 | 入力検査・描画・PNG検査・HTML検査が失敗したら終了コード1で止める。生成は作業領域で行い、全図が成功してから出力先へ確定する。失敗した図を省いてカタログを成功扱いしない。 | script, doc: scripts/catalog.py。SKILL.mdの手順4。 |
| STEP-06 | catalog.py checkで全図の原本、PNGの全チャンクCRCと展開データ、HTML、変換記録を検査する。PNGとHTMLを目視し、日本語の欠け・関係線の重なり・一覧と拡大と原本取得を確認する。未確認の目視はvalidation.jsonのvisual_reviewをpendingにする。 catalog.py previewで一覧・検索・拡大・原本リンクを検査し、実行記録のpreview.pngとpreview.jsonへ画面とハッシュを保存する。reviewは対応する画面記録が無ければ止める。notes.mdは未確認が無い場合も「- なし」を保存する。 | script, validate: scripts/catalog.py。catalog.jsonのcommand検査。 |
| OUT-01 | artifacts/usecase/{in:name}/にcatalog.json、index.html、validation.json、diagrams/<id>.mmdと同名の.pngを出力する。図ごとに原本と画像を1つずつ持ち、相対パスの参照先を検査する。 | validate, script: scripts/catalog.py。出力のpath・countとcatalog.jsonのcommand検査。 |
| OUT-02 | 原本はusecase-betaを使い、全アクターと全ユースケースを明示宣言する。アクターはシステム境界の外、ユースケースは境界の中に置く。catalog.jsonはschema_version・title・description・diagramsを持つ。HTMLは一覧・PNG拡大・原本表示・PNGと原本の取得を備える。 | validate, script: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonとindex.htmlのcommand検査。 |
| OUT-03 | 図題名・説明・ラベルは入力の言語と意味を保つ。日本語の入力には日本語の説明を書く。入力にない機能・権限・include・extend・汎化を追加しない。 | review: 完了前に入力と図・カタログの説明を照合する。 |
| OUT-04 | カタログ名の指定がない場合と「お任せ」の場合はcatalogを使い、対象システムから名前を作らない。カタログ名と図IDは小文字kebab-caseにし、図IDを重複させない。利用者が図IDを指定しない場合は、入力の機能範囲の順にd01・d02から振る。図はIDの昇順にする。新規Mermaidの要素IDは登場順にA01・U01・S01から振る。既存Mermaidの明示IDは保持し、宣言の重複を拒否する。 | validate, script: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonのcommand検査。 |
| OUT-05 | 1カタログは1〜24図、1図のアクターとユースケースの合計は2〜40個とする。PNGの縦横は各12000px以下、面積は30000000px以下とする。上限を超える場合は機能範囲で図を分ける。 | validate, script: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonのcommand検査。 |
| OUT-06 | 既存出力はbuildの--replaceがあるときだけ更新する。--replaceはカタログ更新の依頼がある場合だけ付ける。出力が一致する場合は既存出力を再利用する。未管理ファイルを持つ出力先とシンボリックリンクの出力先は変更せず止める。 | script, doc: scripts/catalog.py。SKILL.mdの手順4、references/authoring.md。 |
| OUT-07 | catalog.jsonの図ID・原本・PNG・アクター・境界、index.htmlの表示内容、validation.jsonの原本とPNGとHTMLとカタログのSHA-256を一致させる。PNGはUTF-8検査の対象にせず、catalog.jsonのcommand検査からバイナリを検査する。 | validate, script: scripts/catalog.py。catalog.jsonのcommand検査。 |
| OUT-08 | Mermaidのinitディレクティブ・frontmatterで描画設定を上書きしない。validation.jsonは全図の成功を記録し、skip・ignoreによる検査の省略を認めない。HTMLは外部スクリプトと外部画像を読み込まない。 | validate, script: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonのcommand検査。 |
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
| catalog カタログ情報 | `artifacts/usecase/{in:name}/catalog.json` | 0〜1 件（OUT-01） | JSON スキーマに合う（OUT-02）。`python3 {skill}/scripts/catalog.py check --catalog {file}` が通る。STEP-03、STEP-06、OUT-01、OUT-02、OUT-04、OUT-05、OUT-07、OUT-08 の指摘も出す（check・finish・応答を終える前だけ。編集の直後は検査しない）（OUT-02） |
| html HTMLカタログ | `artifacts/usecase/{in:name}/index.html` | 0〜1 件（OUT-01） | — |
| validation 変換と検証の記録 | `artifacts/usecase/{in:name}/validation.json` | 0〜1 件（OUT-01） | — |
| mermaid Mermaid原本 | `artifacts/usecase/{in:name}/diagrams/*.mmd` | 0〜24 件（OUT-01） | — |

`{run}` は実行記録の置き場 `.skill-runs/generate-usecase-diagram` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。

- 保護ファイルが実行中に変わっていない（CTL-02）
- 上の出力と、変えてよいファイル `artifacts/usecase/{in:name}/diagrams/*.png`のほかに、start の後に変わったファイルが無い（CTL-05。git の作業ツリーで判定し、git が無いときは検査しない）
<!-- END GENERATED:contract -->

## 6. 完了前チェックリスト

<!-- BEGIN GENERATED:checklist -->
- [ ] OUT-03 図題名・説明・ラベルは入力の言語と意味を保つ。日本語の入力には日本語の説明を書く。入力にない機能・権限・include・extend・汎化を追加しない。
- [ ] RPT-01 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- [ ] `python3 <skill>/scripts/run.py finish` が終了コード0で終わった
<!-- END GENERATED:checklist -->

## 7. 報告

<!-- BEGIN GENERATED:report -->
最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。決めきれなかったことは、finish の前に `.skill-runs/generate-usecase-diagram/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを「## 補足」に入れる。中断するときは `run.py abort --reason <理由>` を実行し、abort が出力した本文を同じようにそのまま使う。本文の形は次のとおり。

```text
## 結果

generate-usecase-diagram: 完了（検証に合格）

<`python3 {skill}/scripts/catalog.py report --catalog {root}/artifacts/usecase/{in:name}/catalog.json` の出力>

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

hooks は、このスキルの実行中（`.skill-runs/generate-usecase-diagram/state.json` の status が active）だけ出力を検査する。hooks が無い環境でも、`run.py check` と `finish` が同じ検査をする。

hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（Claude Code は `.claude/settings.json`、Codex は `.codex/hooks.json` に追記する。Codex では、追記した hooks を `/hooks` で信頼するまで動かない）

保護ファイル（スキルのディレクトリからの相対パス）: `SKILL.md`、`scripts/**`、`assets/**`、`references/**`

このスキル（決定、契約、手順、スクリプト）を変えるときは、次の順にする。保護ファイルだけを直接書き換えると、封印と違うため次の `run.py start` が止まる（CTL-02）。`<skill-foundation>` は skill-foundation のディレクトリを指す。

1. 実行中なら `python3 <skill>/scripts/run.py abort --reason <理由>` で止める
2. `dev/spec.json` を直す。手で書く部分（この SKILL.md の「2. 手順」、`scripts/` のスキル固有のスクリプト、`references/`、`assets/examples/`）は直接直す
3. `python3 <skill-foundation>/scripts/render_skill.py --dir <skill>` で生成した部分を作り直す
4. 決定や契約を変えたなら `dev/probes.json` の違反例も合わせ、`python3 <skill-foundation>/scripts/probe.py <skill>` を通す
5. `python3 <skill-foundation>/scripts/skill_lint.py <skill> --final --seal` を通す。通ると封印し直す
<!-- END GENERATED:control -->
