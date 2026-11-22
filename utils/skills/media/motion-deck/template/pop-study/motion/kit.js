/*!
 * kit.js — Remotion で作った解説動画の部品を、HTML の要素として使えるようにする。
 * どれもフレームの関数（Motion.component）なので、動画・発表・書き出しで同じに動く。
 *
 *   <div class="runner" data-color="coral" data-hat></div>
 *   <pre class="code" data-title="main.go" data-lang="go" data-reveal="3:7-9" data-focus="2:4-5; 4:7">…</pre>
 *     （data-reveal / data-focus は「文:行」。文3で7〜9行目が出る、文2から4〜5行目を強調…）
 *   <div class="terminal" data-command="go run main.go" data-at="2"><div data-at="3">完了</div></div>
 *   <div class="gantt" data-max="20" data-ticks="0,5,10,15,20" data-unit="分">…</div>
 *   <div class="hbars" data-max="30">…</div>   <div class="gauge" …>   <div class="wave" …>   <div class="tiles" …>
 */
(function () {
  'use strict';
  const M = window.Motion;
  if (!M) throw new Error('kit.js は motion.js の後に読み込んでください');

  // 部品の字体（JetBrains Mono）を先に読み込む。書き出しは document.fonts.ready を待つので、絵に必ず効く
  if (document.fonts) ['400', '700'].forEach((w) => document.fonts.load(`${w} 40px "JetBrains Mono"`).catch(() => {}));

  const COLORS = { cyan: 'var(--cyan)', coral: 'var(--coral)', yellow: 'var(--yellow)', green: 'var(--green)', ink: 'var(--ink)', white: 'var(--white)', muted: 'var(--muted)' };
  const color = (v, d) => (v ? COLORS[v] || v : d);
  const num = (v, d) => (v == null || v === '' ? d : Number(v));
  const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  /** "2:4-5; 4:7" → [[2,[4,5]],[4,[7]]]（文:行の範囲）。文は番号か名前 */
  function parsePairs(spec) {
    if (!spec) return [];
    return spec.split(/[;,]\s*(?=[^:;,]+:)/).map((part) => {
      const [cue, lines] = part.split(':').map((x) => x.trim());
      const out = [];
      (lines || '').split(/[\s,]+/).filter(Boolean).forEach((r) => {
        const m = /^(\d+)(?:-(\d+))?$/.exec(r);
        if (!m) return;
        for (let i = Number(m[1]); i <= Number(m[2] || m[1]); i++) out.push(i);
      });
      return [cue, out];
    });
  }

  // ───────── 走者（Runner）：goroutine などを表すキャラクター ─────────
  M.component('.runner', (el, s) => {
    const size = num(el.dataset.size, 96);
    const fill = color(el.dataset.color, 'var(--cyan)');
    const hat = el.hasAttribute('data-hat');
    const sleepy = el.hasAttribute('data-sleepy');
    const still = el.hasAttribute('data-still');
    const seed = num(el.dataset.seed, 0);
    el.innerHTML = `<svg width="${size}" height="${size * 1.15}" viewBox="0 0 100 115">
      <g class="body">
        ${hat ? '<path d="M28 26 C14 20 18 2 34 7 C40 -4 62 -4 67 7 C84 2 87 20 72 26 Z" fill="var(--white)" stroke="var(--ink)" stroke-width="5"/>' : ''}
        <rect x="15" y="22" width="70" height="72" rx="32" fill="${fill}" stroke="var(--ink)" stroke-width="5"/>
        <circle cx="40" cy="52" r="11" fill="var(--white)" stroke="var(--ink)" stroke-width="4"/>
        <circle cx="66" cy="52" r="11" fill="var(--white)" stroke="var(--ink)" stroke-width="4"/>
        ${sleepy
          ? `<rect x="28" y="40" width="24" height="12" fill="${fill}"/><rect x="54" y="40" width="24" height="12" fill="${fill}"/>
             <line x1="29" y1="52" x2="51" y2="52" stroke="var(--ink)" stroke-width="4"/><line x1="55" y1="52" x2="77" y2="52" stroke="var(--ink)" stroke-width="4"/>`
          : '<circle cx="44" cy="53" r="5" fill="var(--ink)"/><circle cx="70" cy="53" r="5" fill="var(--ink)"/>'}
      </g>
      <line class="l1" x1="36" y1="96" x2="34" y2="111" stroke="var(--ink)" stroke-width="7" stroke-linecap="round"/>
      <line class="l2" x1="64" y1="96" x2="66" y2="111" stroke="var(--ink)" stroke-width="7" stroke-linecap="round"/>
    </svg>`;
    const body = el.querySelector('.body');
    const l1 = el.querySelector('.l1');
    const l2 = el.querySelector('.l2');
    return (frame) => {
      const moving = !still && !el.hasAttribute('data-still') && !M.env.static;
      const ph = Math.sin(frame / 3.2 + seed);
      body.setAttribute('transform', `translate(0 ${moving ? ph * 5 : 0})`);
      l1.setAttribute('x2', String(34 + (moving ? ph * 8 : 0)));
      l2.setAttribute('x2', String(66 - (moving ? ph * 8 : 0)));
    };
  });

  // ───────── コード（Code）：行の出現・強調・薄く ─────────
  const KEYWORDS = {
    go: 'package import func go defer for range var const chan return if else switch case select type struct interface map make new nil true false break continue',
    js: 'const let var function return if else for while of in new class extends import from export default async await try catch throw true false null undefined this',
    ts: 'const let var function return if else for while of in new class extends import from export default async await try catch throw true false null undefined this type interface implements',
    py: 'def return if elif else for while in import from as class with try except raise True False None and or not lambda async await pass yield',
    sh: 'if then else fi for do done while case esac function export',
    rs: 'fn let mut pub use mod struct enum impl trait match if else for while loop return async await move ref self Self true false',
  };
  const TYPES = 'string int int64 float64 bool byte error any number boolean void str float i32 i64 u8 usize String Vec Option Result';

  function highlightHtml(line) {
    const re = /(<!--.*?-->)|("[^"]*")|(<\/?[\w-]+|\/?>)|([\w-]+)(?==)/g;
    let out = '';
    let last = 0;
    for (const m of line.matchAll(re)) {
      out += esc(line.slice(last, m.index));
      const cls = m[1] ? 't-c' : m[2] ? 't-s' : m[3] ? 't-k' : 't-t';
      out += `<span class="${cls}">${esc(m[0])}</span>`;
      last = m.index + m[0].length;
    }
    return out + esc(line.slice(last));
  }

  function highlight(line, lang) {
    if (lang === 'html' || lang === 'xml') return highlightHtml(line);
    if (lang === 'text' || lang === 'plain') return esc(line);
    const kw = (KEYWORDS[lang] || KEYWORDS.go).split(' ').join('|');
    const comment = lang === 'py' || lang === 'sh' ? '#.*$' : '\\/\\/.*$';
    const re = new RegExp(`(${comment})|("(?:[^"\\\\]|\\\\.)*"|'(?:[^'\\\\]|\\\\.)*'|\`[^\`]*\`)|\\b(${kw})\\b|\\b(${TYPES.split(' ').join('|')})\\b|(<-|:=|=>)|\\b(\\d+(?:\\.\\d+)?)\\b|([A-Za-z_]\\w*)(?=\\()`, 'g');
    let out = '';
    let last = 0;
    for (const m of line.matchAll(re)) {
      out += esc(line.slice(last, m.index));
      const cls = m[1] ? 't-c' : m[2] ? 't-s' : m[3] ? 't-k' : m[4] ? 't-t' : m[5] ? 't-op' : m[6] ? 't-n' : 't-f';
      out += `<span class="${cls}">${esc(m[0])}</span>`;
      last = m.index + m[0].length;
    }
    return out + esc(line.slice(last));
  }

  M.component('.code', (el, s) => {
    const lang = el.dataset.lang || 'go';
    const src = el.textContent.replace(/^\n/, '').replace(/\n\s*$/, '');
    const lines = src.split('\n');
    const reveal = new Map(); // 行 → 文。data-reveal="文:行; 文:行"（data-focus と同じ書き方）
    parsePairs(el.dataset.reveal).forEach(([cue, ls]) => ls.forEach((n) => reveal.set(n, cue)));
    const focus = parsePairs(el.dataset.focus);
    if (el.dataset.size) el.style.setProperty('--code-size', el.dataset.size + 'px');
    if (el.dataset.width) el.style.width = el.dataset.width + 'px';
    const title = el.dataset.title;
    el.innerHTML = (title ? `<div class="code-title">${esc(title)}</div>` : '') +
      `<div class="code-body">${lines.map((l, i) => {
        const at = reveal.get(i + 1);
        return `<span class="ln"${at != null ? ` data-at="${at}" data-anim="fade" data-damping="22"` : ''}>${highlight(l, lang) || ' '}</span>`;
      }).join('')}</div>`;
    const lineEls = Array.from(el.querySelectorAll('.ln'));
    let last = null;
    return () => {
      let current = null;
      for (const [cue, ls] of focus) if (s.reached(cue)) current = ls;
      if (current === last) return;
      last = current;
      lineEls.forEach((ln, i) => {
        const on = current ? current.includes(i + 1) : false;
        ln.classList.toggle('is-focus', on);
        ln.classList.toggle('is-dim', !!current && !on);
      });
    };
  });

  // ───────── ターミナル（Terminal）：コマンドを打ち、出力を出す ─────────
  M.component('.terminal', (el, s) => {
    const command = el.dataset.command || '';
    const at = el.dataset.at != null ? el.dataset.at : 'start';
    const speed = num(el.dataset.typeSpeed, 1.2); // 1文字あたりのフレーム
    if (el.dataset.size) el.style.setProperty('--code-size', el.dataset.size + 'px');
    if (el.dataset.width) el.style.width = el.dataset.width + 'px';
    const outputs = Array.from(el.children);
    outputs.forEach((o) => {
      o.classList.add('out');
      if (o.dataset.at != null && !o.dataset.anim) { o.dataset.anim = 'fade'; o.dataset.damping = o.dataset.damping || '40'; }
    });
    const head = document.createElement('div');
    head.innerHTML = '<span class="prompt">$ </span><span class="cmd"></span><span class="cursor">▍</span>';
    el.insertBefore(head, el.firstChild);
    // ターミナル自体は data-at で出したくない（打つ前から枠は見せる）ので、外側の出現は data-show で指定する
    if (el.dataset.show != null) { el.dataset.at = el.dataset.show; el.dataset.anim = el.dataset.anim || 'up'; } else delete el.dataset.at;
    const cmd = head.querySelector('.cmd');
    const cursor = head.querySelector('.cursor');
    return {
      needs: [{ at, frames: command.length * speed + 12 }],
      update(frame) {
        const since = s.since(at);
        const n = Math.max(0, Math.min(command.length, Math.floor(since / speed)));
        const text = command.slice(0, n);
        if (cmd.textContent !== text) cmd.textContent = text;
        cursor.style.opacity = M.env.static || Math.floor(frame / 15) % 2 === 0 ? '1' : '0';
      },
    };
  });

  // ───────── 時間の帯（Timeline / ガント） ─────────
  M.component('.gantt', (el) => {
    const max = num(el.dataset.max, 10);
    const ticks = (el.dataset.ticks || '').split(',').filter(Boolean).map(Number);
    const unit = el.dataset.unit || '';
    const labelW = num(el.dataset.labelWidth, 200);
    const rowH = num(el.dataset.rowHeight, 88);
    const width = num(el.dataset.width, el.clientWidth || 1600);
    const rows = Array.from(el.querySelectorAll(':scope > .g-row, :scope > [data-label]'));
    const track = width - labelW;
    const x = (t) => (t / max) * track;
    const height = rows.length * rowH;
    el.style.width = width + 'px';
    el.style.height = height + 64 + 'px';
    ticks.forEach((t) => {
      const g = document.createElement('div');
      g.className = 'g-grid';
      Object.assign(g.style, { left: labelW + x(t) + 'px', height: height + 8 + 'px' });
      const lb = document.createElement('div');
      lb.className = 'g-tick';
      lb.textContent = t + unit;
      Object.assign(lb.style, { left: labelW + x(t) + 'px', top: height + 14 + 'px' });
      el.insertBefore(lb, el.firstChild);
      el.insertBefore(g, el.firstChild);
    });
    rows.forEach((row, i) => {
      row.classList.add('g-row');
      Object.assign(row.style, { top: i * rowH + 'px', height: rowH + 'px' });
      if (row.dataset.label && !row.querySelector('.g-label')) {
        const lb = document.createElement('div');
        lb.className = 'g-label';
        lb.textContent = row.dataset.label;
        Object.assign(lb.style, { width: labelW - 20 + 'px', lineHeight: rowH + 'px' });
        row.insertBefore(lb, row.firstChild);
      }
      row.querySelectorAll('.bar').forEach((bar) => {
        const a = num(bar.dataset.start, 0), b = num(bar.dataset.end, max);
        Object.assign(bar.style, { left: labelW + x(a) + 'px', width: x(b) - x(a) + 'px', top: '12px', height: rowH - 24 + 'px' });
        if (bar.dataset.color) bar.style.backgroundColor = color(bar.dataset.color);
        if (bar.hasAttribute('data-hatch')) bar.classList.add('hatch');
        if (bar.textContent.trim() && !bar.querySelector('span')) bar.innerHTML = `<span>${bar.innerHTML}</span>`;
      });
    });
  });

  // ───────── 横棒グラフ（GrowBar） ─────────
  M.component('.hbars', (el) => {
    const max = num(el.dataset.max, 1);
    const width = num(el.dataset.width, 1500);
    const labelW = num(el.dataset.labelWidth, 330);
    const track = width - labelW - 260;
    el.style.width = width + 'px';
    el.style.setProperty('--label-w', labelW + 'px');
    Array.from(el.children).forEach((row) => {
      row.classList.add('hbar');
      const value = num(row.dataset.value, 0);
      const at = row.dataset.at;
      const delay = row.dataset.delay || 0;
      const text = row.innerHTML;
      row.innerHTML = '';
      const label = document.createElement('div');
      label.className = 'hb-label';
      label.textContent = row.dataset.label || '';
      const bar = document.createElement('div');
      bar.className = 'hb-bar' + (row.hasAttribute('data-hatch') ? ' hatch' : '');
      bar.style.width = Math.max(8, (value / max) * track) + 'px';
      bar.style.backgroundColor = color(row.dataset.color, 'var(--cyan)');
      const val = document.createElement('div');
      val.className = 'hb-value';
      val.innerHTML = text;
      row.append(label, bar, val);
      if (at != null) {
        // 行は文の開始で出て、棒は文の長さで伸び、値は伸びきる頃に出る
        delete row.dataset.at;
        label.dataset.at = at; label.dataset.anim = 'fade'; label.dataset.delay = delay;
        bar.dataset.at = at; bar.dataset.anim = 'grow'; bar.dataset.delay = delay; bar.dataset.dur = row.dataset.dur || 24;
        val.dataset.at = at; val.dataset.anim = 'fade'; val.dataset.delay = Number(delay) + Number(row.dataset.dur || 24) - 6;
      }
    });
  });

  // ───────── ゲージ（Gauge） ─────────
  M.component('.gauge', (el) => {
    const value = num(el.dataset.value, 0), max = num(el.dataset.max, 1);
    const unit = el.dataset.unit || '';
    const at = el.dataset.at != null ? el.dataset.at : 'start';
    const dec = (String(el.dataset.value).split('.')[1] || '').length;
    if (el.dataset.width) el.style.width = el.dataset.width + 'px';
    el.innerHTML = `<div class="gg-head"><div class="gg-label">${esc(el.dataset.label || '')}</div>
      <div class="gg-value"><span data-at="${at}" data-anim="count" data-to="${value.toFixed(dec)}" data-format="plain" data-dur="26">0</span><small> / ${max} ${esc(unit)}</small></div></div>
      <div class="gg-track"><div class="gg-fill" data-at="${at}" data-anim="grow" data-dur="26" style="width:${(value / max) * 100}%;background:${color(el.dataset.color, 'var(--green)')}"></div></div>`;
    el.dataset.anim = el.dataset.anim || 'fade';
  });

  // ───────── 波形の飾り（Wave） ─────────
  M.component('.wave', (el) => {
    const bars = num(el.dataset.bars, 40);
    const seed = num(el.dataset.seed, 0);
    const level = num(el.dataset.level, 1);
    const h = num(el.dataset.height, el.clientHeight || 60);
    el.style.height = h + 'px';
    if (el.dataset.width) el.style.width = el.dataset.width + 'px';
    if (el.dataset.color) el.style.setProperty('--wave', color(el.dataset.color));
    el.innerHTML = '<i></i>'.repeat(bars);
    const items = Array.from(el.children);
    const still = el.hasAttribute('data-still');
    return (frame) => {
      const f = still || M.env.static ? 0 : frame;
      items.forEach((it, i) => {
        const v = 0.25 + 0.75 * Math.abs(Math.sin(i * 0.9 + seed) * 0.6 + Math.sin(f / 5 + i * 0.45 + seed) * 0.4) * level;
        it.style.height = Math.max(6, v * h) + 'px';
      });
    };
  });

  // ───────── 升目（data-at の文の長さで左上から埋まる） ─────────
  M.component('.tiles', (el, s) => {
    const count = num(el.dataset.count, 32);
    const cols = num(el.dataset.cols, 16);
    const from = el.dataset.fill != null ? el.dataset.fill : null; // 埋め始める文
    const to = el.dataset.fillTo != null ? el.dataset.fillTo : from;
    el.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
    if (el.dataset.color) el.style.setProperty('--tile', color(el.dataset.color));
    if (el.dataset.width) el.style.width = el.dataset.width + 'px';
    el.innerHTML = '<i></i>'.repeat(count);
    const items = Array.from(el.children);
    let last = -1;
    return {
      needs: from != null ? [{ at: from, frames: 40 }] : [],
      update() {
        const p = from == null ? 1 : s.progress(from, to);
        const n = Math.round(p * count);
        if (n === last) return;
        last = n;
        items.forEach((it, i) => it.classList.toggle('on', i < n));
      },
    };
  });

  // ───────── カメラ：文に合わせて、中の要素に寄る・引く ─────────
  //   <div class="camera" data-shots="2:#line5:1.6; 4:reset">…</div>
  //   「文:寄る先の要素:倍率」を ; で並べる。reset で全体に戻る。動きは約0.8秒のばね。
  M.component('.camera', (el, s) => {
    el.style.transformOrigin = '0 0';
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    const W = () => el.offsetWidth, H = () => el.offsetHeight;
    const rel = (t) => {
      let x = 0, y = 0;
      for (let n = t; n && n !== el; n = n.offsetParent) { x += n.offsetLeft; y += n.offsetTop; }
      return { x: x + t.offsetWidth / 2, y: y + t.offsetHeight / 2 };
    };
    const shots = (el.dataset.shots || '').split(';').map((p) => p.trim()).filter(Boolean).map((p) => {
      const [cue, target, scale] = p.split(':').map((x) => x.trim());
      if (target === 'reset' || !target) return { cue, reset: true };
      const t = el.querySelector(target);
      if (!t) { M.report(`カメラの寄る先「${target}」がありません`); return null; }
      return { cue, t, k: Number(scale || 1.5) };
    }).filter(Boolean);
    const view = (sh) => {
      if (!sh || sh.reset) return { tx: 0, ty: 0, k: 1 };
      const c = rel(sh.t);
      return { tx: W() / 2 - sh.k * c.x, ty: H() / 2 - sh.k * c.y, k: sh.k };
    };
    return {
      needs: shots.map((sh) => ({ at: sh.cue, frames: 26 })),
      update() {
        let i = -1;
        shots.forEach((sh, j) => { if (s.reached(sh.cue)) i = j; });
        const a = view(shots[i - 1]), b = view(shots[i]);
        const p = i < 0 ? 1 : M.spring({ frame: s.since(shots[i].cue), fps: s.fps, config: { damping: 200 }, durationInFrames: 24 });
        const tx = a.tx + (b.tx - a.tx) * p, ty = a.ty + (b.ty - a.ty) * p, k = a.k + (b.k - a.k) * p;
        el.style.transform = k === 1 && tx === 0 && ty === 0 ? '' : `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) scale(${k.toFixed(4)})`;
      },
    };
  });
})();
