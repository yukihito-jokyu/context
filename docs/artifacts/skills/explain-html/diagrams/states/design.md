# states の設計

問いは「ワーカー処理の状態とクライアント表示はどう対応するか」。対象は同じ job_17 であり、観測開始はサーバーが queued として作る時点、観測終了は completed または failed の保存である。将来の削除や再実行が分からないため、対象の全生涯ではなく partial の lifecycle v2 とした。

4状態を同じ粒度で置く。queued→runningはワーカー開始、running→completedは成功、running→failedは失敗とする。③と④の間に矢印は作らない。狭幅でも状態名を保つため1列とし、失敗の矢印はrunningから外側を通ってfailedへ届く。上下に並ぶことは順序ではなく、矢印だけが遷移を示すとcaptionでも説明する。

図内には①〜④、正確な状態名、短い値名と成功／失敗の条件を残す。成功と失敗は主要文字でも示し、色だけには依存しない。resultUrl/reasonの表示条件とGET /jobs/job_17の取得は横の1番号1〜2文で説明する。GETは状態を変える処理ではないので、新しい遷移として描かない。

対応は①サーバーによるqueued作成、②ワーカーのrunning、③成功時の保存と結果表示、④失敗時の保存と理由表示。HTTP一般のGETと202の意味はRFC 9110、各状態やフィールドの意味は架空依頼文と分ける。POST 202の詳細、503と再試行上限は別図の範囲とする。

同梱Archify 2.16.0、editorial/showcaseを使用。標準SVGの背景・グリッド・凡例・文字・viewBoxは無改変で埋め込む。標準出力の補助文字は主要状態名より小さいため、主題に必要な条件を主要ラベルと常時表示の横解説でも対応させ、実測値をreview.jsonへ残す。

実行コマンドは<repository>をリポジトリ、<workdir>をこの成果物フォルダとして表記する。

```sh
node <repository>/utils/skills/discovery/explain-html/vendor/archify-jp/bin/archify.mjs validate lifecycle <workdir>/model.json --quality showcase --json
cd <workdir>
node <repository>/utils/skills/discovery/explain-html/vendor/archify-jp/bin/archify.mjs deliver lifecycle model.json figure.html --quality showcase --json > receipt.json
python3 <repository>/utils/skills/discovery/explain-html/scripts/export_standard_svg.py figure.html figure.svg --model model.json
node <repository>/utils/skills/discovery/explain-html/vendor/archify-jp/bin/archify.mjs visual-check figure.html --json
node <workdir>/check-panel.mjs
```
