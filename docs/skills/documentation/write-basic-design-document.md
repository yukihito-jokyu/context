---
title: write-basic-design-document — 図と採用理由がつながる基本設計書
sidebar_label: write-basic-design-document
---

# write-basic-design-document

会話・議事録・箇条書きの要望から、開発者が詳細設計へ進める基本設計書をMarkdownとHTMLで作ります。構成・画面・データ・外部連携について、設計案と採用理由を図に結び付けます。編集するJSON原本、Mermaid原本、図のPNGも保存します。

## 依頼例

```text
次の会話メモから、開発者が詳細設計へ進める基本設計書を作ってください。
社員が研修を選んで参加を申し込み、本人が取り消せるようにします。
研修担当者は定員と開催日を登録します。定員を超える申込みは確定させません。
外部システムとの連携はありません。技術と取消期限は未定です。
設計案と理由を図で示し、未決事項は確認する質問と影響を残してください。
```

対象と課題が分かれば、未指定の条件を残したドラフトを作ります。要望の事実、新しい提案、未決の設計を区別し、提案を承認済みとして扱いません。資料が矛盾するときは両方の記述を残します。

背景・業務・必要な振る舞いの整理を中心とする場合は、[write-requirement-document](write-requirement-document.md)を使います。基本設計では、その要望をどの責務・画面・データ・連携で実現するかと、選ぶ理由まで示します。物理列・索引・メソッドの定義は詳細設計へ引き継ぎます。

## 図と短い説明で読む

本文は、概要、前提と要望、全体構成、画面と操作、データ設計、外部連携、品質と運用、未決事項と詳細設計への引継ぎ、根拠と補足の順に並びます。図を各観点の章に置き、直前に見る目的、直後に読み取る要点を添えます。

- 全体構成・責務・処理・データ関係の図を作ります。
- 画面がある場合は画面の図、外部連携がある場合は順序を示す図も作ります。
- 状態遷移・配置を含む8種類の図について、採否と理由を残します。
- 要望から設計、図、資料の場所と抜粋へ、内容が分かる名前で移動できます。
- 未決の条件には、確認する質問と、決まるまで確定できない範囲を結び付けます。

独自に作った英字の略語を避け、一般的な技術用語も初出で意味を説明します。短くするために前提や例外を落とさず、段落ごとに1つの論点を説明します。

Markdownは、番号付き見出しと目次、用語・役割の表で読み進められます。図は導入、画像、拡大・定義のリンク、要点、関連設計の順で示します。参考にした要件定義書の書式を使いながら、設計内容と採用理由、詳細設計への引継ぎを中心にします。

## 進め方

1. 要望と資料の抜粋を整理し、設計案と採用理由を原本へ書きます。
2. ローカルのMermaid CLIで図をPNGへ変換し、MarkdownとHTMLを生成します。
3. 参照、図の種類、PNGの実体、原本・画像・Markdown・HTMLの同期を検査します。
4. 本文と図の条件・用語・順序、提案と未決事項、文章のつながりを確認します。

出力は`.skill-runs/write-basic-design-document/out/`に保存します。HTMLにはPNGを埋め込み、原寸表示・代替説明・Mermaid原本を付けます。HTML単体で閲覧でき、元の図も再利用できます。Markdownは同梱PNGを表示し、Mermaid原本へも相対リンクを付けるため、共有時は`out/`一式またはZIPを渡します。

```text
out/
├── basic-design-document.json
├── basic-design-document.md
├── basic-design-document.html
├── manifest.json
└── diagrams/
    ├── d-01-context.mmd
    ├── d-01-context.png
    └── ...
```

Python 3.9以上、Node.js、既存のMermaid CLI 11以降と対応ブラウザが必要です。`document.py doctor`で経路と版を確認します。描画経路は`BASIC_DESIGN_MMDC`、ブラウザは`BASIC_DESIGN_BROWSER`で指定できます。パッケージの自動導入は行いません。

編集する正本は`utils/skills/documentation/write-basic-design-document/`です。hooksをまとめて配布する場合は[plugin配布の方針](../../plugins/distribution.md)を適用します。このスキルのplugin配布物と公開カタログは未作成です。リポジトリ内での検査と、利用者環境への導入・有効化は別に扱います。

## 成果物の例

研修申込みの会話メモから、構成・画面・論理データの設計案と採用理由を6図で示す基本設計書を、MarkdownとHTMLで新しく作りました。二重申込みと定員超過を確定させない条件を設計へつなぎ、利用技術・取消期限・空き枠待ちなどの未決事項には質問と影響を残しています。

**到達点：新規執筆、6図の描画・画像確認、MarkdownとHTMLの同期検査、finishまで完了。HTMLのブラウザ検査、対象アプリの動作試験と設計案の採用承認は未実施。**

### 実行した依頼

