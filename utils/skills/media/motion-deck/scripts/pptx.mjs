// pptx.mjs — 依存なしで .pptx（Office Open XML）を書く。
// スライドは「背景の絵」＋「現れる要素の絵」で組み、要素には PowerPoint のネイティブのアニメーション
// （フロートイン・フェード・ワイプ・ズーム）をクリック順に付ける。ノートには台本を入れる。

import fs from 'node:fs';
import zlib from 'node:zlib';

// ───────── zip ─────────

function dosTime(d) {
  const time = (d.getHours() << 11) | (d.getMinutes() << 5) | Math.floor(d.getSeconds() / 2);
  const date = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  return { time, date };
}

export function writeZip(file, entries) {
  const chunks = [];
  const central = [];
  let offset = 0;
  const { time, date } = dosTime(new Date());
  for (const { name, data } of entries) {
    const raw = Buffer.isBuffer(data) ? data : Buffer.from(data, 'utf8');
    const crc = zlib.crc32(raw);
    const store = /\.(png|jpe?g|m4a|mp3|wav)$/i.test(name);
    const body = store ? raw : zlib.deflateRawSync(raw, { level: 9 });
    const method = store ? 0 : 8;
    const nameBuf = Buffer.from(name, 'utf8');
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0); local.writeUInt16LE(20, 4); local.writeUInt16LE(0x0800, 6); local.writeUInt16LE(method, 8);
    local.writeUInt16LE(time, 10); local.writeUInt16LE(date, 12); local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(body.length, 18); local.writeUInt32LE(raw.length, 22); local.writeUInt16LE(nameBuf.length, 26); local.writeUInt16LE(0, 28);
    chunks.push(local, nameBuf, body);
    const c = Buffer.alloc(46);
    c.writeUInt32LE(0x02014b50, 0); c.writeUInt16LE(20, 4); c.writeUInt16LE(20, 6); c.writeUInt16LE(0x0800, 8); c.writeUInt16LE(method, 10);
    c.writeUInt16LE(time, 12); c.writeUInt16LE(date, 14); c.writeUInt32LE(crc, 16); c.writeUInt32LE(body.length, 20); c.writeUInt32LE(raw.length, 24);
    c.writeUInt16LE(nameBuf.length, 28); c.writeUInt32LE(offset, 42);
    central.push(c, nameBuf);
    offset += 30 + nameBuf.length + body.length;
  }
  const cd = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(entries.length, 8); end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(cd.length, 12); end.writeUInt32LE(offset, 16);
  fs.writeFileSync(file, Buffer.concat([...chunks, cd, end]));
}

// ───────── XML の部品 ─────────

const NS = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"';
const HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';
const esc = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const SLIDE_W = 12192000, SLIDE_H = 6858000; // 16:9

const rels = (list) => `${HEAD}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${list.map(([id, type, target]) => `<Relationship Id="${id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/${type}" Target="${target}"/>`).join('')}</Relationships>`;

const theme = (name) => `${HEAD}<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="${name}"><a:themeElements>
<a:clrScheme name="motion-deck"><a:dk1><a:srgbClr val="1C2530"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="151C26"/></a:dk2><a:lt2><a:srgbClr val="F4EFE4"/></a:lt2>
<a:accent1><a:srgbClr val="00A3CC"/></a:accent1><a:accent2><a:srgbClr val="E0492A"/></a:accent2><a:accent3><a:srgbClr val="EFB02A"/></a:accent3><a:accent4><a:srgbClr val="1F9160"/></a:accent4><a:accent5><a:srgbClr val="006E8C"/></a:accent5><a:accent6><a:srgbClr val="59626F"/></a:accent6>
<a:hlink><a:srgbClr val="006E8C"/></a:hlink><a:folHlink><a:srgbClr val="59626F"/></a:folHlink></a:clrScheme>
<a:fontScheme name="motion-deck"><a:majorFont><a:latin typeface="Hiragino Sans"/><a:ea typeface="Hiragino Sans"/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Hiragino Sans"/><a:ea typeface="Hiragino Sans"/><a:cs typeface=""/></a:minorFont></a:fontScheme>
<a:fmtScheme name="motion-deck"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
<a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>
<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
</a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>`;

const emptyTree = '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>';
const clrMap = '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>';

const master = `${HEAD}<p:sldMaster ${NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="F4EFE4"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree>${emptyTree}</p:spTree></p:cSld>${clrMap}<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>`;
const layout = `${HEAD}<p:sldLayout ${NS} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>${emptyTree}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>`;

