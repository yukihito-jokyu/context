---
name: write-detailed-design-document
description: "要件と基本設計から、共通仕様と機能ごとの処理・通信・物理データ・画面・競合・障害時動作を整合させ、根拠と未検証の影響が分かる詳細設計書を作る 保存先を依頼に合わせ、各項目の図とPNG、参照先の必要条件の抜粋を備える。「要件と基本設計の情報をもとに詳細設計書を作成して」、「実装と試験へ渡せる詳細設計を作って」、「受付から保存と結果返却までを具体的に設計して」、「状態遷移と並行処理と保存の詳細設計を書いて」、「API・データ・画面の条件が一致する詳細設計にして」、「未検証事項を分けながら詳細設計を進めて」と頼まれたときに使う。要望の整理から要件定義書だけを作るには使わない（代わりにwrite-requirement-documentを使う）。構成と採用理由を中心に基本設計書を作るには使わない（代わりにwrite-basic-design-documentを使う）。設計書を作らず実装コードだけを変更するには使わない（代わりに実装を直接行うを使う）。"
---

# 要件と基本設計を実装と試験へ渡せる詳細設計にする

<!-- BEGIN GENERATED:purpose -->
要件と基本設計から、共通仕様と機能ごとの処理・通信・物理データ・画面・競合・障害時動作を整合させ、根拠と未検証の影響が分かる詳細設計書を作る 保存先を依頼に合わせ、各項目の図とPNG、参照先の必要条件の抜粋を備える。
<!-- END GENERATED:purpose -->

## 1. 使う場面

<!-- BEGIN GENERATED:triggers -->
次のような依頼で使う。

- 「要件と基本設計の情報をもとに詳細設計書を作成して」
- 「実装と試験へ渡せる詳細設計を作って」
- 「受付から保存と結果返却までを具体的に設計して」
- 「状態遷移と並行処理と保存の詳細設計を書いて」
- 「API・データ・画面の条件が一致する詳細設計にして」
- 「未検証事項を分けながら詳細設計を進めて」

次の場合は使わない。

- 要望の整理から要件定義書だけを作る → 代わりに: write-requirement-document
- 構成と採用理由を中心に基本設計書を作る → 代わりに: write-basic-design-document
- 設計書を作らず実装コードだけを変更する → 代わりに: 実装を直接行う

依頼の内容から自動で選ばれる。明示して呼ぶときは Codex では `$write-detailed-design-document` と書く。
<!-- END GENERATED:triggers -->

## 2. 手順

このファイルがあるディレクトリを `<skill>` と呼ぶ。作業するプロジェクトのルートを `<root>` と呼ぶ。固有スクリプトはPython 3.9以上の標準ライブラリで動く。PNG変換には既存のNode.js、Mermaid CLI、ChromeまたはPuppeteerのブラウザーを使う。追加取得せず、見つからない場合は不足として報告する。

文書検査は構造と参照を確かめる。要求のnull方針、保存失敗時の状態、エラーの返却形式、完了後の照会結果には意味の不整合が残る場合がある。[検査の範囲と既知の限界](references/limitations.md)を読み、手順9で本文を照合する。独立測定は全項目の合格に達していない。

