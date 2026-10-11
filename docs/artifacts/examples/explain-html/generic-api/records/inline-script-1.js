// Finite traces over the unchanged geometry of an exported Archify diagram.
(() => {
 const motion = matchMedia('(prefers-reduced-motion: reduce)');
 for (const root of document.querySelectorAll('[data-flow-diagram]')) {
  const controls = root.querySelector('.flow-controls');
  const buttons = [...root.querySelectorAll('[data-flow-select]')];
  const status = root.querySelector('.flow-status');
  if (!controls || !buttons.length || !status) continue;
  controls.hidden = false;
  let index = -1, timer = null, deadline = 0, remaining = 0, playing = false, animations = [];
  const duration = 2400;
  function clearTimer() { if (timer !== null) clearTimeout(timer); timer = null; }
  function clearAnimations() { animations.forEach(a => a.cancel()); animations = []; }
  function clearHighlights() {
   root.querySelectorAll('[data-flow-stage]').forEach(n => n.classList.remove('flow-active'));
   root.querySelectorAll('[data-flow-edge]').forEach(n => n.style.opacity = '0');
   buttons.forEach(b => b.removeAttribute('aria-current'));
  }
  function stop() { clearTimer(); clearAnimations(); playing = false; }
  function display(i) {
   clearHighlights(); index = i;
   if (i < 0) { status.textContent = '全体を表示しています'; return; }
   const b = buttons[i], stage = b.dataset.flowSelect;
   b.setAttribute('aria-current', 'step');
   root.querySelectorAll('[data-flow-stage]').forEach(n => n.classList.toggle('flow-active', n.dataset.flowStage === stage));
   status.textContent = b.dataset.flowCaption || b.textContent;
  }
  function signals() {
   clearAnimations();
   if (motion.matches) return;
   const edgeIds = (buttons[index].dataset.flowEdges || '').split(/\s+/).filter(Boolean);
   for (const path of root.querySelectorAll('[data-flow-edge]')) {
    if (!edgeIds.includes(path.dataset.flowEdge)) continue;
    path.style.opacity = '1';
    const order = edgeIds.indexOf(path.dataset.flowEdge);
    const edgeDuration = duration / edgeIds.length;
    animations.push(path.animate([{opacity:0,strokeDashoffset:0,offset:0},{opacity:1,strokeDashoffset:0,offset:.04},{opacity:1,strokeDashoffset:-1,offset:.96},{opacity:0,strokeDashoffset:-1,offset:1}], {duration:edgeDuration, delay:order * edgeDuration, easing:'linear', fill:'both'}));
   }
  }
  function schedule(ms) { remaining = ms; deadline = performance.now() + ms; timer = setTimeout(advance, ms); }
  function advance() {
   timer = null;
   if (index + 1 >= buttons.length) {
    stop(); display(-1); status.textContent = '再生が終了しました。全体を表示しています'; return;
   }
   display(index + 1); signals(); schedule(duration);
  }
  function play() {
   if (playing) return;
   playing = true;
   if (remaining > 0 && index >= 0) { animations.forEach(a => a.play()); schedule(remaining); }
   else { display(index < 0 ? 0 : index); signals(); schedule(duration); }
  }
  function pause() {
   if (!playing) return;
   remaining = Math.max(0, deadline - performance.now()); clearTimer();
   animations.forEach(a => a.pause()); playing = false;
  }
  for (const button of buttons) button.addEventListener('click', () => {
   stop(); remaining = 0; display(buttons.indexOf(button));
  });
  root.querySelector('[data-flow-action="play"]')?.addEventListener('click', play);
  root.querySelector('[data-flow-action="pause"]')?.addEventListener('click', pause);
  root.querySelector('[data-flow-action="reset"]')?.addEventListener('click', () => { stop(); remaining = 0; display(-1); });
  window.addEventListener('hashchange', pause);
  window.addEventListener('popstate', pause);
  // pushState navigation dispatches this event before hiding the page.
  document.addEventListener('explain:navigate', pause);
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  motion.addEventListener('change', () => { pause(); clearAnimations(); });
  window.addEventListener('beforeprint', () => { stop(); remaining = 0; display(-1); });
  display(-1);
 }
})();
