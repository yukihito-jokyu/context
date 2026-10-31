# 図の選び方と変換

## 1. 読者の問いから選ぶ（OUT-09）

すべての図を描くのではなく、次の条件で採否を決める。9種類すべての採否と理由をdiagram_decisionsへ書く。原資料の内容が足りないときは、その箇所を未決として図と本文の両方へ示す。

| 種類 | 適性 | 読者の問い・採用する条件 | Mermaid構文 |
|---|---|---|---|
| context | ◎ | 境界と外部との関係。必ず作る | flowchart LR |
| usecase | ◎ | 誰が何をできるか。必ず作る | flowchart LR |
| workflow | ◎ | 主な業務と分岐。必ず作る | flowchart TD |
| state | ◎ | 状態と変化条件が資料にあるとき | stateDiagram-v2 |
| screen | ○ | 画面名と操作経路が資料にあるとき | flowchart LR |
| domain | ○ | 業務概念と関係を整理する材料があるとき | flowchart または classDiagram |
| sequence | ○ | 外部との順序・失敗時の扱いが資料にあるとき | sequenceDiagram |
| concept | △ | 概念の属性・関係を整理するとき | erDiagram または classDiagram |
| component | △ | 構成自体が要件として指定されるとき | flowchart LR |

usecaseはアクターを境界の外、できることを境界の中に置き、関連を線で結ぶ。実行順序はworkflowで表す。図のラベルは本文と同じ業務の言葉にし、要件・資料・未決事項の内部IDを付けない。原本のrequirement_idsとsource_idsが参照の対応を持ち、図の近くにある名前のリンクから詳細へ進める。classDiagramのメソッド、物理DBの列型・PK・FK、未決定のコンポーネント分割は設計の話題としてdesign_notesへ分ける。

stateDiagram-v2の状態名には英字の識別子を使い、日本語の表示名を二重引用符で囲む。たとえば、`state "確定" as Confirmed` と宣言し、`Confirmed --> Cancelled: 本人が取消` と遷移を書く。`state 確定 as Confirmed` は使わない。状態名の囲みと、ラベルの文章中に引用符を混ぜることは区別する。

## 2. 変換環境（STEP-04）

[Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)をローカルで使う。Pythonは標準ライブラリだけで動く。doctorはREQUIREMENT_MMDC、PATHのmmdc、プロジェクトのnode_modules、既存のnpmキャッシュの順に探す。REQUIREMENT_MMDCは実行ファイルまたはcli.jsのパスにする。Chromeの実行経路を指定するときはREQUIREMENT_BROWSERを使う。新規パッケージは自動取得しない。

既存環境が11.16.0であるため、11以降で使える構文を採用する。[Mermaid 12以降](https://mermaid.ai/open-source/syntax/usecase.html)にはusecase-betaがあるが、このスキルでは互換性を保つためflowchartでユースケースの関係を表す。Mermaid自体にユースケース機能がないとは説明しない。

buildはstrict設定、白背景、拡大率2でPNGを作り、HTMLへ埋め込む。URL、クリック動作、初期化指令、外部画像を図の原本へ加えない。図の文字に引用符とHTMLを混ぜる代わりに、平易なラベルへ言い換え、根拠に元の記述を残す。

doctorは実行経路とバージョンを確かめる。ブラウザーの起動と図の実描画ができるかはbuildで確かめる。起動権限が原因なら、その環境で用意された承認手順に従う。起動失敗のまま同じ条件で再試行を重ねず、承認手順が使えなければ不足する実行経路を報告して待つ。

## 3. 大きさと同期（OUT-05、OUT-06）

1図で1つの問いを扱う。6000文字、幅・高さ6000px、2500万画素のいずれかの上限を超える図は、全体図と業務別の詳細図へ分ける。小さく縮めて収める方法は使わない。図を増やすときはDの連番と要件への双方向参照を保つ。

PNG、Mermaid原本、HTMLを別々に編集しない。構造化原本を直してbuildし、checkで参照とSHA-256を確認する。画素の内容が業務の意味に合っているかは、人またはAIが元資料と照合する。

HTMLの各図には、原寸表示と原本の保存に加え、Mermaid原本を開くdetailsがある。通常の読書では閉じたままにし、図の定義を照合するときに開く。機械の採点に渡すときも、この原本と隣接する本文を一緒に読む。

PNGはバイナリなので共通ランタイムの文字列検査へ直接渡さない。manifestの一覧を介してdocument.pyが実ファイルの署名、CRC、寸法、ハッシュ、HTMLへの埋め込みを検査する。PNGの欠落も完了を止める。
