// More scene TYPES, for variety: type as the picture, before/after, a diagram that draws itself, layers in depth.
// Same contract as scenes.js: fn(root, beat) reads beat.scene, builds DOM in root, adds tweens to the shared tl.
// Helpers from index.html: el, svgEl, tl, C, col, cue, head, ENTER, EXIT, MOVE; from motion.js: reveal, popIn, drawLine,
// addArrow, CAM.
// A `word` field is a caption word, or [word, n] for its nth use; changes land LEAD s before it.

const words = (w) => [].concat(w); // "word" or ["word", n] -> arguments for cue()

// statement: one short claim set large in the display face, line by line on spoken words, with one term marked.
// scene: {eyebrow?, lines: [text], in: [word per line], em?: {text, word, style?: "block"|"underline", color?}, size?: px (default 120)}
//   em.text must sit inside one line. "block" (default): a block in the look's --em colour wipes in behind it and the
//   word turns to the ground colour; "underline": the word turns em.color and an underline draws
function sceneStatement(root, b) {
  const s = b.scene;
  if (s.eyebrow) head(root, s.eyebrow);
  const size = s.size || 120;
  const box = el("div", "abs", root, { left: "120px", top: "240px", display: "flex", flexDirection: "column", gap: size * 0.1 + "px" });
  s.lines.forEach((text, i) => {
    const line = el("div", "t-display", box, { fontSize: size + "px", lineHeight: 1.05, whiteSpace: "nowrap" });
    const at = s.em && text.indexOf(s.em.text);
    if (s.em && at >= 0) {
      line.append(text.slice(0, at));
      const em = el("span", "", line, { position: "relative", display: "inline-block" }, s.em.text);
      line.append(text.slice(at + s.em.text.length));
      const t = cue(b, ...words(s.em.word));
      const c = col(s.em.color || "em");
      if ((s.em.style || "block") === "block") {
        // a solid block wipes in behind the word and the word turns to the ground colour: it stands out on any look
        // without borrowing a role colour (an underline in ink read as faint on a dark ground)
        Object.assign(em.style, { isolation: "isolate", padding: "0 0.12em", margin: "0 0.04em 0 -0.12em" }); // the right padding stays, so a following "." sits clear of the block
        const block = el("span", "abs", em, { left: 0, right: 0, top: "0.06em", bottom: "-0.2em", background: c, zIndex: -1, transformOrigin: "0% 50%" }); // deep enough for descenders (g, y), which turn to the ground colour
        tl.set(block, { scaleX: 0 }, 0);
        tl.to(block, { scaleX: 1, duration: 0.4, ease: MOVE }, t);
        tl.to(em, { color: C.bg, duration: 0.2, ease: ENTER }, t + 0.15);
      } else {
        const mark = el("span", "abs", em, { left: 0, right: 0, bottom: "-0.04em", height: "0.1em", background: c, transformOrigin: "0% 50%" });
        tl.set(mark, { scaleX: 0 }, 0);
        tl.to(em, { color: c, duration: 0.3, ease: ENTER }, t);
        tl.to(mark, { scaleX: 1, duration: 0.45, ease: MOVE }, t);
      }
    } else line.textContent = text;
    reveal(line, cue(b, ...words(s.in[i])), "text");
  });
}

