# 見た目の決まり（Remotion で作った解説動画のスタイル）

このスキルで作るものは、**「動画」と頼まれても「発表資料・スライド」と頼まれても、同じ見た目にする。**
手本は、このユーザーが Remotion で作った解説動画（goroutine 入門、TTS 3モデル比較）。
箇条書きを並べた一般的なスライドの見た目にはしない。

## 目次

1. 画面の骨格
2. 色と文字
3. 部品の一覧（kit.css / kit.js）
4. シーンの型（手本の動画から）
5. 動きの決まり
6. やらないこと

## 1. 画面の骨格

```
┌──────────────────────────────────────────────┐
│ はじめに  なぜ同時に？  goroutineとは …  まとめ │ ← 章バー（data-chapter-bar。上 34px）
│ ━━━━━━━━━━━━━━──────────────────────────────  │
│                                                │
│ 見出し（左上・68px・太字・色付きの語）         │ ← top 112px, 左右 100px
│ 小見出し（色付き 34px）                        │
│                                                │
│   図・コード・カード（大きく、左寄せ）         │
│                                                │
│                                                │
│        ┌──────────────────────────────┐        │
│        │ 今読んでいる文（字幕）        │        │ ← 下 178px は字幕の帯
│        └──────────────────────────────┘        │
└──────────────────────────────────────────────┘
```

- 背景は紙の色（`--paper` #F4EFE4）。全シーン共通。
- 見出しは**左上**。中央寄せにするのは表紙と「つまずきやすい落とし穴を2つ」のような章扉（`.statement`）だけ。
- 内容は見出しの下に左寄せで大きく置く。右側に補足のカード（`.card.yellow`）を置く構図が多い。
- 余白は残してよい。1画面に詰め込まない。
- 1シーンの中で内容を差し替える（`data-until` と `data-at` の重ね）。シーンを細かく分けるより、同じ見出しの下で図が変わっていくほうが手本に近い。

## 2. 色と文字

| 変数 | 色 | 意味 |
|---|---|---|
| `--ink` | #1C2530 | 文字、枠線、影 |
| `--muted` | #59626F | 補足の文字、目盛り |
| `--cyan` / `--cyan-deep` / `--cyan-soft` | 青 | 主役、強調語（見出しの色付きの語は `-deep`） |
| `--coral` / `--coral-soft` | 赤 | 問題、注意、対比のもう一方 |
| `--yellow` / `--yellow-soft` | 黄 | 補足のカード、コードの語の下地 |
| `--green` / `--green-soft` | 緑 | 解決、良い点 |
| `--panel` / `--term` | 濃紺 | コード、ターミナル、まとめのキー |

- 文字: 日本語はヒラギノ角ゴ（太字 700〜800 を多用）、英数・コードは JetBrains Mono（同梱）。
- 大きさ: 見出し 68px（色帯つき 62px）、小見出し 34px、カードの本文 40〜52px、ラベル 28〜34px、注記 28px。**28px 未満は使わない。**
- 箱: 枠 4px の `--ink`、角丸 22px、**ずらした影 8px 8px 0（ぼかしなし）**。コードとターミナルは影 10px。
- 色付きの語: 見出しの中の大事な語を `.c-cyan` / `.c-coral` で色付け。コードの語は `.kw`（黄の下地）。

## 3. 部品の一覧

CSS の部品（kit.css）:

