---
name: write-requirement-document
description: "会話・議事録・箇条書きの要望から、業務担当者と開発者が背景・対象範囲・業務の流れ・必要な振る舞いを同じ理解で確認できる、図を含むHTMLの要件定義書を作る。「認知負荷が低い要件定義書を作成して」、「議事録から図付きの要件定義書を書いて」、「会話の要望を要件定義書のHTMLにまとめて」、「新規システムの対象範囲と業務を要件定義したい」、「MermaidをPNGにして要件定義書に載せて」、「業務担当者と開発者が同じ理解になる要件定義書を作って」と頼まれたときに使う。実装構造・DBテーブル・コンポーネントの詳細設計だけを作るには使わない（代わりに設計書を作成するを使う）。画面の見た目を試しながら要件を決めるには使わない（代わりにhtml-requirements-workshopを使う）。"
---

# 前提と図がつながる要件定義書を書く

<!-- BEGIN GENERATED:purpose -->
会話・議事録・箇条書きの要望から、業務担当者と開発者が背景・対象範囲・業務の流れ・必要な振る舞いを同じ理解で確認できる、図を含むHTMLの要件定義書を作る
<!-- END GENERATED:purpose -->

## 1. 使う場面

<!-- BEGIN GENERATED:triggers -->
次のような依頼で使う。

- 「認知負荷が低い要件定義書を作成して」
- 「議事録から図付きの要件定義書を書いて」
- 「会話の要望を要件定義書のHTMLにまとめて」
- 「新規システムの対象範囲と業務を要件定義したい」
- 「MermaidをPNGにして要件定義書に載せて」
- 「業務担当者と開発者が同じ理解になる要件定義書を作って」

次の場合は使わない。

- 実装構造・DBテーブル・コンポーネントの詳細設計だけを作る → 代わりに: 設計書を作成する
- 画面の見た目を試しながら要件を決める → 代わりに: html-requirements-workshop

依頼の内容から自動で選ばれる。明示して呼ぶときは Codex では `$write-requirement-document` と書く。
<!-- END GENERATED:triggers -->

## 2. 手順

このファイルのディレクトリを `<skill>` と呼ぶ。出力先 `<out>` は `.skill-runs/write-requirement-document/out` とする。

