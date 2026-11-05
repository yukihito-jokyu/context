---
name: write-basic-design-document
description: "会話・議事録・箇条書きの要望から、開発者が構成・画面・データ・外部連携と採用理由を図と短い説明で理解し、詳細設計へ進めるMarkdownとHTMLの基本設計書を作る。「会話や議事録から基本設計を作成して」、「要望のメモを図付きの基本設計書にして」、「構成・画面・データ・外部連携が分かる基本設計を書いて」、「詳細設計へ進めるように設計案と採用理由をまとめて」、「図を多く使い認知負荷の低い基本設計書を作って」、「基本設計のHTMLとMermaidの図を作って」と頼まれたときに使う。背景・業務・必要な振る舞いを整理した要件定義書だけを作るには使わない（代わりにwrite-requirement-documentを使う）。実装コード、メソッド、物理列の定義だけを作るには使わない（代わりに詳細設計と実装を直接行うを使う）。"
---

# 図と採用理由がつながる基本設計書を書く

<!-- BEGIN GENERATED:purpose -->
会話・議事録・箇条書きの要望から、開発者が構成・画面・データ・外部連携と採用理由を図と短い説明で理解し、詳細設計へ進めるMarkdownとHTMLの基本設計書を作る
<!-- END GENERATED:purpose -->

## 1. 使う場面

<!-- BEGIN GENERATED:triggers -->
次のような依頼で使う。

- 「会話や議事録から基本設計を作成して」
- 「要望のメモを図付きの基本設計書にして」
- 「構成・画面・データ・外部連携が分かる基本設計を書いて」
- 「詳細設計へ進めるように設計案と採用理由をまとめて」
- 「図を多く使い認知負荷の低い基本設計書を作って」
- 「基本設計のHTMLとMermaidの図を作って」

次の場合は使わない。

- 背景・業務・必要な振る舞いを整理した要件定義書だけを作る → 代わりに: write-requirement-document
- 実装コード、メソッド、物理列の定義だけを作る → 代わりに: 詳細設計と実装を直接行う

依頼の内容から自動で選ばれる。明示して呼ぶときは Codex では `$write-basic-design-document` と書く。
<!-- END GENERATED:triggers -->

## 2. 手順

このファイルのディレクトリを`<skill>`と呼ぶ。出力先`<out>`は`.skill-runs/write-basic-design-document/out`とする。

