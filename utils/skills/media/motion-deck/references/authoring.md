# シーンの書き方

## 目次

1. 構造
2. data-*属性（宣言的な動き）
3. アニメーション一覧
4. Motion.scene（フレームの関数）
5. Motion.component（部品を作る）
6. 発表モードでの動き
7. シーンの切り替え・章バー・字幕
8. やってはいけないこと

見た目（どの部品をどう並べるか）は[見た目の決まり](style.md)。ここは仕組みの説明。

## 1. 構造

```html
<main id="composition" data-chapter-bar>          <!-- 1920×1080 の書き出し範囲 -->
  <section data-scene="intro" data-chrome="none">   <!-- script.json の scenes[].id と同じ -->
    ...
  </section>
</main>
<script src="motion/boot.js"></script>  <!-- 読み込むのはこの1行だけ -->
```

- 読み込みは`motion/boot.js`の1行だけにする。boot.jsが決まった順に読み込んで起動する：CSSは`motion/motion.css`（実行系）→`motion/kit.css`（部品と色）→`theme.css`（このデッキの調整）、JSは`timeline.js`→`motion/motion.js`→`motion/kit.js`→`scenes.js`→`Motion.start()`。
- `<link>`や`<script src="motion/…">`を直接書かない。`Motion.start()`も書かない（`check`がエラーにする）。
- どうしても足すCSS・JSは属性で渡す：`<script src="motion/boot.js" data-css="extra.css" data-js="chart.js"></script>`（テーマの後・`scenes.js`の前に読む）。
- どれかが読めなければ起動せず、理由を画面に出す（`window.__motionBootError`）。
- `#composition`の属性: `data-chapter-bar`（上に章ごとの進捗。必須）、`data-subtitles="off"`（字幕を出さない）。
- シーンは`position:absolute; inset:0`で重なり、今のシーンだけ表示される。`padding`は安全領域（`--safe-top`112px・`--safe-bottom`178px・`--safe-x`100px）。
- 自由な位置に置く要素は`position:absolute`で、`var(--safe-*)`を基準にする。

## 2. data-*属性

| 属性 | 値 | 意味 |
|---|---|---|
| `data-at` | 文番号（0始まり、`-1`で最後）、文の`name`、`start`、`end` | その文が読まれ始めたら現れる。動きの指定がなければ`up` |
| `data-anim` | 下の一覧から、空白区切りで複数可（例: `"up type"`） | 動き方 |
| `data-delay` | フレーム数（30で1秒） | `data-at`からの遅れ |
| `data-dur` | フレーム数 | 補間系（draw・type・count・grow・wipe・highlight）の長さ。既定はその文の読み終わりまで（最短15） |
| `data-ease` | `out`（既定）`in` `in-out` `linear` `ease` | 補間系の緩急 |
| `data-damping` `data-mass` `data-stiffness` | 数値 | ばねの硬さ（既定は動きごと。小さい`damping`ほど弾む） |
| `data-until` | 文番号か名前 | その文が始まるまでに消える（約10フレーム） |
| `data-out` | `fade`（既定）`down` `up` `left` `right` `scale` | `data-until`での消え方 |
| `data-loop` | `float` `pulse` `spin` `wiggle` `bob`（空白区切りで複数可）、速さは`data-loop-speed` | 待機中もゆっくり動き続ける（浮く・脈打つ・回る）。PPTXと静止画では止まる |
| `data-follow` | SVGの線のセレクタ（例 `#p-main`）。`data-anim="follow"`と組む | 文のあいだに線に沿って進む。`data-anchor="bottom"`で足元を線に合わせる、`data-follow-rotate`で進む向きに回す。要素は`position:absolute`で、線のSVGと同じ箱の中に置く |
| `data-fit` | （値なし）、下限は`data-fit-min`（既定28） | 箱に収まるまで文字を小さくする（長さの読めない文字列に） |
| `data-stagger` | フレーム数（既定6） | 親に付けると、子を順に同じ動きで出す。親の`data-at`・`data-anim`を子が受け継ぐ |
| `data-active` | `"2"`（2から最後まで）、`"2..4"`（2から4の直前まで）、`"..3"` | 範囲内は`is-active`、過ぎたら`is-done`のクラス。強調・薄くする表現はCSSで書く |
| `data-to` `data-from` `data-format="plain"` | 数値 | `count`の終点・始点。小数の桁は`data-to`に合わせる。`plain`で桁区切りなし |

