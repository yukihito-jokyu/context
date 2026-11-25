---
title: motion-deck — ナレーションに合わせて動くスライドを作る
sidebar_label: motion-deck
---

# motion-deck

ナレーションの一文一文に合わせて図・コード・数字が動くHTMLのスライドを作りたいときに使います。1つのデッキを、音声に合わせて自動で進む「動画」と、クリックやリモコンで1ステップずつ進める「発表」の両方で使えます。発表モードには発表者ビューがあり、ナレーションのオン・オフも切り替えられます。PowerPoint（1画面＝1スライド、1文＝1クリックのネイティブのアニメーション付き。文字や図は編集できる図形・テキストで、要素ごとにグループ化）、MP4、1ファイルのHTML、配布用の静止画、発表の1ステップ＝1ページで文字を選べるPDFにも書き出せます。

見た目はデッキが使うテンプレートにそろえます。既定のdefaultは紙色の背景、左上の見出し、太枠とずらした影のカード、章バーと字幕の帯です（章バーはdefaultだけの部品です）。一般的な箇条書きのスライドは作りません。既存のmotion-deckのデッキの修正、声の作り直し、書き出しにも使います。テンプレート（見た目の型）を、言葉の依頼と質疑応答や既存の`.pptx`から作るとき、作ったテンプレートを指摘で直すときにも使います。

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
| 必要なソフト | Node.js 22以上（npmの依存なし）、FFmpeg（音声の連結と動画）、Chrome・Chromium・Edgeのいずれか（検査・静止画・PowerPoint・MP4・PDF） |
| ナレーション | local-ttsと、用意済みの音声合成エンジン。エンジンの準備はlocal-ttsのガイドを参照してください |
| 長さの目安 | 日本語のナレーションで1分あたり約420文字。VoxCPM2での合成は1文字約0.33秒と読み込み約30秒です |
| フォント | コード用のJetBrains Mono（SIL Open Font License）を同梱しています |

## 渡す情報

主題、聞き手、長さ、使い方（発表で使う、動画で配る、両方）を伝えます。PowerPoint・MP4・PDFが必要ならその形式も伝えます。PowerPointだけで使う資料なら、動かない完成した画面のPPTX専用のデッキで作り、ナレーション・字幕・章バー・MP4は作りません。声とエンジンを指定しなければlocal-ttsの既定のものを使います。発表だけで使い、声が要らない場合はそう伝えます。

## 依頼例

```text
motion-deckを使って、「Gitのブランチ入門」を3シーン・約1分のナレーション付きの発表資料にしてください。聞き手はGitを使い始めたばかりの開発者です。発表と動画の両方で使い、PowerPointとPDFにも書き出してください。
```

## 進め方

1. 主題・聞き手・長さ・使い方・声を確かめ、`init`で雛形を作ります。
2. 画面より先に、ナレーションの原稿（`script.json`）を書きます。1シーン＝1つの主張、1文＝画面の変化1つです。
3. 決められた部品とシーンの型でシーンを書き、要素が何番目の文で出るかを`data-at`で指定します。
4. `check`ではみ出し・文字の重なり・原稿との対応・プレーヤーの操作を検査し、`still`の一覧画像で見た目を確かめます。
5. local-ttsでナレーションを合成し、`timeline`で本当の尺にしてから、もう一度検査します。
6. 用途に合わせて、発表用のURL、動画、PowerPoint、MP4、1ファイルのHTML、PDFを渡し、確かめた範囲を報告します。
7. 直したい所があれば、動画モードで開いたプレーヤーの左右の列で指示を書きます。`I`（DOM選択）でステージの要素を、右の原稿で文を、左のシーンの「＋」でシーン全体を選んで指示を溜め、「全部コピー」した文をそのまま貼ると、その指示どおりにデッキを直します。

![動画モードのプレーヤー。左にシーンの一覧、中央にスライド、右にDOM選択のボタン・原稿・選んだ要素と指示の入力欄・溜めた指示の一覧が並ぶ](/skills/motion-deck/player-edit.png)

## 成果物の例

「Gitのブランチ入門」を、idea・switch・merge の3シーン・12文（読み上げ294文字）の新しいmotion-deckのデッキ（defaultテンプレート）として書き、local-ttsの既定の声とQwen3-TTSでナレーションを作りました。動画は0.88分（音声52.5秒）、発表は12ステップで、PowerPointは3スライド・要素のアニメーション12ステップ、PDFは既定の区切りで発表の1ステップ＝1ページの12ページです。作業用の複製で #composition に data-pdf="scene" を付けるとPDFは3ページ（シーン数）になり、見出しを途中で差し替えた複製では4ページ、data-export="pdf" を見るCSSはPDFにだけ効きました。最終のcheckはエラー0件・注意0件でした。音声は聞いておらず、個人の声の音声は載せていません。

