// scenes.js — data-* と部品で書けない動きを、フレームの関数として書く。
// （線に沿って進む・語ごとに出る・寄る/引くなどは data-* と部品で書けるので、ここには書かない）
//
// Motion.scene("シーンid", (s) => {
//   // 準備（一度だけ）：要素を探す
//   return (frame) => {
//     // 毎フレーム：frame と s.* の値だけから見た目を決める（状態を溜めない）
//   };
// });

// 時間の帯：走者が今読んでいる文の上を歩く
Motion.scene("timing", (s) => {
  const runner = s.$("#t-runner");
  const labelW = 260, track = 1720 - 260;
  const spans = [[0, 0, 3], ["head", 3, 6], ["figure", 6, 9], ["card", 9, 12]];
  return () => {
    let sec = 0;
    for (const [cue, a, b] of spans) if (s.reached(cue)) sec = s.interpolate(s.progress(cue), [0, 1], [a, b]);
    runner.style.left = labelW + (sec / 12) * track - 32 + "px";
    runner.style.opacity = s.reached(0, 10) ? 1 : 0;
  };
});
