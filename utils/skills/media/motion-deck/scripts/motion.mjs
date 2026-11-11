#!/usr/bin/env node
// motion.mjs — motion-deck のコマンド。Node 22 以上（WebSocket を使う）、npm の依存なし。
// 外部コマンド: ffmpeg（音声の連結・動画）、Chrome 系ブラウザ（検査・静止画・動画）、
// uv + local-tts スキル（ナレーション）。
//
//   node motion.mjs <command> [deck] [options]
//
// command: init | runtime | check | ssml | synth | timeline | still | render | bundle

import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { buildPptx, effectFor } from './pptx.mjs';

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
    scenes: [],
  };
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
const PLAYER_REQUIRED = ['player', 'scrubber', 'timelinePanel', 'modeToggle', 'presenterView', 'narrationToggle', 'blackout', 'help', 'keyboard'];
const REQUIRED = ['boot', 'composition', 'scenes', 'theme', 'kit', 'chapterBar', 'subtitles', 'liveLayout', 'transitions', 'fonts'];

function bootLists() {
  const src = fs.readFileSync(path.join(SKILL, 'runtime', 'boot.js'), 'utf8');
  const arr = (name) => JSON.parse(new RegExp(`var ${name} = (\\[[^\\]]*\\]);`).exec(src)[1].replace(/'/g, '"'));
  return { css: arr('CSS'), js: arr('JS') };
}

/** deck/motion/ がスキルの runtime/ と完全に同じか（版の照合） */
function runtimeDrift(P) {
  const out = [];
  const walk = (dir, rel = '') => fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(path.join(dir, e.name), rel + e.name + '/') : [rel + e.name]);
  for (const f of walk(path.join(SKILL, 'runtime'))) {
    const a = path.join(SKILL, 'runtime', f), b = path.join(P.root, 'motion', f);
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
  copyDir(path.join(SKILL, 'template'), P.root, false);
  copyDir(path.join(SKILL, 'runtime'), path.join(P.root, 'motion'), true);
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
  copyDir(path.join(SKILL, 'runtime'), path.join(P.root, 'motion'), true);
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

const SECONDS_PER_CHAR = { voxcpm2: 0.33, omnivoice: 0.3, s2: 1.7, voicevox: 0.05 };

function cmdSynth(pos, opt) {
  const P = deckPaths(pos[0]);
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
  const est = todo.reduce((a, x) => a + x.chars, 0) * (SECONDS_PER_CHAR[t.engine || 'voxcpm2'] || 0.5) + 30;
  log(`合成（local-tts）: ${todo.length}シーン、${todo.reduce((a, x) => a + x.chars, 0)}文字。voice=${t.voice || '既定'} engine=${t.engine || '既定'}`);
  log(`目安: 約${Math.ceil(est / 60)}分`);
  if (opt['dry-run']) { todo.forEach((x) => log(`  ${x.sc.id}（${x.chars}文字）`)); return; }

  const localTts = findSkill('local-tts', opt);
  if (!localTts) fail('local-tts スキルが見つかりません。--local-tts <フォルダ> で指定してください');
  if (!which('uv')) fail('uv が見つかりません');

  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'motion-synth-'));
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
      run('uv', args, `local-tts（${x.sc.id}）`);
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
  log(`使い終わったらエンジンを止める: uv run --project "${path.join(localTts, 'tools')}" local-tts server stop`);
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
    scriptHash: sha(fs.readFileSync(P.script, 'utf8') + (exists(P.lexicon) ? fs.readFileSync(P.lexicon, 'utf8') : '')),
    generated: new Date().toISOString(),
    scenes,
  };
  fs.writeFileSync(P.timeline, `window.MOTION_TIMELINE = ${JSON.stringify(tl, null, 1)};\n`);
  const min = (cursor / fps / 60).toFixed(2);
  log(`timeline.js: ${scenes.length}シーン、${min}分（${cursor}フレーム @${fps}fps）${audio ? '、音声あり' : '、音声なし'}`);
  if (estimated.length) log(`  仮の尺（文字数からの見積もり）: ${estimated.join(', ')}`);
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
  const r = inspectSpoken(script, spoken, { allowLatin: !!opt['allow-latin'] });
  errors.push(...r.errors.map((e) => '[原稿] ' + e));
  warnings.push(...r.warnings.map((e) => '[原稿] ' + e));

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
  if (!/id=["']composition["'][^>]*data-chapter-bar|data-chapter-bar[^>]*id=["']composition["']/.test(html)) errors.push('[構成] #composition に data-chapter-bar がありません');
  for (const f of ['theme.css', 'scenes.js']) if (!exists(path.join(P.root, f))) errors.push(`[構成] ${f} がありません`);
  const drift = runtimeDrift(P);
  if (drift.length) errors.push(`[構成] 実行系がスキルの版と違います: ${drift.join(', ')} → node "${path.join(SKILL, 'scripts/motion.mjs')}" runtime "${P.root}"`);
  if (/@keyframes|transition\s*:/.test(html) || (exists(path.join(P.root, 'theme.css')) && /@keyframes/.test(fs.readFileSync(path.join(P.root, 'theme.css'), 'utf8')))) {
    warnings.push('[HTML] @keyframes / transition があります。時間に連動しないので書き出しでずれます');
  }

  let tl = exists(P.timeline) ? loadTimeline(P) : null;
  const hashNow = sha(fs.readFileSync(P.script, 'utf8') + (exists(P.lexicon) ? fs.readFileSync(P.lexicon, 'utf8') : ''));
  if (!tl || tl.scriptHash !== hashNow) {
    log('timeline.js が原稿より古いので作り直します。');
    tl = cmdTimeline([P.root], {});
  }
  if (tl.estimated.length) warnings.push(`[音声] 仮の尺のシーン: ${tl.estimated.join(', ')}（synth で音声を作ると本当の尺になる）`);

  if (!opt['no-browser']) {
    const browser = await launchBrowser();
    try {
      const page = await openDeck(browser, P, tl, '&subtitles=1');
      const feats = await page.evaluate('window.__motion.features()');
      const missing = REQUIRED.filter((k) => !feats[k]);
      if (missing.length) errors.push(`[機能] 備わっていない機能: ${missing.join(', ')}`);
      const runtimeErrors = await page.evaluate('window.__motion.errors.slice()');
      errors.push(...runtimeErrors.map((e) => '[実行] ' + e));
      const filter = opt.scene ? new Set(String(opt.scene).split(',')) : null;
      const seen = new Map();
      for (const pt of checkpoints(tl, filter)) {
        await page.seek(pt.frame);
        const issues = await page.evaluate('window.__motion.lint()');
        for (const is of issues) {
          const k = is.kind + is.el;
          if (!seen.has(k)) seen.set(k, { ...is, where: `${pt.scene} ${pt.label} f${pt.frame}` });
        }
      }
      // 発表モードの各ステップも同じ検査をする（動きを縮めた時間軸）
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
      // 人が開く形（プレーヤー）でも開き、機能の自己申告と、キー操作で実際に動くかを確かめる
      const pl = await openDeck(browser, P, tl, '&mode=live', { player: true });
      const pf = await pl.evaluate('window.__motionPlayer.features()');
      const pmissing = REQUIRED.concat(PLAYER_REQUIRED).filter((k) => !pf[k]);
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
        r.hasAudio = P.audioTime !== null;
        if (r.hasAudio) { const n0 = P.narration; key('v'); r.voice = P.narration === !n0; key('v'); r.voiceBack = P.narration === n0; }
        return r;
      })()`);
      const PROBES = { startLive: '?mode=live で発表モードになる', play: '→でステップの動きが始まる', next: '→をもう一度で次のステップの終わりへ', prev: '←で前のステップ', toVideo: 'P で動画モード', toLive: 'P で発表モードに戻る', blackOn: 'B で画面を隠す', blackOff: 'B で戻す', help: '? でヘルプ', helpClose: 'Esc でヘルプを閉じる', voice: 'V でナレーションのオン・オフ', voiceBack: 'V で戻す' };
      for (const [k, label] of Object.entries(PROBES)) if (k in probe && !probe[k]) errors.push(`[操作] ${label} が動きません`);
      if (!probe.hasAudio) warnings.push('[音声] narration がないので、ナレーションのオン・オフは確かめていません（synth のあとで check し直してください）');
      pl.pageErrors.forEach((e) => errors.push('[ブラウザ] ' + e));
      await pl.close();
      const later = await page.evaluate('window.__motion.errors.slice()');
      later.slice(runtimeErrors.length).forEach((e) => errors.push('[実行] ' + e));
      page.pageErrors.forEach((e) => errors.push('[ブラウザ] ' + e));
      for (const is of seen.values()) {
        const line = `[配置] ${is.where}: ${is.message} ${is.el}`;
        if (is.kind === 'safe-area' || is.kind === 'css-transition' || is.kind === 'overlap') warnings.push(line); else errors.push(line);
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
  else if (opt.cues) pts = checkpoints(tl, filter);
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
      const sc = tl.scenes.filter((s) => f >= s.start).pop();
      const file = path.join(dir, `${String(f).padStart(6, '0')}-${sc ? sc.id : 'frame'}.png`);
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

// ───────────────────────── pptx ─────────────────────────
//
// 発表モードの時間軸で、各ステップ（クリック）の絵を撮る。
//   要素モード：そのステップで現れる要素だけを透明な絵に切り出し、PowerPoint のアニメーションで出す。
//              背景＋切り出した絵を重ねた結果が本物の絵と一致するかを確かめてから使う。
//   差分モード：一致しない（強調の移動、消える要素、独自の動きなど）ときは、変わった範囲だけを
//              本物の絵から切り出してフェードで重ねる。見た目は必ず本物と同じになる。

const PPTX_HELPERS = `
window.__pptx = {
  style: null,
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
  try {
    const page = await openDeck(browser, P, tl, '&mode=live&static=1&notransition=1&subtitles=0');
    const errs = await page.evaluate('window.__motion.errors.slice()');
    if (errs.length) fail('デッキにエラーがあります。check で直してから書き出してください:\n  ' + errs.join('\n  '));
    await page.evaluate(PPTX_HELPERS + '; true');
    const stops = await page.evaluate('__motion.stops');
    const scenes = await page.evaluate('__motion.sceneInfo()');
    const shot = async () => (await page.capture('png')).toString('base64');
    const transparent = (on) => page.send('Emulation.setDefaultBackgroundColorOverride', on ? { color: { r: 0, g: 0, b: 0, a: 0 } } : {});
    for (const sc of scenes) {
      const mine = stops.filter((s) => s >= sc.start && s < sc.start + sc.duration);
      await page.seek(sc.start);
      const background = await shot();
      let prev = background;
      const pictures = [];
      const steps = [];
      const notes = [];
      if (sc.notes) notes.push(sc.notes, '');
      let from = sc.start - 1;
      let visible = []; // 背景の上に今見えている絵（重なり順）
      const layerOf = new Map(); // 要素の id → 絵の番号
      for (let k = 0; k < mine.length; k++) {
        const stop = mine[k];
        await page.seek(stop);
        const next = await shot();
        const ents = await page.evaluate(`__motion.entering(${from}, ${stop})`);
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
        // 消える要素（前に絵として出したもの）
        const exits = (await page.evaluate(`__motion.exiting(${from}, ${stop})`)).filter((x) => layerOf.has(x.id));
        const layersAfter = visible.filter((l) => !exits.some((x) => x.id === l.id)).concat(pieces.map((p) => ({ id: p.e.id, b64: p.b64, x: p.x, y: p.y })));
        const res = await page.evaluate(`__pptx.check(${JSON.stringify(prev)}, ${JSON.stringify(next)}, ${JSON.stringify(background)}, ${JSON.stringify(layersAfter)}, ${W}, ${H})`);
        if (process.env.MOTION_DEBUG) log(`    [${sc.id} ${k}] 現れる${pieces.length} 消える${exits.length} 差 ${res.box ? res.box.n : 0} 残り ${res.rest ? res.rest.n + ' (' + res.rest.x + ',' + res.rest.y + ' ' + res.rest.w + 'x' + res.rest.h + ')' : '-'}`);
        // このステップに属する文（台本）
        const lines = sc.cues.filter((c) => c.start > from && c.start <= stop);
        const label = k === 0 ? '【スライド開始】' : `【クリック ${k}】`;
        if (!res.box) {
          // 見た目が変わらないステップはクリックにしない（前のステップに続けて読む）
          lines.forEach((c) => notes.push(`${label} ${c.text}`, ...(c.note ? [`　メモ: ${c.note}`] : [])));
          from = stop; prev = next;
          continue;
        }
        const t0 = Math.min(...ents.map((e) => e.begin), Infinity);
        const SPRINGY = ['up', 'down', 'left', 'right', 'scale', 'zoom', 'pop', 'fade', 'blur'];
        const TWEENY = ['draw', 'wipe', 'grow', 'grow-y', 'type', 'words', 'highlight', 'wipe-down', 'progress', 'strike'];
        const effects = [];
        for (const x of exits) effects.push({ pic: layerOf.get(x.id), kind: 'exitFade', dur: 300, delay: 0 });
        for (const p of pieces) {
          pictures.push({ png: Buffer.from(p.b64, 'base64'), x: p.x, y: p.y, w: p.w, h: p.h, name: p.e.text.slice(0, 30) || p.e.anims.join(' '), alt: p.e.text });
          layerOf.set(p.e.id, pictures.length - 1);
          const springOnly = p.e.anims.some((a) => SPRINGY.includes(a)) && !p.e.anims.some((a) => TWEENY.includes(a));
          effects.push({ pic: pictures.length - 1, kind: effectFor(p.e.anims), dur: Math.min(3000, ((springOnly ? 15 : p.e.dur) * 1000) / fps), delay: ((p.e.begin - t0) * 1000) / fps });
        }
        visible = layersAfter;
        if (pieces.length) elementSteps++;
        if (res.rest) {
          // 要素の出し入れで説明できない変化（強調の移動、独自の動き）は、その範囲だけ本物の絵で重ねる
          patchSteps++;
          const b = res.rest;
          const x = Math.max(0, b.x - 4), y = Math.max(0, b.y - 4), w = Math.min(W - x, b.w + 8), h = Math.min(H - y, b.h + 8);
          const b64 = await page.evaluate(`__pptx.crop(${JSON.stringify(next)}, ${x}, ${y}, ${w}, ${h})`);
          pictures.push({ png: Buffer.from(b64, 'base64'), x, y, w, h, name: `ステップ${k}の変化`, alt: lines.map((c) => c.text).join(' ') });
          effects.push({ pic: pictures.length - 1, kind: 'fade', dur: 400, delay: 0 });
          visible.push({ id: 'patch' + pictures.length, b64, x, y });
        }
        steps.push({ auto: k === 0, effects });
        lines.forEach((c) => notes.push(`${label} ${c.text}`, ...(c.note ? [`　メモ: ${c.note}`] : [])));
        from = stop;
        prev = next;
      }
      slides.push({ background: Buffer.from(background, 'base64'), transition: { kind: sc.transition, dir: sc.direction }, notes, pictures, steps });
      log(`  ${sc.id}: ${steps.filter((s) => !s.auto).length}クリック、絵 ${pictures.length}枚`);
    }
    await page.close();
  } finally {
    await browser.close();
  }
  const r = buildPptx(out, { title: script.title, width: W, height: H, slides });
  log(`PPTX: ${out}（${r.slides}スライド、絵 ${r.images}枚。要素のアニメーション ${elementSteps}ステップ、差分の重ね ${patchSteps}ステップ）`);
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
    return `<style>\n${inlineCssUrls(fs.readFileSync(f, 'utf8'), path.dirname(f))}\n</style>`;
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

// ───────────────────────── main ─────────────────────────

const HELP = `motion-deck — ナレーションで動く HTML プレゼン

  init <フォルダ> [--title 題名]    雛形を作り、仮の timeline まで用意する
  runtime [deck]                    deck/motion/ の実行系をスキルの最新版に置き換える
  check [deck] [--scene id,..] [--no-browser]
                                    原稿・HTML・配置（はみ出し）を検査する
  ssml [deck]                       原稿から build/ssml/<id>.ssml を作る
  synth [deck] [--voice 名前] [--engine voxcpm2|omnivoice|s2]
        [--scenes id,..] [--force] [--dry-run]
                                    local-tts でシーンごとに音声を作る（原稿が変わったシーンだけ）
  timeline [deck] [--estimate]      音声の時刻から timeline.js と narration.m4a を作る
  still [deck] [--frames 0,90] [--scene id] [--cues] [--live] [--subtitles 0]
                                    静止画（PNG）と一覧画像を out/stills/ に書き出す
                                    --live は発表モードの各ステップ（配布資料にも使える）
  render [deck] [--out x.mp4] [--concurrency 4] [--from f --to f] [--scale 0.5]
         [--crf 18] [--subtitles 0] [--allow-estimated]
                                    MP4 に書き出す
  pptx [deck] [--out x.pptx]       PowerPoint に書き出す（クリックごとのネイティブのアニメーション、
                                    切り替え、台本入りのノート）
  bundle [deck] [--out x.html] [--external-audio]
                                    CSS・JS・画像・音声を1つの HTML にまとめる
`;

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const { pos, opt } = parseArgs(rest);
  const table = { pptx: cmdPptx, init: cmdInit, runtime: cmdRuntime, check: cmdCheck, ssml: cmdSsml, synth: cmdSynth, timeline: cmdTimeline, still: cmdStill, render: cmdRender, bundle: cmdBundle };
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
