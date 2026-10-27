<!-- このファイルは render_skill.py が dev/spec.json から生成する。手で編集しない。 -->

# 業務の概念と関係を図とカタログにする の決定

## IN-01 材料が無ければ質問し対象外は中断する

- 軸: I3
- 決定: 業務資料が無ければ start の前に資料を聞く。ER図または全コードクラスの列挙だけを求める依頼では start せず archify-jp を案内する。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 依頼の指定
- 守らせ方: doc: SKILL.md の手順1
- 機械化しない理由: 痕跡が残らない：出力を作る前の質問と案内は出力の字面で判定できない
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## IN-02 指定された資料と対応する定義を読む

- 軸: I4
- 決定: 読む範囲は利用者が渡した業務説明、仕様、classDiagram、指定したパスとその用語を定義する参照先にする。各図の sources に参照先と実際の記述を残す。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 依頼の指定
- 守らせ方: doc: SKILL.md の手順3
- 機械化しない理由: 痕跡が残らない：読む操作の範囲は最終出力から確定できない
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## STEP-01 資料から原本を作り変換して検査する

- 軸: P1, P2, P3
- 決定: start → inspect → 資料を読む → catalog.json と .mmd を書く → build → check → finish の順にする。既存カタログは update=true のときだけ更新し、既存IDを維持して追加と内容修正を行う。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 機械で守らせられる答え
- 守らせ方: script, doc: scripts/catalog.py の inspect、build、check。SKILL.md の手順2〜7
- 機械化しない理由: 痕跡が残らない：操作の順序は生成後のファイルだけでは確定できない
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## STEP-02 既存のMermaid CLIだけでPNGへ変換する

- 軸: P4
- 決定: Python 3.9以上と既に導入された mmdc を使う。mmdc は引数 --mmdc、環境変数 DOMAIN_MODEL_MMDC、PATH の順に選ぶ。deps で版を確認する。不足時は references/setup.md の導入手順を提示し、インストールせず中断する。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 出力を使う道具や形式の公式の決まり
- 守らせ方: script, doc: scripts/catalog.py の deps と build。references/setup.md
- 機械化しない理由: 痕跡が残らない：インストールを実行したかは生成後のファイルだけでは判定できない
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## STEP-03 失敗したら完成扱いを止める

- 軸: P5
- 決定: build または check が非0なら診断を読み、入力か生成対象を直して再実行する。環境不足を直せないときは run.py abort に実際の理由を渡す。既存の正常な画像とHTMLは全図の変換が成功してから置き換える。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 機械で守らせられる答え
- 守らせ方: script, doc: scripts/catalog.py の build と check。SKILL.md の手順6
- 機械化しない理由: 痕跡が残らない：失敗時は新しい成功出力が存在しない
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## STEP-04 変換結果を検査してから完了する

- 軸: X1
- 決定: validation.json の status は passed、renderer.name は mermaid-cli、renderer.version は空でない文字列にする。各PNGの署名・CRC・寸法・IDAT・終端を検査する。生成したPNGとHTMLを表示して日本語と図の欠けを確認し、notes.md は「- 資料照合: 」「- PNG表示: 」「- HTML操作: 」の順で3行にする。値は「確認済み」または「未実施（実際の理由）」だけにし、理由は英字を含まない日本語で書き、参照パスや識別子は書かない。詳細な根拠と未確認事項はカタログに残す。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, script: scripts/catalog.py の check と build、SKILL.md の手順7
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## OUT-01 出力をカタログごとにまとめる

- 軸: O1
- 決定: 出力は domain-models/{name}/catalog.json、index.html、validation.json、diagrams/<id>.mmd、images/<id>.png に限定する。カタログには1図以上を載せ、図ごとに原本とPNGを1つずつ対応させる。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 依頼の指定
- 守らせ方: validate, script: scripts/catalog.py の check と契約の出力パス
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## OUT-02 固定した構造の原本とカタログを生成する

