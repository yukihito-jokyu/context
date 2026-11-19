---
title: motion-deck — ナレーションに合わせて動くスライドを作る
sidebar_label: motion-deck
---

# motion-deck

ナレーションの一文一文に合わせて図・コード・数字が動くHTMLのスライドを作りたいときに使います。1つのデッキを、音声に合わせて自動で進む「動画」と、クリックやリモコンで1ステップずつ進める「発表」の両方で使えます。発表モードには発表者ビューがあり、ナレーションのオン・オフも切り替えられます。PowerPoint（1画面＝1スライド、1文＝1クリックのネイティブのアニメーション付き）、MP4、1ファイルのHTML、配布用の静止画にも書き出せます。

見た目は紙色の背景、左上の見出し、太枠とずらした影のカード、章バーと字幕の帯に固定しています。一般的な箇条書きのスライドは作りません。既存のmotion-deckのデッキの修正、声の作り直し、書き出しにも使います。

Remotionのプロジェクト（React）として作る場合、文章を読み上げるだけの場合（[local-tts](local-tts.md)）、既存の`.pptx`を編集する場合は対象外です。

## 解説動画

motion-deckの使い方を動画で紹介しています。

<div class="video-embed">
  <iframe src="https://www.youtube-nocookie.com/embed/CTrRRXWexjc" title="motion-deckの解説動画" loading="lazy" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
</div>

