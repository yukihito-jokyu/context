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

「Gitのブランチ入門」を3シーン・12文（読み上げ343文字）のmotion-deckのデッキ（defaultテンプレート）にし、local-ttsの既定の声とQwen3-TTSでナレーションを付けて、1分01秒の動画・12ステップの発表・4スライドのPowerPoint・12ページのPDFにしました。PDFは発表の1ステップ＝1ページで、全ページの文字を取り出せ、画像は使っていません。PDFを見比べたときに合流の図のずれに気づいて直し、書き出しをやり直しました。声の名前と絶対パスは伏せ字にし、個人の声による音声は載せていません。

**到達点：PDFとPPTXの書き出しと確認、修正の列の画面の撮影まで。Qwen3-TTSのサーバーは合成前から別に起動されていた（started elsewhere）ため、synthは起動しておらず、止めずに残した。音声の試聴、PowerPointでの再生確認、PDFビューアでの文字選択の操作、MP4の書き出し、bundleは未実施。**

### 実行した依頼

```text
motion-deckを使って、「Gitのブランチ入門」を3シーン・約1分のナレーション付きの発表資料にしてください。聞き手はGitを使い始めたばかりの開発者です。発表と動画の両方で使い、PowerPointとPDFにも書き出してください。声は既定のもの、エンジンはQwen3-TTSを使います。
```

### 実際の画面

![紙色の背景に、mainの黒い線からfeature/loginの青い枝が分かれる図、ターミナルの打ち込みと今いる枝のカードを移る走るキャラクター、枝がmainに下りて緑の合流のコミットができる図とまとめの表が、各文の終わりごとに12枚並んだ一覧画像](/skills/motion-deck/contact.png)

