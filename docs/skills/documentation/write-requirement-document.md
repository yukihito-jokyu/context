---
title: write-requirement-document — 前提と図がつながる要件定義書
sidebar_label: write-requirement-document
---

# write-requirement-document

会話・議事録・箇条書きの要望から、新規システムの要件定義書をHTMLにします。業務担当者と開発者が、何の課題を解き、どこまで作り、誰が何をできる必要があるかを同じ理解で確認するためのスキルです。編集する原本、Mermaid原本、図のPNGも保存します。

## 依頼例

```text
次のメモから、業務担当者と開発者が読む要件定義書をHTMLで作ってください。
部署ごとの紙台帳では、同じプロジェクターの予約が重なります。
社員は空き時間を確認して予約し、自分の予約を取り消せます。
管理担当者は備品を登録します。貸出・返却の記録と購入は対象外です。
未指定の条件は未決事項として残してください。
```

資料の場所がある場合は、依頼に添えます。課題と対象が分かる間はドラフトを作り、未指定や矛盾を未決事項として残します。記載された要望を、承認済みの要件とは扱いません。

## 読みやすさを作る方法

要件定義書の中心を「何の課題を、誰のどの振る舞いで解決するか」に置きます。冒頭で要点をつかみ、用語と範囲を確認してから、図と個々の要件へ進める順序です。

- 前提と用語を説明し、読者に背景を推測させません。
- 図の直前に見る目的、直後に要点と関連要件を置きます。
- 本文・見出し・図・リンクは内容が分かる名前で示し、内部の識別記号を表示しません。
- 各段落を1つの論点に絞り、前提・理由・条件を文でつなぎます。
- 抽象語や同義の反復を削り、必要な前提と例外を残します。
- 未決事項を文字で示し、確定した内容と区別します。
- 未決と示した条件を、確認する質問と、決まるまで確定できない範囲へ結び付けます。
- 本文は検索・コピーできるHTML文字、図は代替説明と原寸表示を備えたPNGにします。

