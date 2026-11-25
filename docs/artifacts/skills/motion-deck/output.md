# 実行報告：Gitのブランチ入門

## 出力

- デッキ：`<work>/git-branch/`（新しいデッキ、defaultテンプレート）。公開しているのは `index.html`・`theme.css`・`scenes.js`・`script.json`
- 動画：3シーン、0.88分（1575フレーム @30fps、ナレーションの音声は52.5秒）
- 発表：12ステップ（1文＝1ステップ。各シーン4文）
- 声とエンジン：local-ttsの既定の声（`<声の名前>`）、Qwen3-TTS（`--engine qwen3-tts`）
- PowerPoint：`git-branch.pptx`（3スライド、図形50・文字38・画像1、グループ36、要素のアニメーション12ステップ、差分の重ね1ステップ。図形にできず画像にした要素の一覧は出なかった）
- PDF：`git-branch.pdf`（既定の区切りで12ページ＝発表の12ステップ、字幕なし）

| シーン | 章 | 文 | 音声 | 画面 |
|---|---|---|---|---|
| idea | ブランチとは | 4 | 14.3秒 | mainの黒い線とコミットの丸、そこから分かれる水色の feature/login の枝、「枝で失敗しても、main は無傷」のカード |
| switch | 枝を移る | 4 | 17.3秒 | 左に main と feature/login のカードと「今ここ」の札（main → 枝 → main と移る）、右のターミナルで `git switch -c feature/login` と `git switch main` |
| merge | 合流する | 4 | 15.1秒 | 枝の先から緑の線がmainへ下りて合流のコミットができる。ターミナルと「main で実行」のカードは、最後にコマンドの3つのまとめに差し替え |

## 開き方

- 発表：`open "<work>/git-branch/index.html?mode=live"`。→・Space・クリックで1ステップずつ、←で戻る。`V`でナレーションのオン・オフ、`N`で発表者ビュー、`B`/`W`で画面を隠す
- 動画：`open "<work>/git-branch/index.html"`。`P`で発表モードと切り替え
- 直したい所は、動画モードの左右の修正の列で、`I`（DOM選択）で要素を選んで指示を書き、「全部コピー」した文を貼る（`player-edit.png`）

## 検査と確認

- `check`（合成前）：最初は switch 文3の `say` に「main」が残っていてエラー1件。`say` を「メイン」にしてエラー0件・注意2件（仮の尺、ナレーションの切り替え未確認）
- `still --cues`（合成前）の一覧を見て、見出しが左上、太枠とずらした影、紙色の背景、章バー、字幕の帯を確かめた
- `synth --dry-run`：3シーン・294文字・目安約2分 → バックグラウンドで `synth --engine qwen3-tts`（3シーンで約82秒、終了コード0）→ `timeline`
- `synth` の最後の行は「別に起動されたサーバーなので止めていません。」。合成後の `local-tts server status --engine qwen3-tts` は「listening, started elsewhere」で、他で起動されたサーバーのため止めていない
- `check`（合成後・最終）：エラー0件・注意0件、発表モード12ステップ（`check.log`）
- 合成後の `still --cues`（12枚、`contact.png`）と `still --live`（12枚、`live-contact.png`）の一覧を見た。`still --live` の並びは idea×4・switch×4・merge×4 で各シーンの文の数と一致
- PDF（既定）：12ページ＝発表のステップ数、タイトル「Gitのブランチ入門」、全ページ1440×810pt、見出し・ラベル・ターミナルの行の文字を取り出せた。ナレーションの文（字幕）は入っていない
- PPTX：3スライド、画面切り替えは idea なし・switch プッシュ・merge プッシュ、ノートに【スライド開始】【クリック n】の台本と文・シーンのメモ、docProps のタイトルは題名で作成者は motion-deck
- 修正の列：ヘッドレスのChrome（1600×900）で動画モードを `#f=860` で開き、`I` → switch の feature/login のカードをクリック → 指示を入力 →「指示を追加」。対象は `section[data-scene="switch"] > div.row2 > div.where > div.card.cyan`、見ていた画面は「文2（moved）のとき」、溜めた指示は1件（`player-edit.png`）

## #147 の確認（PDF の区切りと PDF だけの見た目）

確認はデッキを作業フォルダ内で複製して行い、試しの出力は公開していない。

1. 既定（`data-pdf` なし）：`pdf` は12ページで、発表のステップ数（12）と同じ
2. 複製の `#composition` に `data-pdf="scene"` を付けた `pdf`：3ページ＝シーン数。各ページの文字は、既定のPDFの4・8・12ページ（各シーン最後のステップ）と同じで、画像でも switch は「今ここ」が main に戻りターミナルに4行が出た最後の画面、merge はまとめの画面だった
   - `--scene switch,merge`：2ページ（switch・merge の最後のステップ）
   - さらに別の複製で merge の見出しを `data-until="summary"` で消し、まとめの文から新しい見出しを出すと4ページ（merge が見出しの前後で2ページに分かれ、前半のページはターミナルと「main で実行」が出た文2の画面）。`check` はエラー0件
3. `data-pdf="scene"` の複製の `theme.css` に `#composition[data-export="pdf"] [data-scene="merge"] .run-card { visibility: visible !important; opacity: 1 !important; }` を足すと、PDFの3ページ目（まとめの画面）に `data-until` で消えたはずの「main で実行」のカードが出た（CSSなしの複製のPDFでは出ない）。同じ複製の `still --live --scene merge` の4枚は、CSSなしの複製と1バイトも違わず、PDFでだけ見た目が変わることを確かめた

## 確かめていないこと

- **音声は聞いていない。** 試聴してほしい箇所：
  - switch 文1（create）・文3（back）：「-c」を `say` で「ハイフン シー」と読ませている
  - switch 文0、merge 文1（run）：「git switch」「git merge」の読み（語彙で「ギット スイッチ」「ギット マージ」）
  - idea 文1〜3、switch 文3、merge 文0〜2：「main」の読み（語彙で「メイン」）
- PowerPointでのアニメーションの再生、PDFビューアでの文字選択の操作、MP4の書き出し（render）、bundle は行っていない
- 仮の尺のシーンは残っていない