const notesMaster = `${HEAD}<p:notesMaster ${NS}><p:cSld><p:spTree>${emptyTree}
<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg" idx="2"/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm><a:off x="381000" y="685800"/><a:ext cx="6096000" cy="3429000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:sp>
<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" sz="quarter" idx="3"/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm><a:off x="685800" y="4343400"/><a:ext cx="5486400" cy="4114800"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="ja-JP"/></a:p></p:txBody></p:sp>
</p:spTree></p:cSld>${clrMap}</p:notesMaster>`;

function notesSlide(paragraphs) {
  const body = paragraphs.length
    ? paragraphs.map((t) => `<a:p><a:r><a:rPr lang="ja-JP" sz="1200" dirty="0"/><a:t>${esc(t)}</a:t></a:r></a:p>`).join('')
    : '<a:p><a:endParaRPr lang="ja-JP"/></a:p>';
  return `${HEAD}<p:notes ${NS}><p:cSld><p:spTree>${emptyTree}
<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg"/></p:nvPr></p:nvSpPr><p:spPr/></p:sp>
<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>${body}</p:txBody></p:sp>
</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>`;
}

// ───────── アニメーション（p:timing） ─────────
//
// effect = { spid, kind, dur (ms), delay (ms) }
// kind: rise | sink | fromLeft | fromRight | fade | wipeLeft | wipeTop | wipeBottom | zoom | zoomOut | pop

const PRESET = {
  rise: [42, 0], sink: [47, 0], fromLeft: [42, 0], fromRight: [42, 0], fade: [10, 0],
  wipeLeft: [22, 8], wipeTop: [22, 1], wipeBottom: [22, 4], zoom: [53, 16], zoomOut: [53, 16], pop: [53, 16],
  exitFade: [10, 0],
};

function behaviors(e, nextId) {
  const tgt = `<p:tgtEl><p:spTgt spid="${e.spid}"/></p:tgtEl>`;
  const set = `<p:set><p:cBhvr><p:cTn id="${nextId()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>${tgt}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>`;
  const fade = (d) => `<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="${nextId()}" dur="${d}"/>${tgt}</p:cBhvr></p:animEffect>`;
  const wipe = (dir, d) => `<p:animEffect transition="in" filter="wipe(${dir})"><p:cBhvr><p:cTn id="${nextId()}" dur="${d}"/>${tgt}</p:cBhvr></p:animEffect>`;
  const anim = (attr, keys, d) => `<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base"><p:cTn id="${nextId()}" dur="${d}" decel="100000" fill="hold"/>${tgt}<p:attrNameLst><p:attrName>${attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst>${keys.map(([tm, v]) => `<p:tav tm="${tm}"><p:val><p:strVal val="${v}"/></p:val></p:tav>`).join('')}</p:tavLst></p:anim>`;
  const d = Math.max(100, Math.round(e.dur));
  switch (e.kind) {
    case 'rise': return set + fade(d) + anim('ppt_y', [[0, '#ppt_y+0.037'], [100000, '#ppt_y']], d);
    case 'sink': return set + fade(d) + anim('ppt_y', [[0, '#ppt_y-0.037'], [100000, '#ppt_y']], d);
    case 'fromLeft': return set + fade(d) + anim('ppt_x', [[0, '#ppt_x-0.025'], [100000, '#ppt_x']], d);
    case 'fromRight': return set + fade(d) + anim('ppt_x', [[0, '#ppt_x+0.025'], [100000, '#ppt_x']], d);
    case 'wipeLeft': return set + wipe('left', d);
    case 'wipeTop': return set + wipe('up', d);
    case 'wipeBottom': return set + wipe('down', d);
    case 'zoom': return set + fade(d) + anim('ppt_w', [[0, '#ppt_w*0.82'], [100000, '#ppt_w']], d) + anim('ppt_h', [[0, '#ppt_h*0.82'], [100000, '#ppt_h']], d);
    case 'zoomOut': return set + fade(d) + anim('ppt_w', [[0, '#ppt_w*1.14'], [100000, '#ppt_w']], d) + anim('ppt_h', [[0, '#ppt_h*1.14'], [100000, '#ppt_h']], d);
    case 'pop': return set + fade(Math.round(d * 0.5)) + anim('ppt_w', [[0, '#ppt_w*0.4'], [65000, '#ppt_w*1.07'], [100000, '#ppt_w']], d) + anim('ppt_h', [[0, '#ppt_h*0.4'], [65000, '#ppt_h*1.07'], [100000, '#ppt_h']], d);
    case 'exitFade': return `<p:animEffect transition="out" filter="fade"><p:cBhvr><p:cTn id="${nextId()}" dur="${d}"/>${tgt}</p:cBhvr></p:animEffect><p:set><p:cBhvr><p:cTn id="${nextId()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="${d - 1}"/></p:stCondLst></p:cTn>${tgt}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="hidden"/></p:to></p:set>`;
    default: return set + fade(d);
  }
}