1. 会話と指定資料から課題と対象を確かめ、両方が分からなければ開始前にまとめて聞く。実装詳細だけの依頼は設計書を案内して終える。[references/authoring.md](references/authoring.md) の1章を読む（IN-01、IN-02、CTL-03）。
2. `python3 <skill>/scripts/run.py start --guess language=ja "<依頼文>"` を実行する。出力の言語を指定されたときは `--set language=<jaまたはen>` を足す。`python3 <skill>/scripts/document.py doctor` で既存の描画経路を確かめる（CTL-01、STEP-04）。
3. [references/html-principles.md](references/html-principles.md) の1〜5章と [references/diagrams.md](references/diagrams.md) の1章を読み、課題、範囲、業務、要件、未決事項を整理する。図の採否を9種類すべてについて決める（STEP-01、STEP-02、OUT-03、OUT-09）。
4. 出力先 `<out>` のディレクトリを作成する。`assets/examples/requirement-document.json` を形の見本にして `<out>/requirement-document.json` を書く。[references/authoring.md](references/authoring.md) の3章に従い、根拠の抜粋と場所、要件と図の双方向参照、図の導入と要点を埋める。内部IDは参照用の項目だけに書き、本文と図には内容が分かる名前を使う（OUT-01、OUT-02、OUT-04、OUT-08）。
5. `python3 <skill>/scripts/document.py build --source <out>/requirement-document.json --out <out>` を実行する。失敗したら表示された原因を直し、buildが成功するまでこの手順を繰り返す。成功してから手順6へ進む。描画経路が無いときは `run.py wait --question "<不足する実行経路>"` で待ち、PNGなしを完成扱いにしない（STEP-03、STEP-05、OUT-05、OUT-06、OUT-07）。
6. `python3 <skill>/scripts/run.py check` を実行する。指摘があれば該当ルールを引き、原本を直して手順5へ戻る。HTML、Mermaid、PNG、manifestがそろい同期していることを確認する（STEP-05、OUT-06）。
7. 完了前チェックリストと [references/authoring.md](references/authoring.md) の4章で、前提、図と本文の条件、文章の流れ、未決事項を原資料と照合する。各受入条件も根拠の抜粋と照合し、新しい業務判断や複数に読める否定を混ぜない。checkの出力またはmanifestにある図名に対応するPNGを開き、文字の欠け・つぶれと本文との条件の一致を確認する。画像を開けない環境では、その確認が未実施であることをnotes.mdへ残す。直したら手順5へ戻る（STEP-02、OUT-03）。
8. 決めきれない作成上の前提があれば `.skill-runs/write-requirement-document/notes.md` に「- 」で書く。`python3 <skill>/scripts/run.py finish` を実行し、終了コード0の本文をそのまま返す（CTL-01、RPT-01）。

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
| IN-01 | 依頼が実装詳細の設計だけなら開始せず設計書の作成を案内する。解く課題と対象が会話・資料のどちらにも無ければ、開始前にその2点をまとめて聞く。条件が未指定または矛盾する材料は、ドラフトを作り未決事項へ残す。 | doc: SKILL.md の手順1、references/authoring.md の1章 |
| IN-02 | 会話、利用者が指定した資料、対象プロジェクトの AGENTS.md を読む。コードの逆解析を主目的にせず、資料にない決定は未決事項か提案として書く。根拠の抜粋と場所を sources に保存する。 | doc: SKILL.md の手順1、references/authoring.md の1章 |
| STEP-01 | 受付、資料の整理、構造化原本の作成、図の変換とHTML生成、検査、意味の確認、finish の順に進める。assets/examples/requirement-document.json を構造の見本にする。 | doc, template: SKILL.md の手順、assets/examples/requirement-document.json |
| STEP-02 | 業務の条件が未指定なら open_questions に質問と決まらない範囲を書く。本文・図で未決とした条件も、対応する質問と影響範囲へ結び付ける。資料が矛盾すれば各記述を sources に残して未決とし、一方を確定した図へ混ぜない。対象と目的が分かる間は作成を続ける。 | review: references/authoring.md の2章、完了前チェックリストで未決事項と図を照合する |
| STEP-03 | scripts/document.py の build が構造化原本から Mermaid原本、PNG、HTML、manifest を作る。check が原本・HTML・PNG・ハッシュ・参照を検査する。PNGを手で差し替えず、原本を直して build し直す。 | script, validate: scripts/document.py の build と check。出力 html の command 検査 |
| STEP-04 | Python 3.9以上、Node.js、既存の mermaid-cli 11以降を使う。doctor で実行経路を確認する。Mermaid図は flowchart、stateDiagram-v2、sequenceDiagram、classDiagram、erDiagram を使う。外部画像・リンク・初期化指令を図へ埋め込まず、追加パッケージとリモート描画サービスは自動導入しない。 | doc: scripts/document.py の doctor と build、references/diagrams.md の2章 |
| STEP-05 | 描画または検査が失敗したら、示されたルールIDを引き、構造化原本を直して build と check を再実行する。描画環境が無ければ不足する実行経路を報告して待ち、PNGなしを完成扱いにしない。 | doc: SKILL.md の手順5と6、scripts/document.py のエラー出力 |
| OUT-01 | {run}/out/ に requirement-document.json、requirement-document.html、manifest.json を各1件、diagrams/ に同名の .mmd と .png を図ごとに出力する。図は context・usecase・workflow を各1件以上持つ。 | validate: 出力の path・count と scripts/document.py の check |
| OUT-02 | HTMLの章を、概要、用語と前提、対象範囲、全体像と業務、機能要件、品質と制約、未決事項、根拠と補足の順にする。目次・見出し・要件名のリンクを付ける。図の直前に読む目的、直後に要点と関連要件を置く。本文をHTML文字で残し、図のPNGを埋め込み、拡大用画像へのリンクも付ける。各図のMermaid原本を任意に開けるdetailsにも保存する。 | script, validate: scripts/document.py の build と check、references/html-principles.md |
| OUT-03 | 各節の冒頭で要点を示し、前提、理由、必要な振る舞いをつなぐ。1段落を1論点にし、誰が何をどの条件で行うかを書く。用語を統一し、抽象的な美辞麗句、同義反復、根拠のない価値判断を削る。短くするために前提・例外を落とさない。 否定の範囲を明示し、双方拒否と両立禁止の両方に読める文を使わない。 | review: references/html-principles.md の1章、Evalのbehavior-1とbehavior-3、完了前チェックリスト |
| OUT-04 | sources は SRC-01、actors は ACT-01、requirements は FR-01、diagrams は D-01、open_questions は Q-01 から出現順の連番にする。IDは原本のid・参照配列とHTMLのリンク先属性だけに使う。本文、見出し、リンクの表示名、代替説明、Mermaidへ書かず、要件名・図名・資料名と場所・確認する条件の名前で示す。原資料のquoteは改変しない。生成日時・乱数を加えない。 | validate: scripts/document.py の原本検査とHTML生成、references/authoring.md の3章 |
| OUT-05 | 本文は1段落1論点にする。図は1つの問いに絞り、Mermaid原本は図ごとに6000文字以下、PNGは幅・高さ6000px以下かつ2500万画素以下にする。上限を超えるときは、全体図と業務別の詳細図に分け、要件への参照を保つ。 | validate: scripts/document.py の寸法・原本長検査、references/diagrams.md の3章 |
| OUT-06 | 構造化原本を変更したら build を実行し、HTMLとmanifestを更新する。manifestに原本・Mermaid・PNGのSHA-256を記録する。check はハッシュとHTMLの埋め込みPNGを照合する。図の原本が変わらないときは同じPNGを再利用できる。 | validate: scripts/document.py の check と together の source・html・manifest |
| OUT-07 | 構造化原本は定義済みのキーだけを持ち、skip_validation・ignore_errors・検証済みの自己申告を受け付けない。検査は現在の原本と出力の実体から行う。 | validate: scripts/document.py の原本キーとmanifest検査 |
| OUT-08 | sources に資料の場所と実際の記述の抜粋を保存し、各要件・図・未決事項から source_ids で参照する。HTMLでは根拠の該当箇所へリンクする。未記載の条件を入力に記載した要件として扱わない。 | validate: scripts/document.py の参照・抜粋検査、references/authoring.md の3章 |
| OUT-09 | context・usecase・workflow は作成する。state は状態と変化条件、screen は画面と操作経路、domain は業務概念の関係、sequence は外部との順序が材料にあるときに選ぶ。concept のER・classは概念整理に限定する。component は構成が要件に指定された場合だけ選ぶ。9種類すべての採否と理由を diagram_decisions に残す。DBの物理列・メソッド・未決定の実装構造は design_notes へ分ける。 | validate: scripts/document.py の図の種別・選択記録検査、references/diagrams.md の1章 |
| RPT-01 | 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。 | runtime, validate, review: scripts/run.py の finish と abort が本文を組み立て、.skill-runs/<name>/report.md にも保存する。check と finish が notes.md の形を検査する |
| CTL-01 | 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。 | runtime, validate: scripts/run.py。finish は契約の検査に通らないと終了コード1で終わる |
| CTL-03 | ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。 | runtime, doc: scripts/run.py の start は、聞くべき入力が無いと終了コード3で止まり、質問を出力する。wait は hooks の強制を止める |
| CTL-04 | hooks は、このスキルの実行中（status: active）に、編集の後と応答を終える前に出力を検査する。実行記録への直接の編集は拒否する。実行していないときは何もしない。ユーザーの発言を止めたり書き換えたりしない。 | runtime: scripts/hook.py。install.py が Claude Code（.claude/settings.json）と Codex（.codex/hooks.json）に登録する |