**到達点：init から pdf までの全コマンドと、#147の確認（既定のPDFのページ数、data-pdf="scene"でのページ数と各ページの画面、--sceneでの絞り込み、見出しの差し替えでの区切り、data-export="pdf"のCSSがPDFにだけ効くこと）、PDF・PPTXの中身の確認、修正の列の撮影まで。#147の確認は作業用の複製で行い、その出力は公開していない。Qwen3-TTSのサーバーは別に起動されていた（started elsewhere）ため止めずに残した。音声の試聴、PowerPointでの再生、PDFビューアでの文字選択の操作、render（MP4）、bundle は未実施。**

### 実行した依頼

```text
motion-deckを使って、「Gitのブランチ入門」を3シーン・約1分のナレーション付きの発表資料にしてください。聞き手はGitを使い始めたばかりの開発者です。発表と動画の両方で使い、PowerPointとPDFにも書き出してください。声は既定のもの、エンジンはQwen3-TTSを使います。
```

### 実際の画面

![紙色の背景に、mainの黒い線とコミットの丸から水色のfeature/loginの枝が分かれる図、mainとfeature/loginのカードの横で「今ここ」の札が移りターミナルでgit switchを打つ画面、枝の先から緑の線がmainへ下りて合流し最後にコマンドの3つのまとめが出る画面が、各文の終わりごとに12枚並んだ一覧画像](/skills/motion-deck/contact.png)