1. 依頼の対象資料・対象機能・出力先・言語を読み取る。SKILL.mdを読んだ直後の最初の探索はinspectにし、プロジェクト全体の一覧を先に取得しない。初めに`python3 <skill>/scripts/design.py inspect --root <root> --source <指定された資料かディレクトリ>`で資料を列挙する。指定がなければ`--source`を省き、`docs`直下の一組を探す。追加の探索が必要な場合もdocsと指定先に範囲を絞り、Git内部やプロジェクト全体を一覧化しない。一組に決まった対象資料は一覧を`sources`に渡す。対象外の依頼は代わりを示し、対象が決まらないときはstart前にまとめて聞く（IN-01、IN-02、CTL-03）
2. `python3 <skill>/scripts/run.py start --set 'sources=docs/requirement.md,docs/basic-design.md' "<依頼文>"`を実行する。例の二つのパスは手順1で列挙した資料へ置き換え、カンマ区切りの一覧を一つの引数で渡す。startのsourcesにはJSONの角括弧と引用符を付けない。出力先は明示指定、会話で合意した先、既存設計の先の順に決め、いずれもなければdocs/detailed-designを使って報告する。.skill-runsは成果物の固定保存先にしない。選んだ出力先を必ず--set output_dirで渡す。対象機能・言語の指定があれば`--set scope=<対象機能> --set output_dir=<出力先> --set language=<言語>`を足す。指定のない値は渡さない。正規化された資料一覧が列挙結果と一致すれば手順3へ進み、成功済みのstartを繰り返さない。入力が誤っていた場合だけ`start --restart`に訂正値と元の依頼文を渡す。終了コード3なら質問へ答えを得てからやり直す（CTL-01）
3. [references/design-guide.md](references/design-guide.md)の1〜7章を読み、列挙した要件・基本設計の本文と必要な参照先を読む。資料一覧にない参照先は本文の参照を確認してから開き、存在を仮定したパスを試さない。読取結果が省略された場合は、省略部分を範囲指定して読み、読めた前半を繰り返さない。不一致、制約、採用判断、未検証を分ける。外部検証の実施を依頼されていなければ試験条件を設計し、実環境を変更しない（IN-02、STEP-01、STEP-04）
4. `assets/examples/design.json`を形の見本に、出力先の`design.json`を作る。既存の台帳がある場合はIDと判断の記録を読んで対象だけを更新する。根拠は`python3 <skill>/scripts/design.py cite --root <root> --path <資料> --line <行> --kind <種類> --id S001`で取得する。見本の製品条件や数値はコピーせず、対象の値を資料から引き継ぐか追加提案として記す（OUT-01、OUT-04、OUT-09）
5. 用語、責務、型、状態、時刻を共通定義へ置く。各対象要件を機能と確認条件へ対応付け、対象外には理由を付ける。機能ごとに目的と根拠、開始条件と入力、処理、結果、異常・競合・中断、確認方法を具体化する（OUT-02、OUT-10）
6. 境界は操作ごとに分ける。request_fieldsとresponse_variantsに全項目の型・必須性・NULL可否・制約、request_policyに欠落と未知項目の扱いを書く。state_policyに許可状態・権利・副作用、state_effectsに各結果の状態と遷移IDを記す。機能と回復の各呼出しについて、開始できる状態から成功・失敗・未確認の結果まで辿り、遷移のない経路を残さない。物理列を定義し、primary_key・unique_keysだけでキー構成を決める。列や制約へキーを再定義しない。索引と移行、画面項目と操作とフォーカスを設計し、機能と共通定義へ参照をつなぐ。処理順はシーケンス図、状態は状態図、データの関係はER図を使い、採った図と省いた図の理由を書く。厳密な条件は図から台帳の対応IDへつなぐ（OUT-02、OUT-10、OUT-11、OUT-13、OUT-14、OUT-15）
7. 同時到着、再送、期限の直前・等号・直後、切断、保存前後と外部作用前後の停止、再起動を点検する。勝敗、保存の原子性、排他範囲と取得順、枠の確保・解放、回復と観測結果を記す。未検証は検証内容・採用条件・依存先・独立して進める範囲を付け、要件変更は変更前後・理由・影響と判断の出典を残す（STEP-02、OUT-11、OUT-12）
8. 各項目の近くへ必要な図を配置し（OUT-16）、リンク先の必要な条件を引用か要約で添える（OUT-17）。台帳の構造から各項目の図を生成し、手で書いた横断図はcondition_idsの項目直下に置く。`python3 <skill>/scripts/design.py render --root <root> --dir <出力先> --source <資料のJSON一覧>`で文書を生成する。生成は既存のMermaid CLIで全図をPNGへ変換する。構文・変換の失敗を直し、PNGがないまま進めない。既存の手書き文書と衝突したら上書きせず、`run.py wait --question <保存先の質問>`を実行してから確認する。renderが実行IDを返した場合は終了まで待ち、終了コード0と表示された保存先を確認する。失敗が残る状態でcheckを呼ばない。台帳を直したら再生成し、生成MarkdownとHTMLを直接直さない（STEP-03、OUT-06、OUT-07）
9. `python3 <skill>/scripts/design.py sheets --root <root> --dir <出力先>`でPNGの一覧を作り、全シートを実際に開く。小さく表示される図、多数の遷移、長いラベル、欠け・重なりの疑いがある図は元PNGを拡大して読む。確認したシートと元PNGを出力先のverification-review.mdへ記録する。qa配下には手書き記録を置かない。一覧生成に必要な環境がなければ各PNGを直接開く。図の体裁のために共通の状態名・遷移条件を変えず、表示側の短いラベルと凡例で直す。最後の生成内容のREADME.mdとevidence.md、各図の説明を読む。詳細の意味の照合には`design.py read --root <root> --dir <出力先> --area list`でページ数を確認し、12分野の全ページを`--area <分野> --page <番号>`で読むか、全Markdownまたはreview.htmlの10分野を省略なく読む。readのページをまとめて大量出力せず、リンク付きの行や長い行を除外しない。対象にない分野も非該当の理由まで確認する。入力の条件付き必須とNULL方針、エラー一覧と全応答の項目、自由記述中の許可状態と共通状態名、ガード・状態更新・回復・確認条件を照合する。保存不成立が確認できた場合と、コミット結果が不明な場合の断定を混ぜない。修正したら手順8で再生成し、変更ID・依存先・確認条件・対応PNGを再読し、一覧も再生成する。未読・省略・未確認のPNGが残る間は手順10へ進まない。図の近接配置とPNGの生成、リンク先の必要条件の引用があることを確認する。文書検査と、採用・実装・実機検証を区別する（OUT-03、OUT-05、OUT-08、OUT-10、OUT-11、OUT-12、OUT-16、OUT-17）
10. 手順9の読取りと意味の照合を終えてから、`python3 <skill>/scripts/run.py check`を実行する。指摘があれば、引用・台帳・生成結果の原因を直して手順8・9へ戻る。機械検査で意味の照合を代替せず、検査や契約を緩めて通さない（STEP-05）
11. 決めきれなかったことがあれば`.skill-runs/write-detailed-design-document/notes.md`に「- 」の箇条書きで書き、`python3 <skill>/scripts/run.py finish`を実行する。終了コード1なら手順10へ戻る。終了コード0なら出力された本文をそのまま返答する（RPT-01）