理由・良い例・悪い例は [references/decisions.md](references/decisions.md) にある。
<!-- END GENERATED:decisions -->

## 5. 出力の契約

<!-- BEGIN GENERATED:contract -->
| 出力 | 置き場 | 件数 | 検査（ルールID） |
|---|---|---|---|
| source 要件定義の構造化原本 | `{run}/out/requirement-document.json` | 1〜1 件（OUT-01） | JSON スキーマに合う（OUT-02）。`"language"\s*:\s*"{in:language}"` に一致する行がある（原本の言語を実行時の入力とそろえる）（OUT-02） |
| html 要件定義書のHTML | `{run}/out/requirement-document.html` | 1〜1 件（OUT-01） | `python3 {skill}/scripts/document.py check --source {run}/out/requirement-document.json --out {run}/out` が通る。OUT-01、OUT-02、OUT-04、OUT-05、OUT-06、OUT-07、OUT-08、OUT-09 の指摘も出す（check・finish・応答を終える前だけ。編集の直後は検査しない）（STEP-03） |
| manifest Mermaid・PNGの一覧とハッシュ | `{run}/out/manifest.json` | 1〜1 件（OUT-01） | — |
| mermaid Mermaid原本 | `{run}/out/diagrams/*.mmd` | 3 件以上（OUT-01） | — |

