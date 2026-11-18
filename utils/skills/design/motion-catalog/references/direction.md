# おまかせのときの決め方

指示が曖昧なとき（「良い感じに」「全体的に」「この画面に動きを」）に、対象に合った動きを根拠をもって決めるための物差しです。

材料 → 性格 → 動きの言語 → 場面ごとの選択、の順に決めます。材料から決めるので、プロジェクトが違えば違う答えになり、同じプロジェクトの中では統一されます。偶然では選びません。

## 1. 材料を集める（読むのは少しだけ）

- **何のプロダクトか・誰が使うか**：README、`package.json` の `name`・`description`、トップページの文言。
- **見た目の手がかり**：色（彩度・コントラスト）、角丸の大きさ、書体と太さ、余白の量、言葉づかい（丁寧／くだけた）。
- **今ある動き**：`transition`・`animation`・`@keyframes`・アニメーションライブラリの使用箇所を grep する。あれば、その時間・イージングにそろえる（統一がいちばん優先）。
- **技術**：フレームワーク、スタイルの書き方、入っているアニメーションライブラリ。
- **範囲**：指定された要素か、画面か、全体か。

材料が足りないときは、読める範囲から推測し、推測したことを計画に書く（聞く前に推測する）。

## 2. 性格を決める

主の性格を 1 つ決める。副を足すなら 1 つまでで、副は「決め手の動き」にだけ使う。

| 性格 | 材料の例 | 時間（部品／パネル・画面） | イージングの系統 | 行き過ぎ | ずらし | 決め手の候補 |
|---|---|---|---|---|---|---|
| 落ち着き | 医療・金融・業務、低い彩度、細い文字 | 150–200ms／250–350ms | ease-out | なし | 30–40ms | `fade-through` `shared-axis` `sibling-defocus` |
| 精密 | 開発者向け・ダッシュボード、等幅の数字 | 120–180ms／200–260ms | ease-out、進捗は linear | なし | 20–30ms | `sliding-active-indicator` `number-ticker` `layout-animation` |
| 親しみ | 一般向けアプリ、大きな角丸、明るい色 | 180–250ms／300–400ms | 弱いスプリング | 少し | 40–50ms | `spring` `pop-in` `save-confirm` |
| 遊び | 子ども・ゲーム・SNS、イラスト | 200–300ms／350–500ms | スプリング、back | はっきり | 50–60ms | `jello` `like-heart-burst` `squash-stretch` |
| 高級 | ブランド・ファッション、大きな写真、セリフ体 | 300–500ms／600–1000ms | ease-in-out でゆっくり | なし | 60–100ms | `reveal` `split-text` `ken-burns` `scroll-text-reveal` |
| 力強さ | スポーツ・イベント・LP、太い文字 | 150–250ms／300–500ms | 速く入る ease-out | 少し | 30–40ms | `kinetic-typography` `slit-transition` `scroll-to-full-bleed` |

## 3. 動きの言語を決める

計画の最初に書き出し、すべての場面で使い回す。

- **時間とずらし**：小・中・大の 3 段とずらしの間隔（上の表から）。小は部品の中の変化（下線・トグル・ホバー）、中は要素の登場や開閉、大はパネルや画面全体。退出は登場の 7 割ほどに短くする。ここで決めた値は、各 id の「値の変更」として使う（その id の `params` の最小〜最大の範囲で。範囲の外になるなら範囲の端にする）。
- **イージング**：決めるのは「行き過ぎを使うか」だけ。曲線そのものは各詳細ページの `spec` に従い、`spec` が複数を許すとき（「spring か out」など）は性格の系統に合うほうを選ぶ。行き過ぎ「なし」の性格では、スプリングと back を選ばない。
- **空間の決まり**：出てきた所へ戻る、「次」は右か下から、上に重なるものは拡大と影で手前に出す（`spatial-consistency`）。
- **決め手の動き**：そのプロダクトらしさを担う動きを 1 つ。目立つ場面 1 か所だけに使う（完了の瞬間、ヒーロー、主要ボタンなど）。範囲が 1 つの要素だけのときは、決め手を別に選ばず、その要素の動きを性格に合わせるだけにする。
- **予算**：1 画面で同時に目立つ動きは 1 つ。常に動き続けるものは 1 つまで（5 秒を超えるなら止めるボタンを付ける）。

## 4. 場面ごとに選ぶ