| クラス | 手本での使われ方 | 例 |
|---|---|---|
| `.h` / `.sub` / `.sub.muted` | 見出しと小見出し | `<h2 class="h">チャネル ＝ <span class="c-cyan">通り道</span></h2>` |
| `.title-bar.cyan` + `.kicker` | 色帯つきの見出し（TTS比較） | `<div class="title-bar green"><div><div class="kicker">仕組み</div><div class="h">…</div></div></div>` |
| `.card`（`.cyan` `.yellow` `.coral` `.green` `.dark`、`.big` `.bold`） | 説明・結論・補足 | `<div class="card yellow bold">一つが終わるまで、次は始まらない</div>` |
| `.tile`（`.label` `.value` `.sub-text`） | 数字を大きく | `<div class="tile"><div class="label">学習データ</div><div class="value">58万<small>時間</small></div></div>` |
| `.bubble` / `.chip` | 図の中のラベル、タグ | `<span class="bubble coral">新しい goroutine</span>` |
| `.kw` | 文中のコードの語 | `<span class="kw">sync.WaitGroup</span>` |
| `.point.good` `.bad` `.note` | ✓ / ! / i 付きの一行 | `<div class="point bad">商用は別契約</div>` |
| `.num` / `.roadmap` | 番号、今日の道のり | 雛形の roadmap シーン |
| `.summary`（`.row` `.key` `.val`） | まとめの表 | 雛形の summary シーン |
| `.table`（列に `.cyan` など） | 比較表 | `<table class="table">…</table>` |
| `.quote` / `.quote-en` | 標語・引用 | 「メモリを共有することで通信するのではなく…」 |
| `.statement` | 章扉の大きな一文 | `<div class="statement">つまずきやすい<span class="c-coral">落とし穴</span>を2つ</div>` |
| `.counter` | 黒い箱の黄色い数字 | データ競合の count |
| `.next-link` | 「次は…▶」 | |
| `.bg-cyan` `.bg-cyan-soft` … / `.hatch` | 帯や棒の色・斜線（待ち時間） | |

動く部品（kit.js。属性で設定し、時間に合わせて動く）:

| 部品 | 属性 | 手本 |
|---|---|---|
| `.runner` | `data-color`（cyan/coral/yellow/green）`data-size` `data-hat`（コック帽）`data-sleepy`（寝ている）`data-still`（止まる）`data-seed` | goroutine を表すキャラクター。上下に揺れて足が動く。位置は `Motion.scene` で動かす |
| `pre.code` | `data-title`（main.go など）`data-lang`（go js ts py sh rs html text）`data-size` `data-width` `data-reveal="文:行; 文:行"` `data-focus="文:行; 文:行"` | 文ごとに強調する行が移り、他の行が薄くなる |
| `.terminal` | `data-command` `data-at`（打ち始める文）`data-show`（枠を出す文。省略で最初から）、子の行に `data-at`、色は `.ok` `.warn` `.err` `.dim` | `$ go run main.go` を打ち、結果の行が出る |
| `.gantt` | `data-max` `data-ticks` `data-unit` `data-width` `data-label-width` `data-row-height`、行 `data-label`、棒 `.bar` に `data-start` `data-end` `data-color` `data-hatch` | 時間の帯（夕ごはんの例、ダウンロード）。棒は `data-anim="wipe"` で伸ばす |
| `.hbars` | `data-max` `data-width` `data-label-width`、行に `data-label` `data-value` `data-color` `data-hatch` `data-at` `data-delay`、行の中身が値の文字 | 横棒グラフ。文の開始で伸びる |
| `.gauge` | `data-label` `data-value` `data-max` `data-unit` `data-color` `data-at` `data-width` | メモリ使用量 |
| `.wave` | `data-bars` `data-color` `data-height` `data-width` `data-level` `data-seed` `data-still` | 声を表す揺れる波形 |
| `.tiles` | `data-count` `data-cols` `data-color` `data-fill`（埋め始める文）`data-fill-to` `data-width` | トークンの升目が埋まっていく |
| `.camera` | `data-shots="文:寄る先のセレクタ:倍率; 文:reset"` | 中の要素に寄る・引く（コードの1行、図の一部）。約0.8秒のばね |

## 4. シーンの型（手本の動画から）

| 型 | 構成 | 動き |
|---|---|---|
| 表紙 | `data-chrome="none"`、中央に小見出し＋大きな題名（英字は mono）、下に分岐する線と走者 | 線を `draw`、走者が線に沿って進む（雛形の title） |
| 道のり | 見出し＋`.sub.muted`、`.roadmap` に番号とカード | 文ごとに1つずつ |
| 時間の比較 | `.gantt`（順番にやる／同時にやる）、右下に結論のカード | 棒を `wipe` で伸ばす、待ち時間は `data-hatch` |
| 擬人化 | `.runner` を並べ、`.bubble` で名前。料理人の例は `data-hat` | 走者が移動・分岐。寝ている＝`data-sleepy` |
| 対比 | 左右に `.card.cyan` と `.card.coral`、中に走者や図 | 左を文1、右を文2で |
| コードの解説 | 左に `pre.code`、右に `.card.yellow` の注釈か `.terminal` | 行の強調が文ごとに移る。注釈は `data-until` で差し替え |
| 数字 | `.title-bar` ＋ `.tile` の格子、`.hbars`、`.gauge` | `count`、棒が伸びる |
| 標語 | 中央に `.quote`、下に `.quote-en` | `pop` |
| 章扉 | `.statement`（色付きの語） | `fade` か `scale` |
| 落とし穴 | 見出しに `.c-coral`、手順の `.chip` と矢印、`.counter` | 手順を順に、数字が変わる |
| まとめ | `.summary`（キーは mono） | 文ごとに1行 |
| 次の一歩 | `.card` を3つ（タイトルは mono）、`.next-link` | `data-stagger` |