[画像を原寸で開く](pathname:///skills/motion-deck/contact.png)

合成後の still --cues の一覧。次の文の直前を撮るため、data-until で消える merge の前半は消えかけの薄い状態で写る（発表の各ステップは live-contact.png と git-branch.pdf）

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# motion-deck 実行報告：Gitのブランチ入門

| 項目 | 内容 |
|---|---|
| 出力 | デッキ `<work>/git-branch/index.html`、PowerPoint `git-branch.pptx`、PDF `git-branch.pdf` |
| 全体の長さ（動画） | 1分01秒（1830フレーム、30fps。narration.m4a は61.0秒） |
| ステップ数（発表） | 12ステップ（1文＝1ステップ） |
| シーン数 | 3（ブランチとは／作って移る／合流）、12文、読み上げ343文字 |
| 声とエンジン | local-tts の既定の声 `<声の名前>`、エンジン Qwen3-TTS（`--engine qwen3-tts`で指定） |
| check | エラー 0 件、注意 0 件（synth と timeline の後に再実行） |
| PPTX | 4スライド（merge は見出しが「今日のまとめ」に変わる所で2枚に分かれる）、図形51・文字50・画像3、グループ37。要素のアニメーション12ステップ、差分の重ね3ステップ |
| PDF | 12ページ（発表の12ステップと同じ数）。1ページ1440×810pt（16:9）、字幕なし、文字を選べる・検索できる |
| 音声の試聴 | 未実施（実行者は音声を聞けない）。試聴してほしい箇所は下に記載 |
| 仮の尺のシーン | なし（全シーンに音声あり） |
| 公開しないもの | 音声（個人の声）、timeline.js、lexicon.json、個々の静止画、motion/（スキルの実行系の写し） |

````

### 成果物を取得する

- [実行報告（Markdown）](pathname:///skills/motion-deck/output.md#download)
- [PDFの書き出し（発表の各ステップ）](pathname:///skills/motion-deck/git-branch.pdf#download)
- [PowerPointの書き出し（PPTX）](pathname:///skills/motion-deck/git-branch.pptx#download)
- [pptxの出力](pathname:///skills/motion-deck/pptx.log#download)
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

- init（既定のテンプレート、通常のデッキ）で雛形を作り、script.jsonを3シーン・12文に書き換え、index.html・theme.css・scenes.jsを書いた。枝の線とコミットはPPTXで図形として残るよう、SVGではなく箱で描いた
- 音声なしのcheckで、mergeの「git merge」の吹き出しとまとめの表の文字の重なりを注意として指摘されたので、合流の図をdata-until="sum"で消すようにして、エラー0件・注意2件（仮の尺、ナレーション切り替え未確認）にした。still --cuesの一覧を見て構図を確かめた
- synth --dry-runで3シーン・343文字・目安約2分と出たため、synthを--engine qwen3-ttsでバックグラウンドで実行し、終了コード0・約93秒で3シーン（18.8秒・18.7秒・17.7秒）の音声ができた
- timelineで3シーン・1.02分（1830フレーム）・音声ありになり、ffprobeでnarration.m4aが61.0秒であることを確認。依頼の約1分の範囲に収まった
- 合成後のcheckでエラー0件・注意0件、発表モード12ステップを確認
- pdfで12ページのPDFができ、PDFKitでページ数12（発表のステップ数と同じ）、全ページ1440×810pt、全ページでpage.stringから見出し・ラベル・ターミナルの行などの文字を取り出せること、字幕の文が入っていないことを確認
- PDFのフォントはJetBrains Mono（TrueType）とヒラギノ角ゴ（Type3）の部分埋め込みで、画像のXObjectは0個。メタデータはTitle「index.html」、Creator HeadlessChrome、Producer Skia/PDF
- PDFの1・4・6・10・12ページをPDFKitでPNGにして同じステップのstill --liveの画像と見比べ、10ページ目（mergeの合流）で合流の線が枝より約40px上から始まり緑のコミットがmainの線から浮いているずれに気づいた。合流の線とコミットを同じ図の箱に入れ直し、check（エラー0件・注意0件）・still --cues・still --live・pptx・pdfをやり直して、各ページがstill --liveと一致することを確認した（原稿は変えていないので音声は作り直していない）
- 合成後のstill --cues（12枚）とstill --live（12ステップ、別の--out）の一覧画像を見て、見出しが左上、太枠とずらした影、紙色の背景、章バーと字幕の帯がそろっていることを確認
- pptxで4スライド（mergeは見出しの差し替えで2枚）・図形51・文字50・画像3・グループ37・要素のアニメーション12ステップ・差分の重ね3ステップのPPTXができた。図形にできず画像にした要素の一覧は出なかった
- PPTXのXMLで、文字がテキストボックス（txBox。スライド順に8・14・7・21個）に入っていること、アニメーションの対象がグループ（46・25・14・14件）か画像（0・6・0・0件）で単独の図形がないこと、画面切り替え（プッシュ・円・フェード）とノートの台本・文のメモ・シーンのメモを確認
- ヘッドレスのChrome（1600×900）で動画モードを開き、CDPでI→feature/loginのカードのクリック→親へ→指示の入力→「指示を追加」と操作してplayer-edit.pngを撮り、溜めた指示が1件になったことを画像とDOMで確認
- 公開する全ファイル（PPTXのノート・XML・docProps・画像、PDFの圧縮ストリームとメタデータ、PNGのメタデータを含む）に個人名・ユーザー名・メールアドレス・絶対パス・声の名前がないことを確認し、check.log・synth.log・pptx.logの絶対パスとoutput.mdの声の名前は伏せ字にした
- 合成前と作業の最後にlocal-tts server statusで、Qwen3-TTSが別に起動されたもの（started elsewhere）として動いていることを確認し、止めなかった
- 実行者は音声を聞けず、PowerPointでの再生も、PDFビューアでの文字選択の操作も確かめていない。試聴が必要な箇所をoutput.mdにシーンと文番号で記録

## 確認するポイント

発表モード（`?mode=live`）で1ステップずつ進め、各クリックで今話している内容が画面に出ているかを確かめます。英字・数字・固有名詞・長い文は、実際に音声を聞いて読みを確かめます。静止画や検査の合格は、正しく読めたことの確認の代わりになりません。文字数から見積もった「仮の尺」のシーンが残っていないかも確認します。合成音声を公開する場合は、その旨を示すかを決め、他人の声やエンジンのライセンスはlocal-ttsの決まりに従います。

## 正本を読む

詳細な手順と制約は[motion-deckのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/motion-deck/SKILL.md)を参照してください。