- 時刻の参照はシーン内で閉じる。別シーンの文は参照できない。
- 文を挿入・削除すると番号がずれる。後から触りそうな文は`script.json`で`"name"`を付け、名前で参照する。
- 出現前の要素は`visibility:hidden`で場所を取ったまま隠れる（レイアウトが跳ねない）。場所も空けたくない差し替えは、`data-until`と`position:absolute`の重ねで作る。
- 実行系は`opacity`・`transform`・`filter`・`clip-path`・`--p`をインラインで上書きする。自分で`transform`を付けたい要素は、内側に包んで別の要素にする（インラインの`style="transform:..."`だけは引き継ぐ）。
- 動いている要素には`--p`（0→1の進み）が入るので、CSSで`calc(var(--p) * ...)`として使える。

## 3. アニメーション一覧

ばね（出現。文の開始から約0.5秒で落ち着く）:

| 名前 | 動き | 向いているもの |
|---|---|---|
| `up` | 下から40px上がりながら出る（既定） | 見出し、本文、カード |
| `down` `left` `right` | 上・左・右から | 横に並ぶもの、補足の吹き出し |
| `fade` | 透明度だけ | 背景、控えめな注記 |
| `scale` | 0.82倍から | 図、アイコン |
| `pop` | 0.4倍から弾んで | 強調したい一語、結論、数字 |
| `zoom` | 1.14倍から縮んで | 全面の写真・大きな図 |
| `blur` | ぼかしから | 雰囲気のある見出し |

補間（文の長さに合わせて進む）:

| 名前 | 動き | 向いているもの |
|---|---|---|
| `draw` | SVGの線を描く（要素自身か、中の`path` `line` `polyline` `circle` `rect`など） | 矢印、グラフの線、手書き風の囲み |
| `type` | 文字を一文字ずつ出す（入れ子の`span`の色分けも保つ） | コード、検索語、入力の再現 |
| `count` | 数字を数え上げる | 実績、比較の数値 |
| `grow` / `grow-y` | 横（左から）・縦（下から）に伸びる | 横棒・縦棒グラフ、進捗 |
| `wipe` / `wipe-down` | 左から・上から見えてくる | 表、帯、タイムライン |
| `highlight` | 蛍光ペンを左から引く（色は`--highlight`） | 文中の語句 |
| `strike` | 取り消し線を左から引く | 「time.Sleep(？秒)」のような否定 |
| `progress` | 幅が0→100% | 進捗バーの中身 |
| `words` | 語ごとに少し上がりながら順に出る（日本語は語の区切りで） | 結論の一文、標語 |
| `follow` | `data-follow`の線に沿って進む | 走者、矢印の先、データの流れ |

組み合わせ例: `data-anim="up type"`（上がりながら打つ）、`data-anim="fade grow-y"`。

## 4. Motion.scene（フレームの関数）

宣言で書けない動き（経路に沿った移動、複数要素の連動、物理的な表現）は`scenes.js`に書く。

```js
Motion.scene("compare", (s) => {
  // 準備（一度だけ）: 要素を探す、SVGを組み立てる
  const bar = s.$("#bar-go");
  const dots = s.$$(".dot");
  return (frame) => {
    // 毎フレーム: frame と s.* だけから見た目を決める（状態を溜めない）
    const p = s.progress("measure");                       // 文 measure の開始→終了で 0→1
    bar.style.transform = `scaleX(${p})`;
    dots.forEach((d, i) => {
      const a = s.appear(2, { delay: i * 4 });             // 文2から4フレームずつ遅れて 0→1（ばね）
      d.style.opacity = a;
      d.style.transform = `translateY(${s.interpolate(a, [0, 1], [30, 0])}px)`;
    });
  };
});
```