## 5. 動きの決まり（Remotion の動きの考え方）

**原則**
1. **動きは物理で。** 出現はばね（`spring`）。等速の動きは、線を描く・帯が伸びる・文字を打つなど「進み具合」を表すときだけにする。
2. **きっかけは文。** 動きは秒ではなく、話している文に結び付ける。読んでいないものを先に出さない。文の内容と画面の変化を1対1にする。
3. **順番に、少しずつ。** 並ぶものは`data-stagger`（6〜10フレーム）でずらして出す。同時に全部を出さない。
4. **入りと出は対に。** 消すときも`data-until`＋`data-out`で動かして消す。突然消さない。
5. **場面は重ねて切り替える。** シーンの切り替えは前の絵を残したまま重ねる（`data-transition`）。白紙を挟まない。
6. **視線を導く。** 今の話題に寄る（`.camera`）、今の行を強調する（`data-focus`・`data-active`）、それ以外を薄くする。
7. **画面は生きている。** キャラクターや波形は待機中もゆっくり動かす（`data-loop`、`.runner`）。ただし動き続けるのは1画面に1〜2個まで。
8. **同じ時刻なら同じ絵。** 乱数は`Motion.random(seed)`、揺らぎは`Motion.noise`。どこで止めても、何度書き出しても同じになる。

**動きの語彙**

| 表したいこと | 書き方 |
|---|---|
| 出てくる（標準） | `data-anim="up"`（既定） |
| 横から説明が来る | `left` / `right` |
| 決め所・結論 | `pop`（1画面に1つ） |
| 図・アイコンが現れる | `scale` |
| 全面の絵・写真 | `zoom` |
| 線を描く・矢印を引く | `draw`（SVG） |
| 帯・棒が伸びる | `wipe` / `grow` / `grow-y`、`.hbars`、`.gantt` |
| 数字が増える | `count`、`.gauge`、`.tiles` |
| 打ち込む | `type`、`.terminal` |
| 一文を語ごとに | `words` |
| 語に印を付ける・打ち消す | `highlight` / `strike` |
| 何かが移動する・流れる | `data-anim="follow"` ＋ `data-follow`（線に沿って） |
| 一部に寄る | `.camera` の `data-shots` |
| 今の行・項目を強調 | `data-focus`（コード）、`data-active` |
| 内容を差し替える | 前に `data-until`＋`data-out`、次に `data-at` |
| 待機中も動く | `data-loop="float"` など、`.runner`、`.wave` |
| 場面転換 | `data-transition`（同じ章は fade、章の変わり目は slide） |

**PPTX に書き出したとき**：出現（`up` `left` `scale` `pop` `fade` `wipe` `draw` など）と消える動き（`data-until`）は、PowerPoint のネイティブのアニメーション（フロートイン・ズーム・ワイプ・フェード）になる。強調の移動、`follow`の移動、カメラ、`Motion.scene`の独自の動きは、変わった範囲だけを絵として重ねる（見た目は同じだが、動きはフェードになる）。PPTX でも動かしたい要素は、できるだけ出現・消える動きで表す。

## 6. やらないこと

- 箇条書きだけのスライド、中央寄せのタイトル＋本文の定型、角丸の影がぼやけたカード、グラデーション、写真の背景。
- 絵文字のアイコン（✓ ! i は `.point` の丸、番号は `.num`）。
- 見出しを中央に置く（表紙・章扉以外）。
- 原稿の文をそのまま画面に貼る（字幕と二重になる）。画面には図・キーワード・数字・コードを置く。
- 新しい色を足す。必要なら theme.css で変数を上書きして、意味（青＝主役、赤＝問題…）を保つ。