1. 会話と指定資料から対象と課題を確かめ、不足する点を開始前にまとめて聞く。対象プロジェクトのAGENTS.mdがあれば開始前に読む。要件定義だけか実装詳細だけの依頼は、対応する作業を案内して終える。[references/authoring.md](references/authoring.md)の1章を読む（IN-01、IN-02、CTL-03）。
2. `python3 <skill>/scripts/run.py start --guess language=ja "<依頼文>"`を単独で実行する。資料の検索結果が0件でも開始を止めない。言語を指定されたときは`--set language=<jaまたはen>`を足す。`python3 <skill>/scripts/document.py doctor`で描画の経路と版を確かめる（CTL-01、STEP-04）。
3. [references/authoring.md](references/authoring.md)の2〜3章、[references/html-principles.md](references/html-principles.md)、[references/markdown-format.md](references/markdown-format.md)、[references/diagrams.md](references/diagrams.md)の1章を読む。要望・根拠・設計案・採用理由・未決事項を分け、4観点と8種類の図の採否を決める（STEP-01、STEP-02、OUT-03、OUT-09）。
4. `<out>`を作成する。`assets/examples/basic-design-document.json`を構造の見本にして、`<out>/basic-design-document.json`を書く。要望を設計へ、設計を図と根拠へ結び付け、図から設計へも参照を書く。coverageでfalseとした観点の設計は置かず、不実施の理由をcoverageへ書く。未決の条件を質問と確定できない設計へつなぎ、詳細設計への引継ぎを書く。原本作成用の補助スクリプトを作ったときは、この手順内で使い終えて削除する（STEP-01、OUT-01、OUT-02、OUT-04、OUT-08、OUT-09）。
5. `python3 <skill>/scripts/document.py build --source <out>/basic-design-document.json --out <out>`を実行する。原本の指摘は直して再実行する。描画失敗は[references/diagrams.md](references/diagrams.md)の2章で原因を確認し、起動権限の制限なら実行環境の承認手順を使って同じbuildを再実行する。解決できないときは不足する経路を`run.py wait --question "<不足する経路>"`で報告して待つ（STEP-03、STEP-04、STEP-05、OUT-05、OUT-06、OUT-07）。
6. `python3 <skill>/scripts/run.py check`を実行する。指摘があれば該当するルールを引き、原本を直して手順5へ戻る。Markdown・HTML・Mermaid・PNG・manifestの件数と同期を確かめる（STEP-05、OUT-06）。
7. 完了前チェックリストと[references/authoring.md](references/authoring.md)の4章で意味を確認する。要望と設計・採用理由、図と本文の条件・順序、未決事項の質問と影響を照合する。手順6のcheckが表示したPNGのパスを使い、各画像を開いて文字の欠け・つぶれ・矢印を確認する。独自の英字の略語と冗長な文章を直す。詳細設計への引継ぎは項目同士を比較し、同じ作業を重ねて書いたときは統合する。一般的な技術名も、概要を含む最初の表示箇所で意味を説明する。画像を開けなければ未実施とnotes.mdへ残す。直したら手順5へ戻る（STEP-02、OUT-03）。
8. 決めきれない前提を`.skill-runs/write-basic-design-document/notes.md`へ「- 」で書く。`python3 <skill>/scripts/run.py finish`を実行し、終了コード0の本文をそのまま返す（CTL-01、RPT-01）。

## 3. 入力

<!-- BEGIN GENERATED:inputs -->
| 項目 | キー | 受け付ける書き方 | 無いとき |
|---|---|---|---|
| 出力の言語 | `language` | `ja`、`en` のどれか（日本語→`ja`、英語→`en`）。別名: 言語、lang | 既定値 `ja` |

入力は `run.py start --set <キー>=<値>` で渡す。キーは表のキー・項目名・別名のどれでもよく、全角と半角、大文字と小文字、`-`・`_`・空白の違いは吸収される。契約に無いキーは無視して記録する。依頼文そのものは最後の引数に渡す。依頼文の中の「キー: 値」の行も読む。
<!-- END GENERATED:inputs -->

## 4. ルール

