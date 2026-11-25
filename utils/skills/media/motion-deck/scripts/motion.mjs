#!/usr/bin/env node
// motion.mjs — motion-deck のコマンド。Node 22 以上（WebSocket を使う）、npm の依存なし。
// 外部コマンド: ffmpeg（音声の連結・動画）、Chrome 系ブラウザ（検査・静止画・動画）、
// uv + local-tts スキル（ナレーション）。
//
//   node motion.mjs <command> [deck] [options]
//
// command: init | runtime | check | ssml | synth | timeline | still | render | pdf | pptx | bundle | extract
// 外部コマンド（extract のみ）: LibreOffice（元のスライドの絵。画面は出さない）

import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { buildPptx, effectFor, writeZip } from './pptx.mjs';

const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SAMPLE_RATE = 48000;

// ───────────────────────── 共通 ─────────────────────────

class UserError extends Error {}
const fail = (msg) => { throw new UserError(msg); };
const log = (...a) => console.log(...a);
const warn = (...a) => console.warn('⚠', ...a);
const now = () => new Date().toTimeString().slice(0, 8);

function parseArgs(argv) {
  const pos = [];
  const opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const [k, v] = a.slice(2).split('=', 2);
      if (v !== undefined) opt[k] = v;
      else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) opt[k] = argv[++i];
      else opt[k] = true;
    } else pos.push(a);
  }
  return { pos, opt };
}

const exists = (p) => fs.existsSync(p);
const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const writeJSON = (p, v) => { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, JSON.stringify(v, null, 2) + '\n'); };
const sha = (s) => createHash('sha256').update(s).digest('hex').slice(0, 16);
const which = (cmd) => {
  const r = spawnSync(process.platform === 'win32' ? 'where' : 'which', [cmd], { encoding: 'utf8' });
  return r.status === 0 ? r.stdout.split(/\r?\n/)[0].trim() : null;
};

function deckPaths(dir) {
  const root = path.resolve(dir || '.');
  return {
    root,
    script: path.join(root, 'script.json'),
    lexicon: path.join(root, 'lexicon.json'),
    index: path.join(root, 'index.html'),
    timeline: path.join(root, 'timeline.js'),
    ssmlDir: path.join(root, 'build', 'ssml'),
    sceneAudio: path.join(root, 'narration', 'scenes'),
    narrationWav: path.join(root, 'narration', 'narration.wav'),
    narrationM4a: path.join(root, 'narration', 'narration.m4a'),
    narrationMeta: path.join(root, 'narration', 'narration.json'),
    out: path.join(root, 'out'),
  };
}

// ───────────────────────── 原稿 ─────────────────────────

function loadScript(P) {
  if (!exists(P.script)) fail(`script.json がありません: ${P.script}\n  新しく作るなら: node "${path.join(SKILL, 'scripts/motion.mjs')}" init <フォルダ>`);
  let raw;
  try { raw = readJSON(P.script); } catch (e) { fail(`script.json を読めません: ${e.message}`); }
  const s = {
    title: raw.title || path.basename(P.root),
    fps: raw.fps || 30,
    width: raw.width || 1920,
    height: raw.height || 1080,
    voice: raw.voice || null,
    engine: raw.engine || null,
    pause: raw.pause != null ? raw.pause : 350,
    leadIn: raw.leadIn != null ? raw.leadIn : 0.6,
    tail: raw.tail != null ? raw.tail : 1.0,
    charsPerSecond: raw.charsPerSecond || 7,
    format: raw.format || null,
    scenes: [],
  };
  if (s.format != null && s.format !== 'pptx') fail(`script.json の format「${s.format}」は使えません（PPTX専用のデッキなら "pptx"、通常のデッキなら書かない）`);
  if (!Array.isArray(raw.scenes) || !raw.scenes.length) fail('script.json の scenes が空です');
  const ids = new Set();
  raw.scenes.forEach((sc, i) => {
    if (!sc.id || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(sc.id)) fail(`scenes[${i}] の id「${sc.id}」は英数字・-・_ にしてください`);
    if (ids.has(sc.id)) fail(`シーン id「${sc.id}」が重複しています`);
    ids.add(sc.id);
    const names = new Set();
    const lines = (sc.lines || []).map((l, j) => {
      const line = typeof l === 'string' ? { text: l } : Object.assign({}, l);
      if (!line.text || typeof line.text !== 'string') fail(`${sc.id} の文 ${j} に text がありません`);
      if (line.name != null) {
        if (/^-?\d+$/.test(String(line.name)) || ['start', 'end'].includes(line.name)) fail(`${sc.id} の文 ${j}: name「${line.name}」は使えません（数字・start・end 以外に）`);
        if (names.has(line.name)) fail(`${sc.id}: 文の name「${line.name}」が重複しています`);
        names.add(line.name);
      }
      return line;
    });
    if (!lines.length && !sc.duration) fail(`シーン「${sc.id}」には lines か duration（秒）が必要です`);
    s.scenes.push({
      id: sc.id,
      chapter: sc.chapter || '',
      lines,
      duration: sc.duration || 0,
      hold: sc.hold || 0,
      leadIn: sc.leadIn != null ? sc.leadIn : s.leadIn,
      tail: sc.tail != null ? sc.tail : s.tail,
      notes: sc.notes ? String(sc.notes) : null,
    });
  });
  return s;
}

/** PPTX専用のデッキ（script.json の format が pptx）では使えないコマンドを止める */
function notForPptx(script, cmd, why) {
  if (script.format === 'pptx') fail(`${cmd} は PPTX専用のデッキでは使えません（${why}）。書き出しは pptx を使ってください`);
}

function loadLexicon(P) {
  if (!exists(P.lexicon)) return {};
  try { return readJSON(P.lexicon); } catch (e) { fail(`lexicon.json を読めません: ${e.message}`); }
}

function makeSpoken(lexicon) {
  const keys = Object.keys(lexicon).sort((a, b) => b.length - a.length);
  const esc = keys.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = keys.length ? new RegExp(`(?<![A-Za-z])(?:${esc.join('|')})(?![A-Za-z])`, 'g') : null;
  return (line) => {
    const base = line.say != null ? line.say : re ? line.text.replace(re, (m) => lexicon[m]) : line.text;
    return base.replace(/[「」『』]/g, '').replace(/\s+/g, ' ').trim();
  };
}