## 3. 入力

<!-- BEGIN GENERATED:inputs -->
| 項目 | キー | 受け付ける書き方 | 無いとき |
|---|---|---|---|
| 対象資料 | `sources` | 一覧（`,`・`、`・改行で区切る）。別名: 資料、入力資料、source | start の前に聞く: 要件定義と基本設計のファイルはどれですか。docs直下に一組あるときは、その二つを読み取って使います。 |
| 対象機能 | `scope` | 文字列。別名: 対象機能、範囲 | 既定値 `入力資料の全対象機能` |
| 出力先 | `output_dir` | パス。別名: 出力先、保存先 | 既定値 `docs/detailed-design` |
| 出力の言語 | `language` | `ja`、`en` のどれか（日本語→`ja`、英語→`en`、japanese→`ja`、english→`en`）。別名: 言語、lang | 既定値 `ja` |

入力は `run.py start --set <キー>=<値>` で渡す。キーは表のキー・項目名・別名のどれでもよく、全角と半角、大文字と小文字、`-`・`_`・空白の違いは吸収される。契約に無いキーは無視して記録する。依頼文そのものは最後の引数に渡す。依頼文の中の「キー: 値」の行も読む。
<!-- END GENERATED:inputs -->

## 4. ルール

<!-- BEGIN GENERATED:decisions -->
| ID | ルール | 守らせ方 |
|---|---|---|
| IN-01 | 対象外の依頼はtriggers.not_forの代わりを示してstartしない。要件と基本設計が見つからない、または候補が2組以上あって対象を決められないときは、start前に対象資料を聞く。独立実行で質問できないときはabortし、資料を作り上げない。 | doc: SKILL.mdの手順1とreferences/design-guide.mdの1章 |
| IN-02 | scripts/design.py inspectで指定資料を列挙し、要件と基本設計の本文、参照された判断・検証記録を読む。未指定ならdocs直下の要件と基本設計の一組を探す。参照先を読めないときは未確認と記録し、リンクがあるだけで確認済みにしない。 | script, doc: scripts/design.py inspectとSKILL.mdの手順1・3 |
| STEP-01 | 資料と対象範囲を整理し、不一致・未決を抽出し、共通の責務・型・状態・時間を決め、機能ごとの開始条件・入力・処理・結果・異常と回復・確認条件を書く。最後に要件の対応と競合・途中失敗を照合する。 | doc: SKILL.mdの手順3〜7とreferences/design-guide.md |
| STEP-02 | design.jsonのdecisionsで情報の区分、採用判断、検証状態を別の項目にする。未検証の外部依存はissuesに検証内容・採用条件・影響先・独立して進める範囲を記す。変更はchangesに変更前後・理由・影響を記す。検証成功には検証記録、採用済みには判断の記録を参照させる。 | validate: scripts/design.py checkが証拠の種類、未決と変更の必須項目を検査する |
| STEP-03 | 資料一覧とSHA-256と引用候補はscripts/design.py inspect・citeで取得する。design.jsonを設計の正本にし、scripts/design.py renderでMarkdownと分野別の閲覧用HTMLを生成する。生成したMarkdownだけを手で修正しない。scripts/design.py checkとreportで参照・文書の一致と件数を検査・集計する。 | script, doc: scripts/design.pyのinspect・cite・render・check・report |
| STEP-04 | ファイルの読書き、python3による同梱scripts、gitによる参照を使う。外部仕様を確認するときは公式資料を読み、対象版と確認の限界を記録する。依頼されていない実装変更、DB操作、アダプター起動、外部送信を設計作成に含めない。 | doc: SKILL.mdの手順3とreferences/design-guide.mdの1章 |
| STEP-05 | checkが失敗したら引用、design.json、生成結果を原因に応じて直す。資料の読取失敗や既存文書の衝突では書込みを止め、影響しない設計を続ける。契約・検査スクリプトを緩めて通さず、実装未確認を検証成功に変えない。 | doc: SKILL.mdの手順8とreferences/design-guide.mdの5章 |
| OUT-01 | output_dirにdesign.json、README.md、common.md、features.md、interfaces.md、data.md、ui.md、recovery.md、verification.md、evidence.md、review.htmlを1件ずつ置く。出力先は利用者の明示指定、会話で合意した保存先、既存設計の保存先の順に決め、どれもなければdocs/detailed-designを提案値として使い報告する。.skill-runs配下を成果物の保存先に固定しない。実行記録は.skill-runs/write-detailed-design-documentに残し、成果物の保存先とは分ける。 | validate: 出力のpath・countとscripts/design.py check |
| OUT-02 | design.jsonをassets/design.schema.jsonの形で書く。共通仕様に責務・用語・状態・時間条件を置き、各機能を目的と根拠、開始条件と入力、処理の流れ、結果、異常・競合・中断、確認方法の六つの節で書く。通信・物理データ・画面・回復・確認条件を対応IDでつなぐ。非該当の分野は理由を記す。 | validate, template: assets/design.schema.jsonとassets/examples/design.json、scripts/design.py check |
| OUT-03 | languageで本文を書く。日本語の文末は「する」「である」で揃える。用語・状態名はdesign.jsonの共通定義と同じ語を使い、画面の表示名との対応を示す。節の導入文で前提と、その節が決めることをつなぐ。 | review: references/design-guide.mdの2章と完了前チェックリストで本文を読む |
| OUT-04 | IDは資料S、要件R、責務M、状態ST、判断D、機能F、境界IF、表T、遷移TR、並行制御P、回復RC、画面UI、確認C、未決U、変更CH、図Gに3桁の番号を付ける。各配列は資料に現れる順で採番し、更新時は既存IDを保つ。値は入力資料から引き継ぐか追加提案として判断へ記す。 | validate: scripts/design.py checkがIDの形・一意性・参照を検査する |
| OUT-05 | README.mdは120行以下、分野別の各Markdownとreview.htmlは3000行以下とする。各機能の六つの節は省略しない。上限を超える場合は意味を削って通さず、対象機能を分ける案を示して範囲を確かめる。 | validate: 各Markdownのmax_linesとscripts/design.py check |
| OUT-06 | 生成するMarkdownとHTMLには生成元と本文ハッシュを付ける。renderは出力予定ファイルが手書き、または生成後に編集されていれば書込みを拒否する。design.jsonの更新は既存の要件・判断・IDを読み、依頼の対象だけを変える。資料と無関係なファイルは変更しない。 | validate: scripts/design.py render・checkの生成マーカーと本文ハッシュ検査 |
| OUT-07 | design.jsonを変えたらrenderで入口と分野別文書と閲覧用HTMLを同時に再生成する。README.mdに台帳の内容ハッシュを含める。checkは全文書を再計算して一致を確認し、要件から機能と確認条件、共通状態から遷移と画面の参照を照合する。 | validate: togetherのdesign-dataとentry、scripts/design.py check |
| OUT-08 | 必須項目の空文字とTODO・TBD・FIXMEの仮置きを認めない。定義できない内容はissuesに検証内容と採用条件を持つ未決として記し、非該当には理由を書く。「検証していない」は成功に置き換えない。 | validate: scripts/design.py checkの空値・仮置き検査 |
| OUT-09 | 資料ごとにpath、開始行、終了行、引用、SHA-256、資料の種類を持つ。引用はその範囲の本文と照合する。文書の根拠には実際の記述と絶対パス・行番号のリンクを出す。資料の記載を検証した事実へ読み替えない。 | validate, script: scripts/design.py cite・check、evidence.mdの生成 |
| OUT-10 | 対象機能の責務、操作ごとに分けた境界の許可状態・権利・副作用、入力項目・型・制約・検査順・最大サイズ・出力・エラー、保存対象・原子性・物理制約・索引・移行、画面の入力検査・操作・保存結果・フォーカス・更新、確認条件を読む。各要件が設計か影響付き未決と確認条件につながることを確かめる。補助関数とコードの各行は固定しない。 | review: references/design-guide.mdの3章と完了前チェックリスト |
| OUT-11 | 保護するデータ、排他の範囲と取得順、実行権・枠の確保と解放、上限更新、時刻の判定場所と等号、切断・再送・保存前後・外部作用前後・再起動の扱いを読む。機能と回復の各呼出しが境界の許可状態を満たし、状態・物理データ・画面・返却が一致し、二重実行や判断の覆しを起こさない条件を確かめる。 | review: references/design-guide.mdの4章と完了前チェックリスト |
| OUT-12 | 資料からの引継ぎ、追加提案、証拠のある検証結果、採用判断を区別して読む。未決の検証内容・採用条件・依存先が妥当で、依存しない設計を止めていないことを確かめる。資料間の不一致と要件変更は出典、変更前後、理由、影響を記し、未確認を承認済みにしない。 | review: references/design-guide.mdの5章と完了前チェックリスト |
| OUT-13 | 表のprimary_key・unique_keysとkey_policyにキー構成と理由を置く。列のconstraintと表のconstraints・indexesでは主キー・一意キーを再定義しない。列名の存在と重複、キー構成の重複、主キー列のNULL不可を検査する。キーを持たない形式は空配列と理由で示す。 | validate: scripts/design.py checkとassets/design.schema.jsonが構造と対応を検査する |
| OUT-14 | 内部・外部の各操作にrequest_fieldsとresponse_variantsを置き、各項目にpath・type・required・nullable・constraintを記す。request_policyに欠落・未知項目と入力なしの扱いを書く。型は構造化した項目を正本とし、input・responseは処理の意味を説明する。項目pathと応答名の重複を検査する。 | validate: scripts/design.py checkとassets/design.schema.jsonが構造と対応を検査する |
| OUT-15 | 境界のstate_effectsに状態定義・現在状態・応答名outcome・次状態・transition_id・理由を記す。状態変更は実在する遷移と状態定義・現在状態・次状態を一致させる。状態を保つ場合はfrom=to、transition_id=nullと理由を書く。state_policyに許可状態・権利・副作用を書く。状態のない操作は空配列と理由を示す。 | validate: scripts/design.py checkとassets/design.schema.jsonが構造と対応を検査する |
| OUT-16 | 各Markdownの説明対象の項目直下に、その台帳項目を表す図を置く。処理は処理順、状態は状態と遷移、境界は要求と応答、表は物理列、確認は開始条件・事象・観測結果、他は項目と条件の対応を図示する。Mermaidフェンスと同内容の.mmdと、実際に変換した.pngをdiagramsへ保存する。図の直下に伝えることと厳密な条件の場所を示す。章末への一括配置、無関係な装飾図、画像欠落、MermaidとPNGの不一致を完了にしない。 | validate, script: scripts/design.pyとscripts/presentation.pyが生成と一致を検査する。 scripts/contact_sheet.shが既存の描画環境で確認用の画像一覧を作る。 |
| OUT-17 | 根拠と関連仕様のリンクには、その項目で必要な本文の引用または要約を添える。根拠は実際の引用を>で示し、関連仕様は条件・判断・観測結果を>または本文で取り出す。参照IDや資料名だけの表示、名前だけの言い換えで必要な条件を隠さない。目次・戻る・ダウンロードの操作リンクは対象外とする。要約は原文と区別し、原文と逆の意味や確定度を付けない。 | validate, script: scripts/design.pyとscripts/presentation.pyが生成と一致を検査する。 |
| RPT-01 | 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。 | runtime, validate, review: scripts/run.py の finish と abort が本文を組み立て、.skill-runs/<name>/report.md にも保存する。check と finish が notes.md の形を検査する |
| CTL-01 | 手順の最初に `run.py start`、出力を書いた後に `run.py check`、最後に `run.py finish` を実行する。`finish` が終了コード0で終わるまで、完了と返答しない。 | runtime, validate: scripts/run.py。finish は契約の検査に通らないと終了コード1で終わる |
| CTL-03 | ユーザーに聞くことは `run.py start` の前にまとめて聞く。start の後に聞く必要が出たときは、`run.py wait --question <質問>` を実行してから聞く。聞けない状況では既定値を使い、報告の「既定値で決めた値」に載せる。 | runtime, doc: scripts/run.py の start は、聞くべき入力が無いと終了コード3で止まり、質問を出力する。wait は hooks の強制を止める |
| CTL-04 | 出力の検査の hooks は、このスキルの実行中（status: active）に、編集の後と応答を終える前に出力を検査することと、実行記録（`.skill-runs/<name>/state.json`・`report.md`）への編集ツールでの直接の編集を拒否することの2つだけを行う。実行していないときは何もしない。スキル自身のファイルと hooks の設定の変更、ユーザーの発言を止めたり書き換えたりしない。hooks が無い環境でも、`run.py check` と `finish` が同じ出力の検査をする。 | runtime: scripts/hook.py。install.py が Claude Code（.claude/settings.json）と Codex（.codex/hooks.json）に登録する |

