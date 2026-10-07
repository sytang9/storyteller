// The event track: word-timed changes on top of any scene, so a beat keeps moving after its picture is built.
// scene.events: [{kind, word, ...}]. `word` is a caption word or [word, n]; each change lands LEAD s before it.
// Text events find their target by its text inside the scene ("target": "125"); the first match wins. A counter
// shows "0" while the scene is built, so target its label, not its number.
// Kinds and fields:
//   hero   {text, x, y, size?: 128, color?, until?}          a big word in the display face at scene px (x, y)
//   lift   {x, y, size?: 96, color?, text?, until?}           the caption word leaves the band and lands at (x, y)
//   mark   {target, style?: sweep|underline|circle, color?}   a highlight drawn on a phrase as it is spoken
//   swap   {target, to, color?}                               the phrase rolls out and `to` rolls in, in place
//   strike {target, to?}                                      a line through the phrase; `to` appears beside it
//   number {target, to, dur?: 0.8}                            a plain number counts to `to`, landing on the word
//   note   {target, text, side?: above|below|left|right, color?, until?}  a short tag with a drawn arrow
//   push   {target, zoom?: 1.5, until?}                       the camera pushes in on the phrase's box
// `until` (a word) ends the event: the item leaves, or the camera returns.
// Helpers from index.html: el, svgEl, tl, C, col, cue, wordAt, ENTER, EXIT, MOVE; from motion.js: popIn, reveal, drawLine,
// addArrow, CAM; countUp from scenes.js. wrapText (the `wrap` below) is shared with the morph transition.
window.LIFTS = [];
window.PUSHES = [];
(function () {
  const W = (w) => [].concat(w);
  const leave = (nodes, b, e) => e.until && tl.to(nodes, { opacity: 0, duration: 0.3, ease: EXIT }, cue(b, ...W(e.until)));

  // the box of a node in its scene's px, from offsets (the pop-in transforms at time 0 are ignored on purpose)
  function sceneBox(node, root) {
    let x = 0;
    let y = 0;
    for (let n = node; n && n !== root; n = n.offsetParent) {
      x += n.offsetLeft + (gsap.getProperty(n, "xPercent") / 100) * n.offsetWidth; // a label centred with xPercent
      y += n.offsetTop + (gsap.getProperty(n, "yPercent") / 100) * n.offsetHeight;
    }
    return { x0: x, y0: y, x1: x + node.offsetWidth, y1: y + node.offsetHeight };
  }

  // wrap the first HTML text match of `text` in an inline-block span, so it can be measured and moved
  function wrap(root, b, text) {
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let t = walk.nextNode(); t; t = walk.nextNode()) {
      const i = t.data.indexOf(text);
      if (i < 0 || t.parentNode.namespaceURI !== "http://www.w3.org/1999/xhtml") continue;
      // in a flex or grid box each text run is its own item and loses its edge spaces: keep the runs in one span
      const p = t.parentNode;
      if (/flex|grid/.test(getComputedStyle(p).display)) {
        const inner = document.createElement("span");
        while (p.firstChild) inner.appendChild(p.firstChild);
        p.appendChild(inner);
      }
      const mid = t.splitText(i);
      mid.splitText(text.length);
      const span = document.createElement("span");
      Object.assign(span.style, { display: "inline-block", position: "relative", isolation: "isolate" });
      mid.replaceWith(span);
      span.appendChild(mid);
      return span;
    }
    throw new Error(`beat ${b.id}: event target "${text}" not found in the scene`);
  }

  function hero(root, b, e) {
    const n = el("div", "abs t-display", root, { left: e.x + "px", top: e.y + "px", fontSize: (e.size || 128) + "px", color: col(e.color || "accent"), whiteSpace: "nowrap", transformOrigin: "0% 100%" }, e.text);
    reveal(n, cue(b, ...W(e.word)), "text");
    leave(n, b, e);
  }

  function mark(root, b, e) {
    const s = wrap(root, b, e.target);
    const c = col(e.color || "accent");
    const t = cue(b, ...W(e.word));
    if (e.style === "circle") {
      const w = s.offsetWidth + 56;
      const h = s.offsetHeight + 40;
      const svg = svgEl("svg", s, { class: "abs", width: w, height: h, style: "left:-28px;top:-20px;overflow:visible" });
      // two half-ellipses round the phrase; the second ends a little past the start, like a pen mark
      const [rx, ry] = [w / 2 - 2, h / 2 - 2];
      const p = svgEl("path", svg, { d: `M2 ${h / 2} A${rx} ${ry} 0 1 1 ${w - 2} ${h / 2} A${rx} ${ry} 0 1 1 ${10} ${h / 2 - 8}`, fill: "none", stroke: c, "stroke-width": 4, "stroke-linecap": "round" });
      tl.set(p, { opacity: 0 }, 0);
      tl.set(p, { opacity: 1 }, t);
      drawLine(p, t, 0.5);
      return;
    }
    const css = e.style === "underline"
      ? { left: 0, right: 0, bottom: "-0.04em", height: "0.09em", background: c }
      : { left: "-0.12em", right: "-0.12em", top: "0.1em", bottom: "0.02em", background: `color-mix(in srgb, ${c} 30%, transparent)`, zIndex: -1 };
    const bar = el("span", "abs", s, { ...css, transformOrigin: "0% 50%" });
    tl.set(bar, { scaleX: 0 }, 0);
    tl.to(bar, { scaleX: 1, duration: 0.45, ease: MOVE }, t);
  }

  function swap(root, b, e) {
    const s = wrap(root, b, e.target);
    s.textContent = "";
    Object.assign(s.style, { overflow: "hidden", verticalAlign: "bottom", paddingBottom: "0.08em" });
    const a = el("span", "", s, { display: "inline-block" }, e.target);
    const z = el("span", "abs", s, { left: 0, top: 0, whiteSpace: "nowrap", color: col(e.color || "accent") }, e.to);
    s.style.width = Math.max(a.offsetWidth, z.offsetWidth) + "px"; // the slot fits the longer text from the start
    const t = cue(b, ...W(e.word));
    tl.set(z, { yPercent: 110 }, 0);
    tl.to(a, { yPercent: -110, duration: 0.4, ease: EXIT }, t);
    tl.to(z, { yPercent: 0, duration: 0.45, ease: ENTER }, t + 0.1);
  }

  function strike(root, b, e) {
    const s = wrap(root, b, e.target);
    const t = cue(b, ...W(e.word));
    const line = el("span", "abs", s, { left: "-0.05em", right: "-0.05em", top: "52%", height: "0.08em", background: C.ink, transformOrigin: "0% 50%" });
    tl.set(line, { scaleX: 0 }, 0);
    tl.to(line, { scaleX: 1, duration: 0.35, ease: MOVE }, t);
    tl.to(s, { opacity: 0.55, duration: 0.3 }, t + 0.3);
    if (e.to) {
      // the new text sits just after the old one, out of the flow, so nothing reflows when it appears
      const n = el("span", "abs", s.parentNode, { left: s.offsetLeft + s.offsetWidth + 16 + "px", top: s.offsetTop + "px", whiteSpace: "nowrap", color: C.accent }, e.to);
      reveal(n, t + 0.45, "text");
    }
  }

  function number(root, b, e) {
    const s = wrap(root, b, e.target);
    const from = parseFloat(e.target.replace(/[^\d.-]/g, ""));
    if (Number.isNaN(from)) throw new Error(`beat ${b.id}: number target "${e.target}" is not a number`);
    const land = wordAt(b, ...W(e.word));
    countUp(s, from, e.to, land, Math.min(e.dur || 0.8, land - b.start - 0.1)); // never starts before the beat
  }

  const NOTE_GAP = 100; // px between the target and its tag
  const TIP_GAP = 6; // scene px between the arrow tip and the target: at most 12 px on screen at the 2x fit cap
  function note(root, b, e) {
    const s = wrap(root, b, e.target);
    // punctuation right after the phrase joins its box, so the arrow never points into a full stop
    const tail = s.nextSibling;
    const punct = tail && tail.nodeType === Node.TEXT_NODE && tail.data.match(/^[.,;:!?]+/);
    if (punct) {
      s.appendChild(document.createTextNode(punct[0]));
      tail.data = tail.data.slice(punct[0].length);
    }
    const bx = sceneBox(s, root);
    const c = col(e.color || "accent");
    const tag = el("div", "abs", root, { fontSize: "36px", lineHeight: 1.2, fontWeight: 700, color: c, whiteSpace: "nowrap" }, e.text);
    const tw = tag.offsetWidth;
    const th = tag.offsetHeight;
    const cx = (bx.x0 + bx.x1) / 2;
    const cy = (bx.y0 + bx.y1) / 2;
    const side = e.side || "above";
    // tag position and the arrow's two ends (from the tag to just outside the target)
    const at = {
      above: { x: cx + 40, y: bx.y0 - NOTE_GAP - th, from: [cx + 40 + 12, bx.y0 - NOTE_GAP], to: [cx, bx.y0 - TIP_GAP] },
      below: { x: cx + 40, y: bx.y1 + NOTE_GAP, from: [cx + 40 + 12, bx.y1 + NOTE_GAP], to: [cx, bx.y1 + TIP_GAP] },
      left: { x: bx.x0 - NOTE_GAP - tw, y: cy - th - 20, from: [bx.x0 - NOTE_GAP, cy - 20], to: [bx.x0 - TIP_GAP, cy] },
      right: { x: bx.x1 + NOTE_GAP, y: cy - th - 20, from: [bx.x1 + NOTE_GAP, cy - 20], to: [bx.x1 + TIP_GAP, cy] },
    }[side];
    Object.assign(tag.style, { left: at.x + "px", top: at.y + "px" });
    const svg = svgEl("svg", root, { class: "abs", width: 1920, height: 900, style: "left:0;top:0;overflow:visible" });
    const [x0, y0] = at.from;
    const [x1, y1] = at.to;
    const bend = side === "above" || side === "below" ? [x0, y1] : [x1, y0]; // one soft curve
    const g = svgEl("g", svg, {});
    const path = svgEl("path", g, { d: `M${x0} ${y0} Q${bend[0]} ${bend[1]} ${x1} ${y1}`, fill: "none", stroke: c, "stroke-width": 4, "stroke-linecap": "round" });
    const ang = Math.atan2(y1 - bend[1], x1 - bend[0]);
    const tip = (r, da) => `${x1 - r * Math.cos(ang + da)} ${y1 - r * Math.sin(ang + da)}`;
    const head = svgEl("path", g, { d: `M${tip(16, 0.5)} L${x1} ${y1} L${tip(16, -0.5)}`, fill: "none", stroke: c, "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" });
    const t = cue(b, ...W(e.word));
    reveal(tag, t, "text");
    tl.set([path, head], { opacity: 0 }, 0);
    tl.set(path, { opacity: 1 }, t + 0.15);
    drawLine(path, t + 0.15, 0.4);
    tl.to(head, { opacity: 1, duration: 0.15 }, t + 0.5);
    addArrow(b, svg, x1, y1, s, t + 0.7); // checked after the build, in frame px
    leave([tag, g], b, e);
  }

  // lift and push need the scene's fit (and the caption band) first: index.html finishes them after the assembly
  function lift(root, b, e) {
    window.LIFTS.push({ b, e, t: wordAt(b, ...W(e.word)) });
  }
  function push(root, b, e) {
    const s = wrap(root, b, e.target);
    window.PUSHES.push({ b, e, box: sceneBox(s, root), t: cue(b, ...W(e.word)) });
  }

  window.wrapText = wrap;
  const KINDS = { hero, lift, mark, swap, strike, number, note, push };
  window.runEvents = (root, b) =>
    (b.scene.events || []).forEach((e) => {
      if (!KINDS[e.kind]) throw new Error(`beat ${b.id}: no event kind "${e.kind}" (${Object.keys(KINDS).join(", ")})`);
      KINDS[e.kind](root, b, e);
    });
})();

