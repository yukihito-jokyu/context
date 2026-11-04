# 設計の観点を図で確かめる

## 1. 採否と配置（OUT-09）

coverageはarchitecture・screen・data・integrationの順に書く。architectureとdataは採用する。利用者の画面操作を設計するときはscreenを採用し、外部システムとの受け渡しを扱うときはintegrationを採用する。画面がない夜間処理ではscreenを省く。未指定なら採否の理由と確認する条件を記し、要望にない構成を確定して図を増やさない。

| kind | 選ぶ条件 | area | Mermaid構文 |
|---|---|---|---|
| context | 対象と外部の境界。必ず作る | architecture | flowchart LR |
| component | 責務と依存の分担。必ず作る | architecture | flowchart LR |
| workflow | 主な処理と分岐。必ず作る | 対応する観点 | flowchart TD |
| screen | coverageのscreenがtrue | screen | flowchart LR |
| data | 論理データの関係。必ず作る | data | flowchart、erDiagram、classDiagram |
| sequence | coverageのintegrationがtrue | integration | sequenceDiagram |
| state | 状態と変化の条件を設計する | 対応する観点 | stateDiagram-v2 |
| deployment | 実行場所・ネットワークの配置が指定されているか、配置の案を明示して比較する | architecture | flowchart LR |

8種類すべての採否と理由をdiagram_decisionsへ書く。図のareaが本文中の配置先になる。各図に、読む目的intro、読み取る要点takeaway、画像を見られないときの説明alt、対応するdesign_idsとsource_idsを付ける。

画面遷移図だけで外部呼出しの順序を説明せず、連携はsequenceへ分ける。データは概念・論理関係を示す。物理的な型・主キー・外部キー・メソッドの定義は図に詰めず、handoffへ分ける。主な処理を示すworkflowと、責務の静的な関係を示すcomponentを区別する。

stateDiagram-v2では`state "確定" as Confirmed`のように、日本語の表示名を二重引用符で囲む。英字の内部名と、読者に見える表示名を区別する。図の表示名は本文と同じ言葉にし、内部IDや独自の略語へ置き換えない。

## 2. ローカルでの変換（STEP-04、STEP-05）

Python 3.9以上、Node.js、既存の[Mermaid CLI](https://github.com/mermaid-js/mermaid-cli) 11以降を使う。doctorはBASIC_DESIGN_MMDC、PATHのmmdc、プロジェクトのnode_modules、既存のnpmキャッシュの順に探す。BASIC_DESIGN_MMDCには実行ファイルかcli.jsのパスを指定する。Chromeの経路を指定する場合はBASIC_DESIGN_BROWSERを使う。

doctorが確認するのは経路と版である。Chromeの起動とPNGの生成はbuildで確かめる。起動権限が足りない場合は、環境の承認手順を使う。承認手順が使えないときは不足する経路を示して待ち、同じ起動失敗を繰り返さない。新規パッケージとリモート描画サービスを自動導入しない。

エラーがブラウザの起動失敗を示したら、実行環境の権限制限を確認する。サンドボックスが原因なら、用意された承認手順で同じbuildを再実行する。一時的な起動失敗と確認できた場合の再試行は1回までとし、失敗したら不足する経路を示して待つ。原因を変えずに同じコマンドを繰り返さない。

描画はstrict設定、白背景、倍率2で行う。図へURL、クリック動作、初期化指令、外部画像を加えない。11以降で使える構文に限定し、公式サイトの最新版だけにある構文を混ぜない。

## 3. 図の大きさと同期（OUT-05、OUT-06）

1つの図で1つの問いを扱う。Mermaid原本6000文字、幅と高さ6000px、2500万画素のいずれかを超えた場合は、全体図と処理別の図へ分ける。文字を縮小して押し込まない。

原本を変更したらbuildで派生出力を作り直す。checkはMermaidの内容、PNGの署名・CRC・寸法・ハッシュ、manifest、HTMLの再生成結果を照合する。意味は元資料と照合し、画像を開いて文字の欠け・つぶれ・矢印の重なりを確認する。

PNGを生成できることと、図が意味を正しく伝えることは別に確かめる。HTMLには通常の図、原寸表示、Mermaid原本のdetailsを持たせ、評価には本文と図の原本を省略せず渡す。