// compare: the old way beside the new. The left panel enters first; the right panel wipes in on its word.
// strike crosses out left items that go away; links tie a left item to what it became on the right.
// scene: {eyebrow, title, left: {label, items: [text | {text, color?, word?}], word, color?}, right: {label, items, word, color?},
//         strike?: {items: [left indices], word}, links?: [{from: left index, to: right index, word}]}
//   items: 6 at most per side, each 5 words or fewer (one line)
const CMP = { x: [120, 1040], w: 760, top: 0, row: 96, gap: 20, labelH: 72 };
function sceneCompare(root, b) {
  const s = b.scene;
  head(root, s.eyebrow, s.title);
  const wrap = el("div", "abs", root, { left: 0, top: "240px", width: "1920px", height: CMP.labelH + Math.max(s.left.items.length, s.right.items.length) * (CMP.row + CMP.gap) + "px" });
  const rowY = (k) => CMP.labelH + k * (CMP.row + CMP.gap);
  const sides = [s.left, s.right].map((side, i) => {
    const panel = el("div", "abs", wrap, { left: CMP.x[i] + "px", top: 0, width: CMP.w + "px", height: rowY(side.items.length) + "px" });
    const color = col(side.color || (i ? "accent" : "mute"));
    el("div", "abs t-eyebrow", panel, { left: 0, top: "16px", color }, side.label);
    const rows = side.items.map((it, k) => {
      const c = typeof it === "string" ? color : col(it.color || side.color || (i ? "accent" : "mute"));
      const r = el("div", "abs card t-body", panel, { left: 0, top: rowY(k) + "px", width: CMP.w + "px", height: CMP.row + "px", fontSize: "40px", display: "flex", alignItems: "center", padding: "0 28px", whiteSpace: "nowrap", borderLeft: `6px solid ${c}` }, typeof it === "string" ? it : it.text);
      r.dataset.color = c;
      return r;
    });
    const t = cue(b, ...words(side.word));
    // an item with its own `word` enters on it, so the list builds with the voice; the rest enter with the side
    const own = (k) => typeof side.items[k] === "object" && side.items[k].word;
    rows.forEach((r, k) => own(k) && reveal(r, cue(b, ...words(side.items[k].word)), "card", { from: "left" }));
    if (i === 0) rows.forEach((r, k) => own(k) || reveal(r, t + k * 0.12, "card", { from: "left" })); // each row grows out of its colour edge
    else {
      tl.fromTo(panel, { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.6, ease: MOVE, immediateRender: true }, t);
    }
    return { panel, rows };
  });
  // the divider: a thin rule between the panels
  const mid = (CMP.x[0] + CMP.w + CMP.x[1]) / 2;
  const div = el("div", "abs", wrap, { left: mid - 1 + "px", top: CMP.labelH + "px", width: "2px", height: rowY(Math.max(s.left.items.length, s.right.items.length)) - CMP.labelH + "px", background: C.line, transformOrigin: "50% 0%" });
  tl.fromTo(div, { scaleY: 0 }, { scaleY: 1, duration: 0.5, ease: MOVE, immediateRender: true }, cue(b, ...words(s.right.word)) - 0.2);
  if (s.strike) {
    const t = cue(b, ...words(s.strike.word));
    s.strike.items.forEach((k, j) => {
      const r = sides[0].rows[k];
      const line = el("span", "abs", r, { left: "20px", right: "20px", top: CMP.row / 2 - 2 + "px", height: "4px", background: C.ink, transformOrigin: "0% 50%" });
      tl.set(line, { scaleX: 0 }, 0);
      tl.to(line, { scaleX: 1, duration: 0.35, ease: MOVE }, t + j * 0.1);
      tl.to(r, { color: C.mute, opacity: 0.55, duration: 0.3 }, t + j * 0.1 + 0.2);
    });
  }
  const svg = svgEl("svg", wrap, { class: "abs", width: 1920, height: rowY(6), style: "left:0;top:0;overflow:visible" });
  (s.links || []).forEach((l) => {
    const y0 = rowY(l.from) + CMP.row / 2;
    const y1 = rowY(l.to) + CMP.row / 2;
    const x0 = CMP.x[0] + CMP.w;
    const x1 = CMP.x[1];
    const tint = sides[1].rows[l.to].dataset.color;
    const path = svgEl("path", svg, { d: `M${x0} ${y0} C${mid} ${y0} ${mid} ${y1} ${x1} ${y1}`, fill: "none", stroke: tint, "stroke-width": 4, "stroke-linecap": "round" });
    const t = cue(b, ...words(l.word));
    tl.set(path, { opacity: 0 }, 0);
    tl.set(path, { opacity: 1 }, t);
    drawLine(path, t, 0.45);
    tl.to(sides[1].rows[l.to], { borderColor: tint, duration: 0.3 }, t + 0.35);
  });
}

