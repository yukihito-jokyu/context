<!-- このファイルは render_skill.py が dev/spec.json から生成する。手で編集しない。 -->

# ユースケース図をPNGとHTMLカタログにする の決定

## IN-01 対象と材料を確かめる

- 軸: I3
- 決定: 対象システム・アクター・機能が分からないときはstartの前に確認する。シーケンス図・ER図・状態遷移図の依頼はarchify-jpへ案内し、Web公開の依頼は公開先を確認する。
- 理由: 承認済み計画の入力と出力を維持するため。
- 決め方: 依頼の指定
- 守らせ方: doc: SKILL.mdの手順1、references/authoring.md。
- 機械化しない理由: 痕跡が残らない：材料が無い場合の確認と対象外への案内は出力に残らない。
- 良い例:

  ```text
  会員が蔵書を検索する要件で会員と検索を描く。
  ```
- 悪い例:

  ```text
  注文の要件に認証・決済を無断で追加する。
  ```

## IN-02 入力と構文資料を読む

- 軸: I4
- 決定: 指定された入力ファイルと依頼文、references/authoring.md、assets/examples/request.jsonを読む。入力が参照するリポジトリを調べるときは対象機能の根拠を読む。無関係な機能から要件を補わない。
- 理由: 承認済み計画の入力と出力を維持するため。
- 決め方: 依頼の指定
- 守らせ方: doc: SKILL.mdの手順2、references/authoring.md。
- 機械化しない理由: 痕跡が残らない：読んだ範囲を出力だけで確定できない。
- 良い例:

  ```text
  指定要件の検索機能だけを確認する。
  ```
- 悪い例:

  ```text
  全リポジトリから機能を推測する。
  ```

## STEP-01 受付から検査まで順に進める

- 軸: P1
- 決定: 質問を済ませ、run.py start、入力の整理、catalog.py build、PNGとHTMLの目視、run.py check、run.py finishの順に実行する。
- 理由: 出力の対応を機械で検査し、実行者による違いを減らすため。
- 決め方: 機械で守らせられる答え
- 守らせ方: doc: SKILL.mdの手順1〜8。
- 機械化しない理由: 痕跡が残らない：実行順序は出力の字面だけでは確定できない。
- 良い例:

  ```text
  生成と目視の後にcheckとfinishを実行する。
  ```
- 悪い例:

  ```text
  描画せず完了とする。
  ```

## STEP-02 要件文と既存Mermaidを分けて扱う

- 軸: P2
- 決定: 要件文からは明示されたアクター・機能・関係をMermaidにする。既存Mermaidは原本を保持して検査する。includeは必須処理、extendは条件付き追加、汎化は明示された継承関係がある場合だけ使う。
- 理由: 承認済み計画の入力と出力を維持するため。
- 決め方: 依頼の指定
- 守らせ方: doc: SKILL.mdの手順3、references/authoring.md。
- 機械化しない理由: 痕跡が残らない：入力を解釈して分岐した時点の行為は出力だけでは確定できない。
- 良い例:

  ```text
  注文時の必須支払処理をincludeで表す。
  ```
- 悪い例:

  ```text
  クーポンという名だけでextendを追加する。
  ```

## STEP-03 変換と構造の取得をスクリプトに任せる

- 軸: P3
- 決定: scripts/catalog.py buildがMermaidからPNG・HTMLを生成する。scripts/render_diagram.pyがMermaidの構文解析結果からアクター・境界・関係を取得する。catalog.jsonへこれらの情報を手入力しない。
- 理由: 出力の対応を機械で検査し、実行者による違いを減らすため。
- 決め方: 機械で守らせられる答え
- 守らせ方: script, validate: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonのcommand検査。
- 良い例:

  ```text
  原本から取得したアクターと画像を同じカードに示す。
  ```
- 悪い例:

  ```text
  原本にないアクターをカタログへ手入力する。
  ```

## STEP-04 既存のMermaidとChromeを使う