理由・良い例・悪い例は [references/decisions.md](references/decisions.md) にある。
<!-- END GENERATED:decisions -->

## 5. 出力の契約

<!-- BEGIN GENERATED:contract -->
| 出力 | 置き場 | 件数 | 検査（ルールID） |
|---|---|---|---|
| design-data 設計の台帳 | `{in:output_dir}/design.json` | 1〜1 件（OUT-01） | `python3 {skill}/scripts/design.py check --root {root} --dir {in:output_dir} --source {in:sources}` が通る。STEP-02、OUT-01、OUT-04、OUT-05、OUT-06、OUT-07、OUT-08、OUT-09、OUT-13、OUT-14、OUT-15、OUT-16、OUT-17 の指摘も出す（台帳の構造、引用、対応ID、採用・検証の証拠、生成文書の一致を確かめる）（check・finish・応答を終える前だけ。編集の直後は検査しない）（OUT-02） |
| entry 入口文書 | `{in:output_dir}/README.md` | 1〜1 件（OUT-01） | 120 行以下（OUT-05） |
| common-design 共通仕様 | `{in:output_dir}/common.md` | 0〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| feature-design 機能詳細 | `{in:output_dir}/features.md` | 0〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| interface-design 境界の契約 | `{in:output_dir}/interfaces.md` | 0〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| data-design 物理データ | `{in:output_dir}/data.md` | 0〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| ui-design 画面 | `{in:output_dir}/ui.md` | 0〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| recovery-design 障害と再起動 | `{in:output_dir}/recovery.md` | 0〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| verification-design 対応と確認条件 | `{in:output_dir}/verification.md` | 0〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| evidence-design 根拠と未決と変更 | `{in:output_dir}/evidence.md` | 0〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| review-view 分野別の閲覧と確認 | `{in:output_dir}/review.html` | 1〜1 件（OUT-01） | 3000 行以下（OUT-05） |
| diagram-assets 図の原本と画像の対応 | `{in:output_dir}/diagrams/manifest.json` | 1〜1 件（OUT-16） | `"mermaid": "diagrams/` に一致する行がある（Mermaid原本の対応を記録する。）（OUT-16）。`"png": "diagrams/` に一致する行がある（変換したPNGの対応を記録する。）（OUT-16） |