この構成は[W3C COGA](https://www.w3.org/TR/coga-usable/)の明確な構造、短い文章、暗黙の前提の説明を参照しています。読みやすさは見た目だけでは決まらないため、文章と図の意味も原資料と照合します。

## 図の選択

システムコンテキスト図・ユースケース図・業務フロー図を作ります。状態遷移図は、状態と変化条件の材料があるときに作ります。画面遷移図・ドメインモデル図・シーケンス図は、画面と操作経路、業務概念、外部との順序を説明する材料があるときに選びます。9種類すべてについて、採否と理由を残します。

ER図・クラス図は概念整理に使い、物理DBや実装構造の詳細は設計へ引き継ぎます。コンポーネント図は、構成自体が要件として指定される場合に作ります。

## 進め方

1. 原資料から課題・範囲・業務・要件・未決事項を整理します。
2. 構造化原本を作り、要件と図の参照、資料の場所と抜粋を書きます。
3. ローカルのMermaid CLIで図をPNGにし、HTMLを生成します。
4. 参照、PNGの実体、原本とHTMLの同期を検査し、意味のつながりを確認します。

出力は`.skill-runs/write-requirement-document/out/`へ保存します。HTMLには画像を埋め込むため、HTML単体でも読めます。原本と再利用用の画像は一式で保管します。

```text
out/
├── requirement-document.json
├── requirement-document.html
├── manifest.json
└── diagrams/
    ├── d-01-context.mmd
    ├── d-01-context.png
    └── ...
```

Python 3.9以上と、既存のMermaid CLI 11以降・Node.js・対応ブラウザが必要です。自動インストールは行いません。描画経路を明示するときは`REQUIREMENT_MMDC`、ブラウザは`REQUIREMENT_BROWSER`を指定します。今回の生成環境で確認した経路はmacOSのChromeです。

導入には[write-requirement-document plugin](../../plugins/write-requirement-document.md)を使います。編集する正本は `utils/skills/documentation/write-requirement-document/` に保ち、`.agents/skills`・`.codex/skills` へ本体やリンクを置きません。hooksの設定と呼び出し口はplugin側が管理し、正本の汎用検査ランタイムを呼びます。pluginの入口に従い、単体配置用の `install.py` は実行しません。

Codex・Claude Code向けの配布物を生成できます。ビルドと検証は、製品へのインストール・有効化・hooksの信頼設定とは別です。導入方法と配布物はpluginのガイドを参照してください。

plugin の指摘収集は hooks による追加機能です。収集の指示はスキル本文へ追加せず、hooks を有効にしたときだけ案内します。無効時も要件定義書の作成・検証・出力は機能します。確認画面での承認と収集データの利用は [plugin ガイド](../../plugins/write-requirement-document.md) を参照してください。

## 成果物の例

undefined

**到達点：会話メモから新規執筆し、5図を描画・目視・検査してhooksなしで完了。実承認と独立モデル評価は未実施。。**

### 実行した依頼

```text
次の会議室予約の会話メモから、業務担当者と開発者が確認する要件定義書をHTMLで作ってください。現在は口頭で予約していて、同じ会議室の利用時間が重なります。社員は会議室の空き時間を確認し、会議室と開始・終了時刻を指定して予約できます。同じ会議室の重複する時間帯の予約は受け付けません。施設管理担当者は予約できる会議室を登録します。社員は自分の確定した予約を取り消せます。予約の状態は確定・取消で、取消から確定には戻せません。未指定の条件や業務範囲は未決事項として残してください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
最終の返答は、次の本文をそのまま使う。前後に文を足さず、要約しない。
========================================
## 結果

write-requirement-document: 完了（検証に合格）

## 出力

- `.skill-runs/write-requirement-document/out/requirement-document.json`（source 要件定義の構造化原本）
- `.skill-runs/write-requirement-document/out/requirement-document.html`（html 要件定義書のHTML）
- `.skill-runs/write-requirement-document/out/manifest.json`（manifest Mermaid・PNGの一覧とハッシュ）
- `.skill-runs/write-requirement-document/out/diagrams/d-01-context.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-requirement-document/out/diagrams/d-02-usecase.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-requirement-document/out/diagrams/d-03-workflow.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-requirement-document/out/diagrams/d-04-workflow.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-requirement-document/out/diagrams/d-05-state.mmd`（mermaid Mermaid原本）
````

### 成果物を取得する

- [要件定義書HTML](pathname:///skills/write-requirement-document/out/requirement-document.html#download)
- [原本JSON](pathname:///skills/write-requirement-document/out/requirement-document.json#download)
- [全出力ZIP](pathname:///skills/write-requirement-document/requirement-document.zip#download)
- [検証結果](pathname:///skills/write-requirement-document/verification.md#download)
- [実コマンドと検証](pathname:///skills/write-requirement-document/validation.json#download)
- [再描画用スクリプト](pathname:///skills/write-requirement-document/reproduce_skill.py#download)
- [実行入力の原本](pathname:///skills/write-requirement-document/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/write-requirement-document/execution.json#download)

### 確認した結果

- 新しいOS一時場所へ正本全44ファイルをコピーし、最新SKILLと資料を読んで会議室予約の会話メモから新たに原本を執筆した。古い成果物は使用していない。
- hooksを呼ばずにstart/build/check/finishを完了した。collectorの呼出しと収集ディレクトリの作成は0件。
- document.py buildとrun.py check/finishは終了コード0、指摘0件。既存の描画経路のみ利用した。
- 機能要件6件、未決事項6件とその影響、9種類の採否を整理し、5枚のMermaid・PNGを生成した。
- 全5枚のPNGを開き、ラベルの欠け・つぶれと本文・原資料の条件の一致を確認した。
- 対象外の業務、時刻境界、同時申込みの採否、入力条件、取消の条件、品質目標を未決事項へ結び付けた。取消から確定へ戻せない条件は確定事項として維持した。
- ZIPのCRCと全出力13ファイルのパス・内容が実出力と一致することを確認した。
- sourceManifestで実行前後と実行用コピーの正本全44ファイルの一致を確認した。公開ログの個人パスはマスクした。
- 公開再描画スクリプトを別の新規一時場所で--finish付きで実行し、終了コード0と正本不変、収集ディレクトリ未作成を確認した。再描画の目視未実施はその実行の補足へ明記した。

## 確認するポイント

- 背景と目的、利用者、対象外が、口頭の補足なしに分かるか。
- 図の条件・用語・順序が本文と一致しているか。
- 短くするために前提・例外を落としていないか。
- 未指定の条件と実装案を、確定した要件へ混ぜていないか。
- 原本と図とHTMLが同期し、根拠の記述へ移動できるか。

## 正本を読む

手順、契約、HTMLの思想は[SKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/documentation/write-requirement-document/SKILL.md)と、同梱の`references/html-principles.md`にあります。
