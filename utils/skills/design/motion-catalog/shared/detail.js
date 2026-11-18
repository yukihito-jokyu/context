/* ============================================================
   詳細ページの共通処理
   animations/<id>.html から CatalogDetail.mount(データ) で呼ぶ。

   データの形:
   - id:          英小文字とハイフン。ファイル名・プロンプトで使う
   - name:        名前（日本語）
   - en:          英語名。AI に指示するときの言葉
   - cat:         カテゴリ名
   - kind:        "motion"（動き）/ "concept"（考え方）/ "style"（表現スタイル）
   - description: 何の動きか
   - use:         使う場面
   - params:      バーで変えられる値。{ key, label, value(初期値), min, max, step, unit }
                  CSS では var(--key, 初期値) として受け取る
   - total:       params から全体の長さ（ms）を計算する関数
   - spec:        [項目, 内容] の配列。イージング・順序など、params 以外の決まり
   - loop:        ループ時に再生し直す間隔（ms）。0 は CSS や run の中でずっと動き続けるもの
   - run:         （任意）再生のたびに呼ぶ関数 (stage, values) => 後片付けの関数。JS が必要な動きに使う
   プレビューの HTML は同じページの <template id="stage">、動きの本体は <style id="motion"> に書く。

   URL の末尾が #preview のときは、プレビューだけをループ表示する（一覧のカード用）。
   ============================================================ */