`{run}` は実行記録の置き場 `.skill-runs/write-detailed-design-document` を指す。`run.py start` の前からあったファイルで、内容が変わっていないものは検査しない。

- 出力 design-data、entry は一緒に変える。一部だけを変えると OUT-07 の指摘になる（設計の台帳を変えたら、内容ハッシュを持つ入口文書も再生成する）
<!-- END GENERATED:contract -->

## 6. 完了前チェックリスト

<!-- BEGIN GENERATED:checklist -->
- [ ] OUT-03 languageで本文を書く。日本語の文末は「する」「である」で揃える。用語・状態名はdesign.jsonの共通定義と同じ語を使い、画面の表示名との対応を示す。節の導入文で前提と、その節が決めることをつなぐ。
- [ ] OUT-10 対象機能の責務、操作ごとに分けた境界の許可状態・権利・副作用、入力項目・型・制約・検査順・最大サイズ・出力・エラー、保存対象・原子性・物理制約・索引・移行、画面の入力検査・操作・保存結果・フォーカス・更新、確認条件を読む。各要件が設計か影響付き未決と確認条件につながることを確かめる。補助関数とコードの各行は固定しない。
- [ ] OUT-11 保護するデータ、排他の範囲と取得順、実行権・枠の確保と解放、上限更新、時刻の判定場所と等号、切断・再送・保存前後・外部作用前後・再起動の扱いを読む。機能と回復の各呼出しが境界の許可状態を満たし、状態・物理データ・画面・返却が一致し、二重実行や判断の覆しを起こさない条件を確かめる。
- [ ] OUT-12 資料からの引継ぎ、追加提案、証拠のある検証結果、採用判断を区別して読む。未決の検証内容・採用条件・依存先が妥当で、依存しない設計を止めていないことを確かめる。資料間の不一致と要件変更は出典、変更前後、理由、影響を記し、未確認を承認済みにしない。
- [ ] RPT-01 最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない。中断したときは、`run.py abort` が出力した本文を同じように使う。決めきれなかったことは、finish の前に `.skill-runs/<name>/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを本文の「## 補足」に入れる。
- [ ] `python3 <skill>/scripts/run.py finish` が終了コード0で終わった
<!-- END GENERATED:checklist -->

## 7. 報告

<!-- BEGIN GENERATED:report -->
最終の返答は、`run.py finish` が出力した本文をそのまま使い、前後に文を足さず、要約しない（RPT-01）。決めきれなかったことは、finish の前に `.skill-runs/write-detailed-design-document/notes.md` に「- 」で始まる箇条書きで書く（10 項目まで）。finish がそれを「## 補足」に入れる。中断するときは `run.py abort --reason <理由>` を実行し、abort が出力した本文を同じようにそのまま使う。本文の形は次のとおり。

```text
## 結果