// diagram: a picture that draws itself. Nodes pop on their words, edges draw on theirs, and on focus.word the camera
// pushes into a group of nodes while the rest dim. Coordinates are node centres in scene px (x 0-1920, y 0-900).
// scene: {eyebrow, title, nodes: [{id, text, x, y, w?, h?, shape?: "box"|"pill"|"dot", color?, word}],
//         edges: [{from, to, word, label?, dashed?, color?}], focus?: {nodes: [ids], word, zoom?: 1.6}}
//   a dot is a 28 px circle with its text below; boxes default to 300 x 96
const NODE = { w: 300, h: 96, dot: 28 };
function sceneDiagram(root, b) {
  const s = b.scene;
  const h = head(root, s.eyebrow, s.title);
  const size = (n) => (n.shape === "dot" ? { w: NODE.dot, h: NODE.dot } : { w: n.w || NODE.w, h: n.h || NODE.h });
  const byId = Object.fromEntries(s.nodes.map((n) => [n.id, { ...n, ...size(n) }]));
  const all = Object.values(byId);
  // the wrapper hugs the nodes, so the fit (index.html) frames the drawing, not the whole stage
  const pad = 60;
  const bx = { x0: Math.min(...all.map((n) => n.x - n.w / 2)) - pad, y0: Math.min(...all.map((n) => n.y - n.h / 2)) - pad };
  bx.x1 = Math.max(...all.map((n) => n.x + Math.max(n.w, n.shape === "dot" ? 260 : 0) / 2)) + pad;
  bx.y1 = Math.max(...all.map((n) => n.y + n.h / 2 + (n.shape === "dot" ? 64 : 0))) + pad;
  const W = bx.x1 - bx.x0;
  const H = bx.y1 - bx.y0;
  const wrap = el("div", "abs", root, { left: bx.x0 + "px", top: bx.y0 + "px", width: W + "px", height: H + "px" });
  if (s.focus) wrap.setAttribute("data-layout-allow-overflow", ""); // the push frames the focus group; the rest may leave the frame
  const X = (x) => x - bx.x0;
  const Y = (y) => y - bx.y0;
  const svg = svgEl("svg", wrap, { class: "abs", width: W, height: H, style: "left:0;top:0;overflow:visible" });
  // an edge runs between the two node borders, along the line joining their centres; its tip stops 6 px short of
  // the border (at most 12 px on screen at the 2x fit cap, the arrow check's tolerance)
  const rim = (n, dx, dy) => {
    const t = Math.min(n.w / 2 / Math.abs(dx || 1e-9), n.h / 2 / Math.abs(dy || 1e-9)) + 6 / Math.hypot(dx, dy);
    return [n.x + dx * t, n.y + dy * t];
  };
  const parts = {};
  const hits = {}; // the box an arrow must touch: the node, or a dot's circle
  (s.edges || []).forEach((e) => {
    const a = byId[e.from];
    const z = byId[e.to];
    if (!a || !z) throw new Error(`beat ${b.id}: edge ${e.from}->${e.to} names a missing node`);
    const dx = z.x - a.x;
    const dy = z.y - a.y;
    const [x0, y0] = rim(a, dx, dy);
    const [x1, y1] = rim(z, -dx, -dy);
    const stroke = col(e.color || "ink");
    const g = svgEl("g", svg, {});
    const path = svgEl("path", g, { d: `M${X(x0)} ${Y(y0)} L${X(x1)} ${Y(y1)}`, fill: "none", stroke, "stroke-width": 4, "stroke-linecap": "round", ...(e.dashed ? { "stroke-dasharray": "10 12" } : {}) });
    const ang = Math.atan2(y1 - y0, x1 - x0);
    const tip = (r, da) => `${X(x1) - r * Math.cos(ang + da)} ${Y(y1) - r * Math.sin(ang + da)}`;
    const head_ = svgEl("path", g, { d: `M${tip(18, 0.45)} L${X(x1)} ${Y(y1)} L${tip(18, -0.45)}`, fill: "none", stroke, "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" });
    // an edge waits for both of its nodes: an arrow that lands before its target shows points at nothing
    const t = Math.max(cue(b, ...words(e.word)), ...[a, z].map((n) => cue(b, ...words(n.word)) + 0.2));
    if (e.dashed) popIn(path, t, { opacity: 0 });
    else {
      tl.set(path, { opacity: 0 }, 0); // a zero-length dash with a round cap still draws a dot
      tl.set(path, { opacity: 1 }, t);
      drawLine(path, t, 0.45);
    }
    popIn(head_, t + 0.4, { opacity: 0 });
    addArrow(b, svg, X(x1), Y(y1), () => hits[e.to], t + 0.8); // checked after the build, in frame px
    if (e.label) {
      const len = Math.hypot(x1 - x0, y1 - y0);
      const [nx, ny] = [-(y1 - y0) / len, (x1 - x0) / len]; // the label sits 36 px to one side of the line
      const lab = el("div", "abs t-label mute", wrap, { left: X((x0 + x1) / 2 + nx * 36) + "px", top: Y((y0 + y1) / 2 + ny * 36) + "px", whiteSpace: "nowrap", transform: "translate(-50%, -50%)" }, e.label);
      popIn(lab, t + 0.3, { opacity: 0 });
      parts[`${e.from}>${e.to}:label`] = lab;
    }
    parts[`${e.from}>${e.to}`] = g;
  });
  all.forEach((n) => {
    const color = col(n.color || "accent");
    let node;
    if (n.shape === "dot") {
      node = el("div", "abs", wrap, { left: X(n.x) - 130 + "px", top: Y(n.y) - n.h / 2 + "px", width: "260px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" });
      hits[n.id] = el("div", "", node, { width: n.w + "px", height: n.h + "px", borderRadius: "50%", background: color });
      el("div", "t-label", node, { textAlign: "center" }, n.text);
    } else {
      node = el("div", "abs card t-body", wrap, {
        left: X(n.x) - n.w / 2 + "px", top: Y(n.y) - n.h / 2 + "px", width: n.w + "px", height: n.h + "px", display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 20px", borderColor: color, borderWidth: "3px", background: `color-mix(in srgb, ${color} 14%, ${C.surface})`, ...(n.shape === "pill" ? { borderRadius: n.h / 2 + "px" } : {}),
      }, n.text);
    }
    hits[n.id] = hits[n.id] || node;
    // a box grows from its edge with its text following; a dot settles from 0.6 and its text rises after it
    if (n.shape === "dot") {
      reveal(hits[n.id], cue(b, ...words(n.word)), "icon");
      reveal(node.lastChild, cue(b, ...words(n.word)) + 0.1, "text");
    } else reveal(node, cue(b, ...words(n.word)), "card");
    parts[n.id] = node;
  });
  if (s.focus) {
    const f = s.focus.nodes.map((id) => byId[id]);
    const k = s.focus.zoom || 1.6;
    const fx = X((Math.min(...f.map((n) => n.x - n.w / 2)) + Math.max(...f.map((n) => n.x + n.w / 2))) / 2);
    const fy = Y((Math.min(...f.map((n) => n.y - n.h / 2)) + Math.max(...f.map((n) => n.y + n.h / 2))) / 2);
    const t = cue(b, ...words(s.focus.word));
    tl.to(wrap, { x: W / 2 - fx * k, y: H / 2 - fy * k, scale: k, transformOrigin: "0 0", duration: 0.9, ease: CAM }, t - 0.3);
    const keep = new Set(s.focus.nodes);
    const dim = Object.entries(parts).filter(([key]) => !keep.has(key) && !key.split(/[>:]/).every((p) => keep.has(p) || p === "label"));
    tl.to(dim.map(([, n]) => n), { opacity: 0.2, duration: 0.5, ease: EXIT }, t - 0.3);
    if (h) tl.to(h.parentNode, { opacity: 0, duration: 0.4, ease: EXIT }, t - 0.3);
  }
}