- 軸: O2
- 決定: catalog.json は schema_version、name、title、diagrams を持つ。図は id、title、description、terms、sources、unresolved を持つ。sources は path と quote を持つ。原本は classDiagram で始める。HTMLはオフラインの一覧・検索・拡大・原本参照を備える。PNGは破損していない画像にする。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 依頼の指定
- 守らせ方: validate, script: scripts/catalog.py の check。assets/examples/catalog.json
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## OUT-03 根拠のある業務概念と関係を表す

- 軸: O3, X2
- 決定: 業務概念・主な属性・関係名・資料にある多重度を図にする。ラベルは資料の用語を使う。コードのメソッドやDBの外部キーを業務概念に置き換えない。資料にない概念・属性・関係・多重度を断定せず、足りない情報を unresolved に書く。sources.quote の実際の記述と図・説明を照合する。入力で指定された業務領域を省略しない。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 依頼の指定
- 守らせ方: review: 完了前チェックリストで sources.quote と図・説明を照合する
- 機械化しない理由: 意味の判断が要る：業務の意味と資料の含意は文字列の形だけでは判定できない
- 良い例:

  ```text
  人数が不明なら多重度を省略し未確認事項に書く
  ```
- 悪い例:

  ```text
  資料にない必須人数を推測し1と書く
  ```

## OUT-04 IDと並び順を固定する

- 軸: O4
- 決定: name と図の id は英小文字・数字・ハイフンで、英小文字から始める。図は id の昇順、terms は重複なしの昇順にする。ファイル名は id と一致させ、JSONはキーの昇順・2空白で書く。既存IDは同じ図の更新で維持する。termsはMermaidに宣言した概念の表示名から生成し、表示名がない概念は概念IDを使う。同じファイルの引用は1件にまとめ、参照先の昇順に並べる。 プロジェクト内の資料パスはプロジェクトルートからの相対パスに統一する。プロジェクト外の資料とURLは入力の参照先を保つ。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, script: scripts/catalog.py の check と build
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## OUT-05 説明と根拠と未確認事項を省略しない

- 軸: O5
- 決定: 図は1〜1000件にする。各図に空でない題名と説明と1件以上の sources を持たせる。terms と unresolved は配列にし、未確認事項が無ければ空配列にする。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate: scripts/catalog.py の check
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## OUT-06 既存カタログを確認してから更新する

- 軸: O6
- 決定: inspect で既存図のIDを読む。index.html があるときは update=true の依頼でだけ build --update を使う。依頼のない既存図は残す。build は前回 validation.json にあるIDの削除と同名の未知のファイルの置換を拒否する。 原本・変換版・設定と既存PNGのハッシュが前回の検証記録と一致する図はPNGを再利用し、未変更図の画像を維持する。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 機械で守らせられる答え
- 守らせ方: script, doc: scripts/catalog.py の inspect と build。SKILL.md の手順3
- 機械化しない理由: 痕跡が残らない：利用者が更新を依頼したかはファイルの字面だけでは判定できない
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## OUT-07 原本とPNGと一覧の対応を検査する

- 軸: O7
- 決定: check は全ファイルのSHA-256と validation.json の記録を照合し、metadata・Mermaid・PNG・HTMLの組が一致することを確認する。変更のない再実行でも report.sections が全カタログを検査する。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate, script: scripts/catalog.py の check と report、report.sections
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
  ```

## OUT-08 検査を止める記法を生成しない

- 軸: O8
- 決定: Mermaidとcatalog.jsonに skip ci、ci skip、eslint-disable、noqa、type: ignore、validation: false の記法を書かない。Mermaidの初期化ディレクティブとclick文は生成せず、変換設定はbuildが固定する。
- 理由: 実行者が変わっても判断と出力を揃えるため。
- 決め方: 機械で守らせられる答え
- 守らせ方: validate: scripts/catalog.py の check
- 良い例:

  ```text
  契約どおりに出力する
  ```
- 悪い例:

  ```text
  契約と違う出力にする
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
