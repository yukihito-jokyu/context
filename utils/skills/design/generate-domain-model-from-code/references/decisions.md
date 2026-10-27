<!-- このファイルは render_skill.py が dev/spec.json から生成する。手で編集しない。 -->

# コードから根拠付きのドメインモデル図を作る の決定

## IN-01 コードがない依頼を中断する

- 軸: I3
- 決定: コードが読めない、対象ファイルが0件、概念が0件のいずれかなら理由を示して中断する。構想図だけの依頼はarchify-jpへ案内する。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: doc: references/model-format.md
- 機械化しない理由: 痕跡が残らない：実行の順序と中断の判断は出力だけでは確定できない
- 良い例:

  ```text
  コードが読めない、対象ファイルが0件、概念が0件のいずれかなら理由を示して中断する。構想図だけの依頼はarchify-jpへ案内する。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## IN-02 指定範囲のコードを調査する

- 軸: I4
- 決定: catalog.py inspectが列挙したファイルとルートのREADME・AGENTS.mdを読む。依存パッケージ・生成物・symlinkは除外する。未読のコードはunreadにパスと理由を書く。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: doc: references/model-format.md
- 機械化しない理由: 痕跡が残らない：実行の順序と中断の判断は出力だけでは確定できない
- 良い例:

  ```text
  catalog.py inspectが列挙したファイルとルートのREADME・AGENTS.mdを読む。依存パッケージ・生成物・symlinkは除外する。未読のコードはunreadにパスと理由を書く。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## STEP-01 調査してから図を生成する

- 軸: P1
- 決定: 受付、start、inspect、コードの読解、model.jsonの作成、build、check、画像とHTMLの確認、finishの順に進める。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: doc: references/model-format.md
- 機械化しない理由: 痕跡が残らない：実行の順序と中断の判断は出力だけでは確定できない
- 良い例:

  ```text
  受付、start、inspect、コードの読解、model.jsonの作成、build、check、画像とHTMLの確認、finishの順に進める。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## STEP-02 概要図と領域別の図を作る

- 軸: P2
- 決定: 全概念を置いたoverviewを1つ作り、領域が2つ以上なら領域別の図も作る。領域は概念の宣言元ファイルの親ディレクトリとする。領域を跨ぐ関係は両端の概念を図へ残す。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: validate, script: scripts/catalog.py のverifyが図の集合とMermaidを再計算する。
- 良い例:

  ```text
  全概念を含むoverviewを1つ作り、領域が2つ以上なら領域別の図も作る。領域を跨ぐ関係は両端の概念を含める。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## STEP-03 派生物をスクリプトで生成する

- 軸: P3
- 決定: AIはmodel.jsonを作る。Mermaid、PNG、HTML、manifest.jsonはcatalog.py buildで生成し、手で書き換えない。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: validate, script: scripts/catalog.py のverifyがMermaidとHTMLを再生成して比較する。
- 良い例:

  ```text
  AIはmodel.jsonを作る。Mermaid、PNG、HTML、manifest.jsonはcatalog.py buildで生成し、手で書き換えない。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## STEP-04 インストール済みのMermaid CLIを使う

- 軸: P4
- 決定: Python 3.9以上、git、インストール済みMermaid CLIとブラウザーを使う。MMDCでCLI、PUPPETEER_EXECUTABLE_PATHでブラウザーを指定する。CLIがなければ中断し、導入が必要と伝える。自動ダウンロードは行わない。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 出力を使う道具や形式の公式の決まり
- 守らせ方: doc: references/model-format.md
- 機械化しない理由: 痕跡が残らない：実行の順序と中断の判断は出力だけでは確定できない
- 良い例:

  ```text
  Python 3.9以上、git、インストール済みMermaid CLIとブラウザーを使う。MMDCでCLI、PUPPETEER_EXECUTABLE_PATHでブラウザーを指定する。CLIがなければ中断し、導入が必要と伝える。自動ダウンロードは行わない。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## STEP-05 変換に失敗したら公開を止める

- 軸: P5
- 決定: 変換失敗、画像不正、根拠の不一致では中断する。全図の変換と検査の成功後に出力を置き換える。古い画像と仮の画像で成功を代替しない。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: doc: references/model-format.md
- 機械化しない理由: 痕跡が残らない：実行の順序と中断の判断は出力だけでは確定できない
- 良い例:

  ```text
  変換失敗、画像不正、根拠の不一致では中断する。全図の変換と検査の成功後に出力を置き換える。古い画像と仮の画像で成功を代替しない。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## STEP-06 生成後に画像の構造を検査する

- 軸: X1
- 決定: checkとfinishでPNGのCRCと圧縮データを検査する。画像とHTMLを開いて文字・関係・検索・絞り込み・拡大・原本取得も確認する。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: validate, script: scripts/catalog.py のverifyがPNGを検査する。
- 良い例:

  ```text
  checkとfinishでPNGのCRCと圧縮データを検査する。画像とHTMLを開いて文字・関係・検索・絞り込み・拡大・原本取得も確認する。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## OUT-01 実行記録配下に出力する