`s`（シーンの文脈）:

| 名前 | 返り値 |
|---|---|
| `s.frame` | シーン先頭からのフレーム（再生中は小数） |
| `s.fps` `s.duration` `s.cues` | フレームレート、シーンの長さ、文の一覧（`{text, name, start, end}`） |
| `s.$(sel)` `s.$$(sel)` | シーン内の要素 |
| `s.cue(ref)` | 文の`{start, end, text}` |
| `s.since(ref, delay?)` | 文の開始からの経過フレーム（前は負） |
| `s.reached(ref, delay?)` | 開始したか |
| `s.appear(ref, {delay, damping, mass, stiffness}?)` | 開始で0→1へ動くばね |
| `s.progress(from, to?, {easing}?)` | 文`from`の開始から文`to`の終わりまでの0→1 |
| `s.active()` | 今の文番号（前は-1） |
| `s.between(from, to)` | `from`の開始から`to`の開始の直前までtrue |
| `s.phase(from, to, fadeIn?, fadeOut?)` | `between`をフェード付きの不透明度で |
| `s.interpolate` `s.spring` `s.Easing` `s.clamp` | 下の関数と同じ |

グローバル関数（Remotionと同じ形）:

- `Motion.interpolate(x, [入力...], [出力...], {easing, extrapolateLeft, extrapolateRight})` — 既定は両端`clamp`（Remotionの既定と違う）。`'extend'`・`'identity'`も可。
- `Motion.spring({frame, fps, from, to, delay, durationInFrames, reverse, config: {damping, mass, stiffness, overshootClamping}})` — 解析解なので小数のフレームでも滑らか。`durationInFrames`でその長さに伸び縮み、`reverse`で逆再生。
- `Motion.measureSpring({fps, config, threshold})` — ばねが落ち着くまでのフレーム数。
- `Motion.interpolateColors(x, [入力...], ['#rrggbb' か 'rgb()' ...])` — 色の補間（CSSの変数は不可）。
- `Motion.random(seed)` — 種から決まる0〜1。`Math.random()`の代わり（毎回同じ値になる）。
- `Motion.noise(x, y, seed)` — なめらかなノイズ（-1〜1）。揺らぎや手書き風の線に。
- `Motion.env` — `{ render, static }`。`static`はPPTX・静止画の書き出しで、待機中の揺れを止めたいとき true。
- `Motion.Easing` — `linear` `quad` `cubic` `sin` `circle` `exp` `back(s)` `elastic(b)` `bezier(x1,y1,x2,y2)` `ease`と、`in(e)` `out(e)` `inOut(e)`。

規則:

- 準備の関数で`Date.now()`、タイマー、イベントで状態を変えない。乱数が要るなら`(i * 9301 + 49297) % 233280 / 233280`のように番号から作る。
- 更新の関数は毎フレーム呼ばれる。重い処理（DOMの作り直し、`innerHTML`の書き換え）は避け、`style`と属性の更新にとどめる。
- 他のシーンの要素に触らない。

## 5. Motion.component（部品を作る）

`kit.js`の部品はこの仕組みで作られている。同じ見た目を何度も使うなら、デッキの`scenes.js`で部品を足せる。

```js
Motion.component(".badge-live", (el, s) => {
  // 準備：全シーンの該当要素ごとに一度。子の要素を組み立ててよい（data-* も付けられる）
  el.innerHTML = '<i class="dot"></i>' + el.innerHTML;
  const dot = el.querySelector(".dot");
  return {
    // 毎フレーム（その要素のシーンが表示されている間）
    update(frame) { dot.style.opacity = Math.floor(frame / 15) % 2 ? 0.3 : 1; },
    // 発表モードで、ある文の動きに何フレーム要るか（打ち込みなど長い動きのとき）
    needs: [{ at: el.dataset.at || "start", frames: 30 }],
  };
});
```