/** steps = [{ auto: bool, effects: [...] }]。auto のステップはスライドが始まると自動で動く */
function timing(steps) {
  const groups = steps.filter((s) => s.effects.length);
  if (!groups.length) return '';
  let id = 2;
  const nextId = () => ++id;
  const parts = groups.map((g) => {
    const outer = nextId();
    const inner = nextId();
    const cond = g.auto ? '<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>' : '<p:cond delay="indefinite"/>';
    const effects = g.effects.map((e, i) => {
      const [preset, sub] = PRESET[e.kind] || PRESET.fade;
      const node = !g.auto && i === 0 ? 'clickEffect' : 'withEffect';
      const cid = nextId();
      const cls = e.kind.startsWith('exit') ? 'exit' : 'entr';
      return `<p:par><p:cTn id="${cid}" presetID="${preset}" presetClass="${cls}" presetSubtype="${sub}" fill="hold" nodeType="${node}"><p:stCondLst><p:cond delay="${Math.max(0, Math.round(e.delay))}"/></p:stCondLst><p:childTnLst>${behaviors(e, nextId)}</p:childTnLst></p:cTn></p:par>`;
    }).join('');
    return `<p:par><p:cTn id="${outer}" fill="hold"><p:stCondLst>${cond}</p:stCondLst><p:childTnLst><p:par><p:cTn id="${inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>${effects}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>`;
  }).join('');
  return `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>${parts}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>`;
}

const TRANSITION = {
  fade: () => '<p:fade/>',
  slide: (dir) => `<p:push dir="${{ left: 'l', right: 'r', up: 'u', down: 'd' }[dir] || 'l'}"/>`,
  wipe: (dir) => `<p:wipe dir="${{ left: 'l', right: 'r', up: 'u', down: 'd' }[dir] || 'l'}"/>`,
  zoom: () => '<p:zoom/>',
  iris: () => '<p:circle/>',
  clock: () => '<p:wheel spokes="1"/>',
  flip: () => '<p:fade/>',
};

// ───────── スライド ─────────

/**
 * slides = [{ background: Buffer(png), transition: {kind, dir}, notes: [string],
 *             pictures: [{ png: Buffer, x, y, w, h (px), name, alt }],
 *             steps: [{ auto, effects: [{ pic: index, kind, dur, delay }] }] }]
 */