// Pushes and lifts need each scene's fit (index.html) and the caption band, so the assembly calls this last.
// bodies: [{b, body, cam, f: {tx, ty, sc}}]; spans: caption word spans by beat id and word index.
window.finishEvents = function (bodies, SPANS) {
  const byId = Object.fromEntries(bodies.map((q) => [q.b.id, q]));
  const endOf = (b) => { const i = D.beats.indexOf(b); return i + 1 < D.beats.length ? D.beats[i + 1].start : D.total; };
  // push: the camera moves so the target's box sits in the middle of the free area, at `zoom`
  window.PUSHES.forEach(({ b, e, box, t }) => {
    const q = byId[b.id];
    const ui = b.kind === "ui" && !(b.scene.eyebrow || b.scene.title);
    const [top, bottom] = ui ? [UI_MARGIN, FRAME_H - UI_MARGIN] : [FIT_TOP, FIT_BOTTOM];
    const bw = q.f.sc * (box.x1 - box.x0);
    const bh = q.f.sc * (box.y1 - box.y0);
    // the zoomed box must fit the free area with a margin, so a push never pushes the target out of frame
    const k = Math.max(1, Math.min(e.zoom || 1.5, (0.8 * (1920 - 2 * FIT_X)) / bw, (0.8 * (bottom - top)) / bh));
    const fx = q.f.tx + q.f.sc * (box.x0 + box.x1) / 2;
    const fy = q.f.ty + q.f.sc * (box.y0 + box.y1) / 2;
    tl.to(q.cam, { x: 960 - fx * k, y: (top + bottom) / 2 - fy * k, scale: k, duration: 0.8, ease: CAM }, Math.max(b.start, t - 0.2));
    if (e.until) tl.to(q.cam, { x: 0, y: 0, scale: 1, duration: 0.7, ease: CAM }, cue(b, ...[].concat(e.until)));
  });
  // lift: the caption word leaves the band and lands in the scene at (x, y), in the display face. It lives in a
  // layer above the stage, so it leaves on its own at `until` or at the end of its beat.
  const liftLayer = el("div", "abs", document.getElementById("root"), { left: 0, top: 0, width: "1920px", height: "1080px" });
  window.LIFTS.forEach(({ b, e, t }) => {
    const q = byId[b.id];
    const w = [].concat(e.word);
    const k = b.words.findIndex((x, i) => norm(x.w) === w[0].toLowerCase() && b.words.slice(0, i).filter((y) => norm(y.w) === w[0].toLowerCase()).length === (w[1] || 0));
    const size = e.size || 96;
    const x = q.f.tx + q.f.sc * e.x;
    const y = q.f.ty + q.f.sc * e.y;
    const n = el("div", "abs t-display", liftLayer, { left: x + "px", top: y + "px", fontSize: size * q.f.sc + "px", color: col(e.color || "accent"), whiteSpace: "nowrap", transformOrigin: "0 0" }, e.text || b.words[k].w.replace(/[^\w'-]/g, ""));
    const span = (SPANS[b.id] || {})[k];
    tl.set(n, { opacity: 0 }, 0);
    if (span) {
      // start on top of the spoken word in the band, at the caption's size, then fly up to the scene
      const r = span.getBoundingClientRect(); // the band is never transformed, so this is frame px
      tl.fromTo(n, { opacity: 1, x: r.left - x, y: r.top - y, scale: 48 / (size * q.f.sc) }, { opacity: 1, x: 0, y: 0, scale: 1, duration: 0.7, ease: MOVE, immediateRender: false }, t - 0.05);
      tl.to(span, { opacity: 0.3, duration: 0.2 }, t - 0.05); // the word is not shown twice
    } else popIn(n, t - 0.3, { opacity: 0, y: 30, scale: 0.85 });
    tl.to(n, { opacity: 0, duration: 0.3, ease: EXIT }, e.until ? cue(b, ...[].concat(e.until)) : endOf(b) - 0.5);
  });
};
