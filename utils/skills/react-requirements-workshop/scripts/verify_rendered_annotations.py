#!/usr/bin/env python3
"""Exercise review annotations in a real browser at wide and narrow widths."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from common import load, snapshot_id

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
parser.add_argument('--snapshot', required=True)
parser.add_argument('--url', default='http://127.0.0.1:5173/')
parser.add_argument('--output', type=Path)
parser.add_argument('--screenshot-dir', type=Path)
args = parser.parse_args()
root = args.workspace.resolve()
metadata = load(root / 'discussion' / f'{args.snapshot}.json')
if snapshot_id(metadata) != args.snapshot:
    raise SystemExit('snapshot mismatch')
local_binary = root / 'node_modules/.bin/agent-browser'
browser_binary = str(local_binary) if local_binary.exists() else shutil.which('agent-browser')
if not browser_binary or not Path(browser_binary).exists():
    raise SystemExit('agent-browser CLI is required for rendered verification')
output = args.output or root / 'discussion/verification' / f'{args.snapshot}.json'
output = output.resolve()
if output.exists():
    raise SystemExit(f'refusing to overwrite verification: {output}')
screenshot_dir = args.screenshot_dir.resolve() if args.screenshot_dir else None
if screenshot_dir and screenshot_dir.exists() and any(screenshot_dir.iterdir()):
    raise SystemExit(f'refusing to overwrite screenshots: {screenshot_dir}')
environment = os.environ.copy()
if not environment.get('AGENT_BROWSER_HOME'):
    candidate = root / 'node_modules/agent-browser'
    if not candidate.is_dir():
        npm_root = subprocess.run(['npm', 'root', '-g'], text=True, capture_output=True, check=True).stdout.strip()
        candidate = Path(npm_root) / 'agent-browser'
    if candidate.is_dir():
        environment['AGENT_BROWSER_HOME'] = str(candidate)
session = f'review-verify-{os.getpid()}'

def browser(*arguments: str) -> object:
    completed = subprocess.run([browser_binary, '--session', session, *arguments, '--json'], env=environment, text=True, capture_output=True, timeout=90)
    if completed.returncode:
        raise RuntimeError(f'agent-browser {arguments[0]} failed: {completed.stderr.strip() or completed.stdout.strip()}')
    reply = json.loads(completed.stdout)
    if reply.get('success') is not True:
        raise RuntimeError(str(reply.get('error')))
    return reply.get('data', {})

script = r'''(async () => {
  const meta = __META__;
  const wait = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 20))));
  await wait();
  const canvas = document.querySelector('.review-canvas');
  const stage = document.querySelector('.review-stage');
  const stageRect = stage.getBoundingClientRect(), canvasRect = canvas.getBoundingClientRect();
  const canvasStyle = getComputedStyle(canvas), stageStyle = getComputedStyle(stage);
  const frameSeparated = canvasRect.left - stageRect.left >= 12 && stageRect.right - canvasRect.right >= 12 && stageRect.bottom - canvasRect.bottom >= 12 && canvasStyle.borderLeftWidth !== '0px' && canvasStyle.backgroundColor !== stageStyle.backgroundColor && document.querySelector('.review-frame-label')?.textContent.includes('画面案');
  const noteOutsideCanvas = !meta.snapshot.note || (document.querySelector('.review-frame-label')?.textContent.includes(meta.snapshot.note) && !canvas.textContent.includes(meta.snapshot.note));
  const target = key => [...canvas.querySelectorAll('[data-review-target]')].filter(node => node.getAttribute('data-review-target') === key);
  const detailTarget = key => [...canvas.querySelectorAll('[data-screen-detail-target]')].filter(node => node.getAttribute('data-screen-detail-target') === key);
  const boxes = () => [...canvas.querySelectorAll('.review-box')];
  const aligned = (box, node, padding = 0) => {
    if (!box || !node) return false;
    const a = box.getBoundingClientRect(), b = node.getBoundingClientRect();
    return Math.abs(a.left - (b.left - padding)) <= 2 && Math.abs(a.top - (b.top - padding)) <= 2 && Math.abs(a.right - (b.right + padding)) <= 2 && Math.abs(a.bottom - (b.bottom + padding)) <= 2;
  };
  const fixed = meta.fixed_annotations ?? meta.review_points.map(point => ({number: point.number, target_key: point.target_key, padding_px: 0}));
  const fixedChecks = fixed.map(annotation => {
    const box = boxes().find(node => node.classList.contains('point') && Number(node.querySelector('.review-number')?.textContent) === annotation.number);
    if (annotation.target_key) return target(annotation.target_key).length === 1 && aligned(box, target(annotation.target_key)[0], annotation.padding_px ?? 8);
    if (!box) return false;
    const surface = canvas.getBoundingClientRect(), rect = box.getBoundingClientRect();
    return Math.abs((rect.left - surface.left + canvas.scrollLeft) / canvas.scrollWidth * 100 - annotation.x_percent) < 1 && Math.abs((rect.top - surface.top + canvas.scrollTop) / canvas.scrollHeight * 100 - annotation.y_percent) < 1;
  });
  const first = meta.review_points[0], firstBox = boxes().find(node => node.classList.contains('point') && Number(node.querySelector('.review-number')?.textContent) === first?.number);
  const firstTarget = first && target(first.target_key)[0];
  const centerHit = firstTarget ? (() => { const r = firstTarget.getBoundingClientRect(); return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) })() : null;
  const framePassThrough = !firstTarget || Boolean(centerHit && !centerHit.closest('.review-box'));
  const badge = firstBox?.querySelector('.review-number');
  let numberHit = true, numberFocus = true, numberPassThroughInSelection = true;
  if (badge) {
    badge.scrollIntoView({block: 'center'}); await wait();
    const r = badge.getBoundingClientRect();
    numberHit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === badge;
    badge.click(); await wait();
    numberFocus = document.activeElement?.id === `point-feedback-${first.number}`;
  }
  const selectingButton = [...document.querySelectorAll('.review-panel button')].find(node => node.textContent.includes('要素を選んで指摘'));
  let customCreated = true, customAligned = true, customFramePassThrough = true, numberReuse = true, customNumberFocus = true, hoverAligned = true;
  if (firstTarget && selectingButton) {
    selectingButton.click(); await wait();
    if (badge) {
      const r = badge.getBoundingClientRect();
      numberPassThroughInSelection = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) !== badge;
    }
    firstTarget.dispatchEvent(new PointerEvent('pointermove', {bubbles: true})); await wait();
    const hover = canvas.querySelector('.review-hover');
    hoverAligned = aligned(hover, firstTarget);
    firstTarget.click(); await wait();
    const custom = boxes().find(node => node.classList.contains('custom'));
    customCreated = Boolean(custom && document.querySelector('.review-card.custom'));
    customAligned = aligned(custom, firstTarget);
    const center = firstTarget.getBoundingClientRect();
    customFramePassThrough = !document.elementFromPoint(center.left + center.width / 2, center.top + center.height / 2)?.closest('.review-box');
    const number = Number(custom?.querySelector('.review-number')?.textContent);
    custom?.querySelector('.review-number')?.click(); await wait();
    customNumberFocus = document.activeElement?.id === `custom-feedback-${number}`;
    document.querySelector('.review-card.custom button:last-child')?.click(); await wait();
    [...document.querySelectorAll('.review-panel button')].find(node => node.textContent.includes('要素を選んで指摘'))?.click(); await wait();
    firstTarget.click(); await wait();
    numberReuse = Number(boxes().find(node => node.classList.contains('custom'))?.querySelector('.review-number')?.textContent) === number;
  }
  const scrollers = [...canvas.querySelectorAll('*')].filter(node => {const style = getComputedStyle(node); return /(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 1});
  const nestedScrollValid = scrollers.every(node => node.hasAttribute('data-allow-nested-scroll'));
  const beforeScroll = canvas.scrollTop;
  canvas.scrollTop = Math.min(canvas.scrollHeight - canvas.clientHeight, beforeScroll + 300); await wait();
  const scrollAligned = fixed.filter(a => a.target_key).every(a => aligned(boxes().find(node => node.classList.contains('point') && Number(node.querySelector('.review-number')?.textContent) === a.number), target(a.target_key)[0], a.padding_px ?? 8));
  canvas.scrollTop = beforeScroll; await wait();
  const toggle = document.querySelector('.review-toggle');
  toggle.click(); await wait();
  const pointHide = boxes().length === 0 && document.querySelectorAll('.review-card-number:not(.hidden)').length === 0;
  toggle.click(); await wait();
  const pointShow = boxes().length >= fixed.length;
  [...document.querySelectorAll('[role="tab"]')].find(node => node.textContent.includes('画面の詳細設計')).click(); await wait();
  const detailBoxes = boxes();
  const detailChecks = meta.screen_details.map(detail => detailTarget(detail.target_key).length === 1 && aligned(detailBoxes.find(node => node.classList.contains('detail') && Number(node.querySelector('.review-number')?.textContent) === detail.number), detailTarget(detail.target_key)[0], 3));
  const detailFramePassThrough = [];
  for (const detail of meta.screen_details) {
    const node = detailTarget(detail.target_key)[0];
    if (!node) { detailFramePassThrough.push(false); continue }
    node.scrollIntoView({block: 'center'}); await wait();
    const rect = node.getBoundingClientRect(), hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
    detailFramePassThrough.push(Boolean(hit && !hit.closest('.review-box')));
  }
  const modeSeparated = detailBoxes.every(node => node.classList.contains('detail')) && ![...document.querySelectorAll('.review-panel button')].some(node => node.textContent.includes('要素を選んで指摘'));
  const summary = [...document.querySelectorAll('.review-detail-summary')].find(node => node.getAttribute('aria-expanded') === 'false') ?? document.querySelector('.review-detail-summary');
  const selectedDetail = meta.screen_details[[...document.querySelectorAll('.review-detail-summary')].indexOf(summary)];
  summary?.click(); await wait();
  const detailNavigation = !summary || (detailTarget(selectedDetail.target_key)[0]?.classList.contains('review-target-active') && summary.getAttribute('aria-expanded') === 'true');
  const detailToggle = document.querySelector('.review-toggle');
  detailToggle.click(); await wait();
  const detailHide = boxes().length === 0 && document.querySelectorAll('.review-card-number:not(.hidden)').length === 0;
  detailToggle.click(); await wait();
  [...document.querySelectorAll('[role="tab"]')].find(node => node.textContent.includes('確認ポイント')).click(); await wait();
  const modeReturn = boxes().every(node => !node.classList.contains('detail')) && [...document.querySelectorAll('.review-panel button')].some(node => node.textContent.includes('要素を選んで指摘'));
  return { frameSeparated, noteOutsideCanvas, fixedChecks, detailChecks, framePassThrough, customFramePassThrough, detailFramePassThrough, numberHit, numberFocus, numberPassThroughInSelection, customCreated, customAligned, customNumberFocus, numberReuse, hoverAligned, nestedScrollValid, scrollAligned, pointHide, pointShow, modeSeparated, modeReturn, detailNavigation, detailHide };
})()'''.replace('__META__', json.dumps(metadata, ensure_ascii=False))

results = []
try:
    browser('open', args.url)
    for width, height in ((1568, 784), (1280, 800), (1024, 768), (800, 900)):
        browser('set', 'viewport', str(width), str(height))
        browser('reload')
        browser('eval', '(async () => { await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 20)))); return true })()')
        if screenshot_dir:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            browser('screenshot', str(screenshot_dir / f'{width}x{height}.png'))
        value = browser('eval', script)
        checks = value['result']
        valid = all(all(item) if isinstance(item, list) else item for item in checks.values())
        results.append({'viewport': [width, height], 'valid': valid, 'checks': checks})
finally:
    try:
        browser('close')
    except Exception:
        pass
report = {'snapshot_id': args.snapshot, 'valid': all(item['valid'] for item in results), 'results': results}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
if not report['valid']:
    raise SystemExit(1)
