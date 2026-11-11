---
title: motion-deck — ナレーションに合わせて動くスライドを作る
sidebar_label: motion-deck
---

# motion-deck

ナレーションの一文一文に合わせて図・コード・数字が動くHTMLのスライドを作りたいときに使います。1つのデッキを、音声に合わせて自動で進む「動画」と、クリックやリモコンで1ステップずつ進める「発表」の両方で使えます。発表モードには発表者ビューがあり、ナレーションのオン・オフも切り替えられます。PowerPoint（1文＝1クリックのネイティブのアニメーション付き）、MP4、1ファイルのHTML、配布用の静止画にも書き出せます。

見た目は紙色の背景、左上の見出し、太枠とずらした影のカード、章バーと字幕の帯に固定しています。一般的な箇条書きのスライドは作りません。既存のmotion-deckのデッキの修正、声の作り直し、書き出しにも使います。

Remotionのプロジェクト（React）として作る場合、文章を読み上げるだけの場合（[local-tts](local-tts.md)）、既存の`.pptx`を編集する場合は対象外です。

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

## 成果物の例

「Gitのブランチ入門」を3シーン・15文（433文字）のmotion-deckのデッキにし、local-ttsの既定の声とVoxCPM2でナレーションを付けて、1分15秒の動画・15ステップの発表・3スライドのPowerPointにしました。公開物は原稿・シーンのスクリプト・一覧画像・PPTX・checkとsynthの記録で、個人の声による音声は載せていません。声の名前と絶対パスは伏せ字にしています。

**到達点：PPTXの書き出しとエンジン停止まで。音声の試聴、MP4の書き出し、bundleは未実施。**

### 実行した依頼

```text
motion-deckを使って、「Gitのブランチ入門」を3シーン・約1分のナレーション付きの発表資料にしてください。聞き手はGitを使い始めたばかりの開発者です。発表と動画の両方で使い、PowerPointにも書き出してください。声とエンジンは既定のものを使います。
```

### 実際の画面

![紙色の背景に、ブランチの分岐を描いた線と走るキャラクター、ターミナル風のコードと注釈カード、合流の図とまとめの表が、各文の終わりごとに15枚並んだ一覧画像](/skills/motion-deck/contact.png)

[画像を原寸で開く](pathname:///skills/motion-deck/contact.png)

合成後の still --cues の一覧。次の文の直前を撮るため、data-until で差し替わる注釈カードは消えかけの薄い状態で写る（発表の各ステップは live-contact.png）

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# motion-deck 実行報告：Gitのブランチ入門

| 項目 | 内容 |
|---|---|
| 出力 | デッキ `<work>/git-branch/index.html`、PowerPoint `git-branch.pptx` |
| 全体の長さ（動画） | 1分15秒（2250フレーム、30fps） |
| ステップ数（発表） | 15ステップ（1文＝1ステップ） |
| シーン数 | 3（ブランチとは／作って移る／合流とまとめ）、原稿433文字・15文 |
| 声とエンジン | local-tts の既定の声 `<個人名>`、既定のエンジン VoxCPM2 |
| check | エラー 0 件、注意 0 件（合成と timeline の後に再実行） |
| PPTX | 3スライド、絵58枚。要素のアニメーション15ステップ、差分の重ね6ステップ |
| 音声の試聴 | 未実施（実行者は音声を聞けない）。試聴してほしい箇所は下に記載 |
| 仮の尺のシーン | なし（全シーンに音声あり） |
| 公開しないもの | 音声（個人の声）、timeline.js、個々の静止画、bundle、MP4 |

## 開き方
````

### 成果物を取得する

- [実行報告（Markdown）](pathname:///skills/motion-deck/output.md#download)
- [PowerPointの書き出し（PPTX）](pathname:///skills/motion-deck/git-branch.pptx#download)
- [発表モードの各ステップの一覧画像（PNG）](pathname:///skills/motion-deck/live-contact.png#download)
- [原稿（script.json）](pathname:///skills/motion-deck/script.json#download)
- [シーンのフレームの関数（scenes.js）](pathname:///skills/motion-deck/scenes.js#download)
- [最終のcheckの出力](pathname:///skills/motion-deck/check.log#download)
- [synthとtimelineの出力（要点）](pathname:///skills/motion-deck/synth.log#download)
- [デッキのHTML（シーンの構成）](pathname:///skills/motion-deck/index.html#download)
- [デッキのテーマ（CSS）](pathname:///skills/motion-deck/theme.css#download)
- [実行入力の原本](pathname:///skills/motion-deck/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/motion-deck/execution.json#download)

### 確認した結果

- initで雛形を作り、script.jsonを3シーン・15文・433文字（読み上げ428文字）に書き換えた
- 音声なしのcheckでエラー0件・注意2件（仮の尺、ナレーション切り替え未確認）を確認し、still --cuesの一覧を見て1シーン目の空いた画面を直した
- synth --dry-runで3シーン・428文字・目安約3分と出たため、synthをバックグラウンドで実行し、終了コード0・153秒で3シーン（21.9秒・24.3秒・23.0秒）の音声ができた
- 既定の声と既定のエンジン（VoxCPM2）が使われたことを、local-ttsの設定とサーバーのログで確認
- local-tts server stopでエンジンを止め、server statusでvoxcpm2がnot runningであることを確認
- timelineで3シーン・1.25分（2250フレーム）・音声ありになり、ffprobeでnarration.m4aが75.0秒であることを確認
- 合成後のcheckでエラー0件・注意0件、発表モード15ステップを確認
- 合成後のstill --cues（15枚）とstill --live（15枚）の一覧画像を見て、見出しが左上、太枠とずらした影のカード、章バーと字幕の帯、色の意味がそろっていることを確認
- pptxで3スライド・絵58枚・要素のアニメーション15ステップ・差分の重ね6ステップのPPTXができ、ノートに台本とメモが入っていることを確認
- 実行者は音声を聞けないため、読みの正しさは未確認。試聴が必要な箇所をoutput.mdにシーンと文番号で記録

## 確認するポイント

発表モード（`?mode=live`）で1ステップずつ進め、各クリックで今話している内容が画面に出ているかを確かめます。英字・数字・固有名詞・長い文は、実際に音声を聞いて読みを確かめます。静止画や検査の合格は、正しく読めたことの確認の代わりになりません。文字数から見積もった「仮の尺」のシーンが残っていないかも確認します。合成音声を公開する場合は、その旨を示すかを決め、他人の声やエンジンのライセンスはlocal-ttsの決まりに従います。

## 正本を読む

詳細な手順と制約は[motion-deckのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/motion-deck/SKILL.md)を参照してください。
