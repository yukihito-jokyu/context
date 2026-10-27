# コードからモデル情報を作る

このスキルは、AIがコードを読んで概念を選び、スクリプトが形式と派生物を揃える。言語ごとのAST解析器は使わない。構造の検査と、コードの意味のレビューは別々に行う。

## 入力と走査

IN-01・IN-02：対象コードがない依頼は理由を示して中断する。`repo` の既定値は作業中のリポジトリ、`scope` の既定値は `.` である。名前と出力先は受付時に確認し、同名の出力があれば別の `name` を聞く（OUT-05）。出力を指定された場合は、検査済みカタログ全体をその場所へコピーして渡す。検査前にコピーしない。

`catalog.py inspect` はUTF-8のコードを列挙する。対応拡張子は `.py .ts .tsx .js .jsx .mjs .go .rs .java .kt .cs .rb .php .swift .scala .sql .prisma .ex .exs .dart .cpp .cc .c .h .hpp .vue .svelte` である。`.git`、Agent設定、実行記録、依存パッケージ、ビルド出力、symlinkは読まない。対応していない拡張子のコードを調査したい場合は、その制約を伝えて中断する。列挙したコードをすべて読めなければ `unread` にパスと理由を書く。READMEとAGENTS.mdは背景の確認に使い、コードの根拠の代わりにはしない。

## model.json

OUT-02：`assets/examples/model.json` の形を使う。見本の内容は題材の事実として転用しない。JSONのトップレベルには次の7キーだけを書く。

| キー | 値 |
| --- | --- |
| `schema_version` | 整数 `1` |
| `title` | 日本語の題名 |
| `domains` | `{path, name, description}` の配列。`path` は対象コードが存在するディレクトリの相対パス。単一領域は `.` にできる |
| `concepts` | 下記の概念の配列。1件以上 |
| `relations` | 下記の関係の配列。関係が確認できなければ空配列 |
| `questions` | 未確認点を改行で区切った日本語の文字列。確認事項がなければ空文字列 |
| `unread` | `{path, reason}` の配列。対象コードの未読パスと読めなかった理由 |

概念は `{key, symbol, name, domain, kind, description, attributes, evidence}` を持つ。

- `key` は先頭の根拠の `path` と `symbol` を `::` で結ぶ。例：`sales/order.py::Order`。
- `symbol` はコードの識別子を保持する。`name` はsymbolと同じ表示名に固定し、`description` は役割を日本語で説明する。領域の表示名もpathに固定する。pathが `.` の表示名は `ルート` にする。
- `domain` は宣言元ファイルの親ディレクトリを使い、`domains[].path` と一致させる。例：`sales/order.py` は `sales`、ルートの `order.py` は `.` になる。ここでの領域はコードの配置単位であり、業務上の境界とは断定しない。
- `kind` は `entity`、`value`、`enum`、`concept` の1つ。`entity` はEntity基底型かentity注釈、`value` はValueObject基底型かvalue_object注釈、`enum` は列挙宣言かリテラルの選択型を根拠にする。根拠にその宣言がないクラスは `concept` にする。idという名前やdataclassのfrozenだけでentityやvalueと断定しない。
- `attributes` は `{name, type, evidence}` の配列。選んだ概念に宣言された業務上のスカラー属性を記録する。別概念への参照はrelationsへ記録する。`_`で始まる内部用属性とフレームワークの制御属性は記録しない。属性を確認できなければ空配列にする。
- `evidence` は下記の根拠の配列。空にしない。

関係は `{source, target, kind, member, source_multiplicity, target_multiplicity, evidence}` を持つ。

- `source` と `target` は概念の `key` を指定する。
- `kind` は `association`、`inheritance`、`composition`、`aggregation`、`dependency` の1つ。継承は子から親へ向ける。合成・集約は所有側をsourceにする。通常の参照は `association` にする。
- `member` は参照を表すコード上のメンバー名・関数名をそのまま使う。例：`Order.lines` からOrderLineへの関係は `lines`、`Payment.order` からOrderへの関係は `order` にする。継承は `null` にする。`label` はbuildがmemberから生成する。継承のlabelは `継承` に固定する。関係名を日本語へ言い換えない。日本語の説明は概念のdescriptionとquestionsへ書く。
- 多重度は `null`、`1`、`0..1`、`0..*`、`1..*`、`*` の1つ。確定できなければ `null` にする。コレクション型だけでは最小1件や逆方向の多重度を断定しない。
- `evidence` は関係自体が分かる行を選ぶ。両端のクラス宣言があることだけを関係の根拠にしない。

`id` と関係の `label` は書かなくてもよい。buildがOUT-04の規則で生成して `model.json` に保存する。AIはハッシュを手計算しない。表示名、domains・concepts・relationsの順序もbuildが揃える。questionsを配列で書いた場合も、build後の正本は改行区切りの文字列になる。

## 根拠

根拠は `{path, start, end, quote}` の4キーだけを持つ。`path` はリポジトリ相対パス、`start` と `end` は1始まりの整数の行番号である。`quote` は両端を含む行の全文を改行で連結し、末尾には改行を足さない。空白やコード識別子を言い換えない。

OUT-03・OUT-08：抜粋が存在することと、その抜粋が説明を裏付けることを分けて確認する。業務概念の分類、関係の向きと参照メンバー、所有関係、多重度をコードから説明できるかレビューする。説明できない値は `concept`・`association`・`null` にし、不明点を `questions` へ書く。単なる参照を寿命の所有と断定しない。説明は日本語、symbol・member・quoteは実装の表記を保持する。

## 描画と検査

STEP-01〜STEP-05：調査→model.json→build→check→表示確認→finishの順に進める。Mermaid、PNG、HTMLを手で編集せず、モデル情報からbuildする。領域が1つならoverviewだけ、2つ以上ならoverviewと領域別の図を作る。領域を跨ぐ関係は両端の概念を図へ残す。

CLIはPATH上の `mmdc`、または環境変数 `MMDC` で指定する。ブラウザーの実行ファイルは `PUPPETEER_EXECUTABLE_PATH` で指定できる。依存ツールの自動ダウンロードはしない。変換失敗では理由を示して中断し、旧画像を今回の成功結果として扱わない。

STEP-06・OUT-01・OUT-06：checkとfinishはファイル集合、根拠、ID、コードのスナップショット、Mermaid、PNGのCRC・圧縮データ、HTML、manifestのハッシュを検査する。この検査でPNG内の意味まで照合したとは扱わない。PNGとHTMLを開き、日本語、ラベルの重なり、図の読みやすさ、検索、領域選択、拡大、原本取得を確認する。

OUT-07：検査を省略する指定は追加しない。コードが変わったときは再調査する。同じ実行内での修正にはbuildの `--replace` を使えるが、生成元の印がある出力だけを置き換える。失敗時は既存の出力を保持する。