write-detailed-design-document: 完了（検証に合格）

<`python3 {skill}/scripts/design.py report --root {root} --dir {in:output_dir} --source {in:sources}` の出力>

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
| `scripts/run.py start` | 手順の始め | 入力を正規化し（表記ゆれ・全角・未知のキーを受け入れる）、既定値で補う |
| `scripts/run.py check` と `finish` | 出力を書いた後と最後 | 契約（`assets/contract.json`）の format で出力を直してから検査する。finish は通ったときだけ実行を終える。前の実行の後に契約が変わっていれば、報告の「検証」に出す（止めない） |
| hooks の pre-tool | ファイルを編集する前 | 実行記録（`state.json`・`report.md`）の編集を拒否する。スキル自身のファイルの編集は止めない |
| hooks の post-tool | ファイルを編集した後 | 出力に当たるファイルを format で直し、検査し、指摘を返す |
| hooks の stop | 応答を終える前 | 出力全体を検査し、通るまで応答を終えさせない（最大 3 回。超えると status: failed） |
| hooks の prompt | ユーザーが発言したとき | 質問待ち（wait）を解くだけ。発言を止めたり書き換えたりしない |

hooks は、このスキルの実行中（`.skill-runs/write-detailed-design-document/state.json` の status が active）だけ出力を検査する。hooks が無い環境でも、`run.py check` と `finish` が同じ出力の検査をする。

