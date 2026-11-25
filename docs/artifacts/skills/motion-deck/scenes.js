// scenes.js — data-* と部品で書けない動きを、フレームの関数として書く。

// 作って移る：走者が今いる枝のレーンへ移る（作る文で上へ、戻る文で下へ）
Motion.scene("switch", (s) => {
  const runner = s.$("#s-runner");
  const mainY = 300, featY = 40;
  return () => {
    const up = s.appear("create", { delay: 20 });
    const down = s.appear("back", { delay: 20 });
    const y = mainY + (featY - mainY) * up + (mainY - featY) * down;
    runner.style.top = y + "px";
    runner.style.opacity = s.appear(0, { delay: 10 });
  };
});