```text
次の会話メモから、開発者が詳細設計へ進める基本設計書をMarkdownとHTMLで作ってください。
社員が社内研修を選んで参加を申し込み、本人が取り消せるようにします。研修担当者は研修名、開催日、定員を登録します。同じ社員の二重申込みと、定員を超える申込みは確定させません。社員は自分の申込み結果を確認できます。外部システムとの連携はありません。使う技術、取消期限、取消後の空き枠を待つ仕組みの要否は未定です。設計案と採用理由を図で示し、未決事項は確認する質問と影響を残してください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
## 結果

write-basic-design-document: 完了（検証に合格）

## 出力

- `.skill-runs/write-basic-design-document/out/basic-design-document.json`（source 基本設計の構造化原本）
- `.skill-runs/write-basic-design-document/out/basic-design-document.html`（html 基本設計書のHTML）
- `.skill-runs/write-basic-design-document/out/basic-design-document.md`（markdown 基本設計書のMarkdown）
- `.skill-runs/write-basic-design-document/out/manifest.json`（manifest 図と原本の対応とハッシュ）
- `.skill-runs/write-basic-design-document/out/diagrams/d-01-context.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-basic-design-document/out/diagrams/d-02-component.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-basic-design-document/out/diagrams/d-03-workflow.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-basic-design-document/out/diagrams/d-04-screen.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-basic-design-document/out/diagrams/d-05-data.mmd`（mermaid Mermaid原本）
- `.skill-runs/write-basic-design-document/out/diagrams/d-06-state.mmd`（mermaid Mermaid原本）
````

### 成果物を取得する

- [基本設計書Markdown](pathname:///skills/write-basic-design-document/out/basic-design-document.md#download)
- [基本設計書HTML](pathname:///skills/write-basic-design-document/out/basic-design-document.html#download)
- [原本JSON](pathname:///skills/write-basic-design-document/out/basic-design-document.json#download)
- [全出力ZIP](pathname:///skills/write-basic-design-document/basic-design-document.zip#download)
- [検証結果](pathname:///skills/write-basic-design-document/verification.md#download)
- [実コマンドと検証](pathname:///skills/write-basic-design-document/validation.json#download)
- [実際のHTMLをブラウザで開く](pathname:///skills/write-basic-design-document/out/basic-design-document.html)
- [実行入力の原本](pathname:///skills/write-basic-design-document/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/write-basic-design-document/execution.json#download)

### 確認した結果

- 最新の正本全52ファイルをコピーした新しい作業場所で、独立担当が会話メモから原本を新規執筆しました。実行前後の正本と実行用コピーの一覧・ハッシュが一致しています。
- start・doctor・build・check・finishを実行し、最終build・check・finishは終了コード0、指摘0件でした。初回のブラウザ起動失敗と、環境の承認手順を使った同じbuildの再実行も記録しています。
- 要望5件、設計6件、未決事項7件、引継ぎ4件を整理し、境界・責務・処理・画面・データ関係・状態の6図を生成しました。外部連携をしない理由も記載しています。
- MarkdownをGFMのパーサで読み、本文154項目、6画像、238リンク、番号付き9章、3表を確認しました。本文の欠落・文書内や同梱ファイルへのリンク切れは0件です。
- 全6 PNGを開き、文字と矢印の表示、原資料・本文・採用理由との意味の一致を確認しました。長いラベルを調整して再確認し、再申込み条件が未決である処理図の適用範囲も明記しています。
- 同じJSON原本から生成したMarkdownとHTMLを同期検査しました。Markdownは同梱図を含む一式で、HTMLは画像を埋め込んだ単体ファイルで閲覧できます。
- ZIPのCRCと出力16ファイルのパス・内容の一致を検査しました。公開記録では一時作業の経路と環境情報を省略し、生成したout内のファイルは変更していません。
- 未決事項には質問と影響を残し、引継ぎの重複を比較しました。HTMLのブラウザ検査、設計案の採用承認、対象アプリの動作試験は行っていません。

## 確認するポイント

- 開発者が4つの設計観点と採用理由を理解し、詳細設計へ進めるか。
- 図の主体・条件・順序・データ関係が本文と一致しているか。
- 未指定や矛盾を勝手に確定せず、質問と影響範囲を残しているか。
- 長い説明や独自の略語に頼らず、前提から理由へつながっているか。
- 要望・設計・図から、根拠の実際の記述へ移動できるか。

## 更新版の検証範囲

MarkdownとHTMLを出力する更新版では、3題材を各2名が独立に作成する測定を2回行いました。12件すべてで生成・同期検査が通り、Markdownの本文欠落とリンク切れは0件でした。内容の独立評価は48判定中47件が合格し、1件は本文と補足の説明重複で不合格でした。

設計項目の分け方や図中の内部名などに差が残り、3題材とも収束基準には届いていません。測定値と不合格判定は変更せず、利用者の指定で2回目をもって終了しました。最後に使う別題材（holdout）と、違反を入れた見本を使うレビュー検出率の測定は未実施です。Claude CodeとCodexの製品間比較も行っていません。

手元のカタログHTMLには、2回分の測定値・操作記録・独立評価と残った指摘を反映しています。個人の経路を含む生の操作記録は公開成果物に含めていません。

## 正本を読む

手順と契約は[SKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/documentation/write-basic-design-document/SKILL.md)、原本の書き方は同梱の`references/authoring.md`にあります。
