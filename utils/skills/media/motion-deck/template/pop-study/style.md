# 見た目の決まり（pop-study：明るくポップな勉強会向け）

このテンプレートで作るものは、**「動画」と頼まれても「発表資料・スライド」と頼まれても、同じ見た目にする。**
勉強会で話すための、明るく親しみやすい見た目。後ろの席からも読めるよう、文字は太く大きくする。
箇条書きを並べた一般的なスライドの見た目にはしない。

## 目次

1. 画面の骨格
2. 色と文字
3. 部品の一覧（kit.css / kit.js）
4. シーンの型
5. 動きの決まり
6. やらないこと

## 1. 画面の骨格

```
┌──────────────────────────────────────────────┐
│ 見出し（左上・68px・極太・色付きの語）         │ ← top 112px, 左右 100px
│ 小見出し（色付き 34px）                        │
│                                                │
│   図・コード・カード（大きく、左寄せ）         │
│ ╭────────────────────────────────────────────╮ │
│ │ 結論の帯（.ps-band）                        │ │ ← 下まで使い切る
│ ╰────────────────────────────────────────────╯ │
│        ╭──────────────────────────────╮        │
│        │ 今読んでいる文（字幕）        │        │ ← 下 178px は字幕の帯（丸い帯）
│        ╰──────────────────────────────╯        │
└──────────────────────────────────────────────┘
```

- 背景はクリーム色（`--paper` #FFF6E6）の無地。模様は付けない。全シーン共通。
- 章バーは使わない（`data-chapter-bar="off"`）。
- 画面の隅に飾りの図形（星・丸など）は置かない。ポップさは色と、箱の色付きの影で出す。
- 見出しは**左上**。表紙は左に題名・右に色の箱、章扉は左に大きな番号・右に章名。中央寄せは大きな数字と `.statement` だけ。
- 内容は見出しの下に大きく置き、字幕の帯の上まで使い切る（下半分を空けない）。結論は横長の帯（`.ps-band`）か色のカードで言い切る。
- 余白は標準。1画面に詰め込まない。
- 1シーンの中で内容を差し替える（`data-until` と `data-at` の重ね）。

## 2. 色と文字

| 変数 | 色 | 意味 |
|---|---|---|
| `--paper` / `--paper-deep` | クリーム #FFF6E6 / #F8E7C6 | 地 |
| `--ink` | 濃い紫 #2B2340 | 文字、枠線 |
| `--muted` | #6B6480 | 補足の文字、目盛り |
| `--cyan` / `--cyan-deep` / `--cyan-soft` | オレンジ #FF7A1A / #D4560A / #FFE0C4 | 主役、強調語（見出しの色付きの語は `-deep`） |
| `--coral` / `--coral-deep` / `--coral-soft` | ピンク #FF4F8B / #CF2E69 / #FFD7E6 | 注意、対比のもう一方 |
| `--yellow` / `--yellow-deep` / `--yellow-soft` | イエロー #FFC83D / #9A6B00 / #FFF0B3 | 補足のカード、コードの語の下地 |
| `--green` / `--green-deep` / `--green-soft` | ミント #22C29C / #0F8A6C / #CCF4E8 | 良い点、解決 |
| `--panel` / `--term` | 濃い紫 #2B2340 / #1F1930 | コード、ターミナル、まとめのキー |

- 変数の名前（`--cyan` など）は役割の名前。色の値はビタミンカラーで、`--cyan` はオレンジ、`--coral` はピンク、`--green` はミント。
- 文字: 日本語はヒラギノ角ゴ。見出し（`.h` `.display` `.statement`）は 900、カードやラベルは 700〜800。英数・コードは JetBrains Mono（同梱）。
- 大きさ: 見出し 68px（色帯つき 62px）、小見出し 34px、カードの本文 40〜52px、ラベル 28〜34px、注記 28px。**28px 未満は使わない。**
- 箱: 枠 4px の `--ink`、角丸 34px（コード・ターミナル 30px）、**ずらした色付きの影 10px 10px 0（ぼかしなし）**。影の色は箱の役割の色（`.card.cyan` はオレンジ、`.coral` はピンク、`.yellow` はイエロー、`.green` はミント、色なしと `.tile` はオレンジ）。コードとターミナルの影はピンク 12px。
- 番号（`.num`）はオレンジの丸に濃い紫の枠。
- 字幕の帯は濃い紫の丸い帯（角丸 999px）に、オレンジのずらした影。
- 色付きの語: 見出しの中の大事な語を `.c-cyan` / `.c-coral` で色付け。コードの語は `.kw`（イエローの下地）。