/** 読み上げる文の検査。errors は合成前に直す、warnings は聞いて確かめる */
function inspectSpoken(script, spoken, opts = {}) {
  const errors = [];
  const warnings = [];
  for (const sc of script.scenes) {
    sc.lines.forEach((line, i) => {
      const t = spoken(line);
      const where = `${sc.id} 文${i}`;
      if (!t) errors.push(`${where}: 読み上げる文が空です`);
      if (t.length > 300) errors.push(`${where}: ${t.length}文字。300文字以下に分けてください`);
      const latin = t.match(/[A-Za-z][A-Za-z0-9.+#'-]*/g);
      if (latin && !opts.allowLatin) errors.push(`${where}: 英字「${[...new Set(latin)].join('」「')}」が残っています。lexicon.json に読みを足すか、文に "say" を書いてください`);
      const digits = t.match(/\d[\d,.]*/g);
      if (digits) warnings.push(`${where}: 数字「${digits.join('」「')}」は読みが揺れやすい。漢数字やかなにするか、聞いて確かめてください`);
      if (/[→←⇒※＊*/\\|<>&]/.test(t)) warnings.push(`${where}: 記号が含まれます（${t.match(/[→←⇒※＊*/\\|<>&]/g).join('')}）。言葉に置き換えると安定します`);
    });
  }
  return { errors, warnings };
}

const xml = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function sceneSSML(script, sc, spoken) {
  const parts = sc.lines.map((line, i) => {
    const pause = line.pause != null ? line.pause : script.pause;
    const brk = i < sc.lines.length - 1 && pause > 0 ? `\n  <break time="${pause}ms"/>` : '';
    return `  <mark name="c${i}"/><s>${xml(spoken(line))}</s><mark name="c${i}e"/>${brk}`;
  });
  return `<?xml version="1.0" encoding="UTF-8"?>\n<speak xmlns="http://www.w3.org/2001/10/synthesis" version="1.1" xml:lang="ja-JP">\n${parts.join('\n')}\n</speak>\n`;
}

function ttsSettings(script, opt) {
  // ナレーションは常に local-tts（このPCの音声合成）で作る
  return {
    tts: 'local',
    voice: opt.voice || script.voice || null,
    engine: opt.engine || script.engine || null,
  };
}

const sceneHash = (ssml, t) => sha([ssml, t.tts, t.voice || '', t.engine || ''].join('\n'));

// ───────────────────────── 必ず備わる機能 ─────────────────────────

const BOOT_TAG = /<script\s+src=["']motion\/boot\.js["'][^>]*><\/script>/g;
const PLAYER_REQUIRED = ['player', 'scrubber', 'timelinePanel', 'modeToggle', 'presenterView', 'narrationToggle', 'blackout', 'help', 'keyboard', 'editPanel'];
const REQUIRED = ['boot', 'composition', 'scenes', 'theme', 'kit', 'chapterBar', 'subtitles', 'liveLayout', 'transitions', 'fonts'];

// PPTX専用のデッキで使えない、時間・文番号で見た目が変わる data-* 属性（runtime/motion.js・kit.js が読むもの）
const PPTX_TIMED = [
  // 宣言的な動き（出る・消える・強調・待機中の動き・線に沿った移動・数え上げ）
  'data-at', 'data-anim', 'data-until', 'data-active', 'data-delay', 'data-dur', 'data-ease', 'data-damping', 'data-mass', 'data-stiffness',
  'data-out', 'data-loop', 'data-loop-speed', 'data-stagger', 'data-follow', 'data-follow-rotate', 'data-anchor', 'data-to', 'data-from', 'data-format',
  // 部品の時間の指定（コードの行、ターミナル、升目、カメラ）
  'data-reveal', 'data-focus', 'data-show', 'data-type-speed', 'data-fill', 'data-fill-to', 'data-shots',
  // シーンの切り替えと発表のステップ
  'data-transition', 'data-direction', 'data-enter', 'data-exit', 'data-timing', 'data-live-step',
];

function bootLists() {
  const src = fs.readFileSync(path.join(SKILL, 'runtime', 'boot.js'), 'utf8');
  const arr = (name) => JSON.parse(new RegExp(`var ${name} = (\\[[^\\]]*\\]);`).exec(src)[1].replace(/'/g, '"'));
  return { css: arr('CSS'), js: arr('JS') };
}

// deck/motion/ に配るもの：実行系（ロジック）＋外枠の機能の見た目（base）＋テンプレートの見た目（既定は default）
const DEFAULT_TEMPLATE = 'default';

/** テンプレートの名前を確かめて、そのフォルダを返す */
function templateDir(name) {
  const dir = path.join(SKILL, 'template', name);
  if (name === 'base' || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(name) || !exists(path.join(dir, 'motion')) || !exists(path.join(dir, 'deck'))) {
    const names = fs.readdirSync(path.join(SKILL, 'template')).filter((n) => n !== 'base' && exists(path.join(SKILL, 'template', n, 'deck')));
    fail(`テンプレート「${name}」がありません（使えるもの: ${names.join(', ')}）`);
  }
  return dir;
}

/** <main id="composition"> の data-chapter-bar の値（属性がなければ null、値がなければ ''） */
function chapterBarAttr(html) {
  const tag = /<[a-zA-Z][^>]*\sid=["']composition["'][^>]*>/.exec(html.replace(/<!--[\s\S]*?-->/g, ''));
  const m = tag && /\sdata-chapter-bar(?:\s*=\s*["']([^"']*)["'])?/.exec(tag[0]);
  return m ? (m[1] ?? '') : null;
}

/** テンプレートの雛形（deck/index.html）が章バーを使うか。data-chapter-bar="off" なら使わない */
function templateHasChapterBar(name) {
  const v = chapterBarAttr(fs.readFileSync(path.join(templateDir(name), 'deck', 'index.html'), 'utf8'));
  return v != null && v !== 'off';
}

/** デッキが使うテンプレート（script.json の template。書いていなければ default） */
function deckTemplate(P) {
  let name = DEFAULT_TEMPLATE;
  if (exists(P.script)) { try { name = readJSON(P.script).template || DEFAULT_TEMPLATE; } catch { /* 読めない script.json は loadScript が知らせる */ } }
  return name;
}

const motionSources = (name) => [
  path.join(SKILL, 'runtime'),
  path.join(SKILL, 'template', 'base'),
  path.join(templateDir(name), 'motion'),
];

const walkFiles = (dir, rel = '') => fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walkFiles(path.join(dir, e.name), rel + e.name + '/') : [rel + e.name]);

/** motion/ の中の相対パス → スキル側の元のファイル。同じ名前が2か所にあればエラー */
function motionFiles(name) {
  const map = new Map();
  for (const dir of motionSources(name)) {
    for (const f of walkFiles(dir)) {
      if (map.has(f)) fail(`motion/${f} が2か所にあります: ${map.get(f)} と ${path.join(dir, f)}`);
      map.set(f, path.join(dir, f));
    }
  }
  return map;
}

/** motion/ を配る（既にあるファイルは上書き） */
function copyMotion(P) {
  for (const [f, src] of motionFiles(deckTemplate(P))) {
    const dst = path.join(P.root, 'motion', f);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.copyFileSync(src, dst);
  }
}

/** deck/motion/ がスキルの runtime/ ＋ template/base/ ＋ デッキのテンプレートの motion/ と完全に同じか（版の照合） */
function runtimeDrift(P) {
  const out = [];
  for (const [f, a] of motionFiles(deckTemplate(P))) {
    const b = path.join(P.root, 'motion', f);
    if (!exists(b)) out.push(`${f}（ない）`);
    else if (sha(fs.readFileSync(a)) !== sha(fs.readFileSync(b))) out.push(`${f}（違う）`);
  }
  return out;
}

// ───────────────────────── init / runtime ─────────────────────────

function copyDir(src, dst, overwrite) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dst, e.name);
    if (e.isDirectory()) copyDir(s, d, overwrite);
    else if (overwrite || !exists(d)) fs.copyFileSync(s, d);
  }
}

function cmdInit(pos, opt) {
  const P = deckPaths(pos[0] || fail('作るフォルダを指定してください: init <フォルダ>'));
  if (exists(P.index) || exists(P.script)) fail(`${P.root} には既にデッキがあります（index.html / script.json）`);
  const name = opt.template ? String(opt.template) : DEFAULT_TEMPLATE;
  const format = opt.format ? String(opt.format) : null;
  if (format != null && format !== 'pptx') fail(`--format「${format}」は使えません（PPTX専用のデッキなら --format pptx）`);
  // PPTX専用のデッキは deck-pptx/ から配る
  const src = path.join(templateDir(name), format === 'pptx' ? 'deck-pptx' : 'deck');
  if (!exists(src)) fail(`テンプレート「${name}」には PPTX専用の雛形（template/${name}/deck-pptx/）がありません`);
  copyDir(src, P.root, false);
  if (name !== DEFAULT_TEMPLATE || format) {
    const s = readJSON(P.script);
    writeJSON(P.script, { title: s.title, ...(name !== DEFAULT_TEMPLATE ? { template: name } : {}), ...(format ? { format } : {}), ...s });
  }
  copyMotion(P);
  if (opt.title) {
    const s = readJSON(P.script);
    s.title = opt.title;
    writeJSON(P.script, s);
    const html = fs.readFileSync(P.index, 'utf8').replace(/<title>[^<]*<\/title>/, `<title>${xml(opt.title)}</title>`);
    fs.writeFileSync(P.index, html);
  }
  log(`作成しました: ${P.root}`);
  cmdTimeline([P.root], {});
  log(`\nブラウザで開く: open "${P.index}"`);
}

function cmdRuntime(pos) {
  const P = deckPaths(pos[0]);
  if (!exists(P.index)) fail(`${P.index} がありません`);
  copyMotion(P);
  log(`実行系を更新しました: ${path.join(P.root, 'motion')}`);
  // 古い書き方（個別の読み込み）を boot.js の1行に直す
  let html = fs.readFileSync(P.index, 'utf8');
  const before = html;
  html = html.replace(/[ \t]*<link[^>]+href=["'](?:motion\/(?:motion|kit)\.css|theme\.css)["'][^>]*>\n?/g, '')
    .replace(/[ \t]*<script[^>]+src=["'](?:motion\/(?:motion|kit)\.js|timeline\.js|scenes\.js)["'][^>]*><\/script>\n?/g, '')
    .replace(/[ \t]*<script>\s*Motion\.start\(\);?\s*<\/script>\n?/g, '');
  if (!BOOT_TAG.test(html)) html = html.replace('</body>', '<script src="motion/boot.js"></script>\n</body>');
  BOOT_TAG.lastIndex = 0;
  if (html !== before) { fs.writeFileSync(P.index, html); log('index.html の読み込みを boot.js の1行に直しました'); }
}

// ───────────────────────── ssml ─────────────────────────

function cmdSsml(pos, opt) {
  const P = deckPaths(pos[0]);
  const script = loadScript(P);
  const spoken = makeSpoken(loadLexicon(P));
  const { errors, warnings } = inspectSpoken(script, spoken, { allowLatin: !!opt['allow-latin'] });
  warnings.forEach((w) => warn(w));
  if (errors.length) fail('読み上げ文に問題があります:\n  ' + errors.join('\n  '));
  fs.mkdirSync(P.ssmlDir, { recursive: true });
  let chars = 0;
  for (const sc of script.scenes) {
    if (!sc.lines.length) continue;
    fs.writeFileSync(path.join(P.ssmlDir, `${sc.id}.ssml`), sceneSSML(script, sc, spoken));
    chars += sc.lines.reduce((a, l) => a + spoken(l).length, 0);
  }
  log(`SSML: ${P.ssmlDir}（${script.scenes.filter((s) => s.lines.length).length}シーン、読み上げ ${chars} 文字）`);
  return { script, spoken, chars };
}

// ───────────────────────── synth ─────────────────────────

function findSkill(name, opt) {
  const cands = [
    opt && opt[name],
    process.env[`MOTION_${name.replace('-', '_').toUpperCase()}`],
    path.join(SKILL, '..', name),
    path.join(process.cwd(), '.claude', 'skills', name),
    path.join(os.homedir(), '.claude', 'skills', name),
  ].filter(Boolean);
  return cands.find((c) => exists(path.join(c, 'SKILL.md'))) || null;
}

function run(cmd, args, what) {
  const r = spawnSync(cmd, args, { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (r.error) fail(`${what}: ${r.error.message}`);
  if (r.status !== 0) fail(`${what} に失敗しました（終了コード ${r.status}）\n${(r.stderr || r.stdout || '').trim().split('\n').slice(-15).join('\n')}`);
  return r.stdout;
}

function needFfmpeg() { if (!which('ffmpeg')) fail('ffmpeg が見つかりません（brew install ffmpeg）'); }

const SECONDS_PER_CHAR = { 'qwen3-tts': 0.22, voxcpm2: 0.33, omnivoice: 0.3, s2: 1.7, voicevox: 0.05 };

function cmdSynth(pos, opt) {
  const P = deckPaths(pos[0]);
  notForPptx(loadScript(P), 'synth', 'ナレーションの音声を作らないため');
  const { script, spoken } = cmdSsml(pos, opt);
  const t = ttsSettings(script, opt);
  const only = opt.scenes ? new Set(String(opt.scenes).split(',')) : null;
  if (only) for (const id of only) if (!script.scenes.some((s) => s.id === id)) fail(`シーン「${id}」は script.json にありません`);
  fs.mkdirSync(P.sceneAudio, { recursive: true });

  const todo = [];
  const mixed = [];
  for (const sc of script.scenes) {
    if (!sc.lines.length) continue;
    const ssml = fs.readFileSync(path.join(P.ssmlDir, `${sc.id}.ssml`), 'utf8');
    const hash = sceneHash(ssml, t);
    const metaPath = path.join(P.sceneAudio, `${sc.id}.json`);
    const meta = exists(metaPath) ? readJSON(metaPath).motion : null;
    if (meta && (meta.voice !== t.voice || meta.engine !== t.engine)) mixed.push(`${sc.id}（${meta.voice || '既定'}/${meta.engine || '既定'}）`);
    const fresh = meta && meta.hash === hash && exists(path.join(P.sceneAudio, `${sc.id}.wav`));
    if ((only ? only.has(sc.id) : !fresh) || (opt.force && (!only || only.has(sc.id)))) todo.push({ sc, ssml, hash, chars: sc.lines.reduce((a, l) => a + spoken(l).length, 0) });
  }
  if (mixed.length && !only) warn(`次のシーンは別の声・エンジンで作られています。声をそろえるならそれらも作り直されます: ${mixed.join(', ')}`);
  if (!todo.length) { log('すべてのシーンの音声が最新です。'); return; }
  const est = todo.reduce((a, x) => a + x.chars, 0) * (SECONDS_PER_CHAR[t.engine || 'qwen3-tts'] || 0.5) + 30;
  log(`合成（local-tts）: ${todo.length}シーン、${todo.reduce((a, x) => a + x.chars, 0)}文字。voice=${t.voice || '既定'} engine=${t.engine || '既定'}`);
  log(`目安: 約${Math.ceil(est / 60)}分`);
  if (opt['dry-run']) { todo.forEach((x) => log(`  ${x.sc.id}（${x.chars}文字）`)); return; }

  const localTts = findSkill('local-tts', opt);
  if (!localTts) fail('local-tts スキルが見つかりません。--local-tts <フォルダ> で指定してください');
  if (!which('uv')) fail('uv が見つかりません');

  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'motion-synth-'));
  let used = t.engine; // 停止コマンドに付けるエンジン。speak が出す実際のエンジン（既定を含む）で置き換える
  try {
    for (const x of todo) {
      const started = Date.now();
      log(`[synth] ${now()} ${x.sc.id}（${x.chars}文字）`);
      const wav = path.join(P.sceneAudio, `${x.sc.id}.wav`);
      const jsonPath = path.join(P.sceneAudio, `${x.sc.id}.json`);
      const tmpWav = path.join(tmpRoot, `${x.sc.id}.wav`);
      const args = ['run', '--project', path.join(localTts, 'tools'), 'local-tts', 'speak', path.join(P.ssmlDir, `${x.sc.id}.ssml`), '--output', tmpWav, '--force'];
      if (t.voice) args.push('--voice', t.voice);
      if (t.engine) args.push('--engine', t.engine);
      const out = run('uv', args, `local-tts（${x.sc.id}）`);
      try { used = JSON.parse(out.slice(out.indexOf('{'))).engine || used; } catch { /* 出力が読めなければ指定のエンジンのまま */ }
      const timing = readJSON(tmpWav.replace(/\.wav$/, '.json'));
      fs.copyFileSync(tmpWav, wav);
      const names = new Set((timing.marks || []).map((m) => m.name));
      const missing = x.sc.lines.map((_, i) => [`c${i}`, `c${i}e`]).flat().filter((n) => !names.has(n));
      if (missing.length) fail(`${x.sc.id}: 時刻の印 ${missing.join(', ')} が音声の結果にありません`);
      timing.motion = { hash: x.hash, tts: t.tts, voice: t.voice, engine: t.engine, created: new Date().toISOString() };
      writeJSON(jsonPath, timing);
      log(`        ${timing.audio_seconds.toFixed(1)}秒の音声（${((Date.now() - started) / 1000).toFixed(0)}秒かかりました）`);
    }
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
  log('合成が終わりました。続けて timeline を実行してください。');
  // 停止はこのツールが起動したサーバーだけ案内する。別に起動されたサーバーはほかのセッションが使っているかもしれない
  const status = used ? run('uv', ['run', '--project', path.join(localTts, 'tools'), 'local-tts', 'server', 'status', '--engine', used], 'local-tts server status') : '';
  if (/started elsewhere/.test(status)) log('別に起動されたサーバーなので止めていません。');
  else log(`使い終わったらエンジンを止める: uv run --project "${path.join(localTts, 'tools')}" local-tts server stop${used ? ` --engine ${used}` : ''}`);
}

// ───────────────────────── timeline ─────────────────────────

function cmdTimeline(pos, opt) {
  const P = deckPaths(pos[0]);
  const script = loadScript(P);
  const spoken = makeSpoken(loadLexicon(P));
  const fps = script.fps;
  const scenes = [];
  const estimated = [];
  const stale = [];
  const audioParts = [];
  let cursor = 0;
  const useAudio = !opt.estimate;
  let t = null;
  for (const sc of script.scenes) {
    const leadF = Math.round(sc.leadIn * fps);
    let cues = [];
    let speechF = 0;
    let wav = null;
    if (sc.lines.length) {
      const metaPath = path.join(P.sceneAudio, `${sc.id}.json`);
      const wavPath = path.join(P.sceneAudio, `${sc.id}.wav`);
      let timing = null;
      if (useAudio && exists(metaPath) && exists(wavPath)) {
        timing = readJSON(metaPath);
        t = t || (timing.motion ? { tts: timing.motion.tts, voice: timing.motion.voice, engine: timing.motion.engine } : null);
        const ssml = sceneSSML(script, sc, spoken);
        const meta = timing.motion || {};
        const expected = sceneHash(ssml, { tts: meta.tts, voice: meta.voice, engine: meta.engine });
        if (meta.hash !== expected) { stale.push(sc.id); timing = null; }
      }
      if (timing) {
        const rate = timing.sample_rate;
        const mark = (n) => (timing.marks || []).find((m) => m.name === n);
        cues = sc.lines.map((line, i) => {
          const a = mark(`c${i}`), b = mark(`c${i}e`);
          if (!a || !b) fail(`${sc.id}: 時刻の印 c${i} がありません。synth で作り直してください`);
          return cue(line, leadF + Math.round((a.frame / rate) * fps), leadF + Math.round((b.frame / rate) * fps));
        });
        speechF = Math.ceil(timing.audio_seconds * fps);
        wav = wavPath;
      } else {
        estimated.push(sc.id);
        let tt = 0;
        cues = sc.lines.map((line, i) => {
          const dur = Math.max(1.2, spoken(line).length / script.charsPerSecond);
          const c = cue(line, leadF + Math.round(tt * fps), leadF + Math.round((tt + dur) * fps));
          tt += dur + (i < sc.lines.length - 1 ? (line.pause != null ? line.pause : script.pause) / 1000 : 0);
          return c;
        });
        speechF = Math.ceil(tt * fps);
      }
    }
    let duration = (sc.lines.length ? leadF + speechF + Math.round(sc.tail * fps) : 0) + Math.round(sc.hold * fps);
    duration = Math.max(duration, Math.round(sc.duration * fps), 1);
    scenes.push(Object.assign({ id: sc.id, chapter: sc.chapter, start: cursor, duration, cues }, sc.notes ? { notes: sc.notes } : {}));
    audioParts.push({ wav, leadF, duration });
    cursor += duration;
  }

  let audio = null;
  if (audioParts.some((p) => p.wav)) {
    needFfmpeg();
    const key = sha(JSON.stringify(audioParts.map((p) => [p.wav && fs.statSync(p.wav).mtimeMs, p.wav, p.leadF, p.duration, fps])));
    const meta = exists(P.narrationMeta) ? readJSON(P.narrationMeta) : {};
    if (meta.key !== key || !exists(P.narrationWav) || !exists(P.narrationM4a)) {
      const inputs = [];
      const filters = [];
      audioParts.forEach((p, k) => {
        const n = Math.round((p.duration / fps) * SAMPLE_RATE);
        if (p.wav) {
          inputs.push('-i', p.wav);
          const j = inputs.length / 2 - 1;
          const ms = Math.round((p.leadF / fps) * 1000);
          filters.push(`[${j}:a]aresample=${SAMPLE_RATE},aformat=sample_fmts=s16:channel_layouts=mono,adelay=${ms}:all=1,apad,atrim=end_sample=${n}[s${k}]`);
        } else {
          filters.push(`anullsrc=r=${SAMPLE_RATE}:cl=mono,atrim=end_sample=${n},aformat=sample_fmts=s16[s${k}]`);
        }
      });
      filters.push(`${audioParts.map((_, k) => `[s${k}]`).join('')}concat=n=${audioParts.length}:v=0:a=1[out]`);
      fs.mkdirSync(path.dirname(P.narrationWav), { recursive: true });
      run('ffmpeg', ['-y', '-loglevel', 'error', ...inputs, '-filter_complex', filters.join(';'), '-map', '[out]', '-c:a', 'pcm_s16le', P.narrationWav], 'ナレーションの連結');
      run('ffmpeg', ['-y', '-loglevel', 'error', '-i', P.narrationWav, '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', P.narrationM4a], 'AAC への変換');
      writeJSON(P.narrationMeta, { key, frames: cursor, fps });
    }
    audio = 'narration/narration.m4a';
  }

  const tl = {
    version: 1,
    title: script.title,
    fps,
    width: script.width,
    height: script.height,
    totalFrames: cursor,
    audio,
    voice: t && t.voice, engine: t && t.engine, tts: t && t.tts,
    estimated,
    ...(script.format ? { format: script.format } : {}),
    scriptHash: sha(fs.readFileSync(P.script, 'utf8') + (exists(P.lexicon) ? fs.readFileSync(P.lexicon, 'utf8') : '')),
    generated: new Date().toISOString(),
    scenes,
  };
  fs.writeFileSync(P.timeline, `window.MOTION_TIMELINE = ${JSON.stringify(tl, null, 1)};\n`);
  const min = (cursor / fps / 60).toFixed(2);
  log(`timeline.js: ${scenes.length}シーン、${min}分（${cursor}フレーム @${fps}fps）${audio ? '、音声あり' : '、音声なし'}`);
  if (estimated.length && script.format !== 'pptx') log(`  仮の尺（文字数からの見積もり）: ${estimated.join(', ')}`);
  if (stale.length) warn(`原稿が変わったので音声が古いシーン（仮の尺にしました）: ${stale.join(', ')} → synth で作り直す`);
  return tl;
}

function cue(line, start, end) {
  const c = { text: line.text, start, end: Math.max(end, start + 1) };
  if (line.name) c.name = line.name;
  if (line.auto) c.auto = true; // 発表モードで、前のステップに続けて自動で動く
  if (line.build != null) c.build = Number(line.build); // 発表モードでの動きの長さ（秒）
  if (line.note) c.note = String(line.note); // 発表者ビューに出すメモ
  return c;
}

function loadTimeline(P) {
  if (!exists(P.timeline)) fail('timeline.js がありません。timeline を先に実行してください');
  const src = fs.readFileSync(P.timeline, 'utf8');
  const m = /^window\.MOTION_TIMELINE = ([\s\S]*);\s*$/.exec(src);
  if (!m) fail('timeline.js の形式が違います。timeline で作り直してください');
  return JSON.parse(m[1]);
}

// ───────────────────────── ブラウザ（Chrome DevTools Protocol） ─────────────────────────

function findChrome() {
  const env = process.env.CHROME_PATH;
  if (env && exists(env)) return env;
  const cands = process.platform === 'darwin'
    ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge', '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser', '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary']
    : process.platform === 'win32'
      ? [`${process.env['PROGRAMFILES']}\\Google\\Chrome\\Application\\chrome.exe`, `${process.env['PROGRAMFILES(X86)']}\\Google\\Chrome\\Application\\chrome.exe`, `${process.env['LOCALAPPDATA']}\\Google\\Chrome\\Application\\chrome.exe`, `${process.env['PROGRAMFILES(X86)']}\\Microsoft\\Edge\\Application\\msedge.exe`]
      : [];
  for (const c of cands) if (c && exists(c)) return c;
  for (const c of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge']) { const p = which(c); if (p) return p; }
  return null;
}

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.seq = 0;
    this.pending = new Map();
    this.handlers = new Set();
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString());
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject, method } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(`${method}: ${msg.error.message}`));
        else resolve(msg.result);
      } else this.handlers.forEach((h) => h(msg));
    });
    ws.addEventListener('close', () => { for (const p of this.pending.values()) p.reject(new Error('ブラウザとの接続が切れました')); this.pending.clear(); });
  }
  static connect(url) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(url);
      ws.addEventListener('open', () => resolve(new CDP(ws)), { once: true });
      ws.addEventListener('error', () => reject(new Error('ブラウザに接続できません')), { once: true });
    });
  }
  send(method, params = {}, sessionId) {
    const id = ++this.seq;
    this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject, method }));
  }
}