<!-- BEGIN GENERATED:decisions -->
| ID | ルール | 守らせ方 |
|---|---|---|
| IN-01 | 要件定義だけ、または実装コード・物理列・メソッドの定義だけを求める依頼では開始せず、対応する作業を案内する。解く課題または対象が会話と資料のどちらにも無ければ、開始前に不足する点をまとめて聞く。対象と課題が分かり、条件だけが未指定か矛盾しているときは、未決事項を残して基本設計のドラフトを作る。 | doc: SKILL.md の手順1、references/authoring.md の1章 |
| IN-02 | 会話、利用者が指定した資料、対象プロジェクトのAGENTS.mdを読む。既存コードは利用者が既存構成の確認を指定したときだけ読む。資料の抜粋と場所をsourcesへ保存し、要望の事実と新しく提案する設計を分ける。 | doc: SKILL.md の手順1、references/authoring.md の1章 |
| STEP-01 | 受付、要望と根拠の整理、4観点の設計と理由の作成、構造化原本、図・Markdown・HTMLの生成、検査、意味の確認、finishの順に進める。assets/examples/basic-design-document.jsonを構造の見本にする。原本作成用の補助スクリプトは作成手順内で使い終えて削除し、納品物へ残さない。 | doc, template: SKILL.md の手順、assets/examples/basic-design-document.json |
| STEP-02 | 業務条件や技術が未指定ならopen_questionsへ確認する条件と、決まるまで確定できない設計の範囲を書く。資料が矛盾するときは両方をsourcesへ残し、片方を合意済みとして採用しない。本文と図にある未決の条件を質問と影響範囲へ結び付ける。提案はproposal、入力の事実はstated、未決の設計はopenにし、承認を捏造しない。 | review: references/authoring.md の2章、完了前チェックリストで未決事項と図を照合する |
| STEP-03 | scripts/document.pyのbuildで構造化原本からMermaid原本・PNG・Markdown・HTML・manifestを作る。checkで原本の形、参照、画像の実体と同期を確かめる。派生出力を手で差し替えず、原本を直してbuildを実行する。 | script, validate: scripts/document.py の build と check。出力 html の command 検査 |
| STEP-04 | Python 3.9以上、Node.js、既存のmermaid-cli 11以降を使い、doctorで経路と版を確認する。Mermaidはflowchart・stateDiagram-v2・sequenceDiagram・classDiagram・erDiagramを使う。外部画像、クリック、初期化指令を図へ埋め込まず、新規パッケージとリモート描画サービスを自動導入しない。 | doc: scripts/document.py の doctor と build、references/diagrams.md の2章 |
| STEP-05 | buildまたはcheckが失敗したら、示されたルールIDに従って原本を直し、buildとcheckを実行し直す。描画の実行経路か起動権限が無ければ、環境が用意する承認手順を使う。使えないときは不足する経路を報告して質問待ちにし、PNGが無い状態を完成としない。 | doc: SKILL.md の手順5と6、scripts/document.py のエラー出力 |
| OUT-01 | {run}/out/へbasic-design-document.json・basic-design-document.md・basic-design-document.html・manifest.jsonを各1件、diagrams/へ同名の.mmdと.pngを図ごとに出力する。context・component・workflow・dataの図を各1件以上作る。 | validate: 出力の path・count と scripts/document.py の check |
| OUT-02 | MarkdownとHTMLの章は、概要、前提と要望、全体構成、画面と操作、データ設計、外部連携、品質と運用、未決事項と詳細設計への引継ぎ、根拠と補足の順にする。設計ごとに観点、設計内容、採用理由、状態、要望・図・質問・根拠への参照を持つ。図は各観点の章へ置き、直前に読む目的、直後に要点を示す。HTMLには検索できる本文、PNGの埋め込み、代替説明、原寸表示、Mermaid原本のdetails、目次と名前のリンクを付ける。Markdownにも同じ本文・図の導入と要点・採用理由・未決事項・根拠を出し、図のPNGとMermaid原本は同梱ファイルへの相対リンクにする。Markdownは文書名・目的・目次から始め、章と節を番号付き見出しにし、用語と利用者を表で示す。図は導入・PNG・拡大と原本へのリンク・要点・関連設計の順にする。文書内リンクは番号付き見出しに合わせ、HTMLタグのアンカーを本文へ挿入しない。参考文書は書式だけを参考にし、要件定義の章構成・業務・版番号を転用しない。 | script, validate: scripts/document.py の build と check、references/html-principles.md、references/markdown-format.md |
| OUT-03 | 各節の要点を先に示し、前提から設計と採用理由へ説明をつなぐ。1段落を1論点にし、主体・条件・結果を具体的に書く。同義反復、抽象的な美辞麗句、独自に作った英字の略語を本文・見出し・図・リンクの表示名へ出さない。一般的な技術用語は使うときに初出で意味を説明する。必要な前提・例外・未決事項を短縮のために落とさない。 | review: references/html-principles.mdの1章、Evalのbehavior-3とbehavior-4、完了前チェックリスト |
| OUT-04 | sourcesはSRC-01、actorsはACT-01、requirementsはREQ-01、designsはDES-01、diagramsはD-01、open_questionsはQ-01から出現順の連番にする。IDは原本のid・参照配列とMarkdown・HTMLのリンク先属性だけに使い、本文・見出し・リンクの表示名・代替説明・Mermaidの表示ラベルへ出さない。原資料のquoteは改変しない。生成日時と乱数を加えない。 | validate: scripts/document.py の原本検査とHTML生成、references/authoring.md の3章 |
| OUT-05 | 本文は1段落1論点とし、図は1つの問いを扱う。Mermaid原本は図ごとに6000文字以下、PNGは幅と高さ6000px以下かつ2500万画素以下にする。上限を超えるときは、全体図と処理別の詳細図へ分け、設計への参照を保つ。 | validate: scripts/document.py の寸法・原本長検査、references/diagrams.md の3章 |
| OUT-06 | 構造化原本を変更したらbuildでMarkdown・HTML・manifestを更新する。manifestには原本・Mermaid・PNG・Markdown・HTMLのSHA-256と描画設定を記録し、checkが実体・Markdownの再生成内容・HTMLの埋め込みを照合する。Mermaid・描画設定・描画ツールの版・PNGのハッシュが一致するときだけ同じPNGを再利用する。 | validate: scripts/document.py の check（Markdownを含む全出力）と together の source・html・manifest |
| OUT-07 | 原本とmanifestは定義したキーだけを持つ。skip_validation、ignore_errors、自己申告の検証済みを受け付けず、検査は原本と派生出力の実体で行う。 | validate: scripts/document.py の原本キーとmanifest検査 |
| OUT-08 | sourcesへ資料名・場所・実際の記述の抜粋を保存する。各要望から設計、設計から図と根拠、図から設計と根拠をたどれる参照を持つ。未決の設計は対応する質問を参照し、HTMLでは内容が分かる名前をリンクの表示名にする。入力に無い条件を合意済みの事実として書かない。 | validate: scripts/document.py の参照・抜粋検査、references/authoring.md の3章 |
| OUT-09 | coverageはarchitecture・screen・data・integrationの順に採否と理由を持つ。architectureとdataは採用し、全体構成と責務、処理、データ関係の図を作る。screenを採用したときはscreen、integrationを採用したときはsequenceの図を作る。図の8種類context・component・workflow・screen・data・sequence・state・deploymentの採否と理由をdiagram_decisionsへ残す。画面や外部連携が無いときは理由を示し、未指定のときは未決事項を残す。物理列、索引、メソッドの定義はhandoffへ分ける。 | validate: scripts/document.py の図の種別・選択記録検査、references/diagrams.md の1章 |
| RPT-01 | 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。 | runtime, validate, review: scripts/run.py の finish と abort が本文を組み立て、.skill-runs/<name>/report.md にも保存する。check と finish が notes.md の形を検査する |
| CTL-01 | 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。 | runtime, validate: scripts/run.py。finish は契約の検査に通らないと終了コード1で終わる |
| CTL-03 | ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。 | runtime, doc: scripts/run.py の start は、聞くべき入力が無いと終了コード3で止まり、質問を出力する。wait は hooks の強制を止める |
| CTL-04 | hooks は実行中（status: active）に、編集の後と応答を終える前に出力を検査する。実行記録への直接の編集は拒否する。ユーザーの発言を止めたり書き換えたりしない。hooks が無くても run.py check と finish で同じ出力の検査を行う。 | runtime: scripts/hook.py。install.py が Claude Code（.claude/settings.json）と Codex（.codex/hooks.json）に登録する |

