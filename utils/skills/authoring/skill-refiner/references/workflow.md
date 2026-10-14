# 操作と形式

## 初期化・回答

`S`はこのスキルの絶対パス、`W`は作業領域。以下の入力をファイルへ保存する。スキル名を解決できない場合は正本の絶対パスを使う。

```json
{"skill":"explain-html","cases":[{"id":"loan","task":"備品貸出の仕組みをHTMLで説明してください。","files":[]}]}
```

```sh
python3 "$S/scripts/refine.py" --workspace "$W" init --input input.json
python3 "$S/scripts/review.py" --workspace "$W"
python3 "$S/scripts/refine.py" --workspace "$W" status
python3 "$S/scripts/refine.py" --workspace "$W" ack --response <回答ID> --answer '<指摘への回答>'
```

HTTPサーバーは127.0.0.1へバインドする。レビュー回答はOrigin・Host・セッショントークンを検査する。表示版が古い場合は保存しない。サーバーは権限を持つローカルユーザーやAIから承認を守る認証機構ではない。AIは人間の意思を補作しない。

サーバーを使えない場合は `review.py --workspace "$W" --static` で1枚のHTMLを保存する。人間が返した回答のみ、次で読み込む。

```sh
python3 "$S/scripts/refine.py" --workspace "$W" import-response --input response.json --user-statement '<実際の共有発言>'
```

## 新規エージェント

```sh
python3 "$S/scripts/refine.py" --workspace "$W" ticket --case loan --role generate
python3 "$S/scripts/refine.py" --workspace "$W" register --run <実行ID> --agent <実際のID>
python3 "$S/scripts/refine.py" --workspace "$W" finish --run <実行ID>
```

ticketが返すpromptをそのまま使う。生成担当は出力先へ成果物を保存する。対象スキルと入力ファイルはハッシュで固定する。スキル内のシンボリックリンクは未対応で停止する。実行に伴う `__pycache__`・pyc・.DS_Store は版の比較から除く。

生成担当には、その題材以外の作業領域、指摘、評価基準、制御スキルを渡さない。共有ファイルシステムまで隠せるとは断定しない。必要な入力だけを使う。実際のIDを取得できなければfinishできない。

## 評価関数

人間の指摘を読み、採点尺度まで具体化する。`method`には客観検査のコマンド・合格条件、または主観評価の0/部分点/1の尺度を記載する。コントローラーは任意コードを実行せず、独立評価担当が検査結果を根拠付きで返す。

```json
{
  "threshold": 0.8,
  "criteria": [{
    "id": "traceable", "label": "根拠へ辿れる",
    "feedback": "人間の指摘: 根拠の場所が分からない",
    "method": "各結論の参照先を実際に開く。全件対応=1、半数=0.5、対応なし=0。",
    "weight": 1, "minimum": 0.5
  }]
}
```

```sh
python3 "$S/scripts/refine.py" --workspace "$W" rubric --input rubric.json
# 人間のHTML承認後に未処理回答をackし、最初の成果物を評価する。
python3 "$S/scripts/refine.py" --workspace "$W" ticket --case loan --role evaluate
python3 "$S/scripts/refine.py" --workspace "$W" register --run <実行ID> --agent <新規ID>
python3 "$S/scripts/refine.py" --workspace "$W" finish --run <実行ID> --result <結果JSON>
```

結果は `{"status":"ok","grades":[{"id":"traceable","score":1,"evidence":"確認した参照先と観測結果"}]}`。失敗は `{"status":"error","reason":"実際の失敗理由"}`。必要な全評価項目が一度ずつ揃い、0〜1の有限数と根拠が必要。加重平均と各最低点から合否を決める。

## 改善案

```json
{
  "summary": "評価結果では結論と参照先の対応が不明だった。該当指示を明確にする。",
  "changes": [{
    "path": "SKILL.md", "before": "根拠を示す。", "after": "結論ごとに、根拠の実際の記述と参照先を示す。",
    "reason": "採点結果の未対応箇所を一般化するため"
  }]
}
```

`before`は対象ファイルで1回だけ出現する文字列。全文置換でもよい。新規ファイルは `before:null`。1ファイルに1置換を指定する。既存ファイルの削除は未対応。パスは対象スキル内に限定する。

```sh
python3 "$S/scripts/refine.py" --workspace "$W" analysis --input analysis.json
# HTML承認で候補版を作成した後、新規の生成担当・評価担当で同じ題材を実行する。
python3 "$S/scripts/refine.py" --workspace "$W" promote
```

promoteは再評価合格と最終HTML承認後のみ。開始時の正本が変わっていれば止める。正本・固定版・完成した成果物・承認後の基準は手作業で編集しない。

## 再開と停止

全状態は `state.json`、固定版は `skill-snapshot/`、候補は `candidate-skill/iteration-N/`、成果物は `iteration-N/<case>/generate/`、採点結果は `iteration-N/<case>/evaluate/`。回答は提出時の版・基準・改善案のハッシュを持ち、AIの回答を同じレコードへ保存する。

自動ループでも毎回statusを確認する。人間の指摘を先にackする。範囲変更が必要ならHTMLでpauseし、resume後に次のanalysisを提示する。自動ループの上限に達したらHTMLの進め方選択へ戻る。失敗した実行を再試行する場合はHTMLでretryし、新規チケットと新規IDを使う。
