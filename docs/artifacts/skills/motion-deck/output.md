# 実行報告：Gitのブランチ入門

## 出力

- デッキ：`<work>/git-branch/`（新しいデッキ、defaultテンプレート）。公開しているのは `index.html`・`theme.css`・`scenes.js`・`script.json`
- 動画：3シーン、0.94分（1684フレーム @30fps、ナレーションの音声は56.1秒）
- 発表：12ステップ（1文＝1ステップ。各シーン4文）
- 声とエンジン：local-ttsの既定の声（`<声の名前>`）、Qwen3-TTS（`--engine qwen3-tts`）
- PowerPoint：`git-branch.pptx`（3スライド、図形41・文字29・画像4、グループ31、要素のアニメーション11ステップ、差分の重ね4ステップ。図形にできず画像にした要素はなし）
- PDF：`git-branch.pdf`（12ページ＝発表の12ステップ、字幕なし）

| シーン | 章 | 文 | 音声 | 画面 |
|---|---|---|---|---|
| idea | ブランチとは | 4 | 17.6秒 | mainの線とコミット、そこから分かれる feature/login の枝、枝の先の失敗（赤い丸）と「mainは無事」のカード |
| switch | 作って移る | 4 | 15.9秒 | ターミナルで `git switch -c feature/login` と `git switch main`、右に枝の札と「今ここ」の札が移る |
| merge | 合流する | 4 | 16.8秒 | 枝の先からmainへ緑の線が上がり合流のコミットができる。最後にコマンドの3つのまとめに差し替え |

## 開き方

- 発表：`open "<work>/git-branch/index.html?mode=live"`。→・Space・クリックで1ステップずつ、←で戻る。`V`でナレーションのオン・オフ、`N`で発表者ビュー、`B`/`W`で画面を隠す
- 動画：`open "<work>/git-branch/index.html"`。`P`で発表モードと切り替え
- 直したい所は、動画モードの左右の修正の列で、`I`（DOM選択）で要素を選んで指示を書き、「全部コピー」した文を貼る（`player-edit.png`）

## 検査と確認

- `check`（合成前）：エラー0件・注意2件（仮の尺、ナレーションの切り替え未確認）
- `still --cues`（合成前）の一覧を見て、switch 文3の字幕を「-c を付けずに」とし、読みは `say` で「ハイフン シー」と与えた
- `synth --dry-run`：3シーン・316文字・目安約2分 → バックグラウンドで `synth --engine qwen3-tts`（約89秒、終了コード0）→ `timeline`
- `synth` の最後の行は「別に起動されたサーバーなので止めていません。」で、停止コマンドは出なかった。合成の前後の `local-tts server status --engine qwen3-tts` はどちらも「listening, started elsewhere」
- `check`（合成後・最終）：エラー0件・注意0件、発表モード12ステップ（`check.log`）
- 合成後の `still --cues`（12枚、`contact.png`）と `still --live`（12枚、`live-contact.png`）の一覧を見て、見出しが左上、太枠とずらした影、紙色の背景、章バー、字幕の帯（動画のみ）を確かめた
- `--out` の相対パス：作業フォルダ（デッキの親）で `pdf git-branch --out rel/test.pdf` を実行し、PDFは作業フォルダの `rel/test.pdf` にでき、デッキの中（`git-branch/rel/`）にはできなかった。`references/player.md` の「コマンドを実行したフォルダが基準」と一致（この試しの出力は公開していない）
- PDF：12ページ、タイトル「Gitのブランチ入門」、全ページ1440×810pt、見出し・ラベル・ターミナルの行の文字を取り出せた。ナレーションの文は入っていない
- PPTX：3スライド、画面切り替えはフェード・プッシュ・プッシュ、ノートに【スライド開始】【クリック n】の台本と文・シーンのメモ、docProps のタイトルは題名で作成者は motion-deck
- Qwen3-TTSのサーバーは合成前から別に起動されていた（started elsewhere）ため止めず、そのまま残した

## 確かめていないこと

- **音声は聞いていない。** 試聴してほしい箇所：
  - switch 文1（create）：「git switch -c」を「ギット スイッチ ハイフン シー」と読ませている
  - switch 文3（back）：「-c」を「ハイフン シー」と読ませている
  - merge 文1（cmd）：「git merge」の読み（語彙で「ギット マージ」）
  - idea 文1・文3、switch 文3、merge 文0〜2：「main」の読み（語彙で「メイン」）
- PowerPointでのアニメーションの再生、PDFビューアでの文字選択の操作、MP4の書き出し（render）、bundle は行っていない
- 仮の尺のシーンは残っていない