async function launchBrowser() {
  if (typeof WebSocket === 'undefined') fail('Node 22 以上が必要です（WebSocket）');
  const exe = findChrome();
  if (!exe) fail('Chrome / Chromium / Edge が見つかりません。CHROME_PATH で場所を指定してください');
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), 'motion-chrome-'));
  const proc = spawn(exe, [
    '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${userDir}`,
    '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
    '--allow-file-access-from-files', '--force-color-profile=srgb', '--disable-extensions', 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  const wsUrl = await new Promise((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(() => reject(new Error('ブラウザが起動しません:\n' + buf.slice(-800))), 30000);
    proc.stderr.on('data', (d) => {
      buf += d;
      const m = /DevTools listening on (ws:\/\/\S+)/.exec(buf);
      if (m) { clearTimeout(timer); resolve(m[1]); }
    });
    proc.on('exit', (code) => { clearTimeout(timer); reject(new Error(`ブラウザが終了しました（${code}）\n${buf.slice(-800)}`)); });
  });
  const cdp = await CDP.connect(wsUrl);
  return {
    cdp,
    async close() {
      try { await Promise.race([cdp.send('Browser.close'), new Promise((r) => setTimeout(r, 2000))]); } catch { /* noop */ }
      try { proc.kill(); } catch { /* noop */ }
      try { fs.rmSync(userDir, { recursive: true, force: true }); } catch { /* noop */ }
    },
  };
}

async function openDeck(browser, P, tl, query = '', { player = false } = {}) {
  const { cdp } = browser;
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank', newWindow: true });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  const s = (m, p) => cdp.send(m, p, sessionId);
  const pageErrors = [];
  cdp.handlers.add((msg) => {
    if (msg.sessionId !== sessionId) return;
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = msg.params.exceptionDetails;
      pageErrors.push(`${(d.exception && d.exception.description) || d.text}`.split('\n')[0] + (d.url ? ` (${path.basename(d.url)}:${d.lineNumber + 1})` : ''));
    }
    if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') pageErrors.push(`${msg.params.entry.text}${msg.params.entry.url ? ' ' + msg.params.entry.url : ''}`);
  });
  await s('Page.enable');
  await s('Page.setWebLifecycleState', { state: 'active' }).catch(() => {});
  await s('Runtime.enable');
  await s('Log.enable');
  await s('Emulation.setDeviceMetricsOverride', { width: tl.width, height: tl.height, deviceScaleFactor: 1, mobile: false });
  const evaluate = async (expression) => {
    let timer;
    const r = await Promise.race([
      s('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new UserError(`ページが応答しません（60秒）: ${expression.slice(0, 80)}`)), 60000); }),
    ]).finally(() => clearTimeout(timer));
    if (r.exceptionDetails) throw new Error((r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text);
    return r.result.value;
  };
  // player: 人が開くのと同じ形（?render=1 なし）で開き、プレーヤーができるのを待つ
  const api = player ? '__motionPlayer' : '__motion';
  const q = player ? (query ? '?' + query.replace(/^&/, '') : '') : '?render=1' + query;
  await s('Page.navigate', { url: pathToFileURL(P.index).href + q });
  const deadline = Date.now() + 30000;
  for (;;) {
    let ok = false;
    try { ok = await evaluate(`document.readyState === "complete" && (!!window.${api} || !!window.__motionBootError)`); } catch { /* 遷移中 */ }
    if (ok) break;
    if (Date.now() > deadline) {
      let body = '';
      try { body = await evaluate('document.body ? document.body.innerText.slice(0, 600) : ""'); } catch { /* noop */ }
      fail(`デッキを開けません（window.${api} ができません）\n${pageErrors.join('\n')}\n${body}`);
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  const bootError = await evaluate('window.__motionBootError || ""');
  if (bootError) fail(`デッキを開けません（boot.js）\n${bootError}`);
  if (!player) await evaluate('window.__motion.ready');
  return {
    evaluate,
    pageErrors,
    seek: (f) => evaluate(`window.__motion.seek(${f})`),
    send: s,
    capture: async (format = 'png', quality = 92, clip) => {
      const c = clip || { x: 0, y: 0, width: tl.width, height: tl.height };
      const r = await s('Page.captureScreenshot', { format, quality: format === 'jpeg' ? quality : undefined, clip: Object.assign({ scale: 1 }, c), captureBeyondViewport: false, optimizeForSpeed: true });
      return Buffer.from(r.data, 'base64');
    },
    close: () => cdp.send('Target.closeTarget', { targetId }).catch(() => {}),
  };
}

/** シーンごとの確認点：各文が終わって次の文が始まる直前、と退場の直前 */
function checkpoints(tl, sceneFilter) {
  const pts = [];
  for (const sc of tl.scenes) {
    if (sceneFilter && !sceneFilter.has(sc.id)) continue;
    const settle = Math.max(0, sc.duration - 12);
    if (!sc.cues.length) { pts.push({ scene: sc.id, label: 'end', frame: sc.start + settle }); continue; }
    sc.cues.forEach((c, i) => {
      const next = i + 1 < sc.cues.length ? sc.cues[i + 1].start - 1 : settle;
      pts.push({ scene: sc.id, label: `文${i}${c.name ? '(' + c.name + ')' : ''}`, frame: sc.start + Math.max(c.start, Math.min(next, sc.duration - 1)) });
    });
  }
  return pts;
}

// ───────────────────────── check ─────────────────────────

async function cmdCheck(pos, opt) {
  const P = deckPaths(pos[0]);
  const script = loadScript(P);
  const spoken = makeSpoken(loadLexicon(P));
  const errors = [];
  const warnings = [];
  // PPTX専用のデッキ：文はノートにだけ使い、読み上げない。動きも使わない
  const pptxOnly = script.format === 'pptx';
  if (!pptxOnly) {
    const r = inspectSpoken(script, spoken, { allowLatin: !!opt['allow-latin'] });
    errors.push(...r.errors.map((e) => '[原稿] ' + e));
    warnings.push(...r.warnings.map((e) => '[原稿] ' + e));
  }

  if (!exists(P.index)) fail('index.html がありません');
  const html = fs.readFileSync(P.index, 'utf8').replace(/<!--[\s\S]*?-->/g, '');
  const htmlIds = [...html.matchAll(/<[a-zA-Z][^>]*\sdata-scene="([^"]+)"/g)].map((m) => m[1]);
  for (const sc of script.scenes) if (!htmlIds.includes(sc.id)) errors.push(`[HTML] シーン「${sc.id}」の <section data-scene="${sc.id}"> がありません`);
  for (const id of htmlIds) if (!script.scenes.some((s) => s.id === id)) errors.push(`[HTML] <section data-scene="${id}"> が script.json にありません`);
  const order = htmlIds.filter((id) => script.scenes.some((s) => s.id === id));
  if (order.join() !== script.scenes.map((s) => s.id).filter((id) => htmlIds.includes(id)).join()) warnings.push('[HTML] シーンの並びが script.json と違います（表示は script.json の順）');
  const boots = html.match(BOOT_TAG) || [];
  if (boots.length !== 1) errors.push(`[構成] <script src="motion/boot.js"></script> がちょうど1つ必要です（今は${boots.length}つ）。古いデッキは runtime コマンドで直せます`);
  if (/<(?:script|link)[^>]+(?:src|href)=["'](?:motion\/(?:motion|kit)\.(?:js|css)|timeline\.js|scenes\.js|theme\.css)["']/.test(html) || /Motion\.start\(/.test(html)) errors.push('[構成] 実行系・テーマ・時間軸を直接読み込んでいます。boot.js の1行だけにしてください（runtime コマンドで直せます）');
  if (!/<main[^>]*\sid=["']composition["']/.test(html)) errors.push('[構成] <main id="composition"> がありません');
  // 章バーはテンプレートの雛形に従う。雛形が data-chapter-bar="off" のテンプレートでは付けない（PPTX専用のデッキは雛形どおり "off"）
  const noChapterBar = !pptxOnly && !templateHasChapterBar(deckTemplate(P));
  const bar = chapterBarAttr(html);
  if (noChapterBar) {
    if (bar != null && bar !== 'off') errors.push(`[構成] テンプレート「${deckTemplate(P)}」は章バーを使いません。#composition の data-chapter-bar を外すか "off" にしてください`);
  } else if (bar == null) errors.push('[構成] #composition に data-chapter-bar がありません');
  for (const f of ['theme.css', 'scenes.js']) if (!exists(path.join(P.root, f))) errors.push(`[構成] ${f} がありません`);
  const drift = runtimeDrift(P);
  if (drift.length) errors.push(`[構成] 実行系がスキルの版と違います: ${drift.join(', ')} → node "${path.join(SKILL, 'scripts/motion.mjs')}" runtime "${P.root}"`);
  if (/@keyframes|transition\s*:/.test(html) || (exists(path.join(P.root, 'theme.css')) && /@keyframes/.test(fs.readFileSync(path.join(P.root, 'theme.css'), 'utf8')))) {
    warnings.push('[HTML] @keyframes / transition があります。時間に連動しないので書き出しでずれます');
  }
  if (pptxOnly) {
    for (const a of PPTX_TIMED) {
      const n = (html.match(new RegExp(`\\s${a}(?=[\\s=>/])`, 'g')) || []).length;
      if (n) errors.push(`[PPTX専用] ${a} があります（${n}か所）。PPTX専用のデッキでは動きを使わず、完成した画面だけを書きます`);
    }
    const js = exists(path.join(P.root, 'scenes.js')) ? fs.readFileSync(path.join(P.root, 'scenes.js'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '') : '';
    if (/Motion\.scene\s*\(/.test(js + html)) errors.push('[PPTX専用] Motion.scene を使っています。PPTX専用のデッキでは動きを使わず、完成した画面だけを書きます');
  }

  let tl = exists(P.timeline) ? loadTimeline(P) : null;
  const hashNow = sha(fs.readFileSync(P.script, 'utf8') + (exists(P.lexicon) ? fs.readFileSync(P.lexicon, 'utf8') : ''));
  if (!tl || tl.scriptHash !== hashNow) {
    log('timeline.js が原稿より古いので作り直します。');
    tl = cmdTimeline([P.root], {});
  }
  if (tl.estimated.length && !pptxOnly) warnings.push(`[音声] 仮の尺のシーン: ${tl.estimated.join(', ')}（synth で音声を作ると本当の尺になる）`);

  if (!opt['no-browser']) {
    const browser = await launchBrowser();
    try {
      const page = await openDeck(browser, P, tl, '&subtitles=1');
      const feats = await page.evaluate('window.__motion.features()');
      // PPTX専用のデッキには章バーと字幕がない。章バーを使わないテンプレートには章バーがない
      const required = pptxOnly ? REQUIRED.filter((k) => k !== 'chapterBar' && k !== 'subtitles') : noChapterBar ? REQUIRED.filter((k) => k !== 'chapterBar') : REQUIRED;
      const missing = required.filter((k) => !feats[k]);
      if (missing.length) errors.push(`[機能] 備わっていない機能: ${missing.join(', ')}`);
      const runtimeErrors = await page.evaluate('window.__motion.errors.slice()');
      errors.push(...runtimeErrors.map((e) => '[実行] ' + e));
      const filter = opt.scene ? new Set(String(opt.scene).split(',')) : null;
      const seen = new Map();
      // PPTX専用のデッキは各シーンの完成状態（シーンの終わり）だけを調べる
      const pts = pptxOnly
        ? tl.scenes.filter((sc) => !filter || filter.has(sc.id)).map((sc) => ({ scene: sc.id, label: '完成', frame: sc.start + Math.max(0, sc.duration - 12) }))
        : checkpoints(tl, filter);
      // 各シーンの最後の確認点（最後の状態）では、下が空きすぎていないかも調べる。
      // default は「余白は残してよい」見た目（見出しの下に上から置く）なので調べない。ほかのテンプレートは下の余白まで使う
      const lastPt = deckTemplate(P) === DEFAULT_TEMPLATE ? new Map() : new Map(pts.map((pt) => [pt.scene, pt]));
      for (const pt of pts) {
        await page.seek(pt.frame);
        const issues = await page.evaluate(`window.__motion.lint(${lastPt.get(pt.scene) === pt ? '{ space: true }' : ''})`);
        for (const is of issues) {
          const k = is.kind + is.el;
          if (!seen.has(k)) seen.set(k, { ...is, where: `${pt.scene} ${pt.label} f${pt.frame}` });
        }
      }
      // 発表モードの各ステップも同じ検査をする（動きを縮めた時間軸）。PPTX専用のデッキでは行わない
      if (!pptxOnly) {
        const livePage = await openDeck(browser, P, tl, '&mode=live');
        const info = await livePage.evaluate('({ stops: __motion.stops, scenes: __motion.scenes })');
        for (const f of info.stops) {
          const sc = info.scenes.filter((x) => f >= x.start).pop();
          if (filter && !filter.has(sc.id)) continue;
          await livePage.seek(f);
          for (const is of await livePage.evaluate('window.__motion.lint()')) {
            const k = is.kind + is.el;
            if (!seen.has(k)) seen.set(k, { ...is, where: `${sc.id} 発表ステップ f${f}` });
          }
      }
      livePage.pageErrors.forEach((e) => errors.push('[ブラウザ] ' + e));
      await livePage.close();
      log(`発表モード: ${info.stops.length}ステップ`);
      }
      // 人が開く形（プレーヤー）でも開き、機能の自己申告と、キー操作で実際に動くかを確かめる
      const pl = await openDeck(browser, P, tl, '&mode=live', { player: true });
      const pf = await pl.evaluate('window.__motionPlayer.features()');
      const pmissing = required.concat(PLAYER_REQUIRED).filter((k) => !pf[k]);
      if (pmissing.length) errors.push(`[機能] プレーヤーに備わっていない機能: ${pmissing.join(', ')}`);
      const probe = await pl.evaluate(`(() => {
        const P = window.__motionPlayer, key = (k) => document.body.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
        const bo = () => document.getElementById('md-blackout');
        const r = {};
        r.startLive = P.mode === 'live';
        const s0 = P.step; key('ArrowRight'); r.play = P.playing || P.step === s0 + 1; if (P.playing) key('ArrowRight'); r.next = !P.playing && P.step === s0 + 1; key('ArrowLeft'); r.prev = P.step === s0;
        key('p'); r.toVideo = P.mode === 'video'; key('p'); r.toLive = P.mode === 'live';
        key('b'); r.blackOn = !!bo() && bo().classList.contains('is-on'); key('b'); r.blackOff = !!bo() && !bo().classList.contains('is-on');
        const h = document.getElementById('md-help'); key('?'); r.help = !!h && h.classList.contains('is-open'); key('Escape'); r.helpClose = !!h && !h.classList.contains('is-open');
        r.editHidden = !P.editOpen; key('e'); r.editOn = P.editOpen; key('i'); r.inspect = P.inspecting; key('Escape'); r.inspectOff = !P.inspecting; key('e'); r.editOff = !P.editOpen;
        r.hasAudio = P.audioTime !== null;
        if (r.hasAudio) { const n0 = P.narration; key('v'); r.voice = P.narration === !n0; key('v'); r.voiceBack = P.narration === n0; }
        return r;
      })()`);
      const PROBES = { startLive: '?mode=live で発表モードになる', play: '→でステップの動きが始まる', next: '→をもう一度で次のステップの終わりへ', prev: '←で前のステップ', toVideo: 'P で動画モード', toLive: 'P で発表モードに戻る', blackOn: 'B で画面を隠す', blackOff: 'B で戻す', help: '? でヘルプ', helpClose: 'Esc でヘルプを閉じる', editHidden: '発表モードでは修正の列を隠す', editOn: 'E で修正の列を出す', inspect: 'I で DOM選択', inspectOff: 'Esc で DOM選択をやめる', editOff: 'E で修正の列を隠す', voice: 'V でナレーションのオン・オフ', voiceBack: 'V で戻す' };
      for (const [k, label] of Object.entries(PROBES)) if (k in probe && !probe[k]) errors.push(`[操作] ${label} が動きません`);
      if (!probe.hasAudio && !pptxOnly) warnings.push('[音声] narration がないので、ナレーションのオン・オフは確かめていません（synth のあとで check し直してください）');
      pl.pageErrors.forEach((e) => errors.push('[ブラウザ] ' + e));
      await pl.close();
      const later = await page.evaluate('window.__motion.errors.slice()');
      later.slice(runtimeErrors.length).forEach((e) => errors.push('[実行] ' + e));
      page.pageErrors.forEach((e) => errors.push('[ブラウザ] ' + e));
      for (const is of seen.values()) {
        const line = `[配置] ${is.where}: ${is.message} ${is.el}`;
        if (is.kind === 'safe-area' || is.kind === 'css-transition' || is.kind === 'overlap' || is.kind === 'bottom-space') warnings.push(line); else errors.push(line);
      }
      await page.close();
    } finally { await browser.close(); }
  }

  warnings.forEach((w) => log('⚠ ' + w));
  errors.forEach((e) => log('✗ ' + e));
  log(`\n検査: エラー ${errors.length} 件、注意 ${warnings.length} 件（${tl.scenes.length}シーン、${(tl.totalFrames / tl.fps / 60).toFixed(2)}分）`);
  if (errors.length) process.exitCode = 1;
}

// ───────────────────────── still ─────────────────────────

async function cmdStill(pos, opt) {
  const P = deckPaths(pos[0]);
  const tl = loadTimeline(P);
  const dir = path.resolve(opt.out || path.join(P.out, 'stills'));
  fs.mkdirSync(dir, { recursive: true });
  for (const f of fs.readdirSync(dir)) if (/^\d{6}-.*\.png$|^contact\.png$/.test(f)) fs.rmSync(path.join(dir, f));
  let pts;
  const filter = opt.scene ? new Set(String(opt.scene).split(',')) : null;
  if (opt.live) pts = null; // 発表モードのステップはページを開いてから決まる
  else if (opt.frames) pts = String(opt.frames).split(',').map((x) => ({ frame: Number(x), scene: '', label: '' }));
  // PPTX専用のデッキは動かないので、--cues でもシーンごとに1枚（最後の状態）にする
  else if (opt.cues && loadScript(P).format !== 'pptx') pts = checkpoints(tl, filter);
  else {
    pts = tl.scenes.filter((s) => !filter || filter.has(s.id)).map((s) => ({ frame: s.start + Math.max(0, s.duration - 12), scene: s.id, label: 'end' }));
  }
  const browser = await launchBrowser();
  const files = [];
  try {
    const page = await openDeck(browser, P, tl, (opt.subtitles === '0' ? '&subtitles=0' : '') + (opt.live ? '&mode=live' : ''));
    if (opt.live) {
      const info = await page.evaluate('({ stops: __motion.stops, scenes: __motion.scenes })');
      pts = info.stops.map((f) => ({ frame: f, scene: (info.scenes.filter((x) => f >= x.start).pop() || {}).id }))
        .filter((pt) => !filter || filter.has(pt.scene));
    }
    for (const pt of pts) {
      const f = await page.seek(pt.frame);
      // 発表モードのシーンの区切りは動画モードと違うので、--live では発表モードのシーンを使う
      const id = opt.live ? pt.scene : (tl.scenes.filter((s) => f >= s.start).pop() || {}).id;
      const file = path.join(dir, `${String(f).padStart(6, '0')}-${id || 'frame'}.png`);
      fs.writeFileSync(file, await page.capture('png'));
      files.push(file);
    }
    const errs = await page.evaluate('window.__motion.errors.slice()');
    errs.concat(page.pageErrors).forEach((e) => warn(e));
    await page.close();
  } finally { await browser.close(); }
  files.forEach((f) => log(f));
  if (files.length > 1 && which('ffmpeg') && !opt['no-contact']) {
    const cols = Math.min(3, files.length);
    const rows = Math.ceil(files.length / cols);
    const list = path.join(dir, '.list.txt');
    fs.writeFileSync(list, files.map((f) => `file '${f.replace(/'/g, "'\\''")}'`).join('\n'));
    const contact = path.join(dir, 'contact.png');
    try {
      run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-vf', `scale=640:-1,tile=${cols}x${rows}:padding=8:margin=8:color=0x333333`, '-frames:v', '1', contact], '一覧画像');
      log(`一覧: ${contact}`);
    } finally { fs.rmSync(list, { force: true }); }
  }
}

// ───────────────────────── render ─────────────────────────

async function cmdRender(pos, opt) {
  const P = deckPaths(pos[0]);
  notForPptx(loadScript(P), 'render', '動画・MP4 に書き出さないため');
  needFfmpeg();
  const tl = loadTimeline(P);
  const from = Math.max(0, Number(opt.from || 0));
  const to = Math.min(tl.totalFrames, opt.to ? Number(opt.to) : tl.totalFrames);
  if (to <= from) fail('--from / --to の範囲が空です');
  const out = path.resolve(opt.out || path.join(P.out, `${path.basename(P.root)}.mp4`));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const conc = Math.max(1, Number(opt.concurrency || Math.min(4, Math.max(1, Math.floor(os.cpus().length / 2)))));
  if (tl.estimated.length && !opt['allow-estimated']) fail(`仮の尺のシーンがあります: ${tl.estimated.join(', ')}\n  音声を作ってから書き出すか、--allow-estimated を付けてください`);
  const fps = tl.fps;
  const hasAudio = tl.audio && exists(P.narrationWav);
  const vf = opt.scale ? ['-vf', `scale=trunc(iw*${Number(opt.scale)}/2)*2:-2`] : [];
  const args = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-'];
  if (hasAudio) args.push('-ss', String(from / fps), '-t', String((to - from) / fps), '-i', P.narrationWav);
  args.push('-map', '0:v');
  if (hasAudio) args.push('-map', '1:a', '-c:a', 'aac', '-b:a', '192k');
  args.push(...vf, '-c:v', 'libx264', '-preset', opt.preset || 'medium', '-crf', String(opt.crf || 18), '-pix_fmt', 'yuv420p', '-r', String(fps), '-movflags', '+faststart', out);
  const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'inherit', 'pipe'] });
  let ffErr = '';
  ff.stderr.on('data', (d) => { ffErr += d; });
  const ffDone = new Promise((resolve) => ff.on('close', resolve));

  log(`書き出し: ${to - from}フレーム（${((to - from) / fps / 60).toFixed(2)}分）、並列 ${conc}、→ ${out}`);
  const browser = await launchBrowser();
  const started = Date.now();
  try {
    const query = opt.subtitles === '0' ? '&subtitles=0' : '';
    const pages = await Promise.all(Array.from({ length: conc }, () => openDeck(browser, P, tl, query)));
    const errs = await pages[0].evaluate('window.__motion.errors.slice()');
    if (errs.length) fail('デッキにエラーがあります。check で直してから書き出してください:\n  ' + errs.join('\n  '));
    const buffers = new Map();
    let next = from;
    let written = from;
    let lastLog = 0;
    const window_ = conc * 8;
    const write = async () => {
      while (buffers.has(written)) {
        const b = buffers.get(written);
        buffers.delete(written);
        written++;
        if (!ff.stdin.write(b)) await new Promise((r) => ff.stdin.once('drain', r));
      }
      if (Date.now() - lastLog > 3000) {
        lastLog = Date.now();
        const done = written - from;
        const rate = done / ((Date.now() - started) / 1000);
        const eta = (to - written) / Math.max(rate, 0.01);
        log(`  ${done}/${to - from}（${((done / (to - from)) * 100).toFixed(1)}%）${rate.toFixed(1)}fps 残り約${Math.ceil(eta / 60)}分`);
      }
    };
    let writing = Promise.resolve();
    const worker = async (page) => {
      for (;;) {
        if (next >= to) return;
        while (next - written > window_) await new Promise((r) => setTimeout(r, 5));
        const f = next++;
        await page.seek(f);
        buffers.set(f, await page.capture('jpeg', Number(opt.quality || 92)));
        writing = writing.then(write);
      }
    };
    await Promise.all(pages.map(worker));
    await writing;
    await write();
  } finally {
    ff.stdin.end();
    await browser.close();
  }
  const code = await ffDone;
  if (code !== 0) fail(`ffmpeg が失敗しました:\n${ffErr.slice(-1500)}`);
  log(`完了: ${out}（${((Date.now() - started) / 1000 / 60).toFixed(1)}分かかりました）`);
}

// ───────────────────────── pdf ─────────────────────────
//
// 発表モードの1ステップを1ページにした PDF。各ステップを画像にせず印刷するので、文字を選べる・検索できる。
// ステップごとの iframe を並べたページを作り、1回の印刷で全ページを書き出す（PDF をつなぐ道具が要らない）。

async function cmdPdf(pos, opt) {
  const P = deckPaths(pos[0]);
  const tl = loadTimeline(P);
  const out = path.resolve(opt.out || path.join(P.out, `${path.basename(P.root)}.pdf`));
  const filter = opt.scene ? new Set(String(opt.scene).split(',')) : null;
  const host = path.join(P.root, 'build', 'pdf', 'index.html');
  let pages = 0;
  const browser = await launchBrowser();
  try {
    const page = await openDeck(browser, P, tl, '&mode=live');
    const errs = await page.evaluate('window.__motion.errors.slice()');
    if (errs.length) fail('デッキにエラーがあります。check で直してから書き出してください:\n  ' + errs.join('\n  '));
    const info = await page.evaluate('({ stops: __motion.stops, scenes: __motion.scenes })');
    await page.close();
    const stops = info.stops.filter((f) => !filter || filter.has((info.scenes.filter((x) => f >= x.start).pop() || {}).id));
    if (!stops.length) fail(filter ? `--scene に当てはまるステップがありません: ${opt.scene}` : '発表モードのステップがありません');

    const src = pathToFileURL(P.index).href + '?render=1&mode=live';
    fs.mkdirSync(path.dirname(host), { recursive: true });
    fs.writeFileSync(host, `<!doctype html><meta charset="utf-8"><title>${xml(loadScript(P).title)}</title><style>@page { size: ${tl.width}px ${tl.height}px; margin: 0 }
html, body { margin: 0 } iframe { display: block; border: 0; width: ${tl.width}px; height: ${tl.height}px; break-after: page }</style>
${stops.map((f) => `<iframe data-frame="${f}" src="${src}&frame=${f}"></iframe>`).join('\n')}\n`);

    const { targetId } = await browser.cdp.send('Target.createTarget', { url: 'about:blank', newWindow: true });
    const { sessionId } = await browser.cdp.send('Target.attachToTarget', { targetId, flatten: true });
    const s = (m, p) => browser.cdp.send(m, p, sessionId);
    const evaluate = async (expression) => {
      const r = await s('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error((r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text);
      return r.result.value;
    };
    await s('Page.enable');
    await s('Emulation.setDeviceMetricsOverride', { width: tl.width, height: tl.height, deviceScaleFactor: 1, mobile: false });
    await s('Page.navigate', { url: pathToFileURL(host).href });
    const deadline = Date.now() + 120000;
    while (!(await evaluate('document.readyState === "complete" && [...document.querySelectorAll("iframe")].every((f) => f.contentWindow.__motion || f.contentWindow.__motionBootError)').catch(() => false))) {
      if (Date.now() > deadline) fail('デッキを開けません（120秒待っても iframe の window.__motion ができません）');
      await new Promise((r) => setTimeout(r, 100));
    }
    const bootError = await evaluate('[...document.querySelectorAll("iframe")].map((f) => f.contentWindow.__motionBootError).find(Boolean) || ""');
    if (bootError) fail(`デッキを開けません（boot.js）\n${bootError}`);
    // still と同じく、フォントの用意を待ってからそのステップに進め直す
    await evaluate('Promise.all([...document.querySelectorAll("iframe")].map(async (f) => { const m = f.contentWindow.__motion; await m.ready; await m.seek(Number(f.dataset.frame)); }))');
    const r = await s('Page.printToPDF', { printBackground: true, preferCSSPageSize: true, marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0 });
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, Buffer.from(r.data, 'base64'));
    pages = stops.length;
    await s('Target.closeTarget', { targetId }).catch(() => {});
  } finally {
    await browser.close();
    fs.rmSync(path.dirname(host), { recursive: true, force: true });
  }
  log(`完了: ${out}（${pages}ページ）`);
}

// ───────────────────────── pptx ─────────────────────────
//
// 発表モードの時間軸で、各ステップ（クリック）の絵を撮る。
//   要素モード：そのステップで現れる要素だけを透明な絵に切り出し、PowerPoint のアニメーションで出す。
//              背景＋切り出した絵を重ねた結果が本物の絵と一致するかを確かめてから使う。
//   差分モード：一致しない（強調の移動、消える要素、独自の動きなど）ときは、変わった範囲だけを
//              本物の絵から切り出してフェードで重ねる。見た目は必ず本物と同じになる。
//   スライドの区切り：1画面＝1スライド。シーンの途中で見出し（.h）が消えたら画面が入れ替わったとみなし、
//              そのステップから新しいスライドにする（背景はそのステップで現れる要素を隠した絵）。

const PPTX_HELPERS = `
window.__pptx = {
  style: null,
  hideStyle: null,
  // 今見えている見出し（.h）。シーンの section の中での順番で返す
  headings(sceneId) {
    const sec = document.querySelector('#composition [data-scene="' + sceneId + '"]');
    if (!sec) return [];
    return Array.from(sec.querySelectorAll('.h')).map((el, i) => {
      const r = el.getBoundingClientRect();
      const shown = r.width > 0 && r.height > 0 && (!el.checkVisibility || el.checkVisibility({ opacityProperty: true, visibilityProperty: true }));
      return shown ? i : -1;
    }).filter((i) => i >= 0);
  },
  // 指定した要素を隠す（新しいスライドの背景を撮るため）
  hide(ids) {
    if (!this.hideStyle) {
      this.hideStyle = document.createElement('style');
      this.hideStyle.textContent = '.pptx-hide, .pptx-hide * { visibility: hidden !important; }';
      document.head.appendChild(this.hideStyle);
    }
    for (const id of ids) {
      const el = document.querySelector('[data-pptx-id="' + id + '"]');
      if (el) el.classList.add('pptx-hide');
    }
  },
  unhide() {
    document.querySelectorAll('.pptx-hide').forEach((e) => e.classList.remove('pptx-hide'));
  },
  iso(id) {
    if (!this.style) {
      this.style = document.createElement('style');
      this.style.textContent = 'html.pptx-iso, html.pptx-iso body, html.pptx-iso #composition { background: transparent !important; }' +
        'html.pptx-iso #composition * { visibility: hidden !important; }' +
        'html.pptx-iso #composition .pptx-target, html.pptx-iso #composition .pptx-target *:not([style*="visibility: hidden"]) { visibility: visible !important; }';
      document.head.appendChild(this.style);
    }
    document.documentElement.classList.add('pptx-iso');
    const el = document.querySelector('[data-pptx-id="' + id + '"]');
    el.classList.add('pptx-target');
  },
  unIso() {
    document.documentElement.classList.remove('pptx-iso');
    document.querySelectorAll('.pptx-target').forEach((e) => e.classList.remove('pptx-target'));
  },
  async load(b64) {
    const bin = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const bmp = await createImageBitmap(new Blob([bin], { type: 'image/png' }));
    const c = new OffscreenCanvas(bmp.width, bmp.height);
    const g = c.getContext('2d');
    g.drawImage(bmp, 0, 0);
    return { c, g, bmp };
  },
  diffBox(a, b, w, h, tol) {
    const A = a.g.getImageData(0, 0, w, h).data, B = b.g.getImageData(0, 0, w, h).data;
    let x0 = w, y0 = h, x1 = -1, y1 = -1, n = 0;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      if (Math.abs(A[i] - B[i]) > tol || Math.abs(A[i + 1] - B[i + 1]) > tol || Math.abs(A[i + 2] - B[i + 2]) > tol) {
        n++; if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y;
      }
    }
    return n ? { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1, n } : null;
  },
  // prev→next で変わったか（box）。背景に layers（今見えている絵の重なり）を重ねたものが next と一致するか（rest）
  async check(prevB64, nextB64, baseB64, layers, w, h) {
    const prev = await this.load(prevB64), next = await this.load(nextB64);
    const box = this.diffBox(prev, next, w, h, 6);
    const comp = await this.load(baseB64);
    for (const p of layers) { const im = await this.load(p.b64); comp.g.drawImage(im.bmp, p.x, p.y); }
    const rest = this.diffBox(comp, next, w, h, 40);
    return { box, rest: rest && rest.n >= 60 ? rest : null };
  },
  async crop(b64, x, y, w, h) {
    const im = await this.load(b64);
    const c = new OffscreenCanvas(w, h);
    c.getContext('2d').drawImage(im.bmp, -x, -y);
    const blob = await c.convertToBlob({ type: 'image/png' });
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = ''; for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    return btoa(s);
  },
};`;

const PPTX_SHAPES = String.raw`// PPTX 用：DOM を PowerPoint の図形の一覧にする。テンプレートのクラス名は見ず、計算後のスタイルと位置だけを読む。
// 図形にできないもの（SVG・画像・filter など）はその要素だけを画像にする印（fb）を付けて返す。
// 返す形（座標は #composition の px）：
//   { t:'sp', x,y,w,h, radii:[tl,tr,br,bl], fill, line, shadow, name }
//   { t:'text', x,y,w,h, align, pitch, lines:[[{ text, size, color, bold, italic, under, strike, spc, latin, ea }]], name }
//   { t:'pic', fb:'<data-pptx-id>', x,y,w,h, name, alt }
//   { t:'group', name, id, children:[...] }
window.__pptx.conv = (function () {
  var SC = 1, CR = null, FB = [], seq = 0;
  var num = function (v) { return parseFloat(v) || 0; };
  var GENERIC = ['serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui', 'ui-sans-serif', 'ui-serif', 'ui-monospace', 'math', 'emoji', '-apple-system'];

  // 'rgb(1, 2, 3)' 'rgba(1, 2, 3, 0.5)' → { c:'010203', a }。透明は null、読めない形式は undefined
  function color(s, op) {
    if (!s || s === 'transparent') return null;
    var m = /^rgba?\(([^)]+)\)$/.exec(s.trim());
    if (!m) return undefined;
    var p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    var a = (p.length > 3 ? p[3] : 1) * (op == null ? 1 : op);
    if (a <= 0.003) return null;
    return { c: p.slice(0, 3).map(function (n) { return Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0'); }).join('').toUpperCase(), a: Math.min(1, a) };
  }
  function box(r) { return { x: (r.left - CR.left) / SC, y: (r.top - CR.top) / SC, w: r.width / SC, h: r.height / SC }; }
  // カンマ区切り（括弧の中は区切らない）
  function split(s, sep) {
    var out = [], depth = 0, cur = '';
    for (var i = 0; i < s.length; i++) {
      var ch = s[i];
      if (ch === '(') depth++;
      if (ch === ')') depth--;
      if (ch === sep && depth === 0) { out.push(cur.trim()); cur = ''; } else cur += ch;
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  }
  function label(el) {
    var t = (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 30);
    if (t) return t;
    var name = function (e) {
      var cls = (e.getAttribute('class') || '').trim().split(/\s+/)[0];
      return e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (cls ? '.' + cls : '');
    };
    var own = name(el);
    return el.id || el.getAttribute('class') || !el.parentElement ? own : name(el.parentElement) + ' > ' + own;
  }
  function sceneOf(el) { var s = el.closest('[data-scene]'); return s ? s.dataset.scene : ''; }

  // ── 図形にできるか ──
  function transformOk(t) {
    if (!t || t === 'none') return true;
    var m = /^matrix\(([^)]+)\)$/.exec(t);
    if (!m) return false;
    var v = m[1].split(',').map(Number);
    return Math.abs(v[0] - 1) < 0.002 && Math.abs(v[3] - 1) < 0.002 && Math.abs(v[1]) < 0.002 && Math.abs(v[2]) < 0.002;
  }
  function shadowOf(cs) {
    var s = cs.boxShadow;
    if (!s || s === 'none') return { list: [] };
    var parts = split(s, ',');
    var list = [];
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      var cm = /rgba?\([^)]+\)/.exec(p);
      var rest = p.replace(/rgba?\([^)]+\)/, '').trim();
      var inset = /\binset\b/.test(rest);
      var n = rest.replace(/\binset\b/, '').trim().split(/\s+/).map(num);
      list.push({ inset: inset, dx: n[0] || 0, dy: n[1] || 0, blur: n[2] || 0, spread: n[3] || 0, color: cm ? color(cm[0]) : undefined });
    }
    return { list: list };
  }
  function bgOf(cs) {
    var img = cs.backgroundImage;
    if (!img || img === 'none') return {};
    if (/url\(/.test(img)) return { why: '背景画像' };
    if (/repeating-/.test(img)) return { why: '繰り返しの模様（repeating-gradient）' };
    if (/radial-gradient|conic-gradient/.test(img)) return { why: '円や扇のグラデーション' };
    var gs = [], depth = 0, start = -1;
    for (var i = 0; i < img.length; i++) {
      if (img.startsWith('linear-gradient(', i) && depth === 0) start = i;
      if (img[i] === '(') depth++;
      if (img[i] === ')') { depth--; if (depth === 0 && start >= 0) { gs.push(img.slice(start + 16, i)); start = -1; } }
    }
    if (gs.length !== 1) return { why: '重ねた背景' };
    var args = split(gs[0], ',');
    var deg = 180;
    var first = args[0];
    if (/deg$/.test(first)) { deg = num(first); args.shift(); }
    else if (/^to /.test(first)) {
      var d = { 'to top': 0, 'to right': 90, 'to bottom': 180, 'to left': 270 }[first];
      if (d == null) return { why: '斜めのグラデーション' };
      deg = d; args.shift();
    }
    var stops = [];
    for (var k = 0; k < args.length; k++) {
      var cm = /rgba?\([^)]+\)/.exec(args[k]);
      if (!cm) return { why: 'グラデーションの色の形式' };
      var c = color(cm[0]);
      if (c === undefined) return { why: 'グラデーションの色の形式' };
      var pos = /(-?[\d.]+)%/.exec(args[k].replace(cm[0], ''));
      stops.push({ c: c, pos: pos ? num(pos[1]) / 100 : null });
    }
    stops.forEach(function (s, idx) { if (s.pos == null) s.pos = stops.length > 1 ? idx / (stops.length - 1) : 0; });
    var same = stops.every(function (s) { return JSON.stringify(s.c) === JSON.stringify(stops[0].c); });
    var size = cs.backgroundSize;
    var sized = size && size !== 'auto' && size !== 'auto auto';
    if (sized && !same) return { why: '大きさを指定したグラデーション' };
    if (sized && !/no-repeat/.test(cs.backgroundRepeat)) return { why: '繰り返しの背景' };
    return { grad: { deg: deg, stops: stops, same: same, sized: sized } };
  }
  function unsupported(el, cs) {
    var tag = el.tagName.toLowerCase();
    if (el instanceof SVGElement) return 'SVG';
    if (tag === 'img' || tag === 'picture') return '画像（img）';
    if (tag === 'canvas' || tag === 'video' || tag === 'iframe' || tag === 'object' || tag === 'embed') return tag;
    if (cs.filter && cs.filter !== 'none' && !/^blur\(0px\)$/.test(cs.filter)) return 'filter';
    if (cs.backdropFilter && cs.backdropFilter !== 'none') return 'backdrop-filter';
    if ((cs.maskImage && cs.maskImage !== 'none') || (cs.webkitMaskImage && cs.webkitMaskImage !== 'none')) return 'mask';
    if (cs.clipPath && cs.clipPath !== 'none' && !/^inset\(\s*(0(px|%)?\s*)+\)$/.test(cs.clipPath)) return 'clip-path';
    if (cs.mixBlendMode && cs.mixBlendMode !== 'normal') return 'mix-blend-mode';
    if (!transformOk(cs.transform)) return 'transform（回転・拡大・傾き）';
    if (cs.writingMode && !/^horizontal/.test(cs.writingMode)) return '縦書き';
    if (cs.textShadow && cs.textShadow !== 'none') return '文字の影（text-shadow）';
    if (num(cs.webkitTextStrokeWidth) > 0) return '文字の縁取り（text-stroke）';
    if (/text/.test(cs.backgroundClip || cs.webkitBackgroundClip || '')) return '文字の塗り（background-clip: text）';
    if (cs.outlineStyle !== 'none' && num(cs.outlineWidth) > 0) return 'outline';
    var bg = bgOf(cs);
    if (bg.why) return bg.why;
    var sh = shadowOf(cs).list;
    if (sh.length > 1) return '重ねた影（box-shadow）';
    if (sh.length && sh[0].color === undefined) return '影の色の形式';
    if (sh.length && sh[0].spread) return '広げた影（box-shadow の spread）';
    if (sh.length && sh[0].inset && sh[0].blur) return 'ぼかした内側の影';
    var sides = ['Top', 'Right', 'Bottom', 'Left'];
    for (var i = 0; i < 4; i++) {
      var st = cs['border' + sides[i] + 'Style'];
      if (st !== 'none' && st !== 'hidden' && st !== 'solid' && st !== 'dashed' && st !== 'dotted' && num(cs['border' + sides[i] + 'Width']) > 0) return '枠線の種類（' + st + '）';
      if (st !== 'none' && color(cs['border' + sides[i] + 'Color']) === undefined) return '枠線の色の形式';
    }
    if (color(cs.backgroundColor) === undefined || color(cs.color) === undefined) return '色の形式';
    return null;
  }

  // ── 箱（塗り・枠線・影） ──
  function radiiOf(cs, w, h) {
    var keys = ['borderTopLeftRadius', 'borderTopRightRadius', 'borderBottomRightRadius', 'borderBottomLeftRadius'];
    var r = keys.map(function (k, i) {
      var v = (cs[k] || '0').split(/\s+/)[0];
      return /%$/.test(v) ? num(v) / 100 * Math.min(w, h) : num(v);
    });
    var f = Math.min(1, w / (r[0] + r[1] || 1), w / (r[3] + r[2] || 1), h / (r[0] + r[3] || 1), h / (r[1] + r[2] || 1));
    return r.map(function (v) { return v * f; });
  }
  function clipShape(s, clip) {
    if (!clip) return s;
    var x0 = Math.max(s.x, clip.x), y0 = Math.max(s.y, clip.y);
    var x1 = Math.min(s.x + s.w, clip.x + clip.w), y1 = Math.min(s.y + s.h, clip.y + clip.h);
    if (x1 - x0 < 0.5 || y1 - y0 < 0.5) return null;
    var out = Object.assign({}, s, { x: x0, y: y0, w: x1 - x0, h: y1 - y0 });
    // 切り抜く箱の角に接する角は、その角の丸みを受け継ぐ
    var near = function (a, b) { return Math.abs(a - b) < 1.5; };
    var rr = (out.radii || [0, 0, 0, 0]).slice();
    var cr = clip.radii || [0, 0, 0, 0];
    if (near(out.x, clip.x) && near(out.y, clip.y)) rr[0] = Math.max(rr[0], cr[0]);
    if (near(out.x + out.w, clip.x + clip.w) && near(out.y, clip.y)) rr[1] = Math.max(rr[1], cr[1]);
    if (near(out.x + out.w, clip.x + clip.w) && near(out.y + out.h, clip.y + clip.h)) rr[2] = Math.max(rr[2], cr[2]);
    if (near(out.x, clip.x) && near(out.y + out.h, clip.y + clip.h)) rr[3] = Math.max(rr[3], cr[3]);
    out.radii = rr;
    return out;
  }
  // 1つの矩形（要素か、行に分かれたインラインの1片）の塗り・枠線・影
  function boxShapes(cs, b, op, clip, name, out) {
    if (b.w < 0.5 && b.h < 0.5) return;
    var sides = ['Top', 'Right', 'Bottom', 'Left'];
    var bw = sides.map(function (s) { var st = cs['border' + s + 'Style']; return st === 'none' || st === 'hidden' ? 0 : num(cs['border' + s + 'Width']); });
    var bc = sides.map(function (s) { return color(cs['border' + s + 'Color'], op); });
    var bs = sides.map(function (s) { return cs['border' + s + 'Style']; });
    var radii = radiiOf(cs, b.w, b.h);
    var fill = color(cs.backgroundColor, op);
    var bg = bgOf(cs);
    var extra = null; // 大きさを指定した単色のグラデーション（蛍光ペン・取り消し線）
    if (bg.grad) {
      var g = bg.grad;
      if (g.same && g.sized) {
        var sz = cs.backgroundSize.split(/\s+/);
        var pw = b.w - bw[1] - bw[3], ph = b.h - bw[0] - bw[2];
        var len = function (v, full) { return v === 'auto' ? full : /%$/.test(v) ? num(v) / 100 * full : num(v); };
        var w = len(sz[0], pw), h = len(sz[1] || 'auto', ph);
        var ps = (cs.backgroundPosition || '0% 0%').split(/\s+/);
        var at = function (v, free) { return /%$/.test(v) ? num(v) / 100 * free : num(v); };
        var x = b.x + bw[3] + at(ps[0], pw - w), y = b.y + bw[0] + at(ps[1] || '0%', ph - h);
        var c = g.stops[0].c && { c: g.stops[0].c.c, a: g.stops[0].c.a * op };
        if (c && w > 0.5 && h > 0.5) extra = { t: 'sp', x: x, y: y, w: w, h: h, radii: [0, 0, 0, 0], fill: c, name: name };
      } else if (g.same) {
        fill = g.stops[0].c && { c: g.stops[0].c.c, a: g.stops[0].c.a * op };
      } else {
        fill = { grad: { deg: g.deg, stops: g.stops.map(function (s) { return { pos: s.pos, c: s.c ? { c: s.c.c, a: s.c.a * op } : { c: '000000', a: 0 } }; }) } };
      }
    }
    var sh = shadowOf(cs).list[0];
    var shadow = sh && !sh.inset && sh.color ? { dx: sh.dx, dy: sh.dy, blur: sh.blur, c: { c: sh.color.c, a: sh.color.a * op } } : null;
    var uniform = bw[0] > 0 && bw.every(function (v) { return Math.abs(v - bw[0]) < 0.01; }) &&
      bc.every(function (c) { return JSON.stringify(c) === JSON.stringify(bc[0]); }) && bs.every(function (s) { return s === bs[0]; });
    var anyBorder = bw.some(function (v, i) { return v > 0 && bc[i]; });
    var dash = function (s) { return s === 'dashed' ? 'dash' : s === 'dotted' ? 'sysDot' : null; };
    if (uniform && bc[0]) {
      // CSS の枠線は箱の内側、PowerPoint の線は輪郭の中心に引かれるので、線の太さの半分だけ内側に寄せる
      var h2 = bw[0] / 2;
      var s = { t: 'sp', x: b.x + h2, y: b.y + h2, w: Math.max(0.5, b.w - bw[0]), h: Math.max(0.5, b.h - bw[0]), radii: radii.map(function (r) { return Math.max(0, r - h2); }), fill: fill, line: { w: bw[0], c: bc[0], dash: dash(bs[0]) }, shadow: shadow, name: name };
      s = clipShape(s, clip); if (s) out.push(s);
    } else {
      if (fill || shadow) { var s2 = clipShape({ t: 'sp', x: b.x, y: b.y, w: b.w, h: b.h, radii: radii, fill: fill, shadow: shadow, name: name }, clip); if (s2) out.push(s2); }
      if (anyBorder) {
        if (radii.some(function (r) { return r > 0.5; })) return '角の丸い、辺ごとに違う枠線';
        var rects = [
          [b.x, b.y, b.w, bw[0]], [b.x + b.w - bw[1], b.y, bw[1], b.h], [b.x, b.y + b.h - bw[2], b.w, bw[2]], [b.x, b.y, bw[3], b.h],
        ];
        rects.forEach(function (q, i) { if (bw[i] > 0 && bc[i]) { var s3 = clipShape({ t: 'sp', x: q[0], y: q[1], w: q[2], h: q[3], radii: [0, 0, 0, 0], fill: bc[i], name: name }, clip); if (s3) out.push(s3); } });
      }
    }
    // 内側の影（ぼかしなし）は、ずらした側の帯として描く
    if (sh && sh.inset && sh.color) {
      var ix = b.x + bw[3], iy = b.y + bw[0], iw = b.w - bw[1] - bw[3], ih = b.h - bw[0] - bw[2];
      var ic = { c: sh.color.c, a: sh.color.a * op };
      var strips = [];
      if (sh.dx > 0) strips.push([ix, iy, sh.dx, ih]);
      if (sh.dx < 0) strips.push([ix + iw + sh.dx, iy, -sh.dx, ih]);
      if (sh.dy > 0) strips.push([ix, iy, iw, sh.dy]);
      if (sh.dy < 0) strips.push([ix, iy + ih + sh.dy, iw, -sh.dy]);
      strips.forEach(function (q) { var s4 = clipShape({ t: 'sp', x: q[0], y: q[1], w: q[2], h: q[3], radii: [0, 0, 0, 0], fill: ic, name: name }, clip); if (s4) out.push(s4); });
    }
    if (extra) { var s5 = clipShape(extra, clip); if (s5) out.push(s5); }
    return null;
  }

  // ── 文字 ──
  var fontMemo = new Map();
  var probe = null;
  function glyphSig(font, ch) {
    if (!probe) { probe = document.createElement('canvas'); probe.width = probe.height = 48; }
    var g = probe.getContext('2d', { willReadFrequently: true });
    g.clearRect(0, 0, 48, 48); g.font = font; g.fillStyle = '#000'; g.textBaseline = 'top'; g.fillText(ch, 2, 2);
    var d = g.getImageData(0, 0, 48, 48).data, h = 0;
    for (var i = 3; i < d.length; i += 4) h = (h * 31 + d[i]) | 0;
    return h + ':' + g.measureText(ch).width;
  }
  // そのフォントにその文字の字形があるか（後ろの総称フォントを変えても絵が同じなら、そのフォントで描かれている）
  function hasGlyph(fam, ch) {
    var k = fam + '|' + ch;
    if (!fontMemo.has(k)) fontMemo.set(k, glyphSig('32px "' + fam + '", serif', ch) === glyphSig('32px "' + fam + '", sans-serif', ch) && glyphSig('32px "' + fam + '", serif', ch) === glyphSig('32px "' + fam + '", monospace', ch));
    return fontMemo.get(k);
  }
  function families(list) {
    return split(list, ',').map(function (f) { return f.replace(/^["']|["']$/g, '').trim(); }).filter(function (f) { return f && GENERIC.indexOf(f.toLowerCase()) < 0; });
  }
  function pickFont(list, ch) {
    var fs = families(list);
    for (var i = 0; i < fs.length; i++) if (hasGlyph(fs[i], ch)) return fs[i];
    return null;
  }
  function isInlineBox(cs) { return cs.display === 'inline' || cs.display === 'contents'; }

  // 文字を集める箱（block）の中の、文字と、インラインの要素の塗り
  function inlineContent(container, op, clip, out) {
    var chars = [];
    var decor = [];
    (function visit(node, op2) {
      for (var n = node.firstChild; n; n = n.nextSibling) {
        if (n.nodeType === 3) {
          var parent = n.parentElement;
          var pcs = getComputedStyle(parent);
          if (pcs.visibility !== 'visible') continue;
          var text = n.data;
          if (!text) continue;
          var range = document.createRange();
          var idx = 0;
          Array.from(text).forEach(function (ch) {
            var len = ch.length;
            range.setStart(n, idx); range.setEnd(n, idx + len); idx += len;
            if (ch === '\n' || ch === '\r' || (ch === '\t' && pcs.whiteSpace.indexOf('pre') < 0)) return;
            var rr = range.getClientRects();
            if (!rr.length) return;
            var r = rr[rr.length - 1];
            if (r.width < 0.01) return;
            var b = box(r);
            if (clip && (b.x + b.w / 2 < clip.x || b.x + b.w / 2 > clip.x + clip.w || b.y + b.h / 2 < clip.y || b.y + b.h / 2 > clip.y + clip.h)) return;
            chars.push({ ch: ch === '\t' ? ' ' : ch, b: b, el: parent, cs: pcs, op: op2 });
          });
        } else if (n.nodeType === 1) {
          var cs = getComputedStyle(n);
          if (cs.display === 'none' || !isInlineBox(cs)) continue;
          var o = op2 * num(cs.opacity === '' ? 1 : cs.opacity);
          if (o < 0.01) continue;
          var why = unsupported(n, cs);
          if (why) { decor.push({ fb: n, why: why }); continue; }
          if (cs.visibility === 'visible') Array.from(n.getClientRects()).forEach(function (r) { boxShapes(cs, box(r), o, clip, label(n), decor); });
          visit(n, o);
        }
      }
    })(container, op);
    decor.forEach(function (d) { if (d.fb) out.push(fallback(d.fb, d.why)); else out.push(d); });
    if (!chars.length) return;
    // 行に分ける（文字の中心が今の行の下端より下なら次の行）
    var lines = [];
    chars.forEach(function (c) {
      var cy = c.b.y + c.b.h / 2;
      var L = lines[lines.length - 1];
      if (!L || cy > L.bottom || c.b.x + 0.5 < L.right - 2 * c.b.w && cy > L.top + (L.bottom - L.top) / 2) lines.push(L = { top: c.b.y, bottom: c.b.y + c.b.h, left: c.b.x, right: c.b.x + c.b.w, chars: [] });
      L.chars.push(c);
      L.top = Math.min(L.top, c.b.y); L.bottom = Math.max(L.bottom, c.b.y + c.b.h);
      L.left = Math.min(L.left, c.b.x); L.right = Math.max(L.right, c.b.x + c.b.w);
    });
    var ccs = getComputedStyle(container);
    var lh = ccs.lineHeight === 'normal' ? null : num(ccs.lineHeight);
    var pitch = lines.length > 1 ? (lines[lines.length - 1].top + lines[lines.length - 1].bottom - lines[0].top - lines[0].bottom) / 2 / (lines.length - 1) : null;
    if (!pitch) pitch = lh || (lines[0].bottom - lines[0].top);
    var runsOf = function (L) {
      var runs = [];
      L.chars.forEach(function (c) {
        var cs = c.cs;
        var col = color(cs.color, c.op) || { c: '000000', a: 0 };
        var deco = cs.textDecorationLine || '';
        var key = [cs.fontFamily, cs.fontSize, cs.fontWeight, cs.fontStyle, cs.letterSpacing, col.c, col.a, deco].join('|');
        var R = runs[runs.length - 1];
        if (!R || R.key !== key) runs.push(R = {
          key: key, text: '', size: num(cs.fontSize), color: col, bold: num(cs.fontWeight) >= 600, italic: cs.fontStyle !== 'normal',
          under: /underline/.test(deco), strike: /line-through/.test(deco), spc: cs.letterSpacing === 'normal' ? 0 : num(cs.letterSpacing), list: cs.fontFamily,
        });
        R.text += c.ch;
      });
      runs.forEach(function (R) {
        var latinCh = (R.text.match(/[A-Za-z0-9]/) || ['a'])[0];
        var eaCh = (R.text.match(/[　-鿿＀-￯]/) || ['あ'])[0];
        R.latin = pickFont(R.list, latinCh); R.ea = pickFont(R.list, eaCh);
        delete R.key; delete R.list;
      });
      return runs;
    };
    var left = Math.min.apply(null, lines.map(function (L) { return L.left; }));
    var right = Math.max.apply(null, lines.map(function (L) { return L.right; }));
    var mid0 = (lines[0].top + lines[0].bottom) / 2;
    var ta = ccs.textAlign;
    var align = ta === 'center' ? 'ctr' : ta === 'right' || ta === 'end' ? 'r' : 'l';
    // 1行は字の高さの箱に置き、行送りは決めない（行の高さで固定すると PowerPoint は字を行の下寄りに置くため、line-height が大きいほど下にずれる）
    if (lines.length === 1) out.push({ t: 'text', x: left, y: lines[0].top, w: right - left, h: lines[0].bottom - lines[0].top, pitch: null, align: align, lines: lines.map(runsOf), name: label(container) });
    else out.push({ t: 'text', x: left, y: mid0 - pitch / 2, w: right - left, h: pitch * lines.length, pitch: pitch, align: align, lines: lines.map(runsOf), name: label(container) });
  }

  // ── 疑似要素 ::before / ::after を本物の span にする（変換のあいだだけ） ──
  var made = [];
  var sheet = null;
  function materialize(root) {
    if (!sheet) { sheet = document.createElement('style'); sheet.textContent = '.pptx-mat-b::before{content:none!important}.pptx-mat-a::after{content:none!important}'; document.head.appendChild(sheet); }
    var els = [root].concat(Array.from(root.querySelectorAll('*')));
    var todo = [];
    els.forEach(function (el) {
      if (el instanceof SVGElement) return;
      ['::before', '::after'].forEach(function (which) {
        var ps = getComputedStyle(el, which);
        var content = ps.content;
        if (!content || content === 'none' || content === 'normal' || ps.display === 'none') return;
        todo.push({ el: el, which: which, ps: ps, content: content });
      });
    });
    // 先にすべてを測ってから入れ替える（入れ替えた後の値で別の疑似要素を測らない）
    todo = todo.map(function (t) {
      var style = {};
      for (var i = 0; i < t.ps.length; i++) { var k = t.ps[i]; if (k !== 'content') style[k] = t.ps.getPropertyValue(k); }
      var m = /^"((?:[^"\\]|\\.)*)"$/.exec(t.content);
      return Object.assign(t, { style: style, text: m ? m[1].replace(/\\(.)/g, '$1') : null });
    });
    todo.forEach(function (t) {
      if (t.text == null) return; // counter() や attr() は元のまま（図形にしない）
      var span = document.createElement('span');
      span.dataset.pptxPseudo = t.which;
      for (var k in t.style) span.style.setProperty(k, t.style[k]);
      span.textContent = t.text;
      if (t.which === '::before') { t.el.insertBefore(span, t.el.firstChild); t.el.classList.add('pptx-mat-b'); } else { t.el.appendChild(span); t.el.classList.add('pptx-mat-a'); }
      made.push({ el: t.el, span: span });
    });
  }
  function unmaterialize() {
    made.forEach(function (m) { m.span.remove(); m.el.classList.remove('pptx-mat-b', 'pptx-mat-a'); });
    made = [];
  }

  // 画像にする要素。id は __pptx.iso で切り出すため
  function fallback(el, why) {
    var target = el;
    if (target.dataset && target.dataset.pptxPseudo) target = target.parentElement; // 疑似要素は持ち主ごと
    if (!target.dataset.pptxId) target.dataset.pptxId = 'f' + (++seq);
    var b = box(target.getBoundingClientRect());
    FB.push({ id: target.dataset.pptxId, scene: sceneOf(target), text: label(target), why: why });
    return { t: 'pic', fb: target.dataset.pptxId, x: b.x, y: b.y, w: b.w, h: b.h, name: label(target), alt: (target.textContent || '').replace(/\s+/g, ' ').trim() };
  }

  function opacityAbove(el) {
    var op = 1;
    for (var p = el.parentElement; p && p.id !== 'composition'; p = p.parentElement) op *= num(getComputedStyle(p).opacity);
    return op;
  }
  function clipAbove(el) {
    var clip = null;
    var chain = [];
    for (var p = el.parentElement; p && p.id !== 'composition'; p = p.parentElement) chain.unshift(p);
    chain.forEach(function (p) { clip = clipOf(p, getComputedStyle(p), clip); });
    return clip;
  }
  function clipOf(el, cs, clip) {
    if (cs.overflowX === 'visible' && cs.overflowY === 'visible') return clip;
    var b = box(el.getBoundingClientRect());
    var bt = num(cs.borderTopWidth), br = num(cs.borderRightWidth), bb = num(cs.borderBottomWidth), bl = num(cs.borderLeftWidth);
    var outer = radiiOf(cs, b.w, b.h);
    var c = { x: b.x + bl, y: b.y + bt, w: b.w - bl - br, h: b.h - bt - bb, radii: [Math.max(0, outer[0] - Math.max(bt, bl)), Math.max(0, outer[1] - Math.max(bt, br)), Math.max(0, outer[2] - Math.max(bb, br)), Math.max(0, outer[3] - Math.max(bb, bl))] };
    if (!clip) return c;
    var x0 = Math.max(c.x, clip.x), y0 = Math.max(c.y, clip.y);
    return { x: x0, y: y0, w: Math.max(0, Math.min(c.x + c.w, clip.x + clip.w) - x0), h: Math.max(0, Math.min(c.y + c.h, clip.y + clip.h) - y0), radii: c.radii };
  }

  // 1つの要素とその中身
  function walk(el, op, clip, out, ctx) {
    var cs = getComputedStyle(el);
    if (cs.display === 'none') return;
    if (ctx.isRoot(el) && el !== ctx.top) {
      var g = { t: 'group', name: label(el), children: [] };
      walk(el, op, clip, g.children, Object.assign({}, ctx, { top: el, inRoot: true }));
      if (g.children.length) (ctx.inRoot ? out : ctx.tops).push(g);
      return;
    }
    op *= num(cs.opacity === '' ? 1 : cs.opacity);
    if (op < 0.01) return;
    var why = unsupported(el, cs);
    if (why) {
      if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true }) && !el.querySelector('*')) return;
      out.push(fallback(el, why));
      return;
    }
    var b = box(el.getBoundingClientRect());
    if (cs.visibility === 'visible' && cs.display !== 'contents') {
      var bad = boxShapes(cs, b, op, clip, label(el), out);
      if (bad) { out.push(fallback(el, bad)); return; }
    }
    inlineContent(el, op, clip, out);
    var cclip = clipOf(el, cs, clip);
    for (var c = el.firstElementChild; c; c = c.nextElementSibling) {
      var ccs = getComputedStyle(c);
      if (isInlineBox(ccs)) continue; // 文字と一緒に描いた
      walk(c, op, cclip, out, ctx);
    }
  }

  function begin() {
    var comp = document.getElementById('composition');
    CR = comp.getBoundingClientRect();
    SC = CR.width / comp.offsetWidth || 1;
    FB = [];
    return comp;
  }
  var isRoot = function (el) { return !!(el.dataset && (el.dataset.pptxId && el.dataset.pptxId[0] === 'p' || el.hasAttribute('data-at') || el.hasAttribute('data-anim'))); };
  // PPTX専用のデッキ：シーンの直下の要素ごとに1グループ
  var isTop = function (el) { return !!(el.parentElement && el.parentElement.hasAttribute('data-scene')); };

  return {
    // スライドの最初の状態：背景の色と、「固定の要素」のグループ＋現れる印のある要素ごとのグループ
    // （top が true なら、シーンの直下の要素ごとのグループ。PPTX専用のデッキの完成した画面に使う）
    slide: function (top) {
      var comp = begin();
      materialize(comp);
      try {
        var tops = [];
        var fixed = { t: 'group', name: '固定の要素', children: [] };
        var ctx = { isRoot: top ? isTop : isRoot, top: comp, inRoot: false, tops: tops };
        var ccs = getComputedStyle(comp);
        var bgc = color(ccs.backgroundColor);
        for (var c = comp.firstElementChild; c; c = c.nextElementSibling) walk(c, 1, null, fixed.children, ctx);
        var items = (fixed.children.length ? [fixed] : []).concat(tops);
        return { bg: bgc ? bgc.c : 'FFFFFF', items: items, fallbacks: FB };
      } finally { unmaterialize(); }
    },
    // 現れる要素1つを1つのグループに
    element: function (id) {
      var comp = begin();
      var el = comp.querySelector('[data-pptx-id="' + id + '"]');
      if (!el) return { item: null, fallbacks: [] };
      materialize(el);
      try {
        var g = { t: 'group', name: label(el), children: [] };
        var ctx = { isRoot: isRoot, top: el, inRoot: true, tops: [] };
        walk(el, opacityAbove(el), clipAbove(el), g.children, ctx);
        return { item: g.children.length ? g : null, fallbacks: FB };
      } finally { unmaterialize(); }
    },
    // 透明な画像が空か（何も描かれていないか）
    async empty(b64) {
      var im = await window.__pptx.load(b64);
      var d = im.g.getImageData(0, 0, im.c.width, im.c.height).data;
      for (var i = 3; i < d.length; i += 4) if (d[i] > 8) return false;
      return true;
    },
  };
})();
`;

async function cmdPptx(pos, opt) {
  const P = deckPaths(pos[0]);
  const tl = loadTimeline(P);
  const script = loadScript(P);
  const out = path.resolve(opt.out || path.join(P.out, `${path.basename(P.root)}.pptx`));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const fps = tl.fps;
  const W = tl.width, H = tl.height;
  const PAD = 64; // 影（ずらした影 8〜10px）や疑似要素（つなぎの線など）のはみ出しを含めるための余白
  const browser = await launchBrowser();
  const slides = [];
  let elementSteps = 0, patchSteps = 0;
  let font = null;
  const fallbacks = new Map(); // 画像にした要素（id → シーン・文字・理由）
  try {
    const page = await openDeck(browser, P, tl, '&mode=live&static=1&notransition=1&subtitles=0');
    const errs = await page.evaluate('window.__motion.errors.slice()');
    if (errs.length) fail('デッキにエラーがあります。check で直してから書き出してください:\n  ' + errs.join('\n  '));
    await page.evaluate(PPTX_HELPERS + '; true');
    await page.evaluate(PPTX_SHAPES + '; true');
    const stops = await page.evaluate('__motion.stops');
    const scenes = await page.evaluate('__motion.sceneInfo()');
    const shot = async () => (await page.capture('png')).toString('base64');
    const transparent = (on) => page.send('Emulation.setDefaultBackgroundColorOverride', on ? { color: { r: 0, g: 0, b: 0, a: 0 } } : {});
    // 図形にできなかった要素（fb の印）を透明な画像に切り出し、空のものと空のグループを除く
    const capturePics = async (items, found) => {
      const pics = [];
      (function collect(list) { for (const it of list) { if (it.t === 'group') collect(it.children); else if (it.t === 'pic' && it.fb) pics.push(it); } })(items);
      if (pics.length) {
        await transparent(true);
        for (const it of pics) {
          const x = Math.max(0, Math.floor(it.x - PAD)), y = Math.max(0, Math.floor(it.y - PAD));
          const w = Math.min(W - x, Math.ceil(it.w + PAD * 2)), h = Math.min(H - y, Math.ceil(it.h + PAD * 2));
          if (w <= 0 || h <= 0) { it.drop = true; continue; }
          await page.evaluate(`__pptx.iso(${JSON.stringify(it.fb)}); true`);
          const b64 = (await page.capture('png', 92, { x, y, width: w, height: h })).toString('base64');
          await page.evaluate('__pptx.unIso(); true');
          if (await page.evaluate(`__pptx.conv.empty(${JSON.stringify(b64)})`)) { it.drop = true; continue; }
          const f = found.find((z) => z.id === it.fb);
          if (f && !fallbacks.has(f.id)) fallbacks.set(f.id, f);
          Object.assign(it, { png: Buffer.from(b64, 'base64'), x, y, w, h });
          delete it.fb;
        }
        await transparent(false);
      }
      const prune = (list) => list.filter((it) => !it.drop && (it.t !== 'group' || (it.children = prune(it.children)).length));
      return prune(items);
    };
    const count = (items, n = { sp: 0, text: 0, pic: 0 }) => { for (const it of items) { if (it.t === 'group') count(it.children, n); else n[it.t]++; } return n; };
    if (script.format === 'pptx') {
      // PPTX専用のデッキ：1シーン＝1スライド。各シーンの完成した画面を図形・テキストにする。アニメーションと画面の切り替えはなし
      for (const sc of scenes) {
        const mine = stops.filter((s) => s >= sc.start && s < sc.start + sc.duration);
        await page.seek(mine.length ? mine[mine.length - 1] : sc.start);
        const s = await page.evaluate('__pptx.conv.slide(true)');
        const items = await capturePics(s.items, s.fallbacks);
        const notes = sc.notes ? [sc.notes, ''] : [];
        sc.cues.forEach((c) => notes.push(c.text, ...(c.note ? [`　メモ: ${c.note}`] : [])));
        slides.push({ bg: s.bg, transition: null, notes, items, steps: [] });
        const n = count(items);
        log(`  ${sc.id}: 図形 ${n.sp}・文字 ${n.text}・画像 ${n.pic}`);
      }
    }
    const SPRINGY = ['up', 'down', 'left', 'right', 'scale', 'zoom', 'pop', 'fade', 'blur'];
    const TWEENY = ['draw', 'wipe', 'grow', 'grow-y', 'type', 'words', 'highlight', 'wipe-down', 'progress', 'strike'];
    for (const sc of script.format === 'pptx' ? [] : scenes) {
      const mine = stops.filter((s) => s >= sc.start && s < sc.start + sc.duration);
      await page.seek(sc.start);
      // 1画面＝1スライド。シーンの最初のスライドはシーンの切り替え、途中で分けたスライドはフェードで入る
      let cur = null;
      const sceneSlides = [];
      // background の絵は判定（check）にだけ使う。スライドに置くのは、今見えているものを図形にしたもの
      const startSlide = async (b64, transition) => {
        const s = await page.evaluate('__pptx.conv.slide()');
        const items = await capturePics(s.items, s.fallbacks);
        cur = { bg: s.bg, background: b64, transition, notes: [], items, steps: [], visible: [], layerOf: new Map(), clicks: 0 };
        sceneSlides.push(cur);
      };
      await startSlide(await shot(), { kind: sc.transition, dir: sc.direction });
      if (sc.notes) cur.notes.push(sc.notes, '');
      let prev = cur.background;
      let heads = await page.evaluate(`__pptx.headings(${JSON.stringify(sc.id)})`);
      let from = sc.start - 1;
      for (let k = 0; k < mine.length; k++) {
        const stop = mine[k];
        await page.seek(stop);
        const next = await shot();
        const ents = await page.evaluate(`__motion.entering(${from}, ${stop})`);
        // 見出しが消えたら画面の入れ替わり：このステップから新しいスライドにする
        const nowHeads = await page.evaluate(`__pptx.headings(${JSON.stringify(sc.id)})`);
        const split = k > 0 && heads.some((i) => !nowHeads.includes(i));
        heads = nowHeads;
        if (split) {
          await page.evaluate(`__pptx.hide(${JSON.stringify(ents.map((e) => e.id))}); true`);
          const bg = await shot();
          await startSlide(bg, { kind: 'fade' });
          await page.evaluate('__pptx.unhide(); true');
          prev = bg;
        }
        // 要素を透明な絵に切り出す
        const pieces = [];
        await transparent(true);
        for (const e of ents) {
          const x = Math.max(0, Math.floor(e.rect.x - PAD)), y = Math.max(0, Math.floor(e.rect.y - PAD));
          const w = Math.min(W - x, Math.ceil(e.rect.w + PAD * 2)), h = Math.min(H - y, Math.ceil(e.rect.h + PAD * 2));
          if (w <= 0 || h <= 0) continue;
          await page.evaluate(`__pptx.iso(${JSON.stringify(e.id)}); true`);
          const b64 = (await page.capture('png', 92, { x, y, width: w, height: h })).toString('base64');
          await page.evaluate('__pptx.unIso(); true');
          pieces.push({ e, b64, x, y, w, h });
        }
        await transparent(false);
        // 現れる要素を図形のグループにする
        for (const p of pieces) {
          const r = await page.evaluate(`__pptx.conv.element(${JSON.stringify(p.e.id)})`);
          p.item = r.item ? (await capturePics([r.item], r.fallbacks))[0] : null;
        }
        // 消える要素（このスライドで前に絵として出したもの）
        const exits = (await page.evaluate(`__motion.exiting(${from}, ${stop})`)).filter((x) => cur.layerOf.has(x.id));
        const layersAfter = cur.visible.filter((l) => !exits.some((x) => x.id === l.id)).concat(pieces.map((p) => ({ id: p.e.id, b64: p.b64, x: p.x, y: p.y })));
        const res = await page.evaluate(`__pptx.check(${JSON.stringify(prev)}, ${JSON.stringify(next)}, ${JSON.stringify(cur.background)}, ${JSON.stringify(layersAfter)}, ${W}, ${H})`);
        if (process.env.MOTION_DEBUG) log(`    [${sc.id} ${k}]${split ? ' 新しいスライド' : ''} 現れる${pieces.length} 消える${exits.length} 差 ${res.box ? res.box.n : 0} 残り ${res.rest ? res.rest.n + ' (' + res.rest.x + ',' + res.rest.y + ' ' + res.rest.w + 'x' + res.rest.h + ')' : '-'}`);
        // このステップに属する文（台本）
        const lines = sc.cues.filter((c) => c.start > from && c.start <= stop);
        const first = cur.steps.length === 0 && (k === 0 || split);
        const label = first ? '【スライド開始】' : `【クリック ${cur.clicks + 1}】`;
        if (!res.box && !split) {
          // 見た目が変わらないステップはクリックにしない（前のステップに続けて読む）
          const last = cur.clicks ? `【クリック ${cur.clicks}】` : '【スライド開始】';
          lines.forEach((c) => cur.notes.push(`${last} ${c.text}`, ...(c.note ? [`　メモ: ${c.note}`] : [])));
          from = stop; prev = next;
          continue;
        }
        const t0 = Math.min(...ents.map((e) => e.begin), Infinity);
        const effects = [];
        for (const x of exits) effects.push({ item: cur.layerOf.get(x.id), kind: 'exitFade', dur: 300, delay: 0 });
        for (const p of pieces) {
          if (!p.item) continue;
          p.item.name = p.e.text.slice(0, 30) || p.e.anims.join(' ');
          cur.items.push(p.item);
          cur.layerOf.set(p.e.id, cur.items.length - 1);
          const springOnly = p.e.anims.some((a) => SPRINGY.includes(a)) && !p.e.anims.some((a) => TWEENY.includes(a));
          effects.push({ item: cur.items.length - 1, kind: effectFor(p.e.anims), dur: Math.min(3000, ((springOnly ? 15 : p.e.dur) * 1000) / fps), delay: ((p.e.begin - t0) * 1000) / fps });
        }
        cur.visible = layersAfter;
        if (pieces.length) elementSteps++;
        if (res.rest) {
          // 要素の出し入れで説明できない変化（強調の移動、独自の動き）は、その範囲だけ本物の絵で重ねる
          patchSteps++;
          const b = res.rest;
          const x = Math.max(0, b.x - 4), y = Math.max(0, b.y - 4), w = Math.min(W - x, b.w + 8), h = Math.min(H - y, b.h + 8);
          const b64 = await page.evaluate(`__pptx.crop(${JSON.stringify(next)}, ${x}, ${y}, ${w}, ${h})`);
          cur.items.push({ t: 'pic', png: Buffer.from(b64, 'base64'), x, y, w, h, name: `ステップ${k}の変化`, alt: lines.map((c) => c.text).join(' ') });
          effects.push({ item: cur.items.length - 1, kind: 'fade', dur: 400, delay: 0 });
          cur.visible.push({ id: 'patch' + cur.items.length, b64, x, y });
        }
        cur.steps.push({ auto: first, effects });
        if (!first) cur.clicks++;
        lines.forEach((c) => cur.notes.push(`${label} ${c.text}`, ...(c.note ? [`　メモ: ${c.note}`] : [])));
        from = stop;
        prev = next;
      }
      for (const s of sceneSlides) slides.push({ bg: s.bg, transition: s.transition, notes: s.notes, items: s.items, steps: s.steps });
      const n = count(sceneSlides.flatMap((s) => s.items));
      log(`  ${sc.id}: ${sceneSlides.length}スライド、${sceneSlides.reduce((m, s) => m + s.clicks, 0) + sceneSlides.length - 1}クリック、図形 ${n.sp}・文字 ${n.text}・画像 ${n.pic}`);
    }
    // PPTX のテーマのフォント（発表者ノートの文字）は、テンプレートの本文の書体（kit の --jp）の先頭にそろえる
    font = await page.evaluate(`getComputedStyle(document.getElementById('composition')).getPropertyValue('--jp').split(',')[0].trim().replace(/^["']|["']$/g, '')`);
    await page.close();
  } finally {
    await browser.close();
  }
  const r = buildPptx(out, { title: script.title, width: W, height: H, slides, font: font || undefined });
  if (script.format === 'pptx') log(`PPTX: ${out}（PPTX専用のデッキ。${r.slides}スライド、図形 ${r.shapes}・文字 ${r.texts}・画像 ${r.images}、グループ ${r.groups}。アニメーション・画面の切り替えなし）`);
  else log(`PPTX: ${out}（${r.slides}スライド、図形 ${r.shapes}・文字 ${r.texts}・画像 ${r.images}、グループ ${r.groups}。要素のアニメーション ${elementSteps}ステップ、差分の重ね ${patchSteps}ステップ）`);
  if (fallbacks.size) {
    log(`図形にできず画像にした要素 ${fallbacks.size}件（直すなら HTML/CSS を図形にできる範囲に。references/player.md の「pptx」）:`);
    for (const f of fallbacks.values()) log(`  - ${f.scene}「${f.text}」: ${f.why}`);
  }
}

// ───────────────────────── bundle ─────────────────────────

const MIME = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.otf': 'font/otf', '.m4a': 'audio/mp4', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.mp4': 'video/mp4', '.webm': 'video/webm' };
const isLocal = (u) => u && !/^(?:[a-z]+:|\/\/|#|data:)/i.test(u);
const dataUri = (file) => `data:${MIME[path.extname(file).toLowerCase()] || 'application/octet-stream'};base64,${fs.readFileSync(file).toString('base64')}`;

function inlineCssUrls(css, baseDir) {
  return css.replace(/url\((['"]?)([^'")]+)\1\)/g, (m, q, u) => {
    const f = path.resolve(baseDir, u.split(/[?#]/)[0]);
    return isLocal(u) && exists(f) ? `url("${dataUri(f)}")` : m;
  });
}

function cmdBundle(pos, opt) {
  const P = deckPaths(pos[0]);
  const tl = loadTimeline(P);
  const outFile = path.resolve(opt.out || path.join(P.root, 'dist', `${path.basename(P.root)}.html`));
  const outDir = path.dirname(outFile);
  fs.mkdirSync(outDir, { recursive: true });
  let html = fs.readFileSync(P.index, 'utf8');
  // boot.js の1行を、決まった順の読み込みと起動に展開してから埋め込む
  html = html.replace(BOOT_TAG, (tag) => {
    const b = bootLists();
    const extra = (name) => ((new RegExp(`data-${name}=["']([^"']*)["']`).exec(tag) || [])[1] || '').split(',').map((x) => x.trim()).filter(Boolean);
    const css = b.css.concat(extra('css'));
    const js = b.js.slice(0, 3).concat(extra('js'), b.js.slice(3));
    return css.map((c) => `<link rel="stylesheet" href="${c}">`).join('\n') + '\n' + js.map((j) => `<script src="${j}"></script>`).join('\n') + '\n<script>window.__motionBoot = { bundled: true }; Motion.start();</script>';
  });
  BOOT_TAG.lastIndex = 0;
  html = html.replace(/<link\s+[^>]*rel=["']stylesheet["'][^>]*>/g, (tag) => {
    const href = /href=["']([^"']+)["']/.exec(tag);
    if (!href || !isLocal(href[1])) return tag;
    const f = path.resolve(P.root, href[1]);
    if (!exists(f)) fail(`見つかりません: ${href[1]}`);
    return `<style data-src="${href[1]}">\n${inlineCssUrls(fs.readFileSync(f, 'utf8'), path.dirname(f))}\n</style>`;
  });
  html = html.replace(/<script\s+[^>]*src=["']([^"']+)["'][^>]*><\/script>/g, (tag, src) => {
    if (!isLocal(src)) return tag;
    const f = path.resolve(P.root, src);
    if (!exists(f)) fail(`見つかりません: ${src}`);
    let js = fs.readFileSync(f, 'utf8');
    if (path.basename(f) === 'timeline.js' && tl.audio) {
      const audioFile = path.join(P.root, tl.audio);
      let ref;
      if (opt['external-audio']) {
        ref = path.basename(audioFile);
        fs.copyFileSync(audioFile, path.join(outDir, ref));
      } else ref = dataUri(audioFile);
      const t = Object.assign({}, tl, { audio: ref });
      js = `window.MOTION_TIMELINE = ${JSON.stringify(t)};\n`;
    }
    return `<script>\n${js.replace(/<\/script/gi, '<\\/script')}\n</script>`;
  });
  html = html.replace(/(<(?:img|source|video|audio)\b[^>]*\s(?:src|poster)=["'])([^"']+)(["'])/g, (m, a, u, b) => {
    const f = path.resolve(P.root, u);
    return isLocal(u) && exists(f) ? a + dataUri(f) + b : m;
  });
  html = html.replace(/(<style[^>]*>)([\s\S]*?)(<\/style>)/g, (m, a, css, b) => a + inlineCssUrls(css, P.root) + b);
  html = html.replace(/(\sstyle=")([^"]*url\([^"]*)(")/g, (m, a, css, b) => a + inlineCssUrls(css.replace(/&quot;/g, '"'), P.root).replace(/"/g, '&quot;') + b);
  fs.writeFileSync(outFile, html);
  const mb = (fs.statSync(outFile).size / 1024 / 1024).toFixed(1);
  log(`1ファイルにまとめました: ${outFile}（${mb} MB）${opt['external-audio'] && tl.audio ? '＋音声ファイル' : ''}`);
  if (tl.estimated.length) warn(`仮の尺のシーンが含まれます: ${tl.estimated.join(', ')}`);
}

// ───────────────────────── extract（pptx から見た目を取り出す） ─────────────────────────
// テンプレートにするのは「見た目の決まり」だけ。文章は取り出さない（文字数と書式だけを残す）。
// 写真などの絵も中身なので保存しない（レイアウト・背景の絵と、何度も出る小さい飾りの絵だけを保存する）。

function readZip(file) {
  const buf = fs.readFileSync(file);
  let eocd = -1;
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 65557); i--) if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  if (eocd < 0) fail(`${file} は pptx（zip）として読めません`);
  const count = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16);
  const out = new Map();
  for (let k = 0; k < count; k++) {
    if (buf.readUInt32LE(p) !== 0x02014b50) fail(`${file} の zip の目次が壊れています`);
    const method = buf.readUInt16LE(p + 10), size = buf.readUInt32LE(p + 20);
    const nlen = buf.readUInt16LE(p + 28), xlen = buf.readUInt16LE(p + 30), clen = buf.readUInt16LE(p + 32);
    const name = buf.toString('utf8', p + 46, p + 46 + nlen);
    const lh = buf.readUInt32LE(p + 42);
    const start = lh + 30 + buf.readUInt16LE(lh + 26) + buf.readUInt16LE(lh + 28);
    const raw = buf.subarray(start, start + size);
    out.set(name, method === 8 ? zlib.inflateRawSync(raw) : Buffer.from(raw));
    p += 46 + nlen + xlen + clen;
  }
  return out;
}

/** 小さな XML の木: { n: 名前, a: 属性, c: 子, t: 文字 } */
function parseXml(src) {
  const root = { n: '#root', a: {}, c: [], t: '' };
  const stack = [root];
  const re = /<(\/?)([A-Za-z_][\w:.-]*)((?:\s+[\w:.-]+\s*=\s*(?:"[^"]*"|'[^']*'))*)\s*(\/?)>|<!\[CDATA\[([\s\S]*?)\]\]>|<[?!][\s\S]*?>|([^<]+)/g;
  const unesc = (s) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d)).replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16))).replace(/&amp;/g, '&');
  let m;
  while ((m = re.exec(src))) {
    if (m[2]) {
      if (m[1]) { stack.pop(); continue; }
      const a = {};
      for (const am of m[3].matchAll(/([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g)) a[am[1]] = unesc(am[2] ?? am[3]);
      const el = { n: m[2], a, c: [], t: '' };
      stack[stack.length - 1].c.push(el);
      if (!m[4]) stack.push(el);
    } else if (m[6] != null || m[5] != null) stack[stack.length - 1].t += m[5] != null ? m[5] : unesc(m[6]);
  }
  return root;
}
const kid = (el, name) => el && el.c.find((x) => x.n === name);
const kids = (el, name) => (el ? el.c.filter((x) => x.n === name) : []);
const dig = (el, ...names) => names.reduce((e, n) => kid(e, n), el);
const findAll = (el, name, acc = []) => { if (!el) return acc; for (const x of el.c) { if (x.n === name) acc.push(x); findAll(x, name, acc); } return acc; };

// 色: 16進＋HSL の調整（lumMod / lumOff / tint / shade / alpha）
function hexToHsl(hex) {
  const r = parseInt(hex.slice(0, 2), 16) / 255, g = parseInt(hex.slice(2, 4), 16) / 255, b = parseInt(hex.slice(4, 6), 16) / 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx === mn) return [0, 0, l];
  const d = mx - mn, s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
  const h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h / 6, s, l];
}
function hslToHex([h, s, l]) {
  const f = (p, q, t) => { if (t < 0) t += 1; if (t > 1) t -= 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; };
  let r = l, g = l, b = l;
  if (s) { const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q; r = f(p, q, h + 1 / 3); g = f(p, q, h); b = f(p, q, h - 1 / 3); }
  return [r, g, b].map((x) => Math.round(Math.min(1, Math.max(0, x)) * 255).toString(16).padStart(2, '0')).join('').toUpperCase();
}

function makeColorReader(scheme, clrMap) {
  const PRESET = { black: '000000', white: 'FFFFFF', red: 'FF0000', green: '008000', blue: '0000FF', yellow: 'FFFF00', gray: '808080' };
  return function color(el) {
    if (!el) return null;
    const c = el.c.find((x) => /^a:(srgbClr|schemeClr|sysClr|prstClr|scrgbClr|hslClr)$/.test(x.n));
    if (!c) return null;
    let hex = null, ref = null;
    if (c.n === 'a:srgbClr') hex = c.a.val;
    else if (c.n === 'a:sysClr') hex = c.a.lastClr || (c.a.val === 'window' ? 'FFFFFF' : '000000');
    else if (c.n === 'a:prstClr') hex = PRESET[c.a.val] || null;
    else if (c.n === 'a:schemeClr') { ref = c.a.val; const k = clrMap[ref] || ref; hex = scheme[k] ? scheme[k].slice(1) : null; }
    if (!hex) return null;
    let alpha = 1;
    let hsl = hexToHsl(hex);
    for (const m of c.c) {
      const v = +m.a.val / 100000;
      if (m.n === 'a:lumMod') hsl[2] *= v;
      else if (m.n === 'a:lumOff') hsl[2] += v;
      else if (m.n === 'a:tint') hsl[2] = hsl[2] * v + (1 - v);
      else if (m.n === 'a:shade') hsl[2] *= v;
      else if (m.n === 'a:alpha') alpha = v;
    }
    const out = { hex: '#' + hslToHex(hsl) };
    if (ref) out.scheme = ref;
    if (alpha < 1) out.alpha = +alpha.toFixed(2);
    return out;
  };
}

function cmdExtract(pos, opt) {
  const src = path.resolve(pos[0] || fail('pptx を指定してください: extract <pptx> <出力フォルダ>'));
  if (!exists(src)) fail(`${src} がありません`);
  const outDir = path.resolve(pos[1] || fail('出力フォルダを指定してください: extract <pptx> <出力フォルダ>'));
  if (outDir.startsWith(SKILL + path.sep)) fail('出力フォルダはスキルの外にしてください（取り出したものはテンプレートを作る材料で、コミットしない）');
  fs.mkdirSync(path.join(outDir, 'media'), { recursive: true });
  const zip = readZip(src);
  const xml = (name) => zip.has(name) ? parseXml(zip.get(name).toString('utf8')) : null;
  const relsOf = (part) => {
    const dir = path.posix.dirname(part), r = xml(path.posix.join(dir, '_rels', path.posix.basename(part) + '.rels'));
    const map = {};
    for (const x of findAll(r, 'Relationship')) map[x.a.Id] = { type: x.a.Type.split('/').pop(), target: x.a.TargetMode === 'External' ? null : path.posix.normalize(path.posix.join(dir, x.a.Target)) };
    return map;
  };

  const pres = xml('ppt/presentation.xml');
  const sz = findAll(pres, 'p:sldSz')[0];
  const W = +sz.a.cx, H = +sz.a.cy;
  const presRels = relsOf('ppt/presentation.xml');
  const slideParts = findAll(pres, 'p:sldId').map((x) => presRels[x.a['r:id']].target);

  // テーマ（最初のマスターのもの）
  const firstMaster = presRels[findAll(pres, 'p:sldMasterId')[0].a['r:id']].target;
  const themePart = Object.values(relsOf(firstMaster)).find((r) => r.type === 'theme').target;
  const theme = xml(themePart);
  const scheme = {};
  for (const c of (findAll(theme, 'a:clrScheme')[0] || { c: [] }).c) {
    const v = c.c[0];
    scheme[c.n.slice(2)] = '#' + (v && (v.a.val && v.n === 'a:srgbClr' ? v.a.val : v.a.lastClr || v.a.val) || '000000').toUpperCase();
  }
  const fontOf = (el) => el && { latin: dig(el, 'a:latin')?.a.typeface || '', ea: dig(el, 'a:ea')?.a.typeface || '', jpan: kids(el, 'a:font').find((f) => f.a.script === 'Jpan')?.a.typeface || '' };
  const fs0 = findAll(theme, 'a:fontScheme')[0];
  const themeFonts = { major: fontOf(dig(fs0, 'a:majorFont')), minor: fontOf(dig(fs0, 'a:minorFont')) };

  const colorsUsed = new Map(), fontsUsed = new Map(), mediaUse = new Map();
  const bump = (m, k, n = 1) => { if (k) m.set(k, (m.get(k) || 0) + n); };
  const r3 = (v) => Math.round(v * 1000) / 1000;

  function readPart(part, where, inherit) {
    const doc = xml(part);
    const rels = relsOf(part);
    const masterEl = findAll(doc, 'p:clrMap')[0];
    const clrMap = Object.assign({ bg1: 'lt1', tx1: 'dk1', bg2: 'lt2', tx2: 'dk2' }, inherit?.clrMap, masterEl ? masterEl.a : {});
    const color = makeColorReader(scheme, clrMap);
    const useColor = (c, w = 1) => { if (c) bump(colorsUsed, c.hex, w); return c; };
    const useMedia = (rid, area, role) => {
      const t = rels[rid]?.target;
      if (!t) return null;
      if (!mediaUse.has(t)) mediaUse.set(t, { parts: new Set(), areas: [], roles: new Set() });
      const u = mediaUse.get(t); u.parts.add(where); u.areas.push(area); u.roles.add(role);
      return path.posix.basename(t);
    };
    function fill(spPr, area, role) {
      if (!spPr) return null;
      if (kid(spPr, 'a:noFill')) return { type: 'none' };
      const s = kid(spPr, 'a:solidFill');
      if (s) return { type: 'solid', ...useColor(color(s), area) };
      const g = kid(spPr, 'a:gradFill');
      if (g) {
        const stops = findAll(g, 'a:gs').map((x) => ({ at: r3(+x.a.pos / 100000), ...useColor(color(x), area / 2) }));
        const lin = kid(g, 'a:lin'), path_ = kid(g, 'a:path');
        return { type: 'gradient', kind: path_ ? path_.a.path : 'linear', angle: lin ? +lin.a.ang / 60000 : null, stops };
      }
      const b = kid(spPr, 'a:blipFill');
      if (b) return { type: 'image', image: useMedia(dig(b, 'a:blip')?.a['r:embed'], area, role) };
      if (kid(spPr, 'a:pattFill')) return { type: 'pattern' };
      return null;
    }
    function background() {
      const bg = findAll(doc, 'p:bg')[0];
      if (!bg) return null;
      const pr = kid(bg, 'p:bgPr');
      if (pr) return fill(pr, 1, 'background');
      const ref = kid(bg, 'p:bgRef');
      if (ref) return { type: 'themeBackground', idx: +ref.a.idx, ...useColor(color(ref), 1) };
      return null;
    }
    const phIndex = inherit?.ph || {};
    function textInfo(tb) {
      if (!tb) return null;
      const runs = findAll(tb, 'a:r').concat(findAll(tb, 'a:fld'));
      const chars = runs.reduce((n, r) => n + [...(dig(r, 'a:t')?.t || '')].length, 0);
      if (!chars) return null;
      const paras = kids(tb, 'a:p').filter((p) => findAll(p, 'a:t').some((t) => t.t.trim()));
      const sizes = new Map(), styles = { bold: 0, italic: 0, caps: 0 }, colors = new Map(), fonts = new Map();
      for (const r of runs) {
        const len = [...(dig(r, 'a:t')?.t || '')].length, pr = kid(r, 'a:rPr');
        if (!pr || !len) continue;
        if (pr.a.sz) bump(sizes, +pr.a.sz / 100, len);
        if (pr.a.b === '1') styles.bold += len;
        if (pr.a.i === '1') styles.italic += len;
        if (pr.a.cap === 'all') styles.caps += len;
        const c = color(kid(pr, 'a:solidFill')); if (c) { bump(colors, c.hex, len); bump(colorsUsed, c.hex, len / 400); }
        for (const f of ['a:latin', 'a:ea']) { const t = kid(pr, f)?.a.typeface; if (t) { bump(fonts, t, len); bump(fontsUsed, t, len); } }
      }
      const top = (m) => [...m].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k]) => k);
      const algn = paras.map((p) => kid(p, 'a:pPr')?.a.algn).filter(Boolean);
      const bodyPr = kid(tb, 'a:bodyPr');
      const bullets = paras.filter((p) => kid(kid(p, 'a:pPr'), 'a:buChar') || kid(kid(p, 'a:pPr'), 'a:buAutoNum')).length;
      const out = { chars, paragraphs: paras.length };
      if (sizes.size) out.sizePt = top(sizes);
      if (styles.bold * 2 > chars) out.bold = true;
      if (styles.italic * 2 > chars) out.italic = true;
      if (styles.caps * 2 > chars) out.allCaps = true;
      if (colors.size) out.color = top(colors);
      if (fonts.size) out.font = top(fonts);
      if (algn.length) out.align = top(new Map(algn.map((a) => [a, algn.filter((x) => x === a).length])))[0];
      if (bodyPr?.a.anchor) out.anchor = bodyPr.a.anchor;
      if (bullets) out.bullets = bullets;
      return out;
    }
    function box(xfrm, T) {
      const off = kid(xfrm, 'a:off'), ext = kid(xfrm, 'a:ext');
      if (!off || !ext) return null;
      const [x0, y0] = T(+off.a.x, +off.a.y), [x1, y1] = T(+off.a.x + +ext.a.cx, +off.a.y + +ext.a.cy);
      return { x: r3(x0 / W), y: r3(y0 / H), w: r3((x1 - x0) / W), h: r3((y1 - y0) / H) };
    }
    const placeholders = {};
    function shapes(tree, T) {
      const list = [];
      for (const el of tree.c) {
        const nv = el.c.find((x) => /^p:nv/.test(x.n));
        const ph = nv && findAll(nv, 'p:ph')[0];
        const spPr = kid(el, 'p:spPr') || kid(el, 'p:grpSpPr');
        const xfrm = spPr ? kid(spPr, 'a:xfrm') : kid(el, 'p:xfrm');
        let b = xfrm ? box(xfrm, T) : null;
        let phKey = null;
        if (ph) {
          phKey = ph.a.type || 'body';
          const inh = phIndex['idx:' + ph.a.idx] || phIndex['type:' + phKey];
          if (!b && inh) b = inh.box;
          placeholders['type:' + phKey] = placeholders['type:' + phKey] || { box: b };
          if (ph.a.idx) placeholders['idx:' + ph.a.idx] = { box: b };
        }
        const area = b ? Math.max(0, b.w) * Math.max(0, b.h) : 0;
        const s = {};
        if (el.n === 'p:sp') {
          s.kind = ph ? 'placeholder' : kid(nv, 'p:cNvSpPr')?.a.txBox === '1' ? 'text' : 'shape';
          if (ph) s.placeholder = phKey;
          const geom = kid(spPr, 'a:prstGeom')?.a.prst || (kid(spPr, 'a:custGeom') ? 'custom' : null);
          if (geom && !(s.kind !== 'shape' && geom === 'rect')) s.geom = geom;
          const f = fill(spPr, area, 'shape'); if (f && f.type !== 'none') s.fill = f;
          const ln = kid(spPr, 'a:ln');
          if (ln && !kid(ln, 'a:noFill')) { const c = color(kid(ln, 'a:solidFill')); if (c) s.line = { ...c, widthPt: ln.a.w ? r3(+ln.a.w / 12700) : null }; }
          const t = textInfo(kid(el, 'p:txBody')); if (t) s.text = t;
        } else if (el.n === 'p:pic') {
          s.kind = 'image';
          s.image = useMedia(findAll(el, 'a:blip')[0]?.a['r:embed'], area, ph ? 'placeholder' : 'picture');
        } else if (el.n === 'p:cxnSp') {
          s.kind = 'line';
          const ln = kid(spPr, 'a:ln'); const c = ln && color(kid(ln, 'a:solidFill'));
          if (c) s.line = { ...useColor(c, 0.01), widthPt: ln.a.w ? r3(+ln.a.w / 12700) : null };
        } else if (el.n === 'p:grpSp') {
          s.kind = 'group';
          const off = kid(xfrm, 'a:off'), ext = kid(xfrm, 'a:ext'), cho = kid(xfrm, 'a:chOff'), che = kid(xfrm, 'a:chExt');
          const G = off && ext && cho && che && +che.a.cx && +che.a.cy
            ? (x, y) => T(+off.a.x + (x - +cho.a.x) * +ext.a.cx / +che.a.cx, +off.a.y + (y - +cho.a.y) * +ext.a.cy / +che.a.cy)
            : T;
          s.children = shapes(el, G);
        } else if (el.n === 'p:graphicFrame') {
          const uri = findAll(el, 'a:graphicData')[0]?.a.uri || '';
          s.kind = /table/.test(uri) ? 'table' : /chart/.test(uri) ? 'chart' : /diagram/.test(uri) ? 'diagram' : 'object';
          if (s.kind === 'table') { const rows = findAll(el, 'a:tr'); s.rows = rows.length; s.cols = rows[0] ? kids(rows[0], 'a:tc').length : 0; }
        } else continue;
        if (b) s.box = b;
        if (xfrm?.a.rot) s.rotate = r3(+xfrm.a.rot / 60000);
        list.push(s);
      }
      return list;
    }
    const tree = findAll(doc, 'p:spTree')[0];
    const result = { background: background(), shapes: tree ? shapes(tree, (x, y) => [x, y]) : [] };
    return { result, rels, ph: Object.assign({}, phIndex, placeholders), clrMap };
  }

  // マスター → レイアウト → スライド の順に読み、プレースホルダーの位置を受け継ぐ
  const masters = new Map(), layouts = new Map();
  const slides = [];
  slideParts.forEach((part, i) => {
    const sRels = relsOf(part);
    const layoutPart = Object.values(sRels).find((r) => r.type === 'slideLayout')?.target;
    const masterPart = layoutPart && Object.values(relsOf(layoutPart)).find((r) => r.type === 'slideMaster')?.target;
    if (masterPart && !masters.has(masterPart)) masters.set(masterPart, readPart(masterPart, 'master', null));
    const M = masters.get(masterPart);
    if (layoutPart && !layouts.has(layoutPart)) {
      const L = readPart(layoutPart, 'layout', M);
      const lx = xml(layoutPart);
      L.name = findAll(lx, 'p:cSld')[0]?.a.name || path.posix.basename(layoutPart);
      L.type = findAll(lx, 'p:sldLayout')[0]?.a.type || null;
      L.slides = [];
      layouts.set(layoutPart, L);
    }
    const L = layouts.get(layoutPart);
    if (L) L.slides.push(i + 1);
    const S = readPart(part, 'slide' + (i + 1), L || M);
    const hidden = findAll(xml(part), 'p:sld')[0]?.a.show === '0';
    slides.push({ n: i + 1, layout: L ? L.name : null, ...(hidden ? { hidden: true } : {}), ref: null, ...S.result });
  });

  // 絵: レイアウト・マスター・背景の絵と、2か所以上に出る小さい絵（面積5%未満）だけ保存する（写真などは中身なので保存しない）
  const media = [];
  for (const [part, u] of mediaUse) {
    const name = path.posix.basename(part);
    const decorative = u.parts.has('master') || u.parts.has('layout') || u.roles.has('background') || (u.parts.size >= 2 && Math.max(...u.areas, 0) < 0.05);
    const entry = { file: name, usedIn: [...u.parts].sort(), maxArea: r3(Math.max(...u.areas, 0)) };
    if (decorative && zip.has(part)) { fs.writeFileSync(path.join(outDir, 'media', name), zip.get(part)); entry.saved = 'media/' + name; }
    else entry.saved = null;
    media.push(entry);
  }

  // 元のスライドの絵（比べる相手）。LibreOffice を画面に出さずに使う
  const refs = renderReferences(src, zip, slideParts.length, path.join(outDir, 'ref'), opt);
  if (refs) slides.forEach((s, i) => { if (refs[i]) s.ref = refs[i]; });

  const sortCount = (m, min = 0) => Object.fromEntries([...m].filter(([, v]) => v > min).sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, r3(v)]));
  const out = {
    source: path.basename(src),
    note: '見た目の決まりだけを取り出したもの。文章は含まない（text は文字数と書式だけ）。box は スライドの幅・高さに対する割合',
    slideSize: { widthEmu: W, heightEmu: H, ratio: r3(W / H) },
    theme: { colors: scheme, fonts: themeFonts },
    colorsUsed: sortCount(colorsUsed, 0.005),
    fontsUsed: sortCount(fontsUsed),
    masters: [...masters.values()].map((m) => m.result),
    layouts: [...layouts.values()].sort((a, b) => b.slides.length - a.slides.length).map((l) => ({ name: l.name, type: l.type, slides: l.slides, ...l.result })),
    slides,
    media,
  };
  fs.writeFileSync(path.join(outDir, 'extract.json'), JSON.stringify(out, null, 1) + '\n');
  log(`取り出しました: ${path.join(outDir, 'extract.json')}`);
  log(`  スライド ${slides.length}枚、レイアウト ${layouts.size}種（よく使う順: ${out.layouts.slice(0, 5).map((l) => `${l.name}×${l.slides.length}`).join('、')}）`);
  log(`  テーマのフォント: ${[themeFonts.major.latin, themeFonts.major.ea || themeFonts.major.jpan].filter(Boolean).join(' / ')}、よく使う色: ${Object.keys(out.colorsUsed).slice(0, 6).join(' ')}`);
  log(`  絵: 保存 ${media.filter((m) => m.saved).length}枚（飾り・背景）、保存しない ${media.filter((m) => !m.saved).length}枚（写真など）`);
  log(refs ? `  元のスライドの絵: ${path.join(outDir, 'ref')}` : '  元のスライドの絵は作っていません（LibreOffice がない）');
}

function findSoffice(opt) {
  const cands = [opt.soffice, process.env.MOTION_SOFFICE, '/Applications/LibreOffice.app/Contents/MacOS/soffice', which('soffice'), which('libreoffice')].filter(Boolean);
  return cands.find((c) => exists(c)) || null;
}

/** 1枚ずつの pptx に分けて LibreOffice（画面なし）で PNG にする。返り値は ref/ からの相対パスの配列 */
function renderReferences(src, zip, count, refDir, opt) {
  const soffice = findSoffice(opt);
  if (!soffice) { warn('LibreOffice がないので元のスライドの絵を作れません（macOS: brew install --cask libreoffice）'); return null; }
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'motion-extract-'));
  try {
    const presXml = zip.get('ppt/presentation.xml').toString('utf8');
    const ids = [...presXml.matchAll(/<p:sldId\b[^>]*\/>/g)].map((m) => m[0]);
    const files = [];
    for (let i = 0; i < count; i++) {
      const one = presXml.replace(/<p:sldIdLst>[\s\S]*?<\/p:sldIdLst>/, `<p:sldIdLst>${ids[i]}</p:sldIdLst>`);
      const f = path.join(tmp, `slide-${String(i + 1).padStart(2, '0')}.pptx`);
      writeZip(f, [...zip].map(([name, data]) => ({ name, data: name === 'ppt/presentation.xml' ? one : data })));
      files.push(f);
    }
    const env = { ...process.env };
    if (process.platform === 'darwin') {
      // 画面なしの LibreOffice は fontconfig でフォントを探すので、macOS のフォントの置き場所を教える
      const conf = path.join(tmp, 'fonts.conf');
      const dirs = ['/System/Library/Fonts', '/System/Library/Fonts/Supplemental', '/System/Library/AssetsV2/com_apple_MobileAsset_Font7', '/Library/Fonts', path.join(os.homedir(), 'Library/Fonts')];
      fs.writeFileSync(conf, `<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n${dirs.map((d) => `  <dir>${d}</dir>`).join('\n')}\n  <cachedir>${path.join(os.tmpdir(), 'motion-extract-fccache')}</cachedir>\n</fontconfig>\n`);
      env.FONTCONFIG_FILE = conf;
    }
    const filter = 'png:impress_png_Export:{"PixelWidth":{"type":"long","value":"1920"},"PixelHeight":{"type":"long","value":"' + Math.round(1920 * +/cy="(\d+)"/.exec(presXml.match(/<p:sldSz[^>]*>/)[0])[1] / +/cx="(\d+)"/.exec(presXml.match(/<p:sldSz[^>]*>/)[0])[1]) + '"}}';
    const r = spawnSync(soffice, ['--headless', '--norestore', `-env:UserInstallation=${pathToFileURL(path.join(tmp, 'profile')).href}`, '--convert-to', filter, '--outdir', tmp, ...files], { env, encoding: 'utf8', timeout: 20 * 60 * 1000 });
    if (r.status !== 0) { warn('LibreOffice で絵にできませんでした: ' + (r.stderr || '').trim().split('\n').pop()); return null; }
    fs.mkdirSync(refDir, { recursive: true });
    return files.map((f) => {
      const png = f.replace(/\.pptx$/, '.png');
      if (!exists(png)) return null;
      const name = path.basename(png);
      fs.copyFileSync(png, path.join(refDir, name));
      return 'ref/' + name;
    });
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ───────────────────────── main ─────────────────────────

const HELP = `motion-deck — ナレーションで動く HTML プレゼン

  init <フォルダ> [--title 題名] [--template 名前] [--format pptx]
                                  雛形を作り、仮の timeline まで用意する（テンプレートの既定は default）
                                  --format pptx は PPTX専用のデッキ（動き・声・字幕・章バーなし）
  runtime [deck]                    deck/motion/ の実行系をスキルの最新版に置き換える
  check [deck] [--scene id,..] [--no-browser]
                                    原稿・HTML・配置（はみ出し）を検査する
  ssml [deck]                       原稿から build/ssml/<id>.ssml を作る
  synth [deck] [--voice 名前] [--engine voxcpm2|omnivoice|qwen3-tts|s2]
        [--scenes id,..] [--force] [--dry-run]
                                    local-tts でシーンごとに音声を作る（原稿が変わったシーンだけ）
  timeline [deck] [--estimate]      音声の時刻から timeline.js と narration.m4a を作る
  still [deck] [--frames 0,90] [--scene id] [--cues] [--live] [--subtitles 0]
                                    静止画（PNG）と一覧画像を out/stills/ に書き出す
                                    --live は発表モードの各ステップ（配布資料にも使える）
  render [deck] [--out x.mp4] [--concurrency 4] [--from f --to f] [--scale 0.5]
         [--crf 18] [--subtitles 0] [--allow-estimated]
                                    MP4 に書き出す
  pdf [deck] [--out x.pdf] [--scene id,..]
                                    発表モードの1ステップを1ページにした PDF に書き出す（字幕なし、文字を選べる）
  pptx [deck] [--out x.pptx]       PowerPoint に書き出す（クリックごとのネイティブのアニメーション、
                                    切り替え、台本入りのノート）。PPTX専用のデッキは1シーン＝1スライドで、
                                    アニメーションと切り替えなし
  bundle [deck] [--out x.html] [--external-audio]
                                    CSS・JS・画像・音声を1つの HTML にまとめる
  extract <pptx> <出力フォルダ> [--soffice パス]
                                    pptx から見た目の決まり（色・フォント・背景・骨組み）を extract.json に、
                                    飾りの絵を media/ に、元のスライドの絵を ref/ に取り出す（文章は取り出さない）
`;

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const { pos, opt } = parseArgs(rest);
  const table = { pdf: cmdPdf, pptx: cmdPptx, init: cmdInit, runtime: cmdRuntime, check: cmdCheck, ssml: cmdSsml, synth: cmdSynth, timeline: cmdTimeline, still: cmdStill, render: cmdRender, bundle: cmdBundle, extract: cmdExtract };
  if (!cmd || cmd === 'help' || cmd === '--help' || !table[cmd]) {
    log(HELP);
    if (cmd && !table[cmd] && cmd !== 'help' && cmd !== '--help') process.exitCode = 2;
    return;
  }
  await table[cmd](pos, opt);
}

main().catch((e) => {
  if (e instanceof UserError) console.error('✗ ' + e.message);
  else console.error(e);
  process.exitCode = 1;
}).finally(() => {
  // CDP の WebSocket などが残ってもプロセスを終える
  setTimeout(() => process.exit(process.exitCode || 0), 50).unref();
});
