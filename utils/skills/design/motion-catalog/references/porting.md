# 実装先ごとの移し方

詳細ページ（`animations/<id>.html`）から移すのは、時間・イージング・キーフレーム・順序（遅延）・きっかけです。

- 本体は `<style id="motion">`。値は `CatalogDetail.mount({...})` の `params`（初期値）と `spec`。JS が要る動きは `run`。
- `<template id="stage">` と `run` の中のデモ用の部分（カーソルを動かす `seq`・`move`、自動スクロールの `auto`、一定間隔の `setInterval`）は移さない。

## どの実装先でも同じこと

| 詳細ページ | 移し先 |
|---|---|
| `var(--key, 初期値)` | 決まった値か、プロジェクトのデザイントークン |
| `.is-open` などのクラスの付け外し | コンポーネントの状態（クラス・`data-state` 属性など） |
| `ac-<id>-` のクラス名・キーフレーム名 | プロジェクトの命名 |
| 動きを減らす設定の書き方 | 詳細ページの形をそのまま保つ（`no-preference` の中だけで動かす形も、`reduce` で別の動きに替える形も） |
| `run` の `requestAnimationFrame`・`IntersectionObserver`・タイマー | 片付け（cleanup）を必ず書く |

- 新しいライブラリは勝手に足さない。入っているものを使い、なければ CSS と Web Animations API（`element.animate()`）で書く。足したほうが良いときは、ユーザーに聞く。
- 対象の既存の動きと時間・イージングがずれるときは、既存に合わせるかをユーザーに確かめる。

## 素の HTML / CSS

ほぼそのまま。クラス名だけ置き換え、`run` は実際のイベント（`click`・`pointerdown`・`scroll` など）につなぐ。

## React

- **スタイル**：プロジェクトの書き方に合わせる。
  - グローバル CSS・CSS Modules：`@keyframes` と `transition` をそのまま書く。
  - Tailwind：短い transition は任意値クラス（`duration-[180ms] ease-[cubic-bezier(0.22,1,0.36,1)]`）。キーフレームは、v4 なら CSS の `@theme` に `--animate-*` と `@keyframes`、v3 なら `tailwind.config` の `theme.extend.keyframes`。動きを減らす設定は `motion-safe:` で付ける。
  - styled-components・Emotion：`keyframes` ヘルパー。
- **状態**：`className={open ? "is-open" : undefined}` か `data-state={open ? "open" : "closed"}`。
- **`run`**：要素は `useRef`、処理は `useEffect` に入れ、返り値で片付ける。Next.js の App Router では、フックを使う部品に `"use client"` を付ける。
- **退出**：CSS だけではアンマウント前に動かせない。Motion（`motion` / `framer-motion`）があれば `AnimatePresence`。なければ「閉じている途中」の状態を持ち、`animationend` で外す。
- **FLIP・レイアウトの変化**：Motion があれば `layout`。なければ `useLayoutEffect` で前後の位置を測って `element.animate()`。
- **スプリング**：Motion があれば `transition={{ type: "spring", stiffness, damping, mass }}`（値は `spec` から）。なければ `spec` の `cubic-bezier` か、CSS の `linear()` で近似する。
- **動きを減らす設定**：CSS のメディアクエリ。Motion なら `useReducedMotion()` か `<MotionConfig reducedMotion="user">`。

## Vue

- `<Transition name="x">` の `x-enter-from`・`x-enter-active`・`x-leave-to` などに、時間・イージング・キーフレームを当てる。一覧は `<TransitionGroup>` で、並べ替えは `x-move`（FLIP）。
- `run` は `onMounted` で始めて `onBeforeUnmount` で片付ける。要素は `ref`。

## Svelte

- 出入りは `in:` / `out:` に自作の transition（`{ duration, easing, css }` を返す関数）か CSS クラス。並べ替えは keyed each に `animate:flip`。
- `run` は `onMount` で始め、返り値で片付ける（Svelte 5 なら `$effect` でもよい）。

## ネイティブ（SwiftUI / Jetpack Compose / Flutter）

CSS は移さず、値だけを移す。

| 値 | SwiftUI | Compose | Flutter |
|---|---|---|---|
| 時間 ＋ `cubic-bezier(a,b,c,d)` | `.timingCurve(a, b, c, d, duration:)` | `tween(durationMillis, easing = CubicBezierEasing(a, b, c, d))` | `Duration` ＋ `Cubic(a, b, c, d)` |
| スプリング | `.interpolatingSpring(mass:stiffness:damping:)` | `spring(dampingRatio, stiffness)` | `SpringDescription(mass:, stiffness:, damping:)` |
| 動きを減らす設定 | `@Environment(\.accessibilityReduceMotion)` | 端末のアニメーション速度の設定に従う | `MediaQuery.of(context).disableAnimations` |