// layers: a stack of flat layers seen in 3D (a system's tiers, a road's courses), for a real depth idea only.
// The layers drop into place on their words, separate on spread so each reads, and focus lifts one while the rest dim.
// scene: {eyebrow, title, layers: [{text, sub?, color?, word}] (top first, 5 at most), spread?: word, focus?: {index, word}}
//   spread: the layers land flat and separate on this word, which must follow the last layer word
// CSS 3D, not WebGL: opacity on a preserve-3d node flattens it, so planes appear by visibility and dim by their fill.
const LAYER = { w: 760, h: 420, gap: 220, drop: 260, tilt: "rotateX(58deg) rotateZ(-36deg)", untilt: "rotateZ(36deg) rotateX(-58deg)" };
function sceneLayers(root, b) {
  const s = b.scene;
  head(root, s.eyebrow, s.title);
  const n = s.layers.length;
  // the fit (index.html) sees only this 2D box, so size it to the projected stack: each step up in z rises about
  // sin(58 deg) = 0.85 of the gap on screen, and the tilted plane is about 0.6 of its height tall
  const rise = (n - 1) * LAYER.gap * 0.85;
  const box = el("div", "abs", root, { left: "360px", top: "220px", width: "1200px", height: rise + LAYER.h * 0.6 + 320 + "px", perspective: "2600px" });
  const stack = el("div", "abs", box, { left: "220px", top: rise + 40 + "px", width: LAYER.w + "px", height: LAYER.h + "px", transformStyle: "preserve-3d", transform: LAYER.tilt });
  const lands = [];
  const planes = s.layers.map((l, i) => {
    const p = el("div", "abs", stack, { left: 0, top: 0, width: LAYER.w + "px", height: LAYER.h + "px", transformStyle: "preserve-3d" });
    const fill = el("div", "abs", p, { inset: 0, background: col(l.color || "accent"), border: `3px solid ${C.ink}`, borderRadius: "var(--radius)" });
    // the label stands upright at the layer's front corner (it undoes the stack's tilt), so it reads like flat type
    const tag = el("div", "abs", p, { left: LAYER.w - 40 + "px", top: LAYER.h - 40 + "px", transform: LAYER.untilt, transformOrigin: "0 0", whiteSpace: "nowrap" });
    el("div", "t-h2", tag, { color: C.ink, background: C.bg, padding: "4px 16px", borderRadius: "8px" }, l.text);
    if (l.sub) el("div", "t-label mute", tag, { padding: "4px 16px" }, l.sub);
    const t = cue(b, ...words(l.word));
    const rest = s.spread ? 0 : (n - 1 - i) * LAYER.gap;
    lands.push(t);
    tl.set(p, { visibility: "hidden", z: rest + LAYER.drop }, 0);
    tl.set(p, { visibility: "visible" }, t);
    tl.to(p, { z: rest, duration: 0.5, ease: ENTER }, t);
    return { p, fill, tag };
  });
  // spread: layers rise to their own heights, the top layer highest. Without spread they land already apart.
  if (s.spread) {
    const ts = cue(b, ...words(s.spread));
    if (ts < Math.max(...lands)) throw new Error(`beat ${b.id}: layers spread must come after the last layer word`);
    planes.forEach((q, i) => tl.to(q.p, { z: (n - 1 - i) * LAYER.gap, duration: 0.9, ease: MOVE }, ts + i * 0.06));
  }
  if (s.focus) {
    const tf = cue(b, ...words(s.focus.word));
    if (tf < Math.max(...lands)) throw new Error(`beat ${b.id}: layers focus must come after the last layer word`);
    planes.forEach((q, i) =>
      i === s.focus.index
        ? tl.to(q.p, { z: (n - 1 - i) * LAYER.gap + LAYER.gap * 0.5, duration: 0.6, ease: MOVE }, tf)
        : tl.to([q.fill, q.tag], { opacity: 0.25, duration: 0.5 }, tf),
    );
  }
}

Object.assign(window.SCENES, { statement: sceneStatement, compare: sceneCompare, diagram: sceneDiagram, layers: sceneLayers });