[YouTubeで見る](https://youtu.be/CTrRRXWexjc)

## 導入と前提

hooksを同梱しない単一Skillなので、[`npx skills add`](../../plugins/distribution.md)で導入します。ナレーションは隣に置いた[local-tts](local-tts.md)で作るため、両方を導入します。

```sh
npx skills add https://github.com/yukihito-jokyu/context/tree/main/utils/skills --skill motion-deck --skill local-tts --agent codex claude-code
```

local-ttsは、motion-deckと同じ階層、`.claude/skills/local-tts`、`~/.claude/skills/local-tts`の順に探します。別の場所にある場合は`--local-tts <フォルダ>`か環境変数`MOTION_LOCAL_TTS`で指定します。

| 項目 | 内容 |
| --- | --- |
| 必要なソフト | Node.js 22以上（npmの依存なし）、FFmpeg（音声の連結と動画）、Chrome・Chromium・Edgeのいずれか（検査・静止画・PowerPoint・MP4） |
| ナレーション | local-ttsと、用意済みの音声合成エンジン。エンジンの準備はlocal-ttsのガイドを参照してください |
| 長さの目安 | 日本語のナレーションで1分あたり約420文字。VoxCPM2での合成は1文字約0.33秒と読み込み約30秒です |
| フォント | コード用のJetBrains Mono（SIL Open Font License）を同梱しています |

## 渡す情報

主題、聞き手、長さ、使い方（発表で使う、動画で配る、両方）を伝えます。PowerPointやMP4が必要ならその形式も伝えます。声とエンジンを指定しなければlocal-ttsの既定のものを使います。発表だけで使い、声が要らない場合はそう伝えます。

## 依頼例

```text
motion-deckを使って、「Gitのブランチ入門」を3シーン・約1分のナレーション付きの発表資料にしてください。聞き手はGitを使い始めたばかりの開発者です。発表と動画の両方で使い、PowerPointにも書き出してください。
```

## 進め方

1. 主題・聞き手・長さ・使い方・声を確かめ、`init`で雛形を作ります。
2. 画面より先に、ナレーションの原稿（`script.json`）を書きます。1シーン＝1つの主張、1文＝画面の変化1つです。
3. 決められた部品とシーンの型でシーンを書き、要素が何番目の文で出るかを`data-at`で指定します。
4. `check`ではみ出し・文字の重なり・原稿との対応・プレーヤーの操作を検査し、`still`の一覧画像で見た目を確かめます。
5. local-ttsでナレーションを合成し、`timeline`で本当の尺にしてから、もう一度検査します。
6. 用途に合わせて、発表用のURL、動画、PowerPoint、MP4、1ファイルのHTMLを渡し、確かめた範囲を報告します。
7. 直したい所があれば、動画モードで開いたプレーヤーの左右の列で指示を書きます。`I`（DOM選択）でステージの要素を、右の原稿で文を、左のシーンの「＋」でシーン全体を選んで指示を溜め、「全部コピー」した文をそのまま貼ると、その指示どおりにデッキを直します。

![動画モードのプレーヤー。左にシーンの一覧、中央にスライド、右にDOM選択のボタン・原稿・選んだ要素と指示の入力欄・溜めた指示の一覧が並ぶ](/skills/motion-deck/player-edit.png)

## 成果物の例

「Gitのブランチ入門」を3シーン・13文（読み上げ344文字）のmotion-deckのデッキにし、local-ttsの既定の声と既定のエンジン（VoxCPM2）でナレーションを付けて、1分5秒の動画・13ステップの発表・4スライドのPowerPointにしました。動画モードの修正の列で指示を1件溜めた画面も撮り、声の名前と絶対パスは伏せ字にして、個人の声による音声は載せていません。

**到達点：PPTXの書き出しと修正の列の画面の撮影まで。エンジンのサーバーは別に起動されていたもの（started elsewhere）なので止めずに残した。音声の試聴、MP4の書き出し、bundleは未実施。**

### 実行した依頼

```text
motion-deckを使って、「Gitのブランチ入門」を3シーン・約1分のナレーション付きの発表資料にしてください。聞き手はGitを使い始めたばかりの開発者です。発表と動画の両方で使い、PowerPointにも書き出してください。声とエンジンは既定のものを使います。
```

### 実際の画面

![紙色の背景に、mainから枝が分かれる図と走るキャラクター、ターミナルのコマンドと注釈カード、合流の図とまとめの表が、各文の終わりごとに13枚並んだ一覧画像](/skills/motion-deck/contact.png)

[画像を原寸で開く](pathname:///skills/motion-deck/contact.png)

合成後の still --cues の一覧。次の文の直前を撮るため、data-until で差し替わる注釈カードや前半の図は消えかけの薄い状態で写る（発表の各ステップは live-contact.png）

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# motion-deck 実行報告：Gitのブランチ入門

| 項目 | 内容 |
|---|---|
| 出力 | デッキ `<work>/git-branch/index.html`、PowerPoint `git-branch.pptx` |
| 全体の長さ（動画） | 1分5秒（1956フレーム、30fps。narration.m4a は65.2秒） |
| ステップ数（発表） | 13ステップ（1文＝1ステップ） |
| シーン数 | 3（ブランチとは／作って移る／合流とまとめ）、13文、読み上げ344文字 |
| 声とエンジン | local-tts の既定の声 `<声の名前>`、既定のエンジン VoxCPM2 |
| check | エラー 0 件、注意 0 件（synth と timeline の後に再実行） |
| PPTX | 4スライド（merge は見出しが「今日のまとめ」に変わる所で2枚に分かれる）、絵40枚。要素のアニメーション13ステップ、差分の重ね6ステップ |
| 音声の試聴 | 未実施（実行者は音声を聞けない）。試聴してほしい箇所は下に記載 |
| 仮の尺のシーン | なし（全シーンに音声あり） |
| 公開しないもの | 音声（個人の声）、timeline.js、lexicon.json、個々の静止画、motion/（スキルの実行系の写し） |

## 開き方
````

### 成果物を取得する

- [実行報告（Markdown）](pathname:///skills/motion-deck/output.md#download)
- [PowerPointの書き出し（PPTX）](pathname:///skills/motion-deck/git-branch.pptx#download)
- [プレーヤーの修正の列（PNG）](pathname:///skills/motion-deck/player-edit.png#download)
- [発表モードの各ステップの一覧画像（PNG）](pathname:///skills/motion-deck/live-contact.png#download)
- [原稿（script.json）](pathname:///skills/motion-deck/script.json#download)
- [シーンのフレームの関数（scenes.js）](pathname:///skills/motion-deck/scenes.js#download)
- [最終のcheckの出力](pathname:///skills/motion-deck/check.log#download)
- [synthとtimelineの出力](pathname:///skills/motion-deck/synth.log#download)
- [デッキのHTML（シーンの構成）](pathname:///skills/motion-deck/index.html#download)
- [デッキのテーマ（CSS）](pathname:///skills/motion-deck/theme.css#download)
- [実行入力の原本](pathname:///skills/motion-deck/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/motion-deck/execution.json#download)

### 確認した結果

- init（既定のテンプレート）で雛形を作り、script.jsonを3シーン・13文に書き換え、index.html・theme.css・scenes.jsを書いた
- 音声なしのcheckでエラー0件・注意2件（仮の尺、ナレーション切り替え未確認）。still --cuesの一覧を見て、switchの走者と枝のラベルの重なりを直した
- synth --dry-runで3シーン・344文字・目安約3分と出たため、synthをバックグラウンドで実行し、終了コード0・155秒で3シーン（20.6秒・20.0秒・18.8秒）の音声ができた
- 既定の声と既定のエンジン（VoxCPM2）が使われたことを、local-ttsの設定とVoxCPM2サーバーのログで確認
- timelineで3シーン・1.09分（1956フレーム）・音声ありになり、ffprobeでnarration.m4aが65.2秒であることを確認
- 合成後のcheckでエラー0件・注意0件、発表モード13ステップを確認
- 合成後のstill --cues（13枚）とstill --live（13枚、別の--out）の一覧画像を見て、見出しが左上、太枠とずらした影、章バーと字幕の帯、色の意味がそろっていることを確認
- pptxで4スライド（mergeは見出しの差し替えで2枚）・絵40枚・要素のアニメーション13ステップ・差分の重ね6ステップのPPTXができ、ノートに台本とメモが入っていることを確認
- local-tts server stopは「No server started by this tool is running」。server statusでvoxcpm2とomnivoiceが別に起動されたサーバー（started elsewhere）として動いていることを確認し、止めずに残した
- ヘッドレスのChrome（1600×900）で動画モードをフレーム1146で開き、CDPでI→注釈カードのクリック→指示の入力→「指示を追加」と操作してplayer-edit.pngを撮り、修正の列（シーン・DOM選択・原稿・対象と指示・溜めた指示1件）が写っていることを画像で確認
- 公開する全ファイル（PPTXのノート・XML・docProps・画像のメタデータを含む）に個人名・ユーザー名・メールアドレス・絶対パス・声の名前がないことを確認し、synth.logの絶対パスとoutput.mdの声の名前は伏せ字にした
- 実行者は音声を聞けないため、読みの正しさは未確認。試聴が必要な箇所をoutput.mdにシーンと文番号で記録

## 確認するポイント

発表モード（`?mode=live`）で1ステップずつ進め、各クリックで今話している内容が画面に出ているかを確かめます。英字・数字・固有名詞・長い文は、実際に音声を聞いて読みを確かめます。静止画や検査の合格は、正しく読めたことの確認の代わりになりません。文字数から見積もった「仮の尺」のシーンが残っていないかも確認します。合成音声を公開する場合は、その旨を示すかを決め、他人の声やエンジンのライセンスはlocal-ttsの決まりに従います。

## 正本を読む

詳細な手順と制約は[motion-deckのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/motion-deck/SKILL.md)を参照してください。