hooks の登録: `python3 <skill>/scripts/install.py --project <プロジェクトのルート>`（Codex は `.codex/hooks.json` に追記する。Codex では、追記した hooks を `/hooks` で信頼するまで動かない）

初めて使うときは、ターミナルで `python3 <skill>/scripts/setup.py --project <プロジェクトのルート>` を実行すると、hooks の登録とユーザーの設定（`settings/user-setting.yaml`）を、書く前に差分を確かめながら選ぶだけで行える。AI のツールや CI からは、同じことを引数で行う（`--hooks`、`--features`、`--set`、`--yes`。一覧は `--help`）。

このスキル（ルール、契約、手順、スクリプト）は、実行中でも直せる。品質は出力の検査で確かめるので、直した後は次の順に検査を通す。`<skill-foundation>` は skill-foundation のディレクトリを指す。

1. `dev/spec.json` を直す。手で書く部分（この SKILL.md の「2. 手順」、`scripts/` のスキル固有のスクリプト、`references/`、`assets/examples/`）は直接直す
2. `python3 <skill-foundation>/scripts/render_skill.py --dir <skill>` で生成した部分を作り直す
3. ルールや契約を変えたなら `dev/probes.json` の違反例も合わせ、`python3 <skill-foundation>/scripts/probe.py <skill>` を通す
4. `python3 <skill-foundation>/scripts/skill_lint.py <skill> --final` を通す
<!-- END GENERATED:control -->