- 軸: P4
- 決定: Python 3.9以上の標準ライブラリ、Mermaid 12の完全版mermaid.min.js、ChromeのCDP pipeを使う。catalog.py preflightで版とパスを確認する。追加のパッケージを導入しない。描画中のHTTP・HTTPS接続を遮断する。
- 理由: 追加の依存を導入せず、既存環境で実行するため。
- 決め方: 道具・スクリプト・入力を増やさない答え
- 守らせ方: script, doc: scripts/catalog.py、scripts/render_diagram.py。SKILL.mdの手順2。
- 機械化しない理由: 痕跡が残らない：利用した起動コマンドと接続の全履歴は出力に残らない。
- 良い例:

  ```text
  既存の完全版Mermaidと一時Chromeプロファイルを使う。
  ```
- 悪い例:

  ```text
  CDNからスクリプトを読み込む。
  ```

## STEP-05 失敗時は正常な出力を残す

- 軸: P5
- 決定: 入力検査・描画・PNG検査・HTML検査が失敗したら終了コード1で止める。生成は作業領域で行い、全図が成功してから出力先へ確定する。失敗した図を省いてカタログを成功扱いしない。
- 理由: 承認済み計画の入力と出力を維持するため。
- 決め方: 依頼の指定
- 守らせ方: script, doc: scripts/catalog.py。SKILL.mdの手順4。
- 機械化しない理由: 痕跡が残らない：失敗時の原子的な確定は正常出力だけでは確定できない。
- 良い例:

  ```text
  2枚目の失敗時に以前の正常なカタログを残す。
  ```
- 悪い例:

  ```text
  失敗したPNGの代わりに古いPNGを載せる。
  ```

## STEP-06 原本と画像とHTMLを検査する

- 軸: X1
- 決定: catalog.py checkで全図の原本、PNGの全チャンクCRCと展開データ、HTML、変換記録を検査する。PNGとHTMLを目視し、日本語の欠け・関係線の重なり・一覧と拡大と原本取得を確認する。未確認の目視はvalidation.jsonのvisual_reviewをpendingにする。 catalog.py previewで一覧・検索・拡大・原本リンクを検査し、実行記録のpreview.pngとpreview.jsonへ画面とハッシュを保存する。reviewは対応する画面記録が無ければ止める。notes.mdは未確認が無い場合も「- なし」を保存する。
- 理由: 出力の対応を機械で検査し、実行者による違いを減らすため。
- 決め方: 機械で守らせられる答え
- 守らせ方: script, validate: scripts/catalog.py。catalog.jsonのcommand検査。
- 良い例:

  ```text
  検査に成功し目視待ちはpendingと示す。
  ```
- 悪い例:

  ```text
  画像を開かず目視済みとする。
  ```

## OUT-01 出力先とファイルを固定する

- 軸: O1
- 決定: artifacts/usecase/{in:name}/にcatalog.json、index.html、validation.json、diagrams/<id>.mmdと同名の.pngを出力する。図ごとに原本と画像を1つずつ持ち、相対パスの参照先を検査する。
- 理由: 承認済み計画の入力と出力を維持するため。
- 決め方: 依頼の指定
- 守らせ方: validate, script: scripts/catalog.py。出力のpath・countとcatalog.jsonのcommand検査。
- 良い例:

  ```text
  diagrams/d01.mmdとdiagrams/d01.pngを対応させる。
  ```
- 悪い例:

  ```text
  画像のない図を掲載する。
  ```

## OUT-02 原本とカタログの構造を揃える

- 軸: O2
- 決定: 原本はusecase-betaを使い、全アクターと全ユースケースを明示宣言する。アクターはシステム境界の外、ユースケースは境界の中に置く。catalog.jsonはschema_version・title・description・diagramsを持つ。HTMLは一覧・PNG拡大・原本表示・PNGと原本の取得を備える。
- 理由: 実行環境と公式の構文に合わせ、原本と表示の解釈を揃えるため。
- 決め方: 出力を使う道具や形式の公式の決まり
- 守らせ方: validate, script: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonとindex.htmlのcommand検査。
- 良い例:

  ```text
  actor A01と境界内U01を宣言して関連を結ぶ。
  ```
- 悪い例:

  ```text
  未宣言端点を暗黙ユースケースとして受け入れる。
  ```

## OUT-03 入力の意味と表示文を一致させる