- 軸: O1
- 決定: 出力は実行記録のout/name配下に置く。inventory.json、model.json、index.html、manifest.jsonとdiagrams配下のmmd・pngを保存する。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: validate: 出力契約と scripts/catalog.py のverifyがファイル集合を検査する。
- 良い例:

  ```text
  出力は実行記録のout/name配下に置く。inventory.json、model.json、index.html、manifest.jsonとdiagrams配下のmmd・pngを保存する。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## OUT-02 モデル情報とコード根拠を検査する

- 軸: O2
- 決定: model.jsonはschema_version・title・domains・concepts・relations・questions・unreadを持つ。references/model-format.mdに従い、型・キー・参照先とコードの行・抜粋を検査する。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: validate, template: assets/examples/model.json と scripts/catalog.py のvalidateが型・キー・参照・抜粋を検査する。
- 良い例:

  ```text
  model.jsonはschema_version・title・domains・concepts・relations・questions・unreadを持つ。references/model-format.mdに従い、型・キー・参照先とコードの行・抜粋を検査する。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## OUT-03 日本語の説明とコード識別子を区別する

- 軸: O3
- 決定: 説明は日本語で書く。symbolとコードの抜粋は実装の表記を保持する。名称を翻訳してもコード識別子を変えない。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: review: references/model-format.md
- 機械化しない理由: 意味の判断が要る：説明の言語と識別子の翻訳が意味を変えたかはコードを読んで判断する。
- 良い例:

  ```text
  説明は日本語で書く。symbolとコードの抜粋は実装の表記を保持する。名称を翻訳してもコード識別子を変えない。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## OUT-04 IDと並び順を固定する

- 軸: O4
- 決定: 概念の表示名はsymbol、領域の表示名はpath（.はルート）、関係名はコードのmember（継承は継承）に固定する。確認事項は改行区切りの文字列にする。conceptのIDはkeyのSHA-256先頭12桁にC_を付ける。relationのIDはsource・target・kind・固定した関係名のJSON配列のSHA-256先頭12桁にR_を付ける。domainsはpath、conceptsはkey、relationsはIDで並べる。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, script: scripts/catalog.py のnormalizeとverifyがIDと順序を再計算する。
- 良い例:

  ```text
  conceptのIDはkeyのSHA-256先頭12桁にC_を付ける。relationのIDはsource・target・kind・labelのJSON配列のSHA-256先頭12桁にR_を付ける。domainsはpath、conceptsはkey、relationsはIDで並べる。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## OUT-05 既存の出力を保持する

- 軸: O6
- 決定: 受付時に同名の出力があれば別のnameを聞く。buildは既存の生成結果を拒否する。同じ実行内の修正はgenerate-domain-model-from-codeが生成した出力に限り--replaceで再生成する。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: doc: references/model-format.md
- 機械化しない理由: 痕跡が残らない：実行の順序と中断の判断は出力だけでは確定できない
- 良い例:

  ```text
  受付時に同名の出力があれば別のnameを聞く。buildは既存の生成結果を拒否する。同じ実行内の修正はgenerate-domain-model-from-codeが生成した出力に限り--replaceで再生成する。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## OUT-06 モデルと派生物の対応を検査する

- 軸: O7
- 決定: コード、model、Mermaid、PNG、HTMLのハッシュをmanifestに記録し、checkとfinishで比較する。コードまたはモデルが変わったらinspectとbuildからやり直す。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: validate, script: scripts/catalog.py のverifyがmanifestと実ファイルを比較する。
- 良い例:

  ```text
  コード、model、Mermaid、PNG、HTMLのハッシュをmanifestに記録し、checkとfinishで比較する。コードまたはモデルが変わったらinspectとbuildからやり直す。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## OUT-07 検査の省略指定を拒否する

