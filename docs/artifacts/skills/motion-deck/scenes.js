// scenes.js — data-* と部品で書けない動きを、フレームの関数として書く。

// switch：走者（今いる枝）が、文に合わせて main と feature/login の間を移る
Motion.scene("switch", (s) => {
  const runner = s.$("#sw-runner");
  const yMain = 250, yFeat = 60;
  return () => {
    let y = yMain;
    if (s.reached("create")) y = s.interpolate(s.appear("create"), [0, 1], [yMain, yFeat]);
    if (s.reached("back")) y = s.interpolate(s.appear("back"), [0, 1], [yFeat, yMain]);
    runner.style.top = y + "px";
  };
});