- 軸: O3
- 決定: 図題名・説明・ラベルは入力の言語と意味を保つ。日本語の入力には日本語の説明を書く。入力にない機能・権限・include・extend・汎化を追加しない。
- 理由: 承認済み計画の入力と出力を維持するため。
- 決め方: 依頼の指定
- 守らせ方: review: 完了前に入力と図・カタログの説明を照合する。
- 機械化しない理由: 意味の判断が要る：要件と機能・関係の一致は字面だけでは判定できない。
- 良い例:

  ```text
  検索の要件を検索の図と説明にする。
  ```
- 悪い例:

  ```text
  検索の要件を個人情報の公開機能として説明する。
  ```

## OUT-04 IDと並び順を固定する

- 軸: O4
- 決定: カタログ名の指定がない場合と「お任せ」の場合はcatalogを使い、対象システムから名前を作らない。カタログ名と図IDは小文字kebab-caseにし、図IDを重複させない。利用者が図IDを指定しない場合は、入力の機能範囲の順にd01・d02から振る。図はIDの昇順にする。新規Mermaidの要素IDは登場順にA01・U01・S01から振る。既存Mermaidの明示IDは保持し、宣言の重複を拒否する。
- 理由: 出力の対応を機械で検査し、実行者による違いを減らすため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, script: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonのcommand検査。
- 良い例:

  ```text
  d01とd02の順で表示する。
  ```
- 悪い例:

  ```text
  同じ図IDを2回使う。
  ```

## OUT-05 図と画像の上限を定める

- 軸: O5
- 決定: 1カタログは1〜24図、1図のアクターとユースケースの合計は2〜40個とする。PNGの縦横は各12000px以下、面積は30000000px以下とする。上限を超える場合は機能範囲で図を分ける。
- 理由: 出力の対応を機械で検査し、実行者による違いを減らすため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, script: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonのcommand検査。
- 良い例:

  ```text
  2枚に分割して全機能を残す。
  ```
- 悪い例:

  ```text
  上限を超える要素を黙って捨てる。
  ```

## OUT-06 既存の出力を明示した範囲で更新する

- 軸: O6
- 決定: 既存出力はbuildの--replaceがあるときだけ更新する。--replaceはカタログ更新の依頼がある場合だけ付ける。出力が一致する場合は既存出力を再利用する。未管理ファイルを持つ出力先とシンボリックリンクの出力先は変更せず止める。
- 理由: 承認済み計画の入力と出力を維持するため。
- 決め方: 依頼の指定
- 守らせ方: script, doc: scripts/catalog.py。SKILL.mdの手順4、references/authoring.md。
- 機械化しない理由: 痕跡が残らない：上書き前の内容と更新依頼の有無は正常出力だけでは確定できない。
- 良い例:

  ```text
  更新依頼に対して同名カタログだけを置換する。
  ```
- 悪い例:

  ```text
  既存ディレクトリを無条件に全削除する。
  ```

## OUT-07 関連ファイルの対応を検査する

- 軸: O7
- 決定: catalog.jsonの図ID・原本・PNG・アクター・境界、index.htmlの表示内容、validation.jsonの原本とPNGとHTMLとカタログのSHA-256を一致させる。PNGはUTF-8検査の対象にせず、catalog.jsonのcommand検査からバイナリを検査する。
- 理由: 出力の対応を機械で検査し、実行者による違いを減らすため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, script: scripts/catalog.py。catalog.jsonのcommand検査。
- 良い例:

  ```text
  原本が変わると画像と変換記録も更新する。
  ```
- 悪い例:

  ```text
  原本だけを差し替えて古い画像を再利用する。
  ```

## OUT-08 検査を省く指定を拒否する

- 軸: O8
- 決定: Mermaidのinitディレクティブ・frontmatterで描画設定を上書きしない。validation.jsonは全図の成功を記録し、skip・ignoreによる検査の省略を認めない。HTMLは外部スクリプトと外部画像を読み込まない。
- 理由: 出力の対応を機械で検査し、実行者による違いを減らすため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, script: scripts/catalog.py、scripts/render_diagram.py。catalog.jsonのcommand検査。
- 良い例:

  ```text
  securityLevel strictと固定レイアウトで描画する。
  ```
- 悪い例:

  ```text
  描画失敗をskipで無視する。
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