## 3. 部品の一覧

CSS の部品（kit.css）:

| クラス | 使い方 | 例 |
|---|---|---|
| `.h` / `.sub` / `.sub.muted` | 見出しと小見出し | `<h2 class="h">チャネル ＝ <span class="c-cyan">通り道</span></h2>` |
| `.title-bar.cyan` + `.kicker` | 色帯つきの見出し | `<div class="title-bar green"><div><div class="kicker">仕組み</div><div class="h">…</div></div></div>` |
| `.card`（`.cyan` `.yellow` `.coral` `.green` `.dark`、`.big` `.bold`） | 説明・結論・補足（影は役割の色） | `<div class="card yellow bold">一つが終わるまで、次は始まらない</div>` |
| `.tile`（`.label` `.value` `.sub-text`） | 数字を大きく | `<div class="tile"><div class="label">学習データ</div><div class="value">58万<small>時間</small></div></div>` |
| `.bubble` / `.chip` | 図の中のラベル、タグ | `<span class="bubble coral">注意</span>` |
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
| `.ps-label`（`.cyan` `.coral` `.green` `.yellow`） | 白抜きの丸いラベル（Q・A・NG・OK・次回） | `<span class="ps-label green">OK</span>` |
| `.ps-band`（`.cyan` `.green`） | 横長の帯（結論・次回の案内） | `<div class="ps-band"><span class="ps-label yellow">!</span>結論</div>` |
| `.ps-fill` / `.ps-grow` / `.ps-slot` | 画面を使い切る枠／のこりの高さを使う部分／動きを付ける外側の箱 | 4章 |
| `.ps-cover` `.ps-chapter` `.ps-choices` ほか `.ps-*` | 各シーンの型の組み立て | 4章 |

動く部品（kit.js。属性で設定し、時間に合わせて動く）:

| 部品 | 属性 | 使い方 |
|---|---|---|
| `.runner` | `data-color`（cyan/coral/yellow/green）`data-size` `data-hat`（コック帽）`data-sleepy`（寝ている）`data-still`（止まる）`data-seed` | 処理や人を表すキャラクター（色は役割の色）。上下に揺れて足が動く。位置は `Motion.scene` で動かす |
| `pre.code` | `data-title`（main.go など）`data-lang`（go js ts py sh rs html text）`data-size` `data-width` `data-reveal="文:行; 文:行"` `data-focus="文:行; 文:行"` | 文ごとに強調する行が移り、他の行が薄くなる |
| `.terminal` | `data-command` `data-at`（打ち始める文）`data-show`（枠を出す文。省略で最初から）、子の行に `data-at`、色は `.ok` `.warn` `.err` `.dim` | `$ go run main.go` を打ち、結果の行が出る |
| `.gantt` | `data-max` `data-ticks` `data-unit` `data-width` `data-label-width` `data-row-height`、行 `data-label`、棒 `.bar` に `data-start` `data-end` `data-color` `data-hatch` | 時間の帯（夕ごはんの例、ダウンロード）。棒は `data-anim="wipe"` で伸ばす |
| `.hbars` | `data-max` `data-width` `data-label-width`、行に `data-label` `data-value` `data-color` `data-hatch` `data-at` `data-delay`、行の中身が値の文字 | 横棒グラフ。文の開始で伸びる |
| `.gauge` | `data-label` `data-value` `data-max` `data-unit` `data-color` `data-at` `data-width` | メモリ使用量 |
| `.wave` | `data-bars` `data-color` `data-height` `data-width` `data-level` `data-seed` `data-still` | 声を表す揺れる波形 |
| `.tiles` | `data-count` `data-cols` `data-color` `data-fill`（埋め始める文）`data-fill-to` `data-width` | トークンの升目が埋まっていく |
| `.camera` | `data-shots="文:寄る先のセレクタ:倍率; 文:reset"` | 中の要素に寄る・引く（コードの1行、図の一部）。約0.8秒のばね |

## 4. シーンの型

