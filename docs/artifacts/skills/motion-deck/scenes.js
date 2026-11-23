// scenes.js — data-* と部品で書けない動きだけを、フレームの関数として書く。

// 作って移る：走者（今いる枝）が main と feature/login の間を移る
Motion.scene("switch", (s) => {
  const runner = s.$("#sw-runner");
  const mainTop = 210, featureTop = 70;
  return () => {
    const up = s.appear("create", { delay: 20 });
    const down = s.appear("back", { delay: 10 });
    const top = mainTop + (featureTop - mainTop) * up - (featureTop - mainTop) * down;
    runner.style.top = top + "px";
  };
});