理由・良い例・悪い例は [references/decisions.md](references/decisions.md) にある。
<!-- END GENERATED:decisions -->

## 5. 出力の契約

<!-- BEGIN GENERATED:contract -->
| 出力 | 置き場 | 件数 | 検査（ルールID） |
|---|---|---|---|
| source 基本設計の構造化原本 | `{run}/out/basic-design-document.json` | 1〜1 件（OUT-01） | JSON スキーマに合う（OUT-02）。`"language"\s*:\s*"{in:language}"` に一致する行がある（原本の言語を実行時の入力とそろえる）（OUT-02） |
| html 基本設計書のHTML | `{run}/out/basic-design-document.html` | 1〜1 件（OUT-01） | `python3 {skill}/scripts/document.py check --source {run}/out/basic-design-document.json --out {run}/out` が通る。OUT-01、OUT-02、OUT-04、OUT-05、OUT-06、OUT-07、OUT-08、OUT-09 の指摘も出す（check・finish・応答を終える前だけ。編集の直後は検査しない）（STEP-03） |
| markdown 基本設計書のMarkdown | `{run}/out/basic-design-document.md` | 1〜1 件（OUT-01） | — |
| manifest 図と原本の対応とハッシュ | `{run}/out/manifest.json` | 1〜1 件（OUT-01） | — |
| mermaid Mermaid原本 | `{run}/out/diagrams/*.mmd` | 4 件以上（OUT-01） | — |
| png 図のPNG | `{run}/out/diagrams/*.png` | 4 件以上（OUT-01） | — |