| 場面 | 第一候補 | 性格で変える候補 |
|---|---|---|
| 最初の表示（ページ・セクション） | 1 つなら `fade-in-out`、並んだものは `stagger`（透明度の変化も含む） | 高級 `reveal` `split-text`／遊び `pop-in`／力強さ `kinetic-typography` |
| スクロールで入る要素 | `scroll-reveal` | 高級 `scroll-text-reveal` `parallax`／精密は動かさない |
| ホバー（クリックできるものだけ） | `hover-effect` | 親しみ `magnetic-button`／高級 `animated-underline` `glare-sweep`／精密は色だけ |
| 押す | `press-feedback` | 遊び `jello`／Material 系 `ripple` |
| 切り替え（トグル・タブ・選択） | `toggle-switch` `sliding-active-indicator` `segmented-control` | `radio-selection-motion` |
| 開閉（メニュー・アコーディオン） | `accordion` `dropdown-transition` | `container-transform` |
| モーダル・シート | `dialog` `bottom-sheet` | `sibling-defocus` |
| 一覧の追加・削除・並べ替え | `enter-exit` `layout-animation` | `drag-to-reorder` `flip-technique` |
| 画面の移動 | `shared-axis` `fade-through` | `shared-element` `view-transition` `container-transform` |
| 読み込み（時間が分からない） | 形が分かるなら `skeleton-shimmer`、分からないなら `three-dot-loader` | `indeterminate-progress` |
| 読み込み（進み具合が分かる） | `determinate-progress` | `circular-progress` |
| 画像の読み込み | `image-blur-up` | |
| 成功・完了 | `save-confirm` `button-loading-success` | 遊び `confetti`（まれな達成だけ） |
| エラー・入力の間違い | `shake`（小さく） | `flash` |
| 通知 | `toast` | `notification-stack` |
| 数字の変化 | `number-ticker` ＋ `tabular-numbers` | `odometer` |
| 文字の強調 | `animated-text-highlight` | `cycling-words` `text-shine` |
| グラフ | `animated-chart` | `axis-rescale-transition` `chart-type-morph` |
| ヘッダー・ナビ | 動かさない | `hide-on-scroll-header` `shrinking-navbar` |
| 背景 | 付けない | 高級 `gradient-flow` `aurora-background`／力強さ `background-beams` |

表の（）の条件（クリックできるものだけ、など）は、計画を作るときに対象のコードで確かめる。表にない場面は `index.tsv` の `use` 列から探す。候補で迷うときだけ、その詳細ページを読んで比べてよい。

## 5. 迷ったときの判断軸

1. **目的**：何を伝える動きか言えないなら入れない（`purposeful-animation`）。
2. **頻度**：1 日に何十回も起きる操作ほど短く控えめにするか、動かさない（`frequency-of-use`）。初回だけの表示やまれな達成は演出してよい。
3. **重要度**：目立たせるのは、その画面でいちばん大事な 1 つだけ（`staging`）。
4. **距離と大きさ**：動く距離・面積が大きいほど長くする。部品は 100–200ms、パネルは 250–400ms、画面全体は 300–500ms。
5. **待たせない**：操作を止める動きは作らず、途中で割り込めるようにする（`interruptible`）。待ち時間は動きで短く感じさせる（`perceived-performance`）。
6. **快適さ**：大きな移動・視差・回転は控えめにする（`motion-comfort`）。動きを減らす設定には必ず対応する。

## 6. 毎回同じにしない（でも偶然には頼らない）

- 「全部 300ms の fade-in」のような定番に逃げない。性格と場面の表から、材料に基づいて選ぶ。
- 決め手の動きは、プロダクトの題材から連想して選ぶ。例：料理→湯気のような `float`・`breathing`、お金→`odometer`、写真→`ken-burns`、読み物→`split-text`、旅行→`parallax`。連想の理由を計画に 1 行書く。
- 1 つのプロダクトの中では、決めた言語を全部の場面に使い回す。

## 7. 計画の形

実装の前に、次の形で示して確認を取る（「確認なしで進めて」と言われているときは、示してそのまま進める）。ファイル名は見込みでよい。

```
性格: 親しみ（根拠: 角丸 16px・明るい水色・くだけた文言）
動きの言語: 小 180ms / 中 300ms / 大 400ms、退出 130ms、ずらし 40ms、行き過ぎ 少し
決め手: 記録が終わった瞬間に save-confirm（チェックを描く）… 家計簿の「記録できた」安心感
場面:
- 一覧の最初の表示 → stagger（ずらし 40ms）… src/components/List.tsx
- ボタン → press-feedback … src/components/Button.tsx
付けない所: ヘッダー（毎回使うため）
```

決めたら、選んだ id の `animations/<id>.html` だけを読んで実装する。
