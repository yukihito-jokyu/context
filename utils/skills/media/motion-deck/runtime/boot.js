/*!
 * boot.js — motion-deck の読み込み口。
 * index.html はこの1行だけを置く：  <script src="motion/boot.js"></script>
 * 実行系・部品・テーマ・時間軸・独自の動きを決まった順に読み込み、起動する。
 * どれかが読めなければ起動せず、理由を画面に出す（window.__motionBootError）。
 *
 * デッキで足したい CSS・JS があれば属性で渡す（テーマの後・scenes.js の前に読む）:
 *   <script src="motion/boot.js" data-css="extra.css" data-js="chart.js"></script>
 */
(function () {
  'use strict';
  // この並びは scripts/motion.mjs（bundle・check）も読む。変えるときは両方で使われることに注意
  var CSS = ['motion/motion.css', 'motion/kit.css', 'theme.css'];
  var JS = ['timeline.js', 'motion/motion.js', 'motion/kit.js', 'scenes.js'];

  var me = document.currentScript;
  var base = me.src.replace(/motion\/boot\.js(\?.*)?$/, '');
  var list = function (v) { return (v || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean); };
  var css = CSS.concat(list(me.dataset.css));
  var js = JS.slice(0, 3).concat(list(me.dataset.js), JS.slice(3));
  var root = document.documentElement;
  root.style.visibility = 'hidden';

  function fail(msg) {
    window.__motionBootError = msg;
    root.style.visibility = '';
    var pre = document.createElement('pre');
    pre.style.cssText = 'font:16px/1.6 monospace;padding:40px;color:#b00;white-space:pre-wrap';
    pre.textContent = 'motion-deck を起動できません。\n' + msg;
    document.body.innerHTML = '';
    document.body.appendChild(pre);
  }
  function loadCss(href) {
    return new Promise(function (resolve, reject) {
      var l = document.createElement('link');
      l.rel = 'stylesheet';
      l.href = base + href;
      l.onload = resolve;
      l.onerror = function () { reject(new Error('読み込めません: ' + href)); };
      document.head.appendChild(l);
    });
  }
  function loadJs(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = base + src;
      s.async = false;
      s.onload = resolve;
      s.onerror = function () {
        reject(new Error('読み込めません: ' + src + (src === 'timeline.js' ? '\nnode <motion-deck>/scripts/motion.mjs timeline を実行してください。' : '')));
      };
      document.body.appendChild(s);
    });
  }

  // CSS は並べた順に足す（後のものが勝つ）。JS は1つずつ順に
  Promise.all(css.map(loadCss))
    .then(function () { return js.reduce(function (p, src) { return p.then(function () { return loadJs(src); }); }, Promise.resolve()); })
    .then(function () {
      if (!window.Motion || !window.MOTION_TIMELINE) throw new Error('実行系か時間軸が読み込まれていません');
      window.__motionBoot = { css: css, js: js };
      window.Motion.start();
      root.style.visibility = '';
    })
    .catch(function (e) { fail(e && e.message ? e.message : String(e)); });
})();