`{run}` は実行記録の置き場 `.skill-runs/write-requirement-document` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。

- 出力 source、html、manifest は一緒に変える。一部だけを変えると OUT-06 の指摘になる（構造化原本を変えたらHTMLとmanifestを再生成する）
<!-- END GENERATED:contract -->

## 6. 完了前チェックリスト

<!-- BEGIN GENERATED:checklist -->
- [ ] STEP-02 業務の条件が未指定なら open_questions に質問と決まらない範囲を書く。本文・図で未決とした条件も、対応する質問と影響範囲へ結び付ける。資料が矛盾すれば各記述を sources に残して未決とし、一方を確定した図へ混ぜない。対象と目的が分かる間は作成を続ける。
- [ ] OUT-03 各節の冒頭で要点を示し、前提、理由、必要な振る舞いをつなぐ。1段落を1論点にし、誰が何をどの条件で行うかを書く。用語を統一し、抽象的な美辞麗句、同義反復、根拠のない価値判断を削る。短くするために前提・例外を落とさない。 否定の範囲を明示し、双方拒否と両立禁止の両方に読める文を使わない。
- [ ] RPT-01 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- [ ] `python3 <skill>/scripts/run.py finish` が終了コード0で終わった
<!-- END GENERATED:checklist -->

## 7. 報告

<!-- BEGIN GENERATED:report -->
最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。決めきれなかったことは、finish の前に `.skill-runs/write-requirement-document/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを「## 補足」に入れる。中断するときは `run.py abort --reason <理由>` を実行し、abort が出力した本文を同じようにそのまま使う。本文の形は次のとおり。

```text
## 結果

write-requirement-document: 完了（検証に合格）

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
| hooks の pre-tool | ファイルを編集する前 | 実行中は実行記録（state.json・report.md）への直接の編集を拒否する。スキル自身のファイルは編集できる |
| hooks の post-tool | ファイルを編集した後 | 出力に当たるファイルを format で直し、検査し、指摘を返す |
| hooks の stop | 応答を終える前 | 出力全体を検査し、通るまで応答を終えさせない（最大 3 回。超えると status: failed） |
| hooks の prompt | ユーザーが発言したとき | 質問待ち（wait）を解くだけ。発言を止めたり書き換えたりしない |

hooks は、このスキルの実行中（`.skill-runs/write-requirement-document/state.json` の status が active）だけ出力を検査する。hooks が無い環境でも、`run.py check` と `finish` が同じ検査をする。

hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（Codex は `.codex/hooks.json` に追記する。Codex では、追記した hooks を `/hooks` で信頼するまで動かない）
<!-- END GENERATED:control -->