export function buildPptx(file, { title, width, height, slides }) {
  const emu = SLIDE_W / width;
  const entries = [];
  const media = [];
  const ct = [];
  slides.forEach((sl, i) => {
    const n = i + 1;
    const relList = [['rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml'], ['rId2', 'notesSlide', `../notesSlides/notesSlide${n}.xml`]];
    let rid = 3;
    let spid = 2;
    const addPic = (png, x, y, w, h, name, alt) => {
      const mname = `image${media.length + 1}.png`;
      media.push({ name: `ppt/media/${mname}`, data: png });
      const r = `rId${rid++}`;
      relList.push([r, 'image', `../media/${mname}`]);
      const id = spid++;
      const xml = `<p:pic><p:nvPicPr><p:cNvPr id="${id}" name="${esc(name)}" descr="${esc(alt || '')}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="${r}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="${Math.round(x * emu)}" y="${Math.round(y * emu)}"/><a:ext cx="${Math.max(1, Math.round(w * emu))}" cy="${Math.max(1, Math.round(h * emu))}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>`;
      return { id, xml };
    };
    const bg = addPic(sl.background, 0, 0, width, height, '背景', '');
    const pics = sl.pictures.map((p, k) => addPic(p.png, p.x, p.y, p.w, p.h, p.name || `要素${k + 1}`, p.alt));
    const steps = sl.steps.map((st) => ({ auto: st.auto, effects: st.effects.map((e) => ({ spid: pics[e.pic].id, kind: e.kind, dur: e.dur, delay: e.delay })) }));
    const tr = sl.transition && TRANSITION[sl.transition.kind] ? `<p:transition spd="med">${TRANSITION[sl.transition.kind](sl.transition.dir)}</p:transition>` : '';
    const xml = `${HEAD}<p:sld ${NS}><p:cSld><p:spTree>${emptyTree}${bg.xml}${pics.map((p) => p.xml).join('')}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>${tr}${timing(steps)}</p:sld>`;
    entries.push({ name: `ppt/slides/slide${n}.xml`, data: xml });
    entries.push({ name: `ppt/slides/_rels/slide${n}.xml.rels`, data: rels(relList) });
    entries.push({ name: `ppt/notesSlides/notesSlide${n}.xml`, data: notesSlide(sl.notes || []) });
    entries.push({ name: `ppt/notesSlides/_rels/notesSlide${n}.xml.rels`, data: rels([['rId1', 'notesMaster', '../notesMasters/notesMaster1.xml'], ['rId2', 'slide', `../slides/slide${n}.xml`]]) });
    ct.push(`<Override PartName="/ppt/slides/slide${n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`);
    ct.push(`<Override PartName="/ppt/notesSlides/notesSlide${n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>`);
  });

  const presRels = [['rId1', 'slideMaster', 'slideMasters/slideMaster1.xml'], ['rId2', 'notesMaster', 'notesMasters/notesMaster1.xml'], ['rId3', 'theme', 'theme/theme1.xml'], ['rId4', 'presProps', 'presProps.xml'], ['rId5', 'viewProps', 'viewProps.xml'], ['rId6', 'tableStyles', 'tableStyles.xml']];
  slides.forEach((_, i) => presRels.push([`rId${100 + i}`, 'slide', `slides/slide${i + 1}.xml`]));
  const presentation = `${HEAD}<p:presentation ${NS} saveSubsetFonts="1"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:notesMasterIdLst><p:notesMasterId r:id="rId2"/></p:notesMasterIdLst><p:sldIdLst>${slides.map((_, i) => `<p:sldId id="${256 + i}" r:id="rId${100 + i}"/>`).join('')}</p:sldIdLst><p:sldSz cx="${SLIDE_W}" cy="${SLIDE_H}"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle><a:defPPr><a:defRPr lang="ja-JP"/></a:defPPr></p:defaultTextStyle></p:presentation>`;
  const now = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  entries.push(
    { name: '[Content_Types].xml', data: `${HEAD}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/><Override PartName="/ppt/notesMasters/notesMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/><Override PartName="/ppt/theme/theme2.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/><Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/><Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/><Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>${ct.join('')}</Types>` },
    { name: '_rels/.rels', data: `${HEAD}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>` },
    { name: 'docProps/core.xml', data: `${HEAD}<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${esc(title)}</dc:title><dc:creator>motion-deck</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">${now}</dcterms:modified></cp:coreProperties>` },
    { name: 'docProps/app.xml', data: `${HEAD}<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Slides>${slides.length}</Slides><Notes>${slides.length}</Notes><Application>motion-deck</Application></Properties>` },
    { name: 'ppt/presentation.xml', data: presentation },
    { name: 'ppt/_rels/presentation.xml.rels', data: rels(presRels) },
    { name: 'ppt/slideMasters/slideMaster1.xml', data: master },
    { name: 'ppt/slideMasters/_rels/slideMaster1.xml.rels', data: rels([['rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml'], ['rId2', 'theme', '../theme/theme1.xml']]) },
    { name: 'ppt/slideLayouts/slideLayout1.xml', data: layout },
    { name: 'ppt/slideLayouts/_rels/slideLayout1.xml.rels', data: rels([['rId1', 'slideMaster', '../slideMasters/slideMaster1.xml']]) },
    { name: 'ppt/notesMasters/notesMaster1.xml', data: notesMaster },
    { name: 'ppt/notesMasters/_rels/notesMaster1.xml.rels', data: rels([['rId1', 'theme', '../theme/theme2.xml']]) },
    { name: 'ppt/theme/theme1.xml', data: theme('motion-deck') },
    { name: 'ppt/theme/theme2.xml', data: theme('motion-deck notes') },
    { name: 'ppt/presProps.xml', data: `${HEAD}<p:presentationPr ${NS}/>` },
    { name: 'ppt/viewProps.xml', data: `${HEAD}<p:viewPr ${NS}><p:normalViewPr><p:restoredLeft sz="15620"/><p:restoredTop sz="80000"/></p:normalViewPr><p:gridSpacing cx="76200" cy="76200"/></p:viewPr>` },
    { name: 'ppt/tableStyles.xml', data: `${HEAD}<a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>` },
  );
  // [Content_Types].xml を先頭に
  entries.sort((a, b) => (a.name === '[Content_Types].xml' ? -1 : b.name === '[Content_Types].xml' ? 1 : 0));
  writeZip(file, [...entries, ...media]);
  return { slides: slides.length, images: media.length };
}

/** data-anim の名前から PowerPoint の効果を選ぶ */
export function effectFor(anims) {
  const a = anims || [];
  if (a.includes('pop')) return 'pop';
  if (a.includes('up')) return 'rise';
  if (a.includes('down')) return 'sink';
  if (a.includes('left')) return 'fromLeft';
  if (a.includes('right')) return 'fromRight';
  if (a.includes('scale')) return 'zoom';
  if (a.includes('zoom')) return 'zoomOut';
  if (a.includes('grow-y')) return 'wipeBottom';
  if (a.includes('wipe-down')) return 'wipeTop';
  if (a.some((x) => ['draw', 'wipe', 'grow', 'type', 'highlight', 'progress', 'strike', 'words'].includes(x))) return 'wipeLeft';
  return 'fade';
}
