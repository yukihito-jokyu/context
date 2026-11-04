# 会話から基本設計へ進める

## 1. 対象と読む範囲（IN-01、IN-02）

会話・議事録・箇条書きから、解く課題と対象を確かめる。不足する点だけを開始前にまとめて聞く。条件が足りなくても対象と課題が分かるときは、分かる部分を設計し、決まらない条件を残す。

基本設計は、要望を実現する責務・画面・論理データ・外部とのやり取りと、その設計を選ぶ理由を示す。要望の言い換えだけで終えない。メソッド、物理列、索引、接続先の実際の設定値は詳細設計への引継ぎに書く。

読むのは会話、指定された資料、対象プロジェクトのAGENTS.mdである。既存構成の確認を指定されたときだけコードを読む。資料にない業務条件や製品の採用を、合意済みと書かない。

## 2. 事実・設計案・未決を分ける（STEP-02）

会話にある要望をrequirementsへ、要望を実現する判断をdesignsへ書く。designsのstatusは、入力に同じ設計が指定されているときstated、新しく設計を提案するときproposal、設計の内容が決まらないときopenにする。statedは承認済みを意味しない。

各設計にstatement、採用理由のreason、補足のdetailsを持たせる。画面は操作の入口・入力・結果・権限、データは概念・関連・保持する情報・更新の条件、外部連携は相手・受け渡す情報・順序・失敗時の扱いを説明する。資料にない内容を補うときは設計案と明記する。

外部連携を行わない場合は、coverageのintegrationをfalseとし、不実施の理由と根拠をそこへ書く。designsにはareaがintegrationの設計を置かない。不実施が全体の構成判断にも関わるときは、architectureの設計の補足へ書く。画面がない場合も同じ扱いとする。

取消期限が未指定なら、open_questionsへ「取消期限」と、決まるまで確定できない画面と受付処理を書く。その設計のquestion_idsから質問へつなぐ。本文や図に「未決」と書くだけでは足りない。品質の未決条件にも同じ参照を付ける。

記録が矛盾する場合は両方の抜粋をsourcesへ残す。承認が必要な案と不要な案を、片方だけ決定済みにしない。共通する構成やデータは作成を進め、分かれる処理は条件未決の案として描く。

## 3. 構造化原本の書き方（OUT-02、OUT-04、OUT-08）

`assets/examples/basic-design-document.json`を形の見本にする。題材の名詞・条件・採否は今回の資料に置き換える。原本の全キーと、各配列の要素の全キーは見本と`document.py`の検査に従う。

| 項目 | 書く内容 |
|---|---|
| title、summary、background、purpose、readers | 課題、設計の要点、目的、読者。重大な未決条件はsummaryにも示す |
| terms、actors、scope | 用語、役割、対象と対象外。対象外が不明なら不明と書き、確認質問を残す |
| sources | 資料名label、行番号か発言の場所location、実際の記述quote |
| requirements | 入力で求められた振る舞い。id、title、statement、source_ids |
| coverage | architecture、screen、data、integrationの順。area、applicable、reason、source_ids、question_ids |
| designs | id、area、title、statement、reason、details、status、requirement_ids、source_ids、diagram_ids、question_ids |
| diagrams | id、kind、area、title、intro、takeaway、alt、design_ids、source_ids、mermaid |
| diagram_decisions | 図の8種類の順にkind、selected、reason、source_ids |
| quality | 性能・可用性・セキュリティ・個人情報・運用・アクセシビリティの順。category、status、statement、acceptance、source_ids、question_ids |
| constraints | 資料で指定された制約のstatementとsource_ids。指定が無ければ空配列 |
| open_questions | id、question、consequence、source_ids。質問と、決まらない設計の範囲 |
| handoff | 詳細設計で具体化する作業の文字列の一覧。1件以上 |

designsのdetailsとqualityのacceptanceは文字列の一覧とする。補足が無ければdetailsは空配列、品質条件が未決ならacceptanceは空配列にして確認質問へつなぐ。

要望は1件以上の設計へ、設計は1件以上の図へ結び付ける。図と設計の参照は両方向に書く。設計のreasonは「必要だから」で済ませず、入力の課題・制約と、その分担や順序を選ぶ理由をつなぐ。

IDは原本のid・参照配列とHTMLの属性だけに使う。表示には要望名、設計名、図名、資料名と場所、質問名を使う。quoteは原資料どおり保存する。本文と図には、独自の略語を新たに作らない。

## 4. 完了前に意味を確かめる（STEP-02、OUT-03）

入力の要望から設計・採用理由へ進み、関連図で同じ関係を確認できるかを読む。各図の条件、方向、順序、状態を近くの本文と照合する。未指定の条件や未合意の変更を確定していないか、原資料の抜粋へ戻って確かめる。

文章は1段落1論点とし、要点、前提、設計、理由がつながるかを確認する。短文にしただけで主語や条件を落とさない。「最適化によって価値を創造する」のような抽象語の反復は、対象と処理の具体的な説明へ直す。

詳細設計へ引き継ぐ作業は項目同士を比較する。例えば物理列・索引の具体化と、メールの接続・再送の具体化を既に書いたなら、別の項目でもう一度まとめて書かない。追加する確認事項は関連する項目へ統合し、同じ作業を重ねない。

本文・見出し・図・リンクに、文書の中だけで定義した英字の略語を出さない。一般に使われる技術用語は、設計の判断に必要なときだけ使い、概要を含む最初の表示箇所で意味を説明する。例えば概要でReactを使うなら「画面を構築するライブラリのReact」と書く。巻末の用語説明だけでは初出の説明にならない。根拠のquoteと、HTMLやMermaidの内部の識別子は表示名と区別して確認する。