- 部品の準備は宣言的アニメーションの解析より先に走る。部品が作った子要素の`data-at`なども効く。
- 返り値は関数（update だけ）か`{ update, needs }`。何も返さなければ配置だけの部品。
- `s`は`Motion.scene`と同じシーンの文脈。

## 6. 発表モードでの動き

発表モード（`?mode=live`、`P`）では、実行系が同じ文を「1クリック＝1ステップ」に並べ直す。

- 各文の動きは既定で30フレーム（1秒）に縮む。`data-delay`・`data-stagger`・`data-dur`・部品の`needs`を見て、必要なら自動で延ばす。
- 補間系（`draw` `type` `count` `wipe` `grow`）の既定の長さは「文の長さ」なので、発表では縮んだ長さで終わる。`s.progress()`も同じ。
- 文を読み終えた位置で止まり、次のクリックで続きを動かす。シーンの最初の文は、前のシーンからの切り替えに続けて自動で動く。
- 原稿の文に`"auto": true`を付けると、その文は前のステップに続けてクリックなしで動く。`"build": 2.5`でその文の動きの長さ（秒）を指定できる。
- ステップの長さは`#composition`の`data-live-step`（フレーム）で変えられる。
- ナレーションをオンにする（`V`）と、各ステップは文の読み上げの長さまで延び、動きは動画と同じく読み上げに合わせて進む。
- 字幕は既定で消える（話すのは本人なので）。`C`で出せる。
- 秒数で書いた動き（`data-delay="90"`など）は発表では間延びする。動きは文に結び付け、遅れは短く（30フレーム以内）にする。

## 7. シーンの切り替え・章バー・字幕

シーンの切り替えは**重なる切り替え**。新しいシーンが入ってくる間、前のシーンは最後の絵のまま下に残る（Remotion の TransitionSeries と同じ見え方）。

| `data-transition` | 動き | PPTXでは |
|---|---|---|
| `fade`（既定） | 重ねてフェード | フェード |
| `slide` | 押し出す（前のシーンが反対側へ出ていく） | プッシュ |
| `wipe` | 拭き取るように現れる | ワイプ |
| `zoom` | 少し大きいところから縮みながら現れる | ズーム |
| `iris` | 中央から円が広がる | 円 |
| `clock` | 時計回りに現れる | ホイール |
| `flip` | 裏返る | フェード |
| `none` | すぐ切り替わる | なし |

- 向きは`data-direction`（`left`＝右から入ってくる（既定）、`right`、`up`、`down`）。長さは`data-enter`（既定18フレーム）、緩急は`data-timing="spring"`で減衰の強いばね（既定は加減速）。
- 使い分け：同じ章の中は`fade`、章が変わるところで`slide`、まとめ・結論は`iris`か`zoom`。1つのデッキで使う種類は2〜3に絞る。
- 章バーは`script.json`の`chapter`が同じ連続するシーンを1つの章にまとめる。色は`--accent`、トラックは`--track`。
- 字幕は今の文を下に出す。色は`--sub-bg`・`--sub-ink`。プレイヤーの`C`で切り替え、書き出しでは`--subtitles 0`で消せる。
- `data-chrome="none"`のシーンは章バーを隠す（字幕は出る）。

## 8. やってはいけないこと

- CSSの`transition`・`animation`・`@keyframes`（書き出しで再現されない。`check`が警告する）。
- `<video>`の自動再生、GIFアニメ（時刻と同期しない）。動く素材が要るなら連番画像を`Motion.scene`で切り替える。
- 外部のCDNやWebフォントに頼った見た目（オフラインや書き出しで崩れる）。画像はデッキのフォルダに置く（`bundle`が埋め込む）。
- 原稿の文をそのまま画面に貼ること（字幕と二重になる）。