default の構図（分かれる線と走者の表紙・時間の帯など）は使わない。勉強会・IT/AI 解説の動画と発表のために、次の21の型を使う（11〜21 は、伸びている IT・AI 系の解説動画の構成の型から学んだもの。出典は作成時の調べ。チャンネル固有の見た目は入れていない）。

**画面を使い切る決まり**：表紙と章扉以外は、見出しと構図を `.ps-fill` で包み、のこりの高さを使う部分に `.ps-grow` を付ける。`.ps-fill` は見出しの下から下の余白（通常は字幕の帯の上、PPTX専用は下の余白 100px）まで伸び、`.ps-grow` の中のカードはその高さいっぱいに伸びる。箱の高さを px で決めない（通常版と PPTX専用版で使える高さが違うため）。

| # | 型 | どんな話に | 構成 | 文ごとの出方 |
|---|---|---|---|---|
| 1 | 色ブロックの表紙 | 始まり | `data-chrome="none"`、`.ps-cover` の左に `.sub` と `.display`、右に縦長の `.ps-block`（オレンジ）とタグ | 題名が `pop`、色の箱が `right`、タグを `data-stagger` |
| 2 | 番号つきの章扉 | 話の区切り | `data-chrome="none"`、`.ps-chapter` の左に上から下までのオレンジの箱に白抜きの番号（`.ps-bignum`）、右に `.kicker`・`.h`・`.ps-chapter-lead` | 番号が `pop`、一言を `words` |
| 3 | クイズ | 問いかけ | `.ps-question`、`.ps-choices.ps-grow` に `.ps-slot` で包んだ `.ps-choice` を3つ（正解に `.correct`） | 選択肢を `pop`。答えの文を `.ps-choice` の `data-active` にすると、正解だけ太い枠と大きな影のミント、他は薄く |
| 4 | ことばの定義 | 新しい用語 | `.ps-define.ps-grow` の左に大きな `.card`（`.ps-term`・`.ps-yomi`・`.ps-meaning`）、右に `.ps-examples` | 用語 → 定義（`words`）→ 例 → 注意 |
| 5 | ビフォー・アフター | 変える前と後 | `.ps-ba.ps-grow` に左右の `.card` と `.ps-arrow`、下に `.ps-band` | 左 → 矢印と右（`pop`）→ 帯（`wipe`） |
| 6 | 手順を順に | やり方・流れ | `.ps-steps.ps-grow` の左に `.ps-step`、右の `.ps-detail` に段ごとの `.card` | 段に `data-active`（今の段だけ色、過ぎた段は ✓）、右は `data-until` で入れ替え |
| 7 | ライブコーディング | コードを書いて動かす | `.ps-live.ps-grow` の左に `pre.code`、右の `.ps-live-side` にやること・`.terminal`・`.ps-result` | `data-reveal`・`data-focus` で行が出る、最後にターミナルと結果 |
| 8 | NG と OK | よくある間違い | `.ps-ngok.ps-grow` の左に NG と OK の `.ps-ngok-row`、右に理由 | NG と `strike` → OK → 理由 |
| 9 | 大きな数字 | 驚きの数字 | 見出し、`.ps-number.ps-grow`、`.hbars`、`.ps-band` | 数字を `count` → 横棒と帯 |
| 10 | 持ち帰り3つ | まとめ | `.ps-takeaways.ps-grow` に `.card.ps-take` を3枚、下に `.ps-band.cyan` | 1枚ずつ `pop` → 次回の帯 |
| 11 | 先に結果を見せる | 冒頭のダイジェスト、謎を示して後で明かす | `.ps-first.ps-grow` に画面いっぱいの結果の `.card`、右下に `.ps-ask`（「どうやって？」） | 結果を `zoom`、コードを `type` → 「どうやって？」を `pop` |
| 12 | 思い込みを崩す | 冒頭のつかみ | `.ps-myth.ps-grow` に上下2枚のカード（思い込み／本当は） | 思い込み → 取り消し線（`strike`）→ 本当はを `pop` |
| 13 | この動画の約束 | 見ると何ができるか | `.ps-promise.ps-grow` の左に `.ps-block`（時間のタグ）、右に `.ps-check` を3行 | ✓ の行を1つずつ |
| 14 | 関数の解剖 | API・関数の使い方 | 見出し、`.ps-sig`（語を `.ps-tok`）、`.ps-parts.ps-grow` に説明のカード3枚 | 文ごとに語に色（`data-active`）と説明のカード |
| 15 | 構成図（データの流れ） | 仕組み・アーキテクチャ | `.ps-flow-row`（左から右へ `.ps-node` と `.ps-link`）、`.ps-flow-notes.ps-grow` に箱ごとの説明 | 箱と線（`wipe`）が順に出て、`.ps-dot` が線に沿って流れる（`follow`、通常版だけ） |
| 16 | ファイルの木 | プロジェクトの構成 | `.ps-tree.ps-grow` の左に `.ps-tree-row` の木、右の `.ps-detail` に説明 | 行に `data-active`、右は `data-until` で入れ替え |
| 17 | A と B の判定 | 道具・手法の比較 | `.ps-vs.ps-grow` に左右のカード（良い点・弱点）、`.ps-verdicts` に判定の帯2本 | A → B → 判定の帯 |
| 18 | ランキング | おすすめ・よく使うもの | `.ps-rank.ps-grow` に `.ps-podium`（左 `.r2`・中央 `.r1`・右 `.r3`） | 3位 → 2位 → 1位を `grow-y` |
| 19 | ニュース速報 | AI・技術のニュース | `.ps-news-head`（NEWS のラベルとタグ）、`.ps-headline`、`.ps-news-body.ps-grow` に要点3行と「何が変わる？」 | 見出し → 要点 → 何が変わる |
| 20 | 結論から話す（PREP） | 意見・おすすめ | `.ps-prep.ps-grow` に 2×2 のカード（結論・理由・例・だから。最後は `.final`） | 1枠ずつ `pop` |
| 21 | トラブルと直し方 | エラー・つまずき | `.ps-trouble.ps-grow` に `.ps-trouble-head` と `.ps-trouble-row`（症状 → 原因 → 直し方） | 1行ずつ左から右へ（`data-stagger`） |

