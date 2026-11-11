// scenes.js — data-* と部品で書けない動きを、フレームの関数として書く。

// 作って移る：走者（今いる枝）が、文に合わせて main → feature/login → main と移る
Motion.scene("switch", (s) => {
  const runner = s.$("#s-runner");
  const size = 64;
  // 走者の足元の位置（小さな図の座標）
  const onMain = [60, 180], onFeat = [600, 60], backMain = [600, 180];
  return () => {
    const toFeat = s.appear("create", { delay: 6 });
    const toMain = s.appear("back", { delay: 6 });
    let x = s.interpolate(toFeat, [0, 1], [onMain[0], onFeat[0]]);
    let y = s.interpolate(toFeat, [0, 1], [onMain[1], onFeat[1]]);
    x = s.interpolate(toMain, [0, 1], [x, backMain[0]]);
    y = s.interpolate(toMain, [0, 1], [y, backMain[1]]);
    runner.style.left = x - size / 2 + "px";
    runner.style.top = y - size + "px";
    runner.style.opacity = s.appear(0, { delay: 20 });
  };
});