(function () {
  const fmt = (p, v) => (p.unit ? `${v}${p.unit}` : String(Number(v.toFixed(2))));

  const KIND = { motion: "動き", concept: "考え方", style: "表現スタイル" };

  const promptText = (a, values) => {
    let text =
      a.kind === "concept"
        ? `motion-catalog スキルの「${a.name}（${a.id}）」の考え方で、動きを見直して。\n対象: 〈ここに見直したい動きや画面を書く〉`
        : a.kind === "style"
          ? `motion-catalog スキルで「${a.name}（${a.id}）」の表現を作って。\n対象: 〈ここに作りたい画面やセクションを書く〉`
          : `motion-catalog スキルで「${a.name}（${a.id}）」を実装して。\n対象: 〈ここに適用したい要素や画面を書く〉`;
    const changed = (a.params || []).filter((p) => values[p.key] !== p.value);
    if (changed.length) text += `\n値の変更: ${changed.map((p) => `${p.label} ${fmt(p, values[p.key])}`).join("、")}`;
    return text;
  };

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
  }

  // 再生：プレビューの HTML を入れ直し（CSS アニメーションが頭から始まる）、run があれば呼ぶ
  function player(a, stage, stageHTML, values) {
    let cleanup = null;
    return () => {
      if (typeof cleanup === "function") cleanup();
      stage.innerHTML = stageHTML;
      cleanup = a.run ? a.run(stage, { ...values }) : null;
    };
  }

  function mountPreview(a, stageHTML) {
    document.body.className = "c-preview";
    document.body.innerHTML = `<div class="c-preview-stage sb-root" aria-hidden="true"></div>`;
    const stage = document.body.firstElementChild;
    const values = Object.fromEntries((a.params || []).map((p) => [p.key, p.value]));
    params(a).forEach((p) => stage.style.setProperty(`--${p.key}`, cssValue(p, p.value)));
    const play = player(a, stage, stageHTML, values);
    play();
    if (a.loop) setInterval(play, a.loop);
  }

  const params = (a) => a.params || [];
  const cssValue = (p, v) => (p.unit ? `${v}${p.unit}` : String(v));

  function mountDetail(a, stageHTML) {
    const params = a.params || [];
    const values = Object.fromEntries(params.map((p) => [p.key, p.value]));
    document.title = `${a.name}（${a.en}） | Animation Catalog`;
    document.body.className = "is-fit";
    document.body.innerHTML = `
<header class="c-header">
  <div class="c-wrap"><span class="c-mark" aria-hidden="true"></span><a class="c-brand" href="../catalog.html">Animation Catalog</a></div>
</header>
<main class="c-main"><div class="c-wrap">
  <div class="c-detail-head">
    <a class="c-back" href="../catalog.html">← 一覧へ</a>
    <h1 class="c-h1">${a.name}</h1>
    <span class="c-en">${a.en}</span>
    <span class="c-id">${[a.id, a.cat, KIND[a.kind] || "動き"].filter((x, i, l) => l.indexOf(x) === i).join(" · ")}</span>
  </div>
  <div class="c-detail">
    <div class="c-detail-left">
      <div class="c-stage">
        <div class="sb-root" style="position:absolute;inset:0;display:grid;place-items:center;border-radius:inherit" aria-hidden="true" data-stage></div>
        <div class="c-stage-tools">
          ${a.loop ? `<button class="c-btn" type="button" aria-pressed="false" aria-label="ループ再生" title="ループ再生（オン／オフ）" data-loop>ループ</button>` : ""}
          <button class="c-btn" type="button" aria-label="もう一度再生" title="もう一度再生" data-replay>↻ 再生</button>
        </div>
      </div>
      ${
        params.length
          ? `
      <section>
        <div class="c-tune-head">
          <h2 class="c-h2">動きの値</h2>
          <span class="c-tune-total">${a.total ? `全体 <span data-total></span>` : ""}</span>
          <button class="c-btn c-btn--sm" type="button" data-reset>初期値に戻す</button>
        </div>
        <div class="c-tune">
          ${params
            .map(
              (p) => `
          <div class="c-tune-row">
            <label for="p-${p.key}">${p.label}</label>
            <input type="range" id="p-${p.key}" data-key="${p.key}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.value}">
            <output data-out="${p.key}">${fmt(p, p.value)}</output>
          </div>`,
            )
            .join("")}
        </div>
      </section>`
          : ""
      }
      <section class="c-prompt">
        <h2 class="c-h2">実装用プロンプト</h2>
        <div class="c-prompt-box">
          <div class="c-prompt-head">
            <span>Claude Code に貼り付け、「対象」を書き換えて使います</span>
            <button class="c-btn c-btn--primary" type="button" data-copy>コピー</button>
          </div>
          <pre></pre>
        </div>
      </section>
    </div>
    <div class="c-detail-right">
      <section class="c-section">
        <h2 class="c-h2">説明</h2>
        <p>${a.description}</p>
        <p><span style="color:var(--c-muted)">使う場面：</span>${a.use}</p>
      </section>
      <section class="c-section">
        <h2 class="c-h2">動きの決まり</h2>
        <dl class="c-spec">${a.spec.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("")}</dl>
      </section>
    </div>
  </div>
</div></main>`;

    const $ = (sel) => document.querySelector(sel);
    const stage = $("[data-stage]");
    const pre = $("pre");
    const totalEl = $("[data-total]");
    const play = player(a, stage, stageHTML, values);

    // 値をプレビュー（CSS 変数）・数値表示・全体の長さ・プロンプトに反映する
    const sync = () => {
      params.forEach((p) => {
        stage.style.setProperty(`--${p.key}`, cssValue(p, values[p.key]));
        $(`[data-out="${p.key}"]`).textContent = fmt(p, values[p.key]);
      });
      if (totalEl && a.total) totalEl.textContent = `${a.total(values)}ms`;
      pre.textContent = promptText(a, values);
    };

    document.querySelectorAll("input[type=range]").forEach((input) => {
      input.addEventListener("input", () => {
        values[input.dataset.key] = Number(input.value);
        sync();
      });
      input.addEventListener("change", play);
    });
    const resetBtn = $("[data-reset]");
    if (resetBtn)
      resetBtn.addEventListener("click", () => {
        params.forEach((p) => {
          values[p.key] = p.value;
          $(`#p-${p.key}`).value = p.value;
        });
        sync();
        play();
      });

    // ループは最初オフ。開いたときに1回だけ再生する
    const loopBtn = $("[data-loop]");
    let loopTimer = null;
    if (loopBtn)
      loopBtn.addEventListener("click", () => {
        const on = loopBtn.getAttribute("aria-pressed") !== "true";
        loopBtn.setAttribute("aria-pressed", String(on));
        clearInterval(loopTimer);
        if (on) {
          play();
          loopTimer = setInterval(play, a.loop);
        }
      });
    $("[data-replay]").addEventListener("click", play);

    const copyBtn = $("[data-copy]");
    copyBtn.addEventListener("click", async () => {
      await copyText(pre.textContent);
      copyBtn.textContent = "コピーしました";
      setTimeout(() => {
        copyBtn.textContent = "コピー";
      }, 1600);
    });

    sync();
    play();
  }

  window.CatalogDetail = {
    mount(a) {
      const stageHTML = document.getElementById("stage").innerHTML;
      if (location.hash === "#preview") mountPreview(a, stageHTML);
      else mountDetail(a, stageHTML);
    },
  };
})();
