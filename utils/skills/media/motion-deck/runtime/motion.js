/*!
 * motion.js — Remotion の考え方を借りた、時間駆動の HTML プレゼンテーション実行系。
 *
 *  - 画面は「フレーム番号の関数」。再生・シーク・書き出しのどこで止めても同じ絵になる。
 *  - ナレーションの文（cue）が時間の目盛り。要素は「何番目の文で出るか」で書く。
 *  - 依存なし。classic script なので file:// でもそのまま開ける。
 *
 * 公開API: window.Motion = { start, scene, interpolate, spring, Easing, clamp }
 * 書き出し用: ?render=1 で開くと window.__motion にシーク関数が生える。
 */
(function (global) {
  'use strict';

  // ───────────────────────── 数学（Remotion と同じ考え方） ─────────────────────────

  const clamp = (v, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v));

  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = (t) => ((ax * t + bx) * t + cx) * t;
    const sy = (t) => ((ay * t + by) * t + cy) * t;
    const dx = (t) => (3 * ax * t + 2 * bx) * t + cx;
    return (x) => {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      let t = x;
      for (let i = 0; i < 8; i++) {
        const err = sx(t) - x;
        if (Math.abs(err) < 1e-6) return sy(t);
        const d = dx(t);
        if (Math.abs(d) < 1e-6) break;
        t -= err / d;
      }
      let lo = 0, hi = 1;
      t = x;
      for (let i = 0; i < 40; i++) {
        const v = sx(t);
        if (Math.abs(v - x) < 1e-6) break;
        if (v < x) lo = t; else hi = t;
        t = (lo + hi) / 2;
      }
      return sy(t);
    };
  }

  const Easing = {
    linear: (t) => t,
    quad: (t) => t * t,
    cubic: (t) => t * t * t,
    sin: (t) => 1 - Math.cos((t * Math.PI) / 2),
    circle: (t) => 1 - Math.sqrt(1 - t * t),
    exp: (t) => (t === 0 ? 0 : Math.pow(2, 10 * (t - 1))),
    back: (s = 1.70158) => (t) => t * t * ((s + 1) * t - s),
    elastic: (b = 1) => (t) => 1 - Math.pow(Math.cos((t * Math.PI) / 2), 3) * Math.cos(t * b * Math.PI),
    bezier,
    in: (e) => e,
    out: (e) => (t) => 1 - e(1 - t),
    inOut: (e) => (t) => (t < 0.5 ? e(t * 2) / 2 : 1 - e((1 - t) * 2) / 2),
  };
  Easing.ease = bezier(0.25, 0.1, 0.25, 1);

  /** interpolate(x, [0, 30], [0, 1], { easing, extrapolateLeft, extrapolateRight })
   *  既定は両端 clamp（Remotion の既定 extend と違う点に注意）。 */
  function interpolate(input, inputRange, outputRange, options) {
    const o = options || {};
    const easing = o.easing || Easing.linear;
    const left = o.extrapolateLeft || 'clamp';
    const right = o.extrapolateRight || 'clamp';
    if (!Array.isArray(inputRange) || inputRange.length < 2 || inputRange.length !== outputRange.length) {
      throw new Error('interpolate: inputRange と outputRange は同じ長さ（2以上）にしてください');
    }
    for (let k = 1; k < inputRange.length; k++) {
      if (!(inputRange[k] >= inputRange[k - 1])) throw new Error('interpolate: inputRange は昇順にしてください: ' + inputRange.join(', '));
    }
    let i = 1;
    while (i < inputRange.length - 1 && input > inputRange[i]) i++;
    const x0 = inputRange[i - 1], x1 = inputRange[i];
    const y0 = outputRange[i - 1], y1 = outputRange[i];
    let t = x1 === x0 ? (input < x0 ? 0 : 1) : (input - x0) / (x1 - x0);
    if (t < 0) {
      if (left === 'clamp') t = 0;
      else if (left === 'identity') return input;
    }
    if (t > 1) {
      if (right === 'clamp') t = 1;
      else if (right === 'identity') return input;
    }
    return y0 + easing(t) * (y1 - y0);
  }

  /** 減衰振動の解析解（0→1）。t は秒 */
  function springCurve(t, c) {
    const mass = c.mass != null ? c.mass : 1;
    const damping = c.damping != null ? c.damping : 10;
    const stiffness = c.stiffness != null ? c.stiffness : 100;
    const w0 = Math.sqrt(stiffness / mass);
    const zeta = damping / (2 * Math.sqrt(stiffness * mass));
    if (t <= 0) return 0;
    if (zeta < 1) {
      const wd = w0 * Math.sqrt(1 - zeta * zeta);
      return 1 - Math.exp(-zeta * w0 * t) * (Math.cos(wd * t) + ((zeta * w0) / wd) * Math.sin(wd * t));
    }
    if (zeta === 1) return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
    const r = Math.sqrt(zeta * zeta - 1);
    const r1 = -w0 * (zeta - r), r2 = -w0 * (zeta + r);
    return 1 + (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r1 - r2);
  }

  /** ばねが落ち着くまでのフレーム数（|1-x| が threshold 未満のまま続く最初のフレーム） */
  function measureSpring(opts) {
    const o = opts || {};
    const fps = o.fps || 30;
    const c = o.config || {};
    const th = o.threshold != null ? o.threshold : 0.005;
    let settled = 0;
    for (let f = 0; f < fps * 60; f++) {
      if (Math.abs(1 - springCurve(f / fps, c)) < th) { if (!settled) settled = f; }
      else settled = 0;
      if (settled && f - settled > fps / 2) return settled;
    }
    return fps * 60;
  }

  /** spring({ frame, fps, from, to, delay, durationInFrames, reverse, config:{ damping, mass, stiffness, overshootClamping } })
   *  frame は小数でもよい（再生中は 60Hz で滑らかに動く）。durationInFrames を付けると、その長さで落ち着くように伸び縮みする。 */
  function spring(opts) {
    const o = opts || {};
    const fps = o.fps || 30;
    const c = o.config || {};
    let frame = Math.max(0, (o.frame || 0) - (o.delay || 0));
    if (o.durationInFrames) {
      const natural = measureSpring({ fps, config: c });
      frame = (frame * natural) / o.durationInFrames;
      if (o.reverse) frame = Math.max(0, natural - frame);
    } else if (o.reverse) {
      frame = Math.max(0, measureSpring({ fps, config: c }) - frame);
    }
    let x = springCurve(frame / fps, c);
    if (c.overshootClamping) x = clamp(x, 0, 1);
    const from = o.from != null ? o.from : 0;
    const to = o.to != null ? o.to : 1;
    return from + (to - from) * x;
  }

  /** 色の補間。#rgb #rrggbb rgb() rgba() を受け付ける（CSS の変数は不可） */
  function parseColor(c) {
    const s = String(c).trim();
    let m = /^#([0-9a-f]{3,8})$/i.exec(s);
    if (m) {
      let h = m[1];
      if (h.length <= 4) h = h.split('').map((x) => x + x).join('');
      const n = parseInt(h.slice(0, 6), 16);
      return [(n >> 16) & 255, (n >> 8) & 255, n & 255, h.length === 8 ? parseInt(h.slice(6), 16) / 255 : 1];
    }
    m = /^rgba?\(([^)]+)\)$/i.exec(s);
    if (m) { const v = m[1].split(/[\s,/]+/).filter(Boolean).map(Number); return [v[0], v[1], v[2], v[3] != null ? v[3] : 1]; }
    throw new Error(`interpolateColors: 色「${c}」を解釈できません（#rrggbb か rgb() で）`);
  }
  function interpolateColors(input, inputRange, colors, options) {
    const cs = colors.map(parseColor);
    const ch = [0, 1, 2, 3].map((k) => interpolate(input, inputRange, cs.map((x) => x[k]), options));
    return `rgba(${Math.round(ch[0])}, ${Math.round(ch[1])}, ${Math.round(ch[2])}, ${+ch[3].toFixed(3)})`;
  }

  /** 種から決まる乱数（0〜1）。同じ種なら必ず同じ値。Math.random の代わりに使う */
  function random(seed) {
    let h = 2166136261;
    const str = String(seed);
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    h += 0x6d2b79f5;
    let t = h;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /** なめらかなノイズ（-1〜1）。noise(x, y?, seed?) */
  function noise(x, y, seed) {
    y = y || 0;
    const sd = seed == null ? 0 : seed;
    const xi = Math.floor(x), yi = Math.floor(y);
    const fx = x - xi, fy = y - yi;
    const sm = (t) => t * t * (3 - 2 * t);
    const v = (i, j) => random(`${sd}:${i}:${j}`) * 2 - 1;
    const a = v(xi, yi), b = v(xi + 1, yi), c = v(xi, yi + 1), d = v(xi + 1, yi + 1);
    const u = sm(fx), w = sm(fy);
    return a + (b - a) * u + (c - a) * w + (a - b - c + d) * u * w;
  }

  // ───────────────────────── 宣言的アニメーション（data-*） ─────────────────────────

  const SPRING_ANIMS = {
    up: (p) => ({ t: `translateY(${(1 - p) * 40}px)`, o: p }),
    down: (p) => ({ t: `translateY(${(p - 1) * 40}px)`, o: p }),
    left: (p) => ({ t: `translateX(${(p - 1) * 48}px)`, o: p }),
    right: (p) => ({ t: `translateX(${(1 - p) * 48}px)`, o: p }),
    scale: (p) => ({ t: `scale(${0.82 + 0.18 * p})`, o: p }),
    zoom: (p) => ({ t: `scale(${1.14 - 0.14 * p})`, o: p }),
    pop: (p) => ({ t: `scale(${0.4 + 0.6 * p})`, o: p }),
    fade: (p) => ({ o: p }),
    blur: (p) => ({ f: `blur(${Math.max(0, (1 - p) * 14)}px)`, o: p }),
  };
  const TWEEN_ANIMS = new Set(['draw', 'type', 'count', 'grow', 'grow-y', 'wipe', 'wipe-down', 'highlight', 'progress', 'strike', 'words', 'follow']);
  // 待機中の動き（data-loop）。frame はシーン内のフレーム
  const LOOPS = {
    float: (f, k) => `translateY(${Math.sin(f / (12 / k)) * 6}px)`,
    pulse: (f, k) => `scale(${1 + Math.sin(f / (8 / k)) * 0.035})`,
    spin: (f, k) => `rotate(${(f * 3 * k) % 360}deg)`,
    wiggle: (f, k) => `rotate(${Math.sin(f / (4 / k)) * 3}deg)`,
    bob: (f, k) => `translateY(${Math.sin(f / (3.2 / k)) * 5}px)`,
  };
  // 消え方（data-until と組む data-out）。q は 1→0
  const OUTS = {
    fade: () => '',
    down: (q) => `translateY(${(1 - q) * 40}px)`,
    up: (q) => `translateY(${(q - 1) * 40}px)`,
    left: (q) => `translateX(${(q - 1) * 48}px)`,
    right: (q) => `translateX(${(1 - q) * 48}px)`,
    scale: (q) => `scale(${0.85 + 0.15 * q})`,
  };
  const SPRING_PRESETS = {
    up: { damping: 18, mass: 0.7 }, down: { damping: 18, mass: 0.7 }, left: { damping: 18, mass: 0.7 },
    right: { damping: 18, mass: 0.7 }, scale: { damping: 16, mass: 0.7 }, zoom: { damping: 20, mass: 0.8 },
    pop: { damping: 9, mass: 0.6, stiffness: 140 }, fade: { damping: 22, mass: 0.8 }, blur: { damping: 20, mass: 0.8 },
  };
  const EASE_BY_NAME = {
    linear: Easing.linear, in: Easing.in(Easing.cubic), out: Easing.out(Easing.cubic),
    'in-out': Easing.inOut(Easing.cubic), inout: Easing.inOut(Easing.cubic), ease: Easing.ease,
  };

  // ───────────────────────── 状態 ─────────────────────────

  const params = new URLSearchParams(location.search);
  const RENDER = params.has('render');
  // static: 待機中の揺れ（走者・波形・カーソル）を止め、章バーをシーンの頭で固定する（PPTX の書き出し用）
  const STATIC = params.has('static');
  const NO_TRANSITION = params.has('notransition');
  const sceneSetups = new Map();
  const components = [];
  const errors = [];
  const state = {
    tl: null,
    fps: 30,
    width: 1920,
    height: 1080,
    total: 1,
    frame: 0,
    playing: false,
    rate: 1,
    mode: null,
    stops: [],
    stopAt: null,
    subtitlesLive: false,
    subtitles: true,
    muted: false,
    scenes: [],
    current: null,
    audio: null,
    lastAudioT: -1,
    lastWall: 0,
  };

  function report(message) {
    if (!errors.includes(message)) errors.push(message);
    console.error('[motion] ' + message);
    if (state.ui) showErrors();
  }

  // ───────────────────────── シーンの文脈（Motion.scene に渡る s） ─────────────────────────

  function makeContext(rec) {
    const ctx = {
      id: rec.tl.id,
      el: rec.el,
      fps: state.fps,
      get duration() { return rec.tl.duration; },
      get cues() { return rec.tl.cues; },
      get frame() { return rec.f; },
      get globalFrame() { return state.frame; },
      $: (sel) => rec.el.querySelector(sel),
      $$: (sel) => Array.from(rec.el.querySelectorAll(sel)),
      interpolate, interpolateColors, spring, measureSpring, Easing, clamp, random, noise,
      /** 文の参照（番号・名前・'start'・'end'）を {start,end,text} にする */
      cue(ref) { return resolveCue(rec, ref); },
      /** 文 ref が始まってからの経過フレーム（前は負） */
      since(ref, delay) { return rec.f - resolveCue(rec, ref).start - (delay || 0); },
      reached(ref, delay) { return ctx.since(ref, delay) >= 0; },
      /** 文 ref の開始で 0→1 へ動くばね */
      appear(ref, opts) {
        const o = opts || {};
        const since = ctx.since(ref, o.delay || 0);
        if (since < 0) return 0;
        return spring({ frame: since, fps: state.fps, config: o.config || { damping: o.damping || 18, mass: o.mass || 0.7, stiffness: o.stiffness || 100 } });
      },
      /** 文 from の開始から文 to の終わりまでの 0→1 */
      progress(from, to, opts) {
        const a = resolveCue(rec, from);
        const b = resolveCue(rec, to == null ? from : to);
        const end = Math.max(b.end, a.start + 1);
        return interpolate(rec.f, [a.start, end], [0, 1], { easing: (opts && opts.easing) || Easing.linear });
      },
      /** 今読んでいる文の番号（読み始める前は -1） */
      active() {
        let idx = -1;
        rec.tl.cues.forEach((c, i) => { if (rec.f >= c.start) idx = i; });
        return idx;
      },
      /** from の開始から to の開始の直前まで true */
      between(from, to) {
        const a = from == null ? -Infinity : resolveCue(rec, from).start;
        const b = to == null ? Infinity : resolveCue(rec, to).start;
        return rec.f >= a && rec.f < b;
      },
      /** between をフェード付きの不透明度で返す */
      phase(from, to, fadeIn, fadeOut) {
        const a = from == null ? -Infinity : resolveCue(rec, from).start;
        const b = to == null ? Infinity : resolveCue(rec, to).start;
        const fi = from == null ? 1 : clamp((rec.f - a) / (fadeIn || 12));
        const fo = to == null ? 1 : clamp((b - rec.f) / (fadeOut || 10));
        return Math.min(fi, fo);
      },
    };
    return ctx;
  }

  function resolveCue(rec, ref) {
    const sc = rec.tl;
    if (ref === 'start' || ref == null) return { start: 0, end: 0, text: '' };
    if (ref === 'end') return { start: sc.duration, end: sc.duration, text: '' };
    if (typeof ref === 'number' || /^-?\d+$/.test(String(ref))) {
      let i = Number(ref);
      if (i < 0) i = sc.cues.length + i;
      const c = sc.cues[i];
      if (!c) throw new Error(`シーン「${sc.id}」に文 ${ref} はありません（文は 0〜${sc.cues.length - 1}）`);
      return c;
    }
    const c = sc.cues.find((x) => x.name === ref);
    if (!c) {
      const names = sc.cues.filter((x) => x.name).map((x) => x.name);
      throw new Error(`シーン「${sc.id}」に名前「${ref}」の文はありません（名前: ${names.join(', ') || 'なし'}）`);
    }
    return c;
  }

  // ───────────────────────── 宣言的アニメーションの解析と適用 ─────────────────────────

  function parseSpecs(rec) {
    const specs = [];
    const nodes = rec.el.querySelectorAll('[data-at],[data-until],[data-anim],[data-active],[data-stagger],[data-loop]');
    nodes.forEach((el) => {
      const d = el.dataset;
      const anims = (d.anim || (d.at != null || d.stagger != null ? 'up' : '')).split(/\s+/).filter(Boolean);
      for (const a of anims) {
        if (!SPRING_ANIMS[a] && !TWEEN_ANIMS.has(a)) {
          report(`シーン「${rec.tl.id}」: data-anim="${a}" は未対応です（${Object.keys(SPRING_ANIMS).concat([...TWEEN_ANIMS]).join(' ')}）`);
        }
      }
      if (d.loop && !d.loop.split(/\s+/).every((l) => LOOPS[l])) report(`シーン「${rec.tl.id}」: data-loop="${d.loop}" は未対応です（${Object.keys(LOOPS).join(' ')}）` + describe(el));
      if (d.out && !OUTS[d.out]) report(`シーン「${rec.tl.id}」: data-out="${d.out}" は未対応です（${Object.keys(OUTS).join(' ')}）` + describe(el));
      const base = {
        at: d.at != null ? d.at : anims.length ? 'start' : null,
        loop: d.loop ? d.loop.split(/\s+/) : null,
        loopSpeed: Number(d.loopSpeed || 1),
        out: d.out || 'fade',
        delay: Number(d.delay || 0),
        until: d.until != null ? d.until : null,
        dur: d.dur != null ? Number(d.dur) : null,
        ease: EASE_BY_NAME[d.ease || 'out'] || EASE_BY_NAME.out,
        spring: {
          damping: d.damping != null ? Number(d.damping) : null,
          mass: d.mass != null ? Number(d.mass) : null,
          stiffness: d.stiffness != null ? Number(d.stiffness) : null,
        },
      };
      if (d.stagger != null) {
        // 親はタイミングの入れ物。子に順番に遅れを付けて同じ動きをさせる
        const step = Number(d.stagger || 6);
        Array.from(el.children).forEach((child, i) => {
          specs.push(makeSpec(rec, child, Object.assign({}, base, { delay: base.delay + i * step, until: null }), anims));
        });
        if (base.until != null || d.active) specs.push(makeSpec(rec, el, Object.assign({}, base, { at: null }), []));
        else return;
      } else {
        specs.push(makeSpec(rec, el, base, anims));
      }
    });
    // 参照の妥当性を最初に一度だけ確かめる（存在しない文番号を早く知らせる）
    for (const s of specs) {
      for (const ref of [s.at, s.until, s.active && s.active.from, s.active && s.active.to]) {
        if (ref == null) continue;
        try { resolveCue(rec, ref); } catch (e) { report(e.message + describe(s.el)); s.broken = true; }
      }
    }
    return specs.filter((s) => !s.broken);
  }

  function makeSpec(rec, el, base, anims) {
    const s = Object.assign({ el, anims, baseTransform: el.style.transform || '', last: {} }, base);
    const act = el.dataset.active;
    if (act) {
      const m = act.split('..');
      s.active = { from: m[0] === '' ? null : m[0], to: m.length > 1 && m[1] !== '' ? m[1] : null };
    }
    if (anims.includes('type')) {
      s.textNodes = [];
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) s.textNodes.push({ node: n, text: n.nodeValue });
      s.textLength = s.textNodes.reduce((a, b) => a + b.text.length, 0);
    }
    if (anims.includes('count')) {
      const to = el.dataset.to != null ? el.dataset.to : el.textContent.replace(/[^\d.\-]/g, '');
      s.countTo = Number(to);
      s.countFrom = Number(el.dataset.from || 0);
      const dot = String(to).split('.')[1];
      s.decimals = dot ? dot.length : 0;
      s.plain = el.dataset.format === 'plain';
      if (!Number.isFinite(s.countTo)) report(`data-anim="count" には data-to="数値" が必要です` + describe(el));
    }
    if (anims.includes('draw')) {
      const shapes = el instanceof SVGGeometryElement ? [el] : Array.from(el.querySelectorAll('path,line,polyline,polygon,circle,rect,ellipse'));
      shapes.forEach((sh) => { sh.setAttribute('pathLength', '1'); sh.style.strokeDasharray = '1 1'; });
      s.shapes = shapes;
    }
    if (anims.includes('words')) {
      // 語ごとに包む（日本語は Intl.Segmenter の語の区切り）
      const seg = typeof Intl !== 'undefined' && Intl.Segmenter ? new Intl.Segmenter('ja', { granularity: 'word' }) : null;
      const texts = [];
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) texts.push(n);
      s.words = [];
      texts.forEach((t) => {
        const parts = seg ? Array.from(seg.segment(t.nodeValue), (x) => x.segment) : t.nodeValue.split(/(\s+)/);
        const frag = document.createDocumentFragment();
        parts.forEach((w) => {
          if (!w.trim()) { frag.appendChild(document.createTextNode(w)); return; }
          const sp = document.createElement('span');
          sp.textContent = w;
          sp.style.display = 'inline-block';
          frag.appendChild(sp);
          s.words.push(sp);
        });
        t.parentNode.replaceChild(frag, t);
      });
    }
    if (anims.includes('follow')) {
      s.followPath = el.dataset.follow ? document.querySelector(el.dataset.follow) : null;
      if (!s.followPath || !(s.followPath instanceof SVGGeometryElement)) report(`data-anim="follow" には data-follow="#線のid"（SVG の path など）が必要です` + describe(el));
    }
    if (anims.includes('grow')) el.style.transformOrigin = el.style.transformOrigin || 'left center';
    if (anims.includes('grow-y')) el.style.transformOrigin = el.style.transformOrigin || 'center bottom';
    return s;
  }

  function setStyle(s, prop, value) {
    if (s.last[prop] === value) return;
    s.last[prop] = value;
    if (prop.startsWith('--')) s.el.style.setProperty(prop, value);
    else s.el.style[prop] = value;
  }

  function applySpec(rec, s) {
    const f = rec.f;
    const fps = state.fps;
    let opacity = 1;
    const transforms = [];
    let filter = '';
    let clip = '';
    let p = 1;
    if (s.at != null && s.anims.length) {
      const cue = resolveCue(rec, s.at);
      const since = f - cue.start - s.delay;
      let tp = 1;
      if (s.anims.some((a) => TWEEN_ANIMS.has(a))) {
        const dur = s.dur != null ? s.dur : Math.max(15, cue.end - cue.start - s.delay);
        tp = since < 0 ? 0 : s.ease(clamp(since / Math.max(1, dur)));
      }
      let sp = 1;
      const springName = s.anims.find((a) => SPRING_ANIMS[a]);
      if (springName) {
        const preset = SPRING_PRESETS[springName];
        const config = {
          damping: s.spring.damping != null ? s.spring.damping : preset.damping,
          mass: s.spring.mass != null ? s.spring.mass : preset.mass,
          stiffness: s.spring.stiffness != null ? s.spring.stiffness : preset.stiffness || 100,
        };
        sp = since < 0 ? 0 : spring({ frame: since, fps, config });
        if (STATIC && Math.abs(1 - sp) < 0.01) sp = 1; // 書き出し用：ほぼ落ち着いたばねは止める（1px 未満の揺れを残さない）
        const r = SPRING_ANIMS[springName](sp);
        if (r.t) transforms.push(r.t);
        if (r.f) filter = r.f;
        opacity *= clamp(r.o * 1.4);
      } else if (since <= 0) {
        opacity = 0;
      }
      p = springName && !s.anims.some((a) => TWEEN_ANIMS.has(a)) ? sp : tp;
      for (const a of s.anims) {
        if (a === 'grow') transforms.push(`scaleX(${tp})`);
        else if (a === 'grow-y') transforms.push(`scaleY(${tp})`);
        else if (a === 'wipe') clip = `inset(0 ${((1 - tp) * 100).toFixed(3)}% 0 0)`;
        else if (a === 'wipe-down') clip = `inset(0 0 ${((1 - tp) * 100).toFixed(3)}% 0)`;
        else if (a === 'draw') {
          s.shapes.forEach((sh) => {
            const v = String(1 - tp);
            if (sh.style.strokeDashoffset !== v) sh.style.strokeDashoffset = v;
            sh.style.visibility = tp <= 0 ? 'hidden' : '';
          });
        } else if (a === 'type') {
          let remain = Math.round(tp * s.textLength);
          s.textNodes.forEach((t) => {
            const take = Math.max(0, Math.min(t.text.length, remain));
            const v = t.text.slice(0, take);
            if (t.node.nodeValue !== v) t.node.nodeValue = v;
            remain -= take;
          });
        } else if (a === 'words') {
          // 語が順に、少し上がりながら出る
          const nW = s.words.length;
          s.words.forEach((w, i) => {
            const q = clamp(tp * (nW + 2) - i, 0, 1);
            w.style.opacity = String(q);
            w.style.transform = q >= 1 ? '' : `translateY(${(1 - q) * 0.4}em)`;
          });
        } else if (a === 'follow' && s.followPath) {
          const path = s.followPath;
          const len = path.getTotalLength();
          const pt = path.getPointAtLength(len * tp);
          const ahead = path.getPointAtLength(Math.min(len, len * tp + 1));
          // 線の座標を、要素の位置の基準（offsetParent）の座標に直す。ステージの縮小（プレイヤー）は打ち消す
          const scale = state.comp.getBoundingClientRect().width / state.width || 1;
          const parent = s.el.offsetParent || rec.el;
          const pr = parent.getBoundingClientRect();
          const m = path.getScreenCTM();
          const q = new DOMPoint(pt.x, pt.y).matrixTransform(m);
          const x = (q.x - pr.left) / scale - parent.clientLeft, y = (q.y - pr.top) / scale - parent.clientTop;
          // 要素の中心（data-anchor="bottom" なら下端の中央）を線の上に置く
          const ax = s.el.offsetWidth / 2, ay = s.el.dataset.anchor === 'bottom' ? s.el.offsetHeight : s.el.offsetHeight / 2;
          setStyle(s, 'left', (x - ax).toFixed(2) + 'px');
          setStyle(s, 'top', (y - ay).toFixed(2) + 'px');
          if (s.el.hasAttribute('data-follow-rotate')) transforms.push(`rotate(${Math.atan2(ahead.y - pt.y, ahead.x - pt.x)}rad)`);
        } else if (a === 'count') {
          const v = s.countFrom + (s.countTo - s.countFrom) * tp;
          const text = s.plain ? v.toFixed(s.decimals) : v.toLocaleString('ja-JP', { minimumFractionDigits: s.decimals, maximumFractionDigits: s.decimals });
          if (s.el.textContent !== text) s.el.textContent = text;
        }
      }
    }
    if (s.until != null) {
      const end = resolveCue(rec, s.until).start;
      const q = clamp((end - f) / 10);
      opacity *= q;
      if (q < 1 && OUTS[s.out]) { const t = OUTS[s.out](q); if (t) transforms.push(t); }
    }
    if (s.loop && !STATIC) for (const l of s.loop) if (LOOPS[l]) transforms.push(LOOPS[l](f, s.loopSpeed));
    if (s.active) {
      const a = s.active.from == null ? -Infinity : resolveCue(rec, s.active.from).start;
      const b = s.active.to == null ? Infinity : resolveCue(rec, s.active.to).start;
      const on = f >= a && f < b;
      if (s.last.active !== on) { s.el.classList.toggle('is-active', on); s.last.active = on; }
      const done = f >= b;
      if (s.last.done !== done) { s.el.classList.toggle('is-done', done); s.last.done = done; }
    }
    if (s.at == null && s.until == null && !s.loop) return;
    setStyle(s, 'opacity', opacity >= 0.999 ? '' : String(Math.max(0, opacity)));
    setStyle(s, 'visibility', opacity <= 0.001 ? 'hidden' : '');
    const t = (s.baseTransform + ' ' + transforms.join(' ')).trim();
    setStyle(s, 'transform', t);
    setStyle(s, 'filter', filter);
    setStyle(s, 'clipPath', clip);
    setStyle(s, '--p', p.toFixed(4));
  }

  // ───────────────────────── 描画 ─────────────────────────

  function sceneAt(frame) {
    const list = state.scenes;
    for (let i = list.length - 1; i >= 0; i--) if (frame >= list[i].tl.start) return list[i];
    return list[0];
  }

  // シーンの切り替え。新しいシーンが入ってくる間、前のシーンは最後の絵のまま下に残る（重なる切り替え）。
  //   data-transition: fade（既定）| slide | wipe | zoom | iris | clock | flip | none
  //   data-direction: left（既定。右から入ってくる）| right | up | down
  //   data-enter: フレーム数（既定 18）  data-timing: linear（既定）| spring
  const TRANSITIONS = ['fade', 'slide', 'wipe', 'zoom', 'iris', 'clock', 'flip', 'none'];

  function transitionInfo(rec) {
    const kind = NO_TRANSITION ? 'none' : rec.el.dataset.transition || 'fade';
    const enter = Number(rec.el.dataset.enter || 18);
    const dir = rec.el.dataset.direction || 'left';
    let p = clamp(rec.f / enter);
    if (rec.el.dataset.timing === 'spring') p = rec.f >= enter ? 1 : clamp(spring({ frame: rec.f, fps: state.fps, config: { damping: 200 }, durationInFrames: enter }));
    else p = Easing.inOut(Easing.cubic)(p);
    return { kind, enter, dir, p, active: kind !== 'none' && rec.f < enter };
  }

  /** 入ってくるシーン（cur）と、下に残る前のシーン（under）の見た目 */
  function transitionStyles(t) {
    const p = t.p;
    const none = { opacity: '', transform: '', clipPath: '', mask: '' };
    const cur = Object.assign({}, none), under = Object.assign({}, none);
    if (!t.active) return { cur, under: null };
    const axis = t.dir === 'up' || t.dir === 'down' ? 'Y' : 'X';
    const sign = t.dir === 'right' || t.dir === 'down' ? -1 : 1;
    const W = axis === 'X' ? state.width : state.height;
    switch (t.kind) {
      case 'fade': cur.opacity = String(p); break;
      case 'slide':
        cur.transform = `translate${axis}(${sign * (1 - p) * W}px)`;
        under.transform = `translate${axis}(${-sign * p * W}px)`;
        break;
      case 'wipe': {
        const q = ((1 - p) * 100).toFixed(3) + '%';
        cur.clipPath = t.dir === 'left' ? `inset(0 0 0 ${q})` : t.dir === 'right' ? `inset(0 ${q} 0 0)` : t.dir === 'up' ? `inset(${q} 0 0 0)` : `inset(0 0 ${q} 0)`;
        break;
      }
      case 'zoom': cur.opacity = String(p); cur.transform = `scale(${1.08 - 0.08 * p})`; under.transform = `scale(${1 - 0.06 * p})`; break;
      case 'iris': cur.clipPath = `circle(${(p * 120).toFixed(3)}% at 50% 50%)`; break;
      case 'clock': cur.mask = `conic-gradient(#000 ${(p * 360).toFixed(2)}deg, transparent 0)`; break;
      case 'flip':
        if (p < 0.5) { cur.opacity = '0'; under.transform = `perspective(2400px) rotateY(${p * 180}deg)`; }
        else cur.transform = `perspective(2400px) rotateY(${(p - 1) * 180}deg)`;
        break;
    }
    return { cur, under };
  }

  function setBox(el, st) {
    if (el.style.opacity !== st.opacity) el.style.opacity = st.opacity;
    if (el.style.transform !== st.transform) el.style.transform = st.transform;
    if (el.style.clipPath !== st.clipPath) el.style.clipPath = st.clipPath;
    if (el.style.webkitMaskImage !== st.mask) { el.style.webkitMaskImage = st.mask; el.style.maskImage = st.mask; }
  }

  /** シーンを、そのシーン内のフレーム f の絵にする */
  function paintScene(rec, f) {
    rec.f = f;
    for (const s of rec.specs) {
      try { applySpec(rec, s); } catch (e) { report(e.message + describe(s.el)); }
    }
    for (const c of rec.components) {
      try { c.update(rec.f, rec.ctx); } catch (e) { report(`部品 ${c.name} でエラー: ${e.message}${describe(c.el)}`); c.update = () => {}; }
    }
    if (rec.update) {
      try { rec.update(rec.f, rec.ctx); } catch (e) { report(`シーン「${rec.tl.id}」の Motion.scene でエラー: ${e.message}`); rec.update = null; }
    }
  }

  function renderFrame(frame) {
    const fr = clamp(frame, 0, state.total - 1);
    state.frame = fr;
    const rec = sceneAt(fr);
    if (state.current !== rec) {
      if (state.current) state.current.el.classList.remove('is-current');
      rec.el.classList.add('is-current');
      state.current = rec;
    }
    rec.f = fr - rec.tl.start;
    const t = transitionInfo(rec);
    const idx = state.scenes.indexOf(rec);
    const prev = t.active && idx > 0 ? state.scenes[idx - 1] : null;
    if (state.under && state.under !== prev) { state.under.el.classList.remove('is-under'); setBox(state.under.el, { opacity: '', transform: '', clipPath: '', mask: '' }); state.under = null; }
    const st = transitionStyles(t);
    if (prev) {
      if (state.under !== prev) {
        // 前のシーンを最後の絵で止めて下に敷く
        prev.el.classList.add('is-under');
        paintScene(prev, prev.tl.duration - 1);
        state.under = prev;
      }
      setBox(prev.el, st.under);
    }
    setBox(rec.el, st.cur);
    paintScene(rec, rec.f);
    renderChrome(rec);
    if (state.ui) updateUI();
  }

  function renderChrome(rec) {
    const comp = state.comp;
    const hide = rec.el.dataset.chrome === 'none';
    if (state.chapterBar) {
      state.chapterBar.style.visibility = hide ? 'hidden' : '';
      const at = STATIC ? rec.tl.start : state.frame;
      state.chapterSegs.forEach((seg) => {
        const p = clamp((at - seg.start) / seg.frames);
        const current = at >= seg.start && at < seg.start + seg.frames;
        seg.fill.style.width = (p * 100).toFixed(3) + '%';
        seg.el.classList.toggle('is-current', current);
      });
    }
    if (state.subtitle) {
      let text = '';
      if (subtitlesOn() && comp.dataset.subtitles !== 'off') {
        const cues = rec.tl.cues;
        for (let i = cues.length - 1; i >= 0; i--) {
          if (rec.f >= cues[i].start) {
            const next = cues[i + 1];
            if (rec.f <= cues[i].end + 20 || (next && rec.f < next.start)) text = cues[i].text;
            break;
          }
        }
      }
      if (state.subtitleText.textContent !== text) state.subtitleText.textContent = text;
      state.subtitle.style.display = text ? '' : 'none';
    }
  }

  // ───────────────────────── 2つの時間軸：動画（ナレーション）と発表（手動） ─────────────────────────
  //
  // 動画: timeline.js のとおり。音声が時計。
  // 発表: 同じ文（cue）を「1クリック＝1ステップ」に並べ直した時間軸を実行系が作る。
  //       各文の動きは約1秒に縮め、文の終わりで止まる。見た目は同じ関数で描くので、
  //       data-* も Motion.scene もそのまま動く。

  const LIVE = { lead: 4, gap: 12, settle: 30, tweenMin: 15, voiceTail: 8 };

  function cueIndexOf(tl, ref) {
    if (ref == null || ref === 'start') return 'start';
    if (ref === 'end') return 'end';
    if (/^-?\d+$/.test(String(ref))) { const i = Number(ref); return i < 0 ? tl.cues.length + i : i; }
    return tl.cues.findIndex((c) => c.name === ref);
  }

  function buildLiveLayout() {
    const step = Math.round(Number(state.comp.dataset.liveStep || 30));
    const scenes = [];
    const stops = [];
    let cursor = 0;
    state.scenes.forEach((rec) => {
      const v = rec.tlVideo;
      const n = v.cues.length;
      const need = v.cues.map((c) => (c.build != null ? Math.round(c.build * state.fps) : step));
      let needStart = 0;
      for (const s of rec.specs) {
        if (s.at == null || !s.anims.length) continue;
        const tween = s.anims.some((a) => TWEEN_ANIMS.has(a));
        const springy = s.anims.some((a) => SPRING_ANIMS[a]);
        const extra = s.delay + (tween ? (s.dur != null ? s.dur : LIVE.tweenMin) : 0) + (springy ? LIVE.settle : 0);
        const idx = cueIndexOf(v, s.at);
        if (idx === 'start') needStart = Math.max(needStart, extra);
        else if (typeof idx === 'number' && idx >= 0 && idx < n && v.cues[idx].build == null) need[idx] = Math.max(need[idx], extra);
      }
      for (const nd of rec.needs || []) {
        const idx = cueIndexOf(v, nd.at);
        const fr = Math.round(nd.frames || 0);
        if (idx === 'start') needStart = Math.max(needStart, fr);
        else if (typeof idx === 'number' && idx >= 0 && idx < n && v.cues[idx].build == null) need[idx] = Math.max(need[idx], fr);
      }
      // ナレーションを流すときは、各ステップを文の読み上げの長さまで延ばす（動きも読み上げに合わせて進む）
      const voiced = !!(state.liveNarration && state.audio && !(state.tl.estimated || []).includes(v.id));
      if (voiced) v.cues.forEach((c, i) => { need[i] = Math.max(need[i], c.end - c.start + LIVE.voiceTail); });
      const exit = Number(rec.el.dataset.exit || 10);
      const cues = [];
      const local = [];
      let t = LIVE.lead;
      v.cues.forEach((c, i) => {
        const end = t + need[i];
        cues.push(Object.assign({}, c, { start: t, end, voice: voiced ? { from: v.start + c.start, frames: c.end - c.start } : null }));
        let stop = i === 0 ? Math.max(end, needStart) : end;
        const nextAuto = i + 1 < n && v.cues[i + 1].auto;
        if (!nextAuto) local.push(stop);
        t = stop + LIVE.gap;
      });
      if (!n) local.push(Math.max(step, needStart));
      const last = local[local.length - 1];
      const duration = last + exit + 2;
      scenes.push({ id: v.id, chapter: v.chapter, notes: v.notes, start: cursor, duration, cues });
      local.forEach((x) => stops.push(cursor + x));
      cursor += duration;
    });
    return { total: cursor, scenes, stops };
  }

  function setLayout(mode) {
    const lay = mode === 'live' ? state.live : state.video;
    state.scenes.forEach((rec, i) => { rec.tl = lay.scenes[i]; });
    state.total = Math.max(1, lay.total);
    state.stops = mode === 'live' ? lay.stops : [];
  }

  /** 今の位置を、もう一方の時間軸の対応する位置に写す（同じシーンの同じ文） */
  function mapPosition(fromRec, f, toMode) {
    const local = f - fromRec.tl.start;
    let idx = -1;
    fromRec.tl.cues.forEach((c, i) => { if (local >= c.start) idx = i; });
    const target = toMode === 'live' ? state.live.scenes : state.video.scenes;
    const sc = target[state.scenes.indexOf(fromRec)];
    if (toMode === 'live') {
      const stops = state.live.stops.filter((s) => s >= sc.start && s < sc.start + sc.duration);
      const c = sc.cues[Math.max(0, idx)];
      const want = c ? sc.start + c.end : stops[0];
      return stops.find((s) => s >= want) != null ? stops.find((s) => s >= want) : stops[stops.length - 1];
    }
    const c = sc.cues[idx];
    return c ? sc.start + c.end : sc.start;
  }

  function setMode(mode, keepPosition) {
    if (mode !== 'live' && mode !== 'video') return;
    if (!state.live) return;
    const fromRec = sceneAt(Math.floor(state.frame));
    const f = state.frame;
    if (state.playing) pause();
    const target = keepPosition !== false && state.mode ? mapPosition(fromRec, f, mode) : null;
    state.mode = mode;
    setLayout(mode);
    store.set('mode', mode);
    if (state.ui) { buildTracks(); state.ui.app.classList.toggle('is-live', mode === 'live'); }
    if (state.chapterBar) buildChapterBar();
    seek(target != null ? target : mode === 'live' ? state.stops[0] : 0);
    if (state.ui) updateUI(true);
    syncNotes(true);
  }

  /** 発表モードのナレーションのオン・オフ。ステップの長さが変わるので時間軸を作り直し、同じステップに戻る */
  function setLiveNarration(on) {
    on = !!on && !!state.audio;
    if (state.liveNarration === on) return;
    const idx = state.mode === 'live' ? stepIndex() : -1;
    if (state.playing) pause();
    state.liveNarration = on;
    store.set('liveNarration', on);
    state.live = buildLiveLayout();
    if (state.mode === 'live') {
      setLayout('live');
      if (state.ui) buildTracks();
      if (state.chapterBar) buildChapterBar();
      seek(state.stops[Math.max(0, Math.min(idx, state.stops.length - 1))]);
    }
    if (state.ui) updateUI(true);
    syncNotes(true);
  }

  /** 発表モードでナレーションを流す：今のステップの文の範囲だけ、動画の音声の該当箇所を鳴らす */
  function syncLiveAudio(f) {
    const a = state.audio;
    if (!a || !a.duration) return;
    let want = null;
    if (state.playing && state.liveNarration) {
      const rec = sceneAt(Math.floor(f));
      const lf = f - rec.tl.start;
      const c = rec.tl.cues.find((x) => x.voice && lf >= x.start && lf < x.start + x.voice.frames);
      if (c) want = (c.voice.from + (lf - c.start)) / state.fps;
    }
    if (want == null) { if (!a.paused) a.pause(); return; }
    a.muted = state.muted;
    a.playbackRate = state.rate;
    if (a.paused || Math.abs(a.currentTime - want) > 0.3) {
      try { a.currentTime = want; } catch (e) { /* noop */ }
      if (a.paused) a.play().catch((e) => { console.warn('[motion] 音声を再生できません', e); });
    }
  }

  // ───────────────────────── 再生 ─────────────────────────

  function clockFrame() {
    const a = state.mode === 'video' ? state.audio : null;
    const now = performance.now();
    if (a && !a.paused && !a.ended && !state.wallTakeover && a.duration && a.currentTime < a.duration - 0.05) {
      const t = a.currentTime;
      if (t !== state.lastAudioT) { state.lastAudioT = t; state.lastWall = now; return t * state.fps; }
      // currentTime の更新が粗いブラウザのために、壁時計で補う
      return (t + Math.min(0.25, ((now - state.lastWall) / 1000) * state.rate)) * state.fps;
    }
    return state.wallFrame + ((now - state.wallStart) / 1000) * state.fps * state.rate;
  }

  function tick() {
    if (!state.playing) return;
    let f = clockFrame();
    if (state.stopAt != null && f >= state.stopAt) {
      f = state.stopAt;
      pause();
      seek(f);
      return;
    }
    if (f >= state.total - 1) {
      pause();
      seek(state.total - 1);
      return;
    }
    // 音声が尽きたら壁時計に引き継ぐ
    const a = state.mode === 'video' ? state.audio : null;
    if (a && (a.ended || (a.duration && a.currentTime >= a.duration - 0.05)) && !state.wallTakeover) {
      state.wallTakeover = true;
      state.wallFrame = f;
      state.wallStart = performance.now();
    }
    renderFrame(f);
    if (state.mode === 'live') syncLiveAudio(f);
    requestAnimationFrame(tick);
  }

  function play(stopAt) {
    if (state.playing) return;
    if (state.frame >= state.total - 1) state.frame = 0;
    state.stopAt = stopAt != null ? stopAt : null;
    state.playing = true;
    state.wallTakeover = false;
    state.wallFrame = state.frame;
    state.wallStart = performance.now();
    state.lastAudioT = -1;
    const a = state.audio;
    if (a && state.mode === 'video') {
      a.playbackRate = state.rate;
      a.muted = state.muted;
      const startAudio = (f) => {
        if (!state.playing || state.mode !== 'video') return;
        if (f / state.fps < a.duration - 0.05) {
          a.currentTime = f / state.fps;
          state.wallTakeover = false;
          a.play().catch((e) => { console.warn('[motion] 音声を再生できません', e); });
        } else state.wallTakeover = true;
      };
      if (a.duration) startAudio(state.frame);
      else a.addEventListener('loadedmetadata', () => startAudio(state.frame), { once: true }); // 読み込み前は壁時計で進め、届いたら合流する
    }
    requestAnimationFrame(tick);
    if (state.ui) updateUI(true);
  }

  function pause() {
    if (!state.playing) return;
    state.playing = false;
    state.stopAt = null;
    if (state.audio) state.audio.pause();
    state.frame = Math.round(state.frame);
    if (state.ui) { updateUI(true); saveHash(); }
  }

  function toggle() {
    if (state.mode === 'live') return next();
    state.playing ? pause() : play();
  }

  function seek(frame, keepPlaying) {
    const f = clamp(Math.round(frame), 0, state.total - 1);
    if (state.playing && !keepPlaying) pause();
    if (state.mode === 'video' && state.audio && state.audio.duration) {
      try { state.audio.currentTime = Math.min(state.audio.duration, f / state.fps); } catch (e) { /* noop */ }
    }
    state.wallFrame = f;
    state.wallStart = performance.now();
    state.wallTakeover = false;
    state.lastAudioT = -1;
    renderFrame(f);
    if (!state.playing) saveHash();
    syncNotes();
  }

  // ─ 発表モードの操作：次へ（動かして止まる）・前へ（すぐ戻る）
  function stepIndex() {
    const f = Math.round(state.frame);
    let idx = -1;
    state.stops.forEach((s, i) => { if (f >= s) idx = i; });
    return idx;
  }
  function next() {
    if (state.mode !== 'live') return goCue(1);
    if (state.playing) {
      // 動いている途中なら、そのステップの終わりまで飛ばす（PowerPoint のクリックと同じ）
      const to = state.stopAt;
      pause();
      seek(to);
      return;
    }
    if (!state.started) state.started = performance.now();
    const f = Math.round(state.frame);
    const to = state.stops.find((s) => s > f);
    if (to == null) return;
    play(to);
    syncNotes(true);
  }
  function prev() {
    if (state.mode !== 'live') return goCue(-1);
    const f = Math.round(state.frame);
    const before = state.stops.filter((s) => s < f);
    seek(before.length ? before[before.length - 1] : state.stops[0]);
  }
  function goStep(i) {
    if (state.mode !== 'live') return;
    seek(state.stops[clamp(i, 0, state.stops.length - 1)]);
  }

  function sceneIndex() { return state.scenes.indexOf(sceneAt(Math.floor(state.frame))); }
  function goScene(delta) {
    const i = clamp(sceneIndex() + delta, 0, state.scenes.length - 1);
    const rec = state.scenes[i];
    if (state.mode === 'live') {
      // シーンの最初のステップへ
      const first = state.stops.find((s) => s >= rec.tl.start);
      seek(first != null ? first : rec.tl.start);
    } else seek(rec.tl.start, true);
  }
  function cueStarts() {
    const out = [];
    state.scenes.forEach((r) => {
      out.push(r.tl.start);
      r.tl.cues.forEach((c) => out.push(r.tl.start + c.start));
    });
    return Array.from(new Set(out)).sort((a, b) => a - b);
  }
  function goCue(delta) {
    const list = cueStarts();
    const f = Math.floor(state.frame);
    if (delta > 0) {
      const n = list.find((x) => x > f);
      seek(n != null ? n : state.total - 1, true);
    } else {
      const p = list.filter((x) => x < f - 6);
      seek(p.length ? p[p.length - 1] : 0, true);
    }
  }

  /** 今の文（発表では「今話すこと」）と次の文 */
  function cueState() {
    const f = Math.round(state.frame);
    const rec = sceneAt(f);
    const lf = f - rec.tl.start;
    let idx = -1;
    rec.tl.cues.forEach((c, i) => { if (lf >= c.start) idx = i; });
    let nextCue = rec.tl.cues[idx + 1] || null;
    let nextScene = null;
    if (!nextCue) {
      const r2 = state.scenes[state.scenes.indexOf(rec) + 1];
      if (r2) { nextScene = r2.tl; nextCue = r2.tl.cues[0] || null; }
    }
    return { rec, idx, cue: rec.tl.cues[idx] || null, nextCue, nextScene };
  }

  // ───────────────────────── プレイヤーUI（Remotion Studio 風） ─────────────────────────

  const store = {
    get(k, d) { try { const v = localStorage.getItem('motion:' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('motion:' + k, JSON.stringify(v)); } catch (e) { /* noop */ } },
  };

  const fmtTime = (frame) => {
    const s = frame / state.fps;
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    const ff = Math.floor(frame % state.fps);
    return `${m}:${String(sec).padStart(2, '0')}.${String(ff).padStart(2, '0')}`;
  };
  const fmtClock = (ms) => {
    const s = Math.max(0, Math.floor(ms / 1000));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  };

  function h(tag, attrs, children, doc) {
    const el = (doc || document).createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === 'class') el.className = attrs[k];
      else if (k === 'text') el.textContent = attrs[k];
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), attrs[k]);
      else el.setAttribute(k, attrs[k]);
    }
    (children || []).forEach((c) => c && el.appendChild(c));
    return el;
  }

  const ICONS = {
    play: '<svg viewBox="0 0 24 24"><path d="M7 4.5v15l13-7.5z" fill="currentColor"/></svg>',
    pause: '<svg viewBox="0 0 24 24"><path d="M6 4h4v16H6zM14 4h4v16h-4z" fill="currentColor"/></svg>',
    prev: '<svg viewBox="0 0 24 24"><path d="M6 5h2v14H6zM20 5v14L9 12z" fill="currentColor"/></svg>',
    next: '<svg viewBox="0 0 24 24"><path d="M16 5h2v14h-2zM4 5v14l11-7z" fill="currentColor"/></svg>',
    stepPrev: '<svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7" stroke="currentColor" stroke-width="2.5" fill="none"/></svg>',
    stepNext: '<svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7" stroke="currentColor" stroke-width="2.5" fill="none"/></svg>',
    full: '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" stroke="currentColor" stroke-width="2" fill="none"/></svg>',
    vol: '<svg viewBox="0 0 24 24"><path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor"/><path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" stroke="currentColor" stroke-width="2" fill="none"/></svg>',
    mute: '<svg viewBox="0 0 24 24"><path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor"/><path d="M16 9l5 6M21 9l-5 6" stroke="currentColor" stroke-width="2"/></svg>',
  };

  function iconButton(name, title, onclick, cls) {
    const b = h('button', { class: 'md-btn' + (cls ? ' ' + cls : ''), title, 'aria-label': title, onclick });
    b.innerHTML = ICONS[name];
    return b;
  }

  function chapterColor(i) {
    const palette = ['#0B84F3', '#7C5CFF', '#14B8A6', '#F59E0B', '#EF4444', '#22C55E', '#EC4899', '#06B6D4'];
    return palette[i % palette.length];
  }

  function chapterList() {
    const chapters = [];
    state.scenes.forEach((r) => {
      const name = r.tl.chapter || '';
      const last = chapters[chapters.length - 1];
      if (last && last.name === name) last.frames += r.tl.duration;
      else chapters.push({ name, start: r.tl.start, frames: r.tl.duration });
    });
    return chapters;
  }

  function buildUI() {
    const app = h('div', { id: 'md-app' });
    const viewport = h('div', { id: 'md-viewport' });
    const stage = h('div', { id: 'md-stage' });
    const blackout = h('div', { id: 'md-blackout' });
    state.comp.parentNode.insertBefore(app, state.comp);
    stage.appendChild(state.comp);
    viewport.append(stage, blackout);
    app.appendChild(viewport);

    // ─ コントロールバー
    const playBtn = iconButton('play', '再生 / 一時停止（Space）', () => toggle(), 'md-video-only');
    const prevBtn = iconButton('prev', '前のシーン（[）', () => goScene(-1));
    const nextBtn = iconButton('next', '次のシーン（]）', () => goScene(1));
    const stepPrevBtn = iconButton('stepPrev', '前のステップ（←）', () => prev(), 'md-live-only');
    const stepNextBtn = iconButton('stepNext', '次のステップ（→ / Space / クリック）', () => next(), 'md-live-only md-step-next');
    const time = h('div', { class: 'md-time' });
    const frameLabel = h('div', { class: 'md-frame' });
    const sceneLabel = h('div', { class: 'md-scene-label' });
    const muteBtn = iconButton(state.muted ? 'mute' : 'vol', 'ミュート（M）', () => { state.muted = !state.muted; store.set('muted', state.muted); if (state.audio) state.audio.muted = state.muted; updateUI(true); }, 'md-video-only');
    const rateSel = h('select', { class: 'md-select md-video-only', title: '再生速度', onchange: (e) => { state.rate = Number(e.target.value); store.set('rate', state.rate); if (state.audio) state.audio.playbackRate = state.rate; if (state.playing) { pause(); play(); } } });
    [0.5, 0.75, 1, 1.25, 1.5, 2].forEach((r) => rateSel.appendChild(h('option', { value: r, text: r + '×' })));
    rateSel.value = String(state.rate);
    const ccBtn = h('button', { class: 'md-chip', title: '字幕（C）', text: '字幕', onclick: () => toggleSubtitles() });
    const modeVideo = h('button', { class: 'md-seg', text: '動画', title: 'ナレーションに合わせて自動で進む（P で切り替え）', onclick: () => setMode('video') });
    const modeLive = h('button', { class: 'md-seg', text: '発表', title: 'クリックで1ステップずつ進める（P で切り替え）', onclick: () => setMode('live') });
    const voiceBtn = h('button', { class: 'md-chip md-live-only', title: state.audio ? '発表中もナレーションを流す（V）' : 'ナレーションの音声がありません（synth → timeline で作る）', text: 'ナレーション', onclick: () => setLiveNarration(!state.liveNarration) });
    if (!state.audio) voiceBtn.disabled = true;
    const notesBtn = h('button', { class: 'md-chip md-live-only', title: '発表者ビュー：台本・次のステップ・経過時間を別ウィンドウに（N）', text: 'ノート', onclick: () => openNotes() });
    const tlBtn = h('button', { class: 'md-chip', title: 'タイムライン（T）', text: 'タイムライン', onclick: () => toggleTimeline() });
    const helpBtn = h('button', { class: 'md-chip', title: 'ショートカット（?）', text: '?', onclick: () => toggleHelp() });
    const fullBtn = iconButton('full', '全画面（F）', () => toggleFullscreen());

    const scrub = h('div', { class: 'md-scrub' });
    const scrubTrack = h('div', { class: 'md-scrub-track' });
    const scrubPlayed = h('div', { class: 'md-scrub-played' });
    const scrubHead = h('div', { class: 'md-scrub-head' });
    const scrubTip = h('div', { class: 'md-tip' });
    scrub.append(scrubTrack, scrubPlayed, scrubHead, scrubTip);

    const bar = h('div', { id: 'md-bar' }, [
      scrub,
      h('div', { class: 'md-row' }, [
        prevBtn, playBtn, stepPrevBtn, stepNextBtn, nextBtn, time, frameLabel, sceneLabel,
        h('div', { class: 'md-spacer' }),
        h('div', { class: 'md-badge md-video-only', text: state.tl.estimated && state.tl.estimated.length ? '仮の尺' : '', title: '音声がまだないシーンは文字数から尺を見積もっています' }),
        h('div', { class: 'md-segs' }, [modeVideo, modeLive]),
        voiceBtn, notesBtn, muteBtn, rateSel, ccBtn, tlBtn, helpBtn, fullBtn,
      ]),
    ]);
    app.appendChild(bar);

    // ─ タイムラインパネル（章・シーン・文のトラック）
    const panel = h('div', { id: 'md-timeline' });
    const labels = h('div', { class: 'md-tl-labels' }, ['章', 'シーン', '文'].map((t) => h('div', { class: 'md-tl-label', text: t })));
    const scroller = h('div', { class: 'md-tl-scroll' });
    const content = h('div', { class: 'md-tl-content' });
    const ruler = h('div', { class: 'md-tl-ruler' });
    const rows = [h('div', { class: 'md-tl-row' }), h('div', { class: 'md-tl-row' }), h('div', { class: 'md-tl-row' })];
    const playhead = h('div', { class: 'md-tl-playhead' });
    content.append(ruler, ...rows, playhead);
    scroller.appendChild(content);
    const zoomOut = h('button', { class: 'md-chip', text: '−', title: '縮小', onclick: () => setZoom(state.zoom / 1.5) });
    const zoomIn = h('button', { class: 'md-chip', text: '＋', title: '拡大', onclick: () => setZoom(state.zoom * 1.5) });
    panel.append(h('div', { class: 'md-tl-side' }, [h('div', { class: 'md-tl-zoom' }, [zoomOut, zoomIn]), labels]), scroller);
    app.appendChild(panel);

    const seekFromPanel = (e) => {
      const rect = content.getBoundingClientRect();
      seek(((e.clientX - rect.left) / state.zoom) * state.fps, false);
    };
    content.addEventListener('pointerdown', (e) => {
      seekFromPanel(e);
      const move = (ev) => seekFromPanel(ev);
      const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', up);
    });
    scroller.addEventListener('wheel', (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      setZoom(state.zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15));
    }, { passive: false });

    // ─ ヘルプとエラー
    const help = h('div', { id: 'md-help', onclick: () => toggleHelp(false) });
    help.innerHTML = `<div class="md-help-card"><h2>共通</h2><dl>
      <dt>P</dt><dd>動画 ⇄ 発表 の切り替え</dd>
      <dt>[ / ]</dt><dd>前のシーン・次のシーンへ</dd>
      <dt>Home / End</dt><dd>最初・最後へ</dd>
      <dt>B / W</dt><dd>画面を黒・白にする（もう一度で戻る）</dd>
      <dt>C / T / F</dt><dd>字幕・タイムライン・全画面</dd>
    </dl><h2>発表（手動で進める）</h2><dl>
      <dt>→ ↓ Space Enter PageDown / クリック</dt><dd>次のステップを動かす（動いている途中なら最後まで飛ばす）</dd>
      <dt>← ↑ Backspace PageUp</dt><dd>前のステップへ戻る</dd>
      <dt>V</dt><dd>ナレーションのオン・オフ（オンなら、クリックごとにその文を読み上げ、動きも読み上げの長さで進む）</dd>
      <dt>N</dt><dd>発表者ビュー（台本・次のステップ・経過時間）を開く</dd>
      <dt>数字 + Enter</dt><dd>そのステップ番号へ移動</dd>
    </dl><h2>動画（ナレーション）</h2><dl>
      <dt>Space / K / クリック</dt><dd>再生・一時停止</dd>
      <dt>← / →</dt><dd>1フレーム戻る・進む（Shift で1秒）</dd>
      <dt>J / L</dt><dd>5秒戻る・進む</dd>
      <dt>↑ / ↓</dt><dd>前の文・次の文へ</dd>
      <dt>0〜9</dt><dd>全体の 0%〜90% へ</dd>
      <dt>M / &lt; &gt;</dt><dd>ミュート・再生速度</dd>
    </dl><p>ダブルクリックで全画面。URL の ?mode=live で発表として、#f=フレーム でその位置から開きます。</p></div>`;
    app.appendChild(help);
    const errBox = h('div', { id: 'md-error' });
    app.appendChild(errBox);

    // ─ スクラブ操作
    const scrubSeek = (e) => {
      const rect = scrub.getBoundingClientRect();
      seek(clamp((e.clientX - rect.left) / rect.width) * (state.total - 1), true);
    };
    let resumeAfter = false;
    scrub.addEventListener('pointerdown', (e) => {
      resumeAfter = state.playing && state.mode === 'video';
      if (state.playing) pause();
      scrubSeek(e);
      scrub.setPointerCapture(e.pointerId);
      scrub.classList.add('is-dragging');
    });
    scrub.addEventListener('pointermove', (e) => {
      const rect = scrub.getBoundingClientRect();
      const x = clamp((e.clientX - rect.left) / rect.width);
      const f = Math.round(x * (state.total - 1));
      const rec = sceneAt(f);
      const lf = f - rec.tl.start;
      let cue = '';
      rec.tl.cues.forEach((c) => { if (lf >= c.start) cue = c.text; });
      scrubTip.textContent = `${state.mode === 'live' ? '' : fmtTime(f) + '  '}${rec.tl.id}${cue ? '｜' + cue : ''}`;
      scrubTip.style.left = x * 100 + '%';
      if (scrub.classList.contains('is-dragging')) scrubSeek(e);
    });
    const endDrag = () => {
      if (!scrub.classList.contains('is-dragging')) return;
      scrub.classList.remove('is-dragging');
      if (state.mode === 'live') {
        // 発表ではドラッグを離した位置の直前のステップに合わせる
        const f = Math.round(state.frame);
        const before = state.stops.filter((s) => s <= f);
        seek(before.length ? before[before.length - 1] : state.stops[0]);
      } else if (resumeAfter) play();
    };
    scrub.addEventListener('pointerup', endDrag);
    scrub.addEventListener('pointercancel', endDrag);

    viewport.addEventListener('click', (e) => { if (e.detail === 1) toggle(); });
    viewport.addEventListener('dblclick', () => toggleFullscreen());
    viewport.addEventListener('contextmenu', (e) => { if (state.mode === 'live') { e.preventDefault(); prev(); } });

    // 全画面で再生中・発表中はUIを隠す
    let idle;
    const wake = () => {
      app.classList.remove('is-idle');
      clearTimeout(idle);
      idle = setTimeout(() => { if (document.fullscreenElement && (state.playing || state.mode === 'live')) app.classList.add('is-idle'); }, 2200);
    };
    app.addEventListener('pointermove', wake);

    state.ui = { app, viewport, stage, blackout, voiceBtn, playBtn, time, frameLabel, sceneLabel, muteBtn, rateSel, ccBtn, modeVideo, modeLive, tlBtn, scrub, scrubTrack, scrubPlayed, scrubHead, panel, content, rows, playhead, scroller, ruler, help, errBox, wake };
    state.zoom = store.get('zoom', 24);
    if (params.has('timeline') ? params.get('timeline') !== '0' : store.get('timeline', false)) app.classList.add('show-timeline');
    app.classList.toggle('is-live', state.mode === 'live');
    buildTracks();
    fit();
    new ResizeObserver(fit).observe(viewport);
    document.addEventListener('keydown', onKey);
    state.keyboard = true;
    document.addEventListener('fullscreenchange', () => { fit(); wake(); });
    window.addEventListener('beforeunload', () => { if (state.notes && !state.notes.closed) state.notes.close(); });
    showErrors();
  }

  /** スクラブバーとタイムラインの中身（時間軸を切り替えたら作り直す） */
  function buildTracks() {
    const ui = state.ui;
    ui.scrubTrack.innerHTML = '';
    const chapters = chapterList();
    chapters.forEach((c, i) => {
      const seg = h('div', { class: 'md-scrub-seg', title: c.name });
      seg.style.left = (c.start / state.total) * 100 + '%';
      seg.style.width = (c.frames / state.total) * 100 + '%';
      seg.style.setProperty('--c', chapterColor(i));
      ui.scrubTrack.appendChild(seg);
    });
    state.scenes.forEach((r) => {
      const t = h('div', { class: 'md-scrub-scene' });
      t.style.left = (r.tl.start / state.total) * 100 + '%';
      ui.scrubTrack.appendChild(t);
    });
    state.stops.forEach((s) => {
      const t = h('div', { class: 'md-scrub-stop' });
      t.style.left = (s / Math.max(1, state.total - 1)) * 100 + '%';
      ui.scrubTrack.appendChild(t);
    });
    ui.rows.forEach((r) => { r.innerHTML = ''; });
    chapters.forEach((c, i) => {
      const b = h('div', { class: 'md-tl-block md-tl-chapter', text: c.name, title: c.name });
      b.style.setProperty('--c', chapterColor(i));
      b.dataset.start = c.start; b.dataset.frames = c.frames;
      ui.rows[0].appendChild(b);
    });
    state.scenes.forEach((r) => {
      const ci = chapters.findIndex((c) => r.tl.start >= c.start && r.tl.start < c.start + c.frames);
      const est = state.mode === 'video' && state.tl.estimated && state.tl.estimated.includes(r.tl.id);
      const b = h('div', { class: 'md-tl-block md-tl-scene' + (est ? ' is-estimated' : ''), text: r.tl.id, title: `${r.tl.id}（${(r.tl.duration / state.fps).toFixed(1)}秒${est ? '・仮の尺' : ''}）` });
      b.style.setProperty('--c', chapterColor(Math.max(0, ci)));
      b.dataset.start = r.tl.start; b.dataset.frames = r.tl.duration;
      ui.rows[1].appendChild(b);
      r.tl.cues.forEach((c, i) => {
        const cb = h('div', { class: 'md-tl-block md-tl-cue', text: `${i}${c.name ? ' ' + c.name : ''}｜${c.text}`, title: `文 ${i}${c.name ? '（' + c.name + '）' : ''}: ${c.text}` });
        cb.dataset.start = r.tl.start + c.start; cb.dataset.frames = Math.max(1, c.end - c.start);
        ui.rows[2].appendChild(cb);
      });
    });
    layoutTimeline();
  }

  function setZoom(z) {
    state.zoom = clamp(z, 2, 400);
    store.set('zoom', state.zoom);
    layoutTimeline();
    updateUI(true);
  }

  function layoutTimeline() {
    const ui = state.ui;
    const pxPerFrame = state.zoom / state.fps;
    ui.content.style.width = Math.ceil(state.total * pxPerFrame) + 40 + 'px';
    ui.content.querySelectorAll('.md-tl-block').forEach((b) => {
      b.style.left = Number(b.dataset.start) * pxPerFrame + 'px';
      b.style.width = Math.max(2, Number(b.dataset.frames) * pxPerFrame - 2) + 'px';
    });
    ui.ruler.innerHTML = '';
    const totalSec = state.total / state.fps;
    const steps = [1, 2, 5, 10, 15, 30, 60, 120, 300];
    const step = steps.find((s) => s * state.zoom >= 70) || 600;
    for (let s = 0; s <= totalSec; s += step) {
      const t = h('div', { class: 'md-tl-tick', text: fmtTime(s * state.fps).replace(/\.\d+$/, '') });
      t.style.left = s * state.zoom + 'px';
      ui.ruler.appendChild(t);
    }
  }

  function fit() {
    const ui = state.ui;
    const vw = ui.viewport.clientWidth, vh = ui.viewport.clientHeight;
    const scale = Math.min(vw / state.width, vh / state.height);
    ui.stage.style.width = state.width + 'px';
    ui.stage.style.height = state.height + 'px';
    ui.stage.style.transform = `translate(${(vw - state.width * scale) / 2}px, ${(vh - state.height * scale) / 2}px) scale(${scale})`;
  }

  function updateUI(force) {
    const ui = state.ui;
    const f = state.frame;
    const fi = Math.floor(f);
    if (force || ui.lastF !== fi) {
      ui.lastF = fi;
      const rec = sceneAt(fi);
      const idx = state.scenes.indexOf(rec);
      if (state.mode === 'live') {
        const si = stepIndex();
        ui.time.textContent = `ステップ ${Math.max(1, si + 1)} / ${state.stops.length}`;
        ui.frameLabel.textContent = state.started ? fmtClock(performance.now() - state.started) : '';
      } else {
        ui.time.textContent = `${fmtTime(fi)} / ${fmtTime(state.total)}`;
        ui.frameLabel.textContent = `${fi}f`;
      }
      const label = `${idx + 1}/${state.scenes.length} ${rec.tl.chapter ? rec.tl.chapter + ' › ' : ''}${rec.tl.id}`;
      if (ui.sceneLabel.textContent !== label) ui.sceneLabel.textContent = label;
      ui.rows[2].querySelectorAll('.md-tl-cue').forEach((b) => {
        const s = Number(b.dataset.start), e = s + Number(b.dataset.frames);
        b.classList.toggle('is-active', fi >= s && fi < e);
      });
    }
    const pct = (f / Math.max(1, state.total - 1)) * 100;
    ui.scrubPlayed.style.width = pct + '%';
    ui.scrubHead.style.left = pct + '%';
    const x = (f / state.fps) * state.zoom;
    ui.playhead.style.transform = `translateX(${x}px)`;
    if (state.playing && ui.app.classList.contains('show-timeline')) {
      const sc = ui.scroller;
      if (x < sc.scrollLeft + 40 || x > sc.scrollLeft + sc.clientWidth - 80) sc.scrollLeft = x - sc.clientWidth * 0.25;
    }
    if (force) {
      ui.playBtn.innerHTML = state.playing ? ICONS.pause : ICONS.play;
      ui.muteBtn.innerHTML = state.muted ? ICONS.mute : ICONS.vol;
      ui.ccBtn.classList.toggle('is-on', subtitlesOn());
      ui.modeVideo.classList.toggle('is-on', state.mode === 'video');
      ui.modeLive.classList.toggle('is-on', state.mode === 'live');
      ui.tlBtn.classList.toggle('is-on', ui.app.classList.contains('show-timeline'));
      ui.voiceBtn.classList.toggle('is-on', !!state.liveNarration);
      ui.app.classList.toggle('is-playing', state.playing);
      const atEnd = state.mode === 'live' && stepIndex() >= state.stops.length - 1 && !state.playing;
      ui.app.classList.toggle('is-last-step', atEnd);
    }
  }

  // 字幕は時間軸ごとに覚える（発表では既定で消す：話すのは本人なので）
  function subtitlesOn() { return state.mode === 'live' ? state.subtitlesLive : state.subtitles; }
  function toggleSubtitles() {
    if (state.mode === 'live') { state.subtitlesLive = !state.subtitlesLive; store.set('subtitlesLive', state.subtitlesLive); }
    else { state.subtitles = !state.subtitles; store.set('subtitles', state.subtitles); }
    renderFrame(state.frame);
    updateUI(true);
  }
  function toggleTimeline() {
    const on = state.ui.app.classList.toggle('show-timeline');
    store.set('timeline', on);
    requestAnimationFrame(fit);
    updateUI(true);
  }
  function toggleHelp(force) { state.ui.help.classList.toggle('is-open', force); }
  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else state.ui.app.requestFullscreen().catch(() => {});
  }
  function toggleBlackout(color) {
    const b = state.ui.blackout;
    const on = b.classList.contains('is-on') && b.dataset.color === color;
    b.dataset.color = color;
    b.classList.toggle('is-on', !on);
    syncNotes(true);
  }

  let typedNumber = '';
  function onKey(e) {
    if (e.target && /input|select|textarea/i.test(e.target.tagName)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    const handled = () => { e.preventDefault(); if (state.ui) state.ui.wake(); };
    const live = state.mode === 'live';
    // 共通
    if (k === 'p' || k === 'P') { handled(); setMode(live ? 'video' : 'live'); return; }
    if (k === '[') { handled(); goScene(-1); return; }
    if (k === ']') { handled(); goScene(1); return; }
    if (k === 'Home') { handled(); live ? goStep(0) : seek(0); return; }
    if (k === 'End') { handled(); live ? goStep(state.stops.length - 1) : seek(state.total - 1); return; }
    if (k === 'b' || k === 'B' || k === '.') { handled(); toggleBlackout('black'); return; }
    if (k === 'w' || k === 'W' || k === ',') { handled(); toggleBlackout('white'); return; }
    if (k === 'c' || k === 'C') { handled(); toggleSubtitles(); return; }
    if (k === 't' || k === 'T') { handled(); toggleTimeline(); return; }
    if (k === 'f' || k === 'F') { handled(); toggleFullscreen(); return; }
    if (k === '?') { handled(); toggleHelp(); return; }
    if (k === 'Escape') { toggleHelp(false); return; }
    if (live && (k === 'v' || k === 'V')) { handled(); setLiveNarration(!state.liveNarration); return; }
    if (live && (k === 'm' || k === 'M')) { handled(); state.ui.muteBtn.click(); return; }
    if (live) {
      if (/^[0-9]$/.test(k)) { handled(); typedNumber = (typedNumber + k).slice(-4); return; }
      if (k === 'Enter' && typedNumber) { handled(); goStep(Number(typedNumber) - 1); typedNumber = ''; return; }
      typedNumber = '';
      if (['ArrowRight', 'ArrowDown', ' ', 'Enter', 'PageDown'].includes(k)) { handled(); next(); }
      else if (['ArrowLeft', 'ArrowUp', 'Backspace', 'PageUp'].includes(k)) { handled(); prev(); }
      else if (k === 'n' || k === 'N') { handled(); openNotes(); }
      return;
    }
    if (k === ' ' || k === 'k' || k === 'K') { handled(); toggle(); }
    else if (k === 'ArrowLeft') { handled(); seek(Math.floor(state.frame) - (e.shiftKey ? state.fps : 1)); }
    else if (k === 'ArrowRight') { handled(); seek(Math.floor(state.frame) + (e.shiftKey ? state.fps : 1)); }
    else if (k === 'j' || k === 'J') { handled(); seek(state.frame - state.fps * 5, true); }
    else if (k === 'l' || k === 'L') { handled(); seek(state.frame + state.fps * 5, true); }
    else if (k === 'ArrowUp') { handled(); goCue(-1); }
    else if (k === 'ArrowDown') { handled(); goCue(1); }
    else if (k === 'PageUp') { handled(); goScene(-1); }
    else if (k === 'PageDown') { handled(); goScene(1); }
    else if (/^[0-9]$/.test(k)) { handled(); seek((Number(k) / 10) * state.total, true); }
    else if (k === 'm' || k === 'M') { handled(); state.ui.muteBtn.click(); }
    else if (k === '<' || k === '>') {
      handled();
      const rates = [0.5, 0.75, 1, 1.25, 1.5, 2];
      const i = clamp(rates.indexOf(state.rate) + (k === '>' ? 1 : -1), 0, rates.length - 1);
      state.ui.rateSel.value = String(rates[i]);
      state.ui.rateSel.dispatchEvent(new Event('change'));
    }
  }

  function saveHash() {
    if (RENDER) return;
    try { history.replaceState(null, '', location.pathname + location.search + '#f=' + Math.round(state.frame)); } catch (e) { /* noop */ }
  }

  // ───────────────────────── 発表者ビュー（別ウィンドウ） ─────────────────────────
  //
  // about:blank のウィンドウは開いた側と同じオリジンになるので、file:// でも直接DOMを操作できる。

  const NOTES_CSS = `
    *{box-sizing:border-box} body{margin:0;background:#111418;color:#e6e9ee;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;height:100vh;display:grid;grid-template-rows:auto 1fr auto}
    header{display:flex;gap:16px;align-items:baseline;padding:12px 20px;border-bottom:1px solid #2b3038}
    .clock{font-size:34px;font-weight:700;font-variant-numeric:tabular-nums}
    .meta{color:#8b93a1} .grow{flex:1}
    main{display:grid;grid-template-columns:1.3fr 1fr;gap:20px;padding:20px;overflow:hidden;min-height:0}
    .col{overflow:auto;min-height:0}
    h3{margin:0 0 6px;font-size:13px;color:#8b93a1;font-weight:600;letter-spacing:.05em}
    .now{font-size:28px;font-weight:700;line-height:1.5;margin-bottom:22px}
    .next{font-size:22px;color:#9ecbff;line-height:1.5;margin-bottom:22px}
    .next small{display:block;color:#8b93a1;font-size:13px}
    .note{background:#1e2228;border-left:4px solid #f59e0b;padding:10px 14px;border-radius:6px;margin-bottom:16px;white-space:pre-wrap}
    ol{margin:0;padding-left:1.6em} li{margin:0 0 8px;color:#8b93a1} li.done{color:#5c6470} li.cur{color:#fff;font-weight:700} li.nx{color:#9ecbff}
    footer{display:flex;gap:10px;padding:12px 20px;border-top:1px solid #2b3038;align-items:center}
    button{background:#1e2228;color:#e6e9ee;border:1px solid #2b3038;border-radius:8px;padding:10px 18px;font:inherit;cursor:pointer}
    button.primary{background:#0b84f3;border-color:#0b84f3;color:#fff;font-weight:700;flex:1}
    .badge{color:#fbbf24}
  `;

  function openNotes() {
    if (state.notes && !state.notes.closed) { state.notes.focus(); return; }
    const w = window.open('', 'motion-deck-notes', 'width=980,height=640');
    if (!w) { report('発表者ビューを開けません（ポップアップがブロックされました）'); return; }
    state.notes = w;
    const d = w.document;
    d.open();
    d.write('<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>発表者ビュー</title></head><body></body></html>');
    d.close();
    d.head.appendChild(h('style', { text: NOTES_CSS }, null, d));
    const el = (tag, cls, text) => h(tag, Object.assign({}, cls ? { class: cls } : {}, text != null ? { text } : {}), null, d);
    const clock = el('div', 'clock', '0:00');
    const step = el('div', 'meta');
    const badge = el('div', 'badge');
    const reset = h('button', { text: 'タイマーをリセット', onclick: () => { state.started = performance.now(); syncNotes(true); } }, null, d);
    const header = h('header', null, [clock, step, badge, el('div', 'grow'), reset], d);
    const now = el('div', 'now');
    const nextEl = el('div', 'next');
    const note = el('div', 'note');
    const left = h('div', { class: 'col' }, [el('h3', null, '今話すこと'), now, note, el('h3', null, '次のクリック'), nextEl], d);
    const list = el('ol');
    const sceneTitle = el('h3');
    const right = h('div', { class: 'col' }, [sceneTitle, list], d);
    const main = h('main', null, [left, right], d);
    const prevB = h('button', { text: '← 前へ', onclick: () => prev() }, null, d);
    const nextB = h('button', { class: 'primary', text: '次へ →', onclick: () => next() }, null, d);
    const footer = h('footer', null, [prevB, nextB], d);
    d.body.append(header, main, footer);
    d.addEventListener('keydown', (e) => onKey(e));
    state.notesUI = { clock, step, badge, now, nextEl, note, list, sceneTitle };
    clearInterval(state.notesTimer);
    state.notesTimer = setInterval(() => {
      if (!state.notes || state.notes.closed) { clearInterval(state.notesTimer); return; }
      state.notesUI.clock.textContent = state.started ? fmtClock(performance.now() - state.started) : '0:00';
      if (state.ui && state.mode === 'live' && state.started) state.ui.frameLabel.textContent = fmtClock(performance.now() - state.started);
    }, 500);
    syncNotes(true);
  }

  function syncNotes(force) {
    const w = state.notes;
    if (!w || w.closed || !state.notesUI) return;
    const cs = cueState();
    const key = `${state.mode}:${state.liveNarration}:${state.scenes.indexOf(cs.rec)}:${cs.idx}:${state.playing}:${state.ui && state.ui.blackout.classList.contains('is-on')}`;
    if (!force && key === state.notesKey) return;
    state.notesKey = key;
    const u = state.notesUI;
    const si = stepIndex();
    u.step.textContent = state.mode === 'live'
      ? `ステップ ${Math.max(1, si + 1)} / ${state.stops.length}　シーン ${state.scenes.indexOf(cs.rec) + 1} / ${state.scenes.length}「${cs.rec.tl.id}」`
      : '動画モード（P で発表に切り替え）';
    u.badge.textContent = [
      state.mode === 'live' && state.liveNarration ? 'ナレーション オン（V）' : '',
      state.ui && state.ui.blackout.classList.contains('is-on') ? '画面を隠しています（B / W）' : '',
    ].filter(Boolean).join('　');
    u.now.textContent = cs.cue ? cs.cue.text : '（シーンの始まり）';
    const notes = [cs.cue && cs.cue.note, cs.idx <= 0 ? cs.rec.tl.notes : null].filter(Boolean).join('\n');
    u.note.textContent = notes;
    u.note.style.display = notes ? '' : 'none';
    u.nextEl.innerHTML = '';
    if (cs.nextScene) u.nextEl.appendChild(h('small', { text: `次のシーン「${cs.nextScene.id}」${cs.nextScene.chapter ? '（' + cs.nextScene.chapter + '）' : ''}` }, null, w.document));
    u.nextEl.appendChild(w.document.createTextNode(cs.nextCue ? cs.nextCue.text : cs.nextScene ? '（文のないシーン）' : '（最後です）'));
    u.sceneTitle.textContent = `このシーンの台本（${cs.rec.tl.chapter || cs.rec.tl.id}）`;
    u.list.innerHTML = '';
    cs.rec.tl.cues.forEach((c, i) => {
      const li = h('li', { text: c.text, class: i < cs.idx ? 'done' : i === cs.idx ? 'cur' : i === cs.idx + 1 ? 'nx' : '' }, null, w.document);
      u.list.appendChild(li);
    });
  }

  function showErrors() {
    const box = state.ui && state.ui.errBox;
    if (!box) return;
    box.innerHTML = '';
    if (!errors.length) { box.style.display = 'none'; return; }
    box.style.display = '';
    box.appendChild(h('div', { class: 'md-error-title', text: `問題が ${errors.length} 件あります` }));
    errors.slice(0, 12).forEach((m) => box.appendChild(h('div', { class: 'md-error-item', text: m })));
    box.appendChild(h('button', { class: 'md-chip', text: '閉じる', onclick: () => { box.style.display = 'none'; } }));
  }

  function describe(el) {
    if (!el || !el.tagName) return '';
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter((c) => c && !c.startsWith('is-')).slice(0, 2) : [];
    if (cls.length) s += '.' + cls.join('.');
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 24);
    const sc = el.closest && el.closest('[data-scene]');
    return `（${sc ? sc.dataset.scene + ' の ' : ''}<${s}>${text ? ' 「' + text + '」' : ''}）`;
  }

  // ───────────────────────── 検査（書き出し前のはみ出し確認） ─────────────────────────

  function lint() {
    const issues = [];
    const rec = state.current;
    if (!rec) return issues;
    const stageRect = state.comp.getBoundingClientRect();
    const W = stageRect.width, H = stageRect.height;
    const safeBottom = parseFloat(getComputedStyle(state.comp).getPropertyValue('--safe-bottom')) || 0;
    const reported = new Set();
    const texts = [];
    const underReported = (el) => { for (let p = el.parentElement; p && p !== rec.el; p = p.parentElement) if (reported.has(p)) return true; return false; };
    rec.el.querySelectorAll('*').forEach((el) => {
      if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) return;
      const cs = getComputedStyle(el);
      if (cs.display === 'none') return;
      if (cs.animationName && cs.animationName !== 'none') issues.push({ kind: 'css-animation', el: describe(el), message: 'CSS animation は時間に連動しません。data-anim か Motion.scene で動かしてください' });
      if (cs.transitionDuration && cs.transitionDuration.split(',').some((d) => parseFloat(d) > 0)) issues.push({ kind: 'css-transition', el: describe(el), message: 'CSS transition は書き出しで再現されません。外してください' });
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      // カメラで寄っている間の中身は、画面からはみ出して当然なので数えない
      const cam = el.closest('.camera');
      if (cam && cam.style.transform) return;
      if (underReported(el)) return;
      const x0 = r.left - stageRect.left, y0 = r.top - stageRect.top, x1 = x0 + r.width, y1 = y0 + r.height;
      if (x0 < -1 || y0 < -1 || x1 > W + 1 || y1 > H + 1) {
        reported.add(el);
        issues.push({ kind: 'offscreen', el: describe(el), message: `画面の外にはみ出しています（${Math.round(x0)},${Math.round(y0)}–${Math.round(x1)},${Math.round(y1)}）` });
        return;
      }
      const clipsX = cs.overflowX !== 'visible', clipsY = cs.overflowY !== 'visible';
      if ((clipsX && el.scrollWidth > el.clientWidth + 2) || (clipsY && el.scrollHeight > el.clientHeight + 2)) {
        reported.add(el);
        issues.push({ kind: 'clipped', el: describe(el), message: `中身が箱に収まらず切れています（${el.scrollWidth}×${el.scrollHeight} > ${el.clientWidth}×${el.clientHeight}）` });
        return;
      }
      const hasText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.nodeValue.trim());
      if (hasText) texts.push({ el, r });
      if (hasText && safeBottom && subtitlesOn() && rec.el.dataset.chrome !== 'none' && rec.tl.cues.length && y1 > H - safeBottom + 2) {
        reported.add(el);
        issues.push({ kind: 'safe-area', el: describe(el), message: '字幕の帯に文字が重なっています' });
      }
    });
    // 文字の箱どうしの重なり（親子は除く）
    for (let i = 0; i < texts.length; i++) {
      for (let j = i + 1; j < texts.length; j++) {
        const a = texts[i], b = texts[j];
        if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
        const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
        const hgt = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        // 行の上下の余白どうしが少し重なるだけのものは除く（小さいほうの箱の 1/4 以上で報告）
        const minH = Math.min(a.r.height, b.r.height), minW = Math.min(a.r.width, b.r.width);
        if (w > 4 && hgt > Math.max(4, minH * 0.25) && w > minW * 0.1) issues.push({ kind: 'overlap', el: describe(a.el) + ' と ' + describe(b.el), message: `文字が重なっています（${Math.round(w)}×${Math.round(hgt)}px）` });
      }
    }
    return issues;
  }

  // ───────────────────────── 起動 ─────────────────────────

  /** data-fit：箱に収まるまで文字を小さくする（下限は data-fit-min、既定 28px）。フォントが届いたらやり直す */
  function fitTexts() {
    state.comp.querySelectorAll('[data-fit]').forEach((el) => {
      if (el.dataset.fitBase == null) el.dataset.fitBase = parseFloat(getComputedStyle(el).fontSize);
      const min = Number(el.dataset.fitMin || 28);
      let size = Number(el.dataset.fitBase);
      el.style.fontSize = size + 'px';
      const scene = el.closest('[data-scene]');
      const shown = scene && getComputedStyle(scene).display !== 'none';
      if (!shown) scene.style.display = 'block';
      while (size > min && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)) {
        size -= 1;
        el.style.fontSize = size + 'px';
      }
      if (!shown) scene.style.display = '';
    });
  }

  // 必ず備わっていなければならない機能。check がこの一覧を確かめる（scripts/motion.mjs の REQUIRED と同じ）
  const KIT_PARTS = ['.runner', '.code', '.terminal', '.gantt', '.hbars', '.gauge', '.wave', '.tiles', '.camera'];
  function features() {
    const f = {
      boot: !!global.__motionBoot,
      composition: !!state.comp && state.comp.tagName === 'MAIN',
      scenes: state.scenes.length > 0 && state.scenes.length === (state.tl ? state.tl.scenes.length : -1),
      theme: !!state.comp && getComputedStyle(state.comp).getPropertyValue('--paper').trim() !== '',
      kit: KIT_PARTS.every((sel) => components.some((c) => c.selector === sel)),
      chapterBar: !!state.chapterBar,
      subtitles: !!state.subtitle,
      liveLayout: !!(state.live && state.live.stops.length >= state.scenes.length),
      transitions: TRANSITIONS.length === 8,
      fonts: !!document.fonts && Array.from(document.fonts).some((ff) => /JetBrains Mono/.test(ff.family) && ff.status === 'loaded'),
    };
    if (state.ui) {
      const ui = state.ui;
      Object.assign(f, {
        player: !!ui.app && !!ui.viewport && !!ui.stage,
        scrubber: !!ui.scrub,
        timelinePanel: !!ui.panel,
        modeToggle: !!ui.modeVideo && !!ui.modeLive,
        presenterView: typeof openNotes === 'function',
        narrationToggle: !!ui.voiceBtn && (!state.audio || !ui.voiceBtn.disabled),
        blackout: !!ui.blackout,
        help: !!ui.help,
        keyboard: !!state.keyboard,
      });
    }
    return f;
  }

  function buildChapterBar() {
    if (state.chapterBar) state.chapterBar.remove();
    const bar = h('div', { class: 'md-chapters' });
    state.chapterSegs = chapterList().map((c) => {
      const fill = h('div', { class: 'md-chapter-fill' });
      const el = h('div', { class: 'md-chapter' }, [h('div', { class: 'md-chapter-name', text: c.name }), h('div', { class: 'md-chapter-track' }, [fill])]);
      el.style.flex = String(c.frames);
      bar.appendChild(el);
      return { el, fill, start: c.start, frames: c.frames };
    });
    state.comp.insertBefore(bar, state.subtitle || null);
    state.chapterBar = bar;
  }

  function start() {
    const tl = global.MOTION_TIMELINE;
    state.comp = document.getElementById('composition');
    if (!state.comp) throw new Error('#composition がありません');
    if (!tl) {
      document.body.innerHTML = '<pre style="font:16px/1.6 monospace;padding:40px;color:#b00">timeline.js がありません。\nnode &lt;motion-deck&gt;/scripts/motion.mjs timeline を実行してください。</pre>';
      return;
    }
    state.tl = tl;
    state.fps = tl.fps;
    state.width = tl.width;
    state.height = tl.height;
    state.comp.style.width = tl.width + 'px';
    state.comp.style.height = tl.height + 'px';
    document.documentElement.classList.add(RENDER ? 'md-render' : 'md-player');

    const sections = Array.from(state.comp.querySelectorAll(':scope > [data-scene]'));
    const byId = new Map(sections.map((el) => [el.dataset.scene, el]));
    const videoScenes = [];
    tl.scenes.forEach((sc) => {
      const el = byId.get(sc.id);
      if (!el) { report(`シーン「${sc.id}」が index.html にありません（<section data-scene="${sc.id}">）`); return; }
      const rec = { el, tl: sc, tlVideo: sc, f: 0 };
      rec.ctx = makeContext(rec);
      state.scenes.push(rec);
      videoScenes.push(sc);
    });
    sections.forEach((el) => {
      if (!tl.scenes.some((s) => s.id === el.dataset.scene)) {
        report(`index.html のシーン「${el.dataset.scene}」が原稿（script.json）にありません。timeline を作り直してください`);
        el.style.display = 'none';
      }
    });
    if (!state.scenes.length) { report('表示できるシーンがありません'); return; }
    // 部品（kit.js など）を先に組み立てる。部品が作った要素の data-* も宣言的アニメーションとして扱う
    state.scenes.forEach((rec) => {
      rec.components = [];
      rec.needs = [];
      for (const comp of components) {
        rec.el.querySelectorAll(comp.selector).forEach((el) => {
          try {
            const r = comp.setup(el, rec.ctx);
            const update = typeof r === 'function' ? r : r && r.update ? r.update : null;
            if (update) rec.components.push({ el, update, name: comp.selector });
            if (r && r.needs) rec.needs.push(...r.needs);
          } catch (e) { report(`部品 ${comp.selector} の準備でエラー: ${e.message}${describe(el)}`); }
        });
      }
    });
    state.scenes.forEach((rec) => { rec.specs = parseSpecs(rec); });
    fitTexts();
    state.video = { total: tl.totalFrames, scenes: videoScenes };
    if (!RENDER && tl.audio) {
      const a = new Audio();
      a.preload = 'auto';
      a.src = tl.audio;
      a.addEventListener('error', () => report(`音声を読み込めません: ${tl.audio}`));
      state.audio = a;
    }
    state.liveNarration = !!state.audio && (params.has('narration') ? params.get('narration') !== '0' : store.get('liveNarration', false));
    state.live = buildLiveLayout();
    const mode = (params.get('mode') === 'live' || params.get('mode') === 'video') ? params.get('mode') : RENDER ? 'video' : store.get('mode', 'video');
    state.mode = mode;
    setLayout(mode);

    sceneSetups.forEach((setup, id) => {
      const rec = state.scenes.find((r) => r.tl.id === id);
      if (!rec) { report(`Motion.scene("${id}") に対応するシーンがありません`); return; }
      try {
        const r = setup(rec.ctx);
        rec.update = typeof r === 'function' ? r : r && r.update ? r.update : null;
      } catch (e) { report(`Motion.scene("${id}") の準備でエラー: ${e.message}`); }
    });

    // 字幕と章バー（ステージの中に置くので、書き出した動画にも入る）
    state.subtitleText = h('div', { class: 'md-subtitle-text' });
    state.subtitle = h('div', { class: 'md-subtitle' }, [state.subtitleText]);
    state.comp.appendChild(state.subtitle);
    if (state.comp.dataset.chapterBar != null && state.comp.dataset.chapterBar !== 'off') buildChapterBar();

    if (RENDER) {
      state.subtitles = params.get('subtitles') !== '0';
      state.subtitlesLive = params.get('subtitles') === '1';
      const ready = (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => { fitTexts(); return true; });
      global.__motion = {
        fps: state.fps, width: state.width, height: state.height, totalFrames: state.total,
        mode: state.mode,
        stops: state.stops.slice(),
        errors,
        scenes: state.scenes.map((r) => ({ id: r.tl.id, chapter: r.tl.chapter, start: r.tl.start, duration: r.tl.duration, cues: r.tl.cues.map((c) => ({ start: c.start, end: c.end, name: c.name || null })) })),
        ready,
        async seek(frame) {
          renderFrame(frame);
          if (document.fonts) await document.fonts.ready;
          const imgs = Array.from(state.current.el.querySelectorAll('img')).filter((i) => !i.complete);
          await Promise.all(imgs.map((i) => i.decode().catch(() => {})));
          // rAF は待たない（裏のタブでは止まるため）。描き直しはスクリーンショット側が行う
          return state.frame;
        },
        lint,
        features,
        /** PPTX 用：フレーム (from, to] のあいだに現れ始める要素（今の時間軸で）。to の絵の状態で測る */
        entering(from, to) {
          const out = [];
          const scale = state.comp.getBoundingClientRect().width / state.width || 1;
          const cr = state.comp.getBoundingClientRect();
          state.scenes.forEach((rec) => {
            const sc = rec.tl;
            if (to < sc.start || from >= sc.start + sc.duration) return;
            const picked = [];
            for (const sp of rec.specs) {
              if (sp.at == null || !sp.anims.length) continue;
              let cue;
              try { cue = resolveCue(rec, sp.at); } catch (e) { continue; }
              const begin = sc.start + cue.start + sp.delay;
              if (begin <= from || begin > to) continue;
              const el = sp.el;
              if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
              const r = el.getBoundingClientRect();
              if (!r.width && !r.height) continue; // 水平・垂直の線は幅か高さが 0
              const tween = sp.anims.some((a) => TWEEN_ANIMS.has(a));
              const dur = tween ? (sp.dur != null ? sp.dur : Math.max(15, cue.end - cue.start - sp.delay)) : 15;
              picked.push({ el, begin, anims: sp.anims.slice(), dur, rect: { x: (r.left - cr.left) / scale, y: (r.top - cr.top) / scale, w: r.width / scale, h: r.height / scale } });
            }
            // 同じステップで親も現れるなら、子は親の絵に含める
            picked.forEach((a) => {
              if (picked.some((b) => b !== a && b.el.contains(a.el))) return;
              a.el.dataset.pptxId = a.el.dataset.pptxId || 'p' + Math.round(random(out.length + ':' + a.begin) * 1e9);
              out.push({ id: a.el.dataset.pptxId, scene: sc.id, begin: a.begin, anims: a.anims, dur: a.dur, rect: a.rect, text: (a.el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 120) });
            });
          });
          return out.sort((a, b) => a.begin - b.begin);
        },
        /** PPTX 用：フレーム (from, to] のあいだに消える要素（data-until）。現れたときに付けた id で返す */
        exiting(from, to) {
          const out = [];
          state.scenes.forEach((rec) => {
            const sc = rec.tl;
            for (const sp of rec.specs) {
              if (sp.until == null || !sp.el.dataset.pptxId) continue;
              let cue;
              try { cue = resolveCue(rec, sp.until); } catch (e) { continue; }
              const end = sc.start + cue.start;
              if (end > from && end <= to + 10) out.push({ id: sp.el.dataset.pptxId, end });
            }
          });
          return out;
        },
        /** PPTX 用：シーンの切り替えと、各ステップに属する文 */
        sceneInfo() {
          return state.scenes.map((rec) => ({
            id: rec.tl.id, chapter: rec.tl.chapter, notes: rec.tl.notes || null,
            transition: rec.el.dataset.transition || 'fade', direction: rec.el.dataset.direction || 'left',
            start: rec.tl.start, duration: rec.tl.duration,
            cues: rec.tl.cues.map((c) => ({ text: c.text, note: c.note || null, start: rec.tl.start + c.start, end: rec.tl.start + c.end })),
          }));
        },
      };
      renderFrame(Number(params.get('frame') || 0));
      return;
    }

    state.subtitles = store.get('subtitles', true);
    state.subtitlesLive = store.get('subtitlesLive', false);
    state.muted = store.get('muted', false);
    state.rate = store.get('rate', 1);
    buildUI();
    if (document.fonts) document.fonts.ready.then(() => { fitTexts(); renderFrame(state.frame); });
    const m = /f=(\d+)/.exec(location.hash);
    if (m) renderFrame(Number(m[1]));
    else renderFrame(state.mode === 'live' ? state.stops[0] : 0);
    updateUI(true);
    global.__motionPlayer = {
      play, pause, seek, next, prev, goStep, setMode, openNotes,
      get frame() { return state.frame; },
      get mode() { return state.mode; },
      get stops() { return state.stops.slice(); },
      get step() { return stepIndex(); },
      get playing() { return state.playing; },
      get narration() { return state.liveNarration; },
      features,
      setNarration: setLiveNarration,
      get audioTime() { return state.audio ? state.audio.currentTime : null; },
      get audioPaused() { return state.audio ? state.audio.paused : null; },
      lint,
    };
  }

  global.Motion = {
    start,
    /** Motion.scene('id', (s) => (frame) => { ... }) — 準備を一度、更新を毎フレーム */
    scene(id, setup) {
      if (sceneSetups.has(id)) report(`Motion.scene("${id}") が二重に登録されています`);
      sceneSetups.set(id, setup);
    },
    /** Motion.component('.runner', (el, s) => (frame) => { ... }) — 全シーンの該当要素に付く部品。
     *  返り値を { update, needs: [{ at, frames }] } にすると、発表モードでその文の動きに必要な長さを伝えられる */
    component(selector, setup) { components.push({ selector, setup }); },
    /** 文の参照が正しいかを部品から確かめる */
    report,
    interpolate, interpolateColors, spring, measureSpring, Easing, clamp, random, noise,
    /** 実行の状況。static は PPTX 書き出しなどで待機中の揺れを止めるとき true */
    env: { render: RENDER, static: STATIC },
  };
})(window);