`{run}` は実行記録の置き場 `.skill-runs/write-basic-design-document` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。

- 出力 source、html、manifest は一緒に変える。一部だけを変えると OUT-06 の指摘になる（原本を変えたらMarkdown・HTML・manifestを再生成する）
<!-- END GENERATED:contract -->

## 6. 完了前チェックリスト

<!-- BEGIN GENERATED:checklist -->
- [ ] STEP-02 業務条件や技術が未指定ならopen_questionsへ確認する条件と、決まるまで確定できない設計の範囲を書く。資料が矛盾するときは両方をsourcesへ残し、片方を合意済みとして採用しない。本文と図にある未決の条件を質問と影響範囲へ結び付ける。提案はproposal、入力の事実はstated、未決の設計はopenにし、承認を捏造しない。
- [ ] OUT-03 各節の要点を先に示し、前提から設計と採用理由へ説明をつなぐ。1段落を1論点にし、主体・条件・結果を具体的に書く。同義反復、抽象的な美辞麗句、独自に作った英字の略語を本文・見出し・図・リンクの表示名へ出さない。一般的な技術用語は使うときに初出で意味を説明する。必要な前提・例外・未決事項を短縮のために落とさない。
- [ ] RPT-01 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- [ ] `python3 <skill>/scripts/run.py finish` が終了コード0で終わった
<!-- END GENERATED:checklist -->

## 7. 報告

<!-- BEGIN GENERATED:report -->
最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。決めきれなかったことは、finish の前に `.skill-runs/write-basic-design-document/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを「## 補足」に入れる。中断するときは `run.py abort --reason <理由>` を実行し、abort が出力した本文を同じようにそのまま使う。本文の形は次のとおり。

```text
## 結果

write-basic-design-document: 完了（検証に合格）

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
| `scripts/run.py start` | 手順の始め | 入力を正規化し（表記ゆれ・全角・未知のキーを受け入れる）、既定値で補い、実行記録を作る |
| `scripts/run.py check` と `finish` | 出力を書いた後と最後 | 契約（`assets/contract.json`）の format で出力を直してから検査する。finish は通ったときだけ実行を終える |
| hooks の pre-tool | ファイルを編集する前 | 実行記録への直接の編集を拒否する。スキル自身のファイルは編集できる |
| hooks の post-tool | ファイルを編集した後 | 出力に当たるファイルを format で直し、検査し、指摘を返す |
| hooks の stop | 応答を終える前 | 実行中は出力全体を検査する（最大 3 回。超えると status: failed） |
| hooks の prompt | ユーザーが発言したとき | 質問待ちを解く。発言を止めたり書き換えたりしない |

出力の検査は実行中（`.skill-runs/write-basic-design-document/state.json` の status が active）に働く。hooks が無い環境でも、`run.py check` と `finish` が同じ検査をする。

hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（Codex は `.codex/hooks.json` に追記する。Codex では、追記した hooks を `/hooks` で信頼するまで動かない）
<!-- END GENERATED:control -->