- 軸: O8
- 決定: model.jsonのskip_validation、no_verify、ignore_errors、disable_checksを拒否する。許可していないキーを追加して検査を止めない。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: validate: scripts/catalog.py のvalidateが検査を省くキーを拒否する。
- 良い例:

  ```text
  model.jsonのskip_validation、no_verify、ignore_errors、disable_checksを拒否する。許可していないキーを追加して検査を止めない。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## OUT-08 概念と関係の意味を根拠で確認する

- 軸: X2
- 決定: 分類の明示がないクラスはconceptにする。entityはEntity基底型かentity注釈、valueはValueObject基底型かvalue_object注釈、enumは列挙宣言かリテラルの選択型のコードを根拠にする。idという属性名やdataclassのfrozenだけで分類しない。参照メンバー・属性・関係種別・多重度の意味をレビューし、断定できない関係種別はassociation、多重度はnullにする。不明点はquestionsに書く。
- 理由: コードの根拠と生成結果を辿れるようにし、実行者による判断の違いを減らす。
- 決め方: 依頼の指定
- 守らせ方: review: references/model-format.md
- 機械化しない理由: 意味の判断が要る：抜粋が存在しても業務上の意味が正しいとは確定しない。
- 良い例:

  ```text
  業務概念を選び、分類・属性・関係名・種別・多重度を根拠から確認する。断定できない分類はconcept、関係種別はassociation、多重度はnullにする。不明な理由をquestionsに書く。
  ```
- 悪い例:

  ```text
  根拠を確認せず出力を変える。
  ```

## RPT-01 最終の返答は finish の本文をそのまま使う

- 軸: R1
- 決定: 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- 理由: 報告の形と中身が AI ごとに分かれない。既定値で決めた値と検証の結果を、読み手が必ず見られる。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, validate, review: scripts/run.py の finish と abort が本文を組み立て、.skill-runs/<name>/report.md にも保存する。check と finish が notes.md の形を検査する
- 良い例:

  ```text
  決めきれなかった既定値を notes.md に「- 」で書き、finish の本文をそのまま返答する
  ```
- 悪い例:

  ```text
  finish の本文を要約し直し、最後に自由な文で補足を足して返答する
  ```

## CTL-01 実行は run.py で始めて終える

- 軸: C1
- 決定: 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。
- 理由: 始まりと終わりをスクリプトで区切ると、検査が必ず走り、hooks が実行中かどうかを判定できる。完了の基準が AI ごとに分かれない。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, validate: scripts/run.py。finish は契約の検査に通らないと終了コード1で終わる
- 良い例:

  ```text
  `run.py finish` が終了コード0で終わってから、その本文で返答する
  ```
- 悪い例:

  ```text
  出力を書いた直後に「完了しました」と返答する
  ```

## CTL-02 実行中はスキル自身のファイルを変えない

- 軸: C2
- 決定: `run.py start` から `run.py finish` までの間、スキルの保護ファイル（`SKILL.md`、`scripts/`、`assets/`、`references/`）と、プロジェクトに登録したこのスキルの hooks を変えない。出力が契約に合わないときは、出力の方を直す。保護ファイルが封印（`assets/seal.json`）と違うと `run.py start` が終了コード1で止まるので、そのときは出力された指摘をユーザーに伝えて止まる。
- 理由: 検査や契約を緩めて通すと、検査が無いのと同じになる。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, validate: scripts/run.py の start が保護ファイルのハッシュと hooks の登録を記録し、check と finish が比べる。`start --restart` は記録を最初の start から引き継ぐ。hooks が編集の前に止める。start は封印と保護ファイルを比べ、違えば始めない
- 良い例:

  ```text
  指摘されたルールIDを決定表で引き、出力のファイルを直す
  ```
- 悪い例:

  ```text
  検査に通すために `assets/contract.json` の正規表現を緩める
  ```

## CTL-03 質問は start の前に済ませる

- 軸: C3, I2
- 決定: ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。
- 理由: 実行の途中で質問するかどうかが AI ごとに分かれると、出力が揃わない。wait を挟むと、質問のために応答を終えることを hooks が止めない。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, doc: scripts/run.py の start は、聞くべき入力が無いと終了コード3で止まり、質問を出力する。wait は hooks の強制を止める
- 良い例:

  ```text
  start の終了コード3で出た質問をユーザーに聞き、答えを `--set` で渡して start をやり直す
  ```
- 悪い例:

  ```text
  出力を半分書いたところで、形式をユーザーに尋ねる
  ```

## CTL-04 hooks は出力の検査だけに使い、入力を止めない

- 軸: C4
- 決定: hooks は、このスキルの実行中（status: active）に、編集の後の検査、応答を終える前の検査、保護ファイルの編集の停止の3つを行う。実行していないときは、封印したスキル（`assets/seal.json` がある）の保護ファイルの編集に、Claude Code で確認を求めることだけを行う。ユーザーの発言を止めたり書き換えたりしない。
- 理由: 縛る対象は AI の出力であり、ユーザーの入力ではない。このスキルを使っていないセッションの邪魔をしない。ただし、実行していない間にスキル自身が変わると、次の実行の検査が緩んだままになるので、封印したファイルの編集だけは人に確かめさせる。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime: scripts/hook.py。install.py が Claude Code（.claude/settings.json）と Codex（.codex/hooks.json）に登録する
- 良い例:

  ```text
  Stop の hook が、検査に通るまで応答の終了を差し戻す
  ```
- 悪い例:

  ```text
  UserPromptSubmit の hook で、依頼文の書き方が違うと拒否する
  ```

## CTL-05 契約の出力のほかにファイルを変えない

- 軸: C5
- 決定: `run.py start` から `run.py finish` までの間に作る・変えるファイルは、「5. 出力の契約」の出力と `control.allow_changes` に挙げたものだけにする。作業用のメモや一時ファイルも、出力の置き場の外に作らない。
- 理由: 出力の外に作るファイル（メモ、控え、別名の写し）は AI ごとに違い、利用者のリポジトリに残る。
- 決め方: 機械で守らせられる答え
- 守らせ方: runtime, validate: scripts/run.py の start が git の作業ツリーの状態を記録し、check と finish が比べる。編集の直後には hooks が知らせる
- 良い例:

  ```text
  下書きも出力の置き場（`.skill-runs/<name>/`）の中に書く
  ```
- 悪い例:

  ```text
  リポジトリの直下に `notes.md` を作って下書きする
  ```