- 動きを付ける要素（`data-anim`）と、`data-active` で見た目が変わる要素は分ける（実行系が `opacity`・`transform` を上書きするため。外側を `.ps-slot` にして動きを付け、内側に `data-active`）。
- PPTX で画像になる CSS（`transform` での拡大・回転、SVG の線）は構図の部品に使わない。線は `.ps-link` のような四角形で描く。
- PPTX専用のデッキ（`deck-pptx/`）では、同じ型を、動きを使わない完成した1枚で書く。
  - クイズ・ファイルの木・関数の解剖は、`is-active` を直に書いて「答えを出した後」の1枚にする。手順は、各段の行に説明を添えて、済んだ段に `is-done`、最後の段に `is-active` を付ける。
  - 入れ替えていた説明は `.ps-stack` で縦に並べる。取り消し線は `text-decoration: line-through`、数え上げは最後の数字にする。データの流れの点は置かない。
- 構図の部品（`.ps-*`）は `kit.css` の「テンプレートの飾り」にある。シーンの型を増やすときもここに足す。

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

**PPTX に書き出したとき**：出現（`up` `left` `scale` `pop` `fade` `wipe` `draw` など）と消える動き（`data-until`）は、PowerPoint のネイティブのアニメーション（フロートイン・ズーム・ワイプ・フェード）になる。強調の移動、`follow`の移動、カメラ、`Motion.scene`の独自の動きは、変わった範囲だけを絵として重ねる（見た目は同じだが、動きはフェードになる）。PPTX でも動かしたい要素は、できるだけ出現・消える動きで表す。シーンの途中で見出し（`.h`）ごと内容を差し替えると、PPTX ではそこからが別のスライドになる。

## 6. やらないこと

- 箇条書きだけのスライド、中央寄せのタイトル＋本文の定型、影がぼやけたカード、グラデーション、写真の背景。
- 絵文字のアイコン（✓ ! i は `.point` の丸、番号は `.num`）。
- 見出しを中央に置く（大きな数字・`.statement` 以外）。
- 原稿の文をそのまま画面に貼る（字幕と二重になる）。画面には図・キーワード・数字・コードを置く。
- 新しい色を足す。必要なら theme.css で変数を上書きして、意味（オレンジ＝主役、ピンク＝注意…）を保つ。
- 背景に模様を付ける。画面の隅に飾りの図形（星・丸など）を置く。