[画像を原寸で開く](pathname:///skills/motion-deck/contact.png)

合成後の still --cues の一覧。次の文の直前を撮るため、data-until で消える要素（「今ここ」の札、mergeのターミナルと「main で実行」のカード）は消えかけの薄い状態で写る。発表の各ステップは live-contact.png と git-branch.pdf

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
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
````

### 成果物を取得する

- [実行報告（Markdown）](pathname:///skills/motion-deck/output.md#download)
- [PDFの書き出し（発表の12ステップ）](pathname:///skills/motion-deck/git-branch.pdf#download)
- [PowerPointの書き出し（PPTX）](pathname:///skills/motion-deck/git-branch.pptx#download)
- [pptxの出力](pathname:///skills/motion-deck/pptx.log#download)
- [プレーヤーの修正の列（PNG）](pathname:///skills/motion-deck/player-edit.png#download)
- [発表モードの各ステップの一覧画像（PNG）](pathname:///skills/motion-deck/live-contact.png#download)
- [原稿（script.json）](pathname:///skills/motion-deck/script.json#download)
- [シーンのフレームの関数（scenes.js。このデッキでは関数なし）](pathname:///skills/motion-deck/scenes.js#download)
- [最終のcheckの出力](pathname:///skills/motion-deck/check.log#download)
- [synthとtimelineの出力](pathname:///skills/motion-deck/synth.log#download)
- [デッキのHTML（シーンの構成）](pathname:///skills/motion-deck/index.html#download)
- [デッキのテーマ（CSS）](pathname:///skills/motion-deck/theme.css#download)
- [実行入力の原本](pathname:///skills/motion-deck/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/motion-deck/execution.json#download)

### 確認した結果

- init git-branch --title "Gitのブランチ入門"（defaultテンプレート、通常のデッキ）で雛形を作り、script.jsonを3シーン（idea・switch・merge、各4文）に、lexicon.jsonを「git switch」「git merge」「main」の読みに書き換え、index.html・theme.cssを新しく書いた。枝とコミットはPPTXで図形として残るよう、細長い箱と丸で組んだ。scenes.jsは関数なし
- 合成前の最初のcheckで switch 文3の say に英字「main」が残っているエラー1件が出たので say を「メイン」に直し、エラー0件・注意2件（仮の尺のシーン、narrationがないためナレーションのオン・オフ未確認）にした
- 合成前のstill --cuesの一覧をReadで見て、見出しが左上、太枠とずらした影、紙色の背景、章バー、字幕の帯がそろっていることを確かめた
- synth --dry-runは「3シーン、294文字。voice=既定 engine=qwen3-tts」「目安: 約2分」。1分を超えるため、synth git-branch --engine qwen3-ttsをバックグラウンドで実行し、終了コード0で idea 14.3秒・switch 17.3秒・merge 15.1秒の音声ができた（約82秒）。最後の行は「別に起動されたサーバーなので止めていません。」で、合成後の local-tts server status --engine qwen3-tts は「listening, started elsewhere」だったため止めていない
- timelineで「3シーン、0.88分（1575フレーム @30fps）、音声あり」。ffprobeでnarration.m4aは52.5秒。依頼の約1分に収まった
- 合成後（最終）のcheckはエラー0件・注意0件、発表モード12ステップ
- 合成後のstill --cues（12枚、contact.png）とstill --live（12枚、live-contact.png）の一覧をReadで見た。still --liveの画像の名前は idea×4・switch×4・merge×4 で、各シーンの文の数と一致した
- #147 既定（data-pdfなし）：pdfで12ページのPDFができ、PDFKitでページ数12（発表のステップ数と同じ）、文書のタイトル「Gitのブランチ入門」、全ページ1440×810pt、見出し・ラベル・ターミナルの行の文字を取り出せること、ナレーションの文（字幕）が入っていないことを確かめた
- #147 data-pdf="scene"：作業用フォルダ内の複製の #composition に data-pdf="scene" を付けて pdf を実行すると3ページ（シーン数。このデッキには途中で見出しが消えるシーンはない）。各ページの文字は既定のPDFの4・8・12ページ（各シーン最後のステップ）と一致し、ページの画像でも最後のステップの画面であることを確かめた
- #147 --scene：同じ複製で pdf --scene switch,merge を実行すると2ページ（switch・mergeの最後のステップ）
- #147 見出しの区切り：別の複製で merge の見出しに data-until="summary" を付け、まとめの文から新しい見出しを出すと（checkはエラー0件）、data-pdf="scene" のPDFは4ページになり、mergeは見出しの前（文2の画面）と後（まとめの画面）の2ページに分かれた
- #147 data-export="pdf"：data-pdf="scene" の複製の theme.css に #composition[data-export="pdf"] [data-scene="merge"] .run-card { visibility: visible !important; opacity: 1 !important; } を足すと、PDFの3ページ目に data-until で消えた「main で実行」のカードが出た（CSSなしの複製では出ない）。同じ複製の still --live --scene merge の4枚は、CSSなしの複製と1バイトも違わなかった
- pptxで3スライド（1シーン1スライド）、図形50・文字38・画像1・グループ36、要素のアニメーション12ステップ・差分の重ね1ステップ。図形にできず画像にした要素の一覧は出なかった
- PPTXのXMLで、画面切り替えが idea なし・switch プッシュ・merge プッシュであること、ノートに【スライド開始】【クリック n】の台本・文のメモ・シーンのメモが入ること、docProps/core.xmlのタイトルが題名でcreatorがmotion-deckであることを確かめた
- ヘッドレスのChrome（1600×900）で動画モードを #f=860 で開き、CDPの入力イベントで I → switchの feature/login のカードをクリック → 指示を入力 → 「指示を追加」と操作してplayer-edit.pngを撮った。対象は section[data-scene="switch"] > div.row2 > div.where > div.card.cyan・見ていた画面は文2（moved）となり、溜めた指示が1件になったことを画像とDOMで確かめた
- 公開する全ファイル（PPTXの中のXML・ノート・docProps、PDFの圧縮ストリーム、PNGのテキストの塊を含む）に個人名・ユーザー名・メールアドレス・絶対パス・声の名前がないことを機械的に調べ（該当0件）、synth.log・pptx.logの絶対パスは<work>に伏せ字にし、output.mdの声の名前は<声の名前>とした
- 実行者は音声を聞けず、PowerPointでの再生もPDFビューアでの文字選択の操作も確かめていない。試聴が必要な箇所はoutput.mdにシーンと文番号で書いた

## 確認するポイント

発表モード（`?mode=live`）で1ステップずつ進め、各クリックで今話している内容が画面に出ているかを確かめます。英字・数字・固有名詞・長い文は、実際に音声を聞いて読みを確かめます。静止画や検査の合格は、正しく読めたことの確認の代わりになりません。文字数から見積もった「仮の尺」のシーンが残っていないかも確認します。合成音声を公開する場合は、その旨を示すかを決め、他人の声やエンジンのライセンスはlocal-ttsの決まりに従います。

## 正本を読む

詳細な手順と制約は[motion-deckのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/motion-deck/SKILL.md)を参照してください。
