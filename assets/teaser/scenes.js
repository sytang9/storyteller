// Generic motion scene TYPES. Each is fn(root, beat): it reads beat.scene (data from beats.timed.json),
// builds DOM in root and adds tweens to the shared tl. Nothing report-specific lives here.
// Helpers from index.html: el, svgEl, tl, C, col, cue, wordAt, popIn, head.
// The assembly centres each scene's content vertically, so tops here only set the internal layout.

// ---- shared card row: used by retype and merge so the cards sit in the same place in both ----
const CARD_W = 400;
const CARD_H = 440;
const CARD_GAP = 100;
const CARD_TOP = 232;
const ROW_RIGHT = 1920 - 100;
const cardX = (i, n) => ROW_RIGHT - (n - i) * CARD_W - (n - 1 - i) * CARD_GAP;
const BAR_W = [0.85, 0.6, 0.75, 0.5];

function toolCards(parent, items, tag) {
  return items.map((t, i) => {
    const card = el("div", "abs card", parent, { left: cardX(i, items.length) + "px", top: CARD_TOP + "px", width: CARD_W + "px", height: CARD_H + "px" });
    el("div", "abs", card, { left: 0, top: 0, width: "100%", height: "12px", background: col(t.color) });
    el("div", "abs t-h2", card, { left: "32px", top: "40px", width: CARD_W - 64 + "px" }, t.name);
    const bars = BAR_W.map((w, k) => el("span", "abs bar", card, { left: "32px", top: 200 + k * 40 + "px", width: (CARD_W - 64) * w + "px" }));
    const chip = tag ? el("div", "abs chip-tag", card, { left: "32px", bottom: "32px", background: C.orange }, tag) : null;
    return { card, bars, tag: chip };
  });
}

// retype: one source document is copied by hand into each target tool in turn.
// scene: {eyebrow, title, source: {title, sub, word}, targets: [{name, color, word}], tag}
const PAPER = { w: 210, h: 280 };
function paperSheet(parent, src, x, y) {
  const p = el("div", "abs", parent, { left: x + "px", top: y + "px", width: PAPER.w + "px", height: PAPER.h + "px", background: "#ffffff", border: `3px solid ${C.ink}`, borderRadius: "8px", transformOrigin: "50% 50%" });
  el("div", "abs t-h2", p, { left: "24px", top: "24px" }, src.title);
  el("div", "abs t-label mute", p, { left: "24px", top: "88px" }, src.sub);
  [0.8, 0.6, 0.7, 0.5].forEach((w, k) => el("span", "abs bar", p, { left: "24px", top: 144 + k * 32 + "px", width: 160 * w + "px", height: "12px" }));
  return p;
}
function sceneRetype(root, b) {
  const s = b.scene;
  head(root, s.eyebrow, s.title);
  const n = s.targets.length;
  const px = cardX(0, n) - 110 - PAPER.w;
  const py = CARD_TOP + CARD_H / 2 - PAPER.h / 2;
  const paper = paperSheet(root, s.source, px, py);
  const tools = toolCards(root, s.targets, s.tag);
  tools.forEach((t) => {
    if (t.tag) tl.set(t.tag, { opacity: 0 }, 0);
    t.bars.forEach((bar) => tl.set(bar, { scaleX: 0 }, 0));
  });
  tools.forEach((t, i) => popIn(t.card, b.start + 0.15 + i * 0.1));
  popIn(paper, cue(b, s.source.word), { opacity: 0, y: 0, scale: 0.7 });
  // a copy of the source flies into each target in turn and lands on that target's word
  const FLY = 0.55;
  s.targets.forEach((target, i) => {
    const at = cue(b, target.word);
    const copy = paperSheet(root, s.source, px, py);
    copy.setAttribute("data-layout-allow-overlap", ""); // flies over the cards on purpose
    const dx = cardX(i, n) + CARD_W / 2 - (px + PAPER.w / 2);
    tl.set(copy, { opacity: 0 }, 0);
    tl.set(copy, { opacity: 1, x: 0, y: 0, scale: 1 }, at - FLY);
    tl.to(copy, { x: dx, duration: FLY, ease: "power2.inOut" }, at - FLY);
    tl.to(copy, { y: -120, duration: FLY / 2, ease: "power2.out", yoyo: true, repeat: 1 }, at - FLY);
    tl.to(copy, { scale: 0.35, duration: FLY, ease: "power2.in" }, at - FLY);
    tl.to(copy, { opacity: 0, duration: 0.15, ease: "power1.in" }, at - 0.1);
    const t = tools[i];
    tl.fromTo(t.card, { borderColor: C.line }, { borderColor: C.orange, duration: 0.15, yoyo: true, repeat: 1, immediateRender: false }, at);
    t.bars.forEach((bar, k) =>
      tl.fromTo(bar, { scaleX: 0, backgroundColor: C.line }, { scaleX: 1, backgroundColor: "#9aa5b6", duration: 0.2, ease: "none", immediateRender: false }, at + k * 0.1),
    );
    if (t.tag) popIn(t.tag, at - 0.05, { opacity: 0, y: 0, scale: 0.6 });
  });
}

// merge: the cards from a retype scene stack in depth and become one card with ordered steps.
// scene: {eyebrow, title?, from: [{name, color}], into, word, landWord, steps: [..], tick: [fromWord, toWord]}
// Depth move ported from catalog block camera-rig-depth-stack (perspective, rotateY/X, translateZ).
function sceneMerge(root, b) {
  const s = b.scene;
  head(root, s.eyebrow, s.title);
  root.style.perspective = "1800px";
  const tools = toolCards(root, s.from, null);
  const n = tools.length;
  const merge = cue(b, s.word);
  const land = cue(b, s.landWord);
  tools.forEach((t, i) => {
    [t.card, ...t.card.querySelectorAll("*")].forEach((m) => m.setAttribute("data-layout-allow-overlap", "")); // they stack into one deck on purpose
    const dx = 960 - CARD_W / 2 - cardX(i, n);
    const depth = n - 1 - i; // the first tool ends at the back
    tl.fromTo(t.card, { x: 0, y: 0, z: 0, rotationY: 0, rotationX: 0 },
      { x: dx + depth * 36, y: -depth * 28, z: -depth * 160, rotationY: -24, rotationX: 8, duration: 0.7, ease: "power3.inOut", immediateRender: false }, merge + i * 0.06);
    tl.to(t.card, { x: dx, y: 0, z: 0, rotationY: 0, rotationX: 0, scale: 0.9, duration: 0.4, ease: "power2.in" }, land - 0.45);
    tl.to(t.card, { opacity: 0, duration: 0.2, ease: "power1.in" }, land - 0.1);
  });
  const JOB_W = 1640;
  const JOB_H = 480;
  const job = el("div", "abs card", root, { left: (1920 - JOB_W) / 2 + "px", top: CARD_TOP + CARD_H - JOB_H + "px", width: JOB_W + "px", height: JOB_H + "px", borderWidth: "3px" });
  el("div", "abs", job, { left: 0, top: 0, width: "100%", height: "12px", background: C.blue });
  el("div", "abs t-h1", job, { left: "64px", top: "56px" }, s.into);
  const k = s.steps.length;
  const x0 = 150;
  const dx = (JOB_W - 2 * x0) / (k - 1);
  const RAIL_Y = 296;
  el("span", "abs", job, { left: x0 + "px", top: RAIL_Y + "px", width: dx * (k - 1) + "px", height: "6px", background: C.line, display: "block" });
  const fill = el("span", "abs", job, { left: x0 + "px", top: RAIL_Y + "px", width: dx * (k - 1) + "px", height: "6px", background: C.good, display: "block", transformOrigin: "0% 50%" });
  const nodes = s.steps.map((name, i) => {
    const g = el("div", "abs", job, { left: x0 + i * dx - 112 + "px", top: RAIL_Y - 40 + "px", width: "224px", display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" });
    const dot = el("div", "t-h2", g, { position: "relative", width: "88px", height: "88px", borderRadius: "50%", background: C.blue, color: "#ffffff" });
    const num = el("div", "abs", dot, { inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }, String(i + 1));
    const tick = svgEl("svg", dot, { viewBox: "0 0 24 24", style: "position:absolute;left:22px;top:22px;width:44px;height:44px" });
    svgEl("path", tick, { d: "M5 12.5 L9.5 17 L19 7.5", fill: "none", stroke: "#ffffff", "stroke-width": 3.4, "stroke-linecap": "round", "stroke-linejoin": "round" });
    el("div", "t-body", g, { whiteSpace: "nowrap" }, name);
    return { g, dot, num, tick };
  });
  tl.set(nodes.map((q) => q.g), { opacity: 0 }, 0);
  tl.set(nodes.map((q) => q.tick), { opacity: 0 }, 0);
  tl.set(fill, { scaleX: 0 }, 0);
  popIn(job, land - 0.15, { opacity: 0, y: 0, scale: 0.92 });
  nodes.forEach((q, i) => popIn(q.g, land + 0.1 + i * 0.08, { opacity: 0, y: 16, scale: 0.8 }));
  const t0 = cue(b, s.tick[0]);
  const t1 = cue(b, s.tick[1]);
  const gap = (t1 - t0) / (k - 1);
  tl.fromTo(fill, { scaleX: 0 }, { scaleX: 1, duration: t1 - t0, ease: "none", immediateRender: false }, t0);
  nodes.forEach((q, i) => {
    const at = t0 + i * gap;
    tl.to(q.dot, { backgroundColor: C.good, duration: 0.2 }, at);
    tl.to(q.num, { opacity: 0, duration: 0.15 }, at);
    tl.fromTo(q.tick, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)", immediateRender: false }, at);
  });
  tl.to(job, { borderColor: C.good, duration: 0.3 }, t1);
}

// lanes: a token walks a swimlane journey; a counter counts hand-offs and lands on counter.word.
// scene: {eyebrow, title, lanes: [{id, name, color, word: [token, nth]}], steps: [{id, name, w}],
//         stops: [[stepId, laneId]], doneStep, counter: {label, word}}   (lanes/steps/stops may come from scene.data)
function sceneLanes(root, b) {
  const s = b.scene;
  const LANES = s.lanes;
  const STEPS = s.steps;
  const STOPS = s.stops;
  const LANE_TOP = 248, LANE_H = 128, COL_X0 = 440, TOKEN_R = 32, DOT_R = 10, TICK_H = 144;
  const LANE_BASE = 0.06, LANE_ACTIVE = 0.16, MOVE = 0.28;
  head(root, s.eyebrow, s.title);
  const handoffs = STOPS.filter((st, i) => i > 0 && st[1] !== STOPS[i - 1][1]).length;
  const counter = el("div", "abs counter", root);
  el("div", "t-eyebrow", counter, {}, s.counter.label);
  const ticker = el("div", "ticker", counter);
  const stack = el("div", "", ticker, { display: "flex", flexDirection: "column" });
  stack.setAttribute("data-layout-allow-overflow", "");
  const of = el("div", "counter-of t-h2 mute", counter, {}, `of ${handoffs}`);
  for (let n = 0; n <= handoffs; n++) el("div", "tick t-num", stack, {}, String(n)).setAttribute("data-layout-allow-overflow", "");

  const laneIdx = Object.fromEntries(LANES.map((l, i) => [l.id, i]));
  const laneY = (id) => LANE_TOP + laneIdx[id] * LANE_H + LANE_H / 2;
  const colStart = [];
  STEPS.reduce((x, st) => (colStart.push(x), x + st.w), COL_X0);
  const stepIdx = Object.fromEntries(STEPS.map((st, i) => [st.id, i]));
  const pts = STOPS.map(([step], i) => {
    const same = STOPS.filter((q) => q[0] === step);
    const k = STOPS.slice(0, i).filter((q) => q[0] === step).length;
    const c = stepIdx[step];
    return { x: colStart[c] + ((k + 0.5) * STEPS[c].w) / same.length, y: laneY(STOPS[i][1]) };
  });
  const bottom = LANE_TOP + LANES.length * LANE_H;
  const laneBgs = LANES.map((l, i) => el("div", "abs lane-bg", root, { top: LANE_TOP + i * LANE_H + "px", background: col(l.color), opacity: LANE_BASE }));
  LANES.concat([null]).forEach((_, i) => el("div", "abs lane-rule", root, { top: LANE_TOP + i * LANE_H - 1 + "px" }));
  const laneNames = LANES.map((l, i) => {
    const n = el("div", "abs lane-name t-body", root, { top: LANE_TOP + i * LANE_H + "px", color: col(l.color), fontWeight: 700 });
    el("span", "lane-dot", n, { background: col(l.color) });
    el("span", "", n, {}, l.name);
    return n;
  });
  colStart.forEach((x) => el("div", "abs col-sep", root, { left: x - 1 + "px", top: LANE_TOP + "px", height: bottom - LANE_TOP + "px" }));
  const stepLabels = STEPS.map((st, i) => el("div", "abs step-label t-label", root, { left: colStart[i] + "px", top: bottom + 24 + "px", width: st.w + "px" }, st.name));
  const stepBars = STEPS.map((st, i) => el("div", "abs step-bar", root, { left: colStart[i] + 16 + "px", top: bottom + 72 + "px", width: st.w - 32 + "px" }));
  const svg = svgEl("svg", root, { class: "abs layer trail", viewBox: "0 0 1920 900" });
  const segs = pts.slice(1).map((p, i) => svgEl("path", svg, { d: `M ${pts[i].x} ${pts[i].y} L ${p.x} ${p.y}` }));
  const dots = pts.map((p, i) => el("div", "abs stop-dot", root, { left: p.x - DOT_R + "px", top: p.y - DOT_R + "px", background: col(LANES[laneIdx[STOPS[i][1]]].color) }));
  const token = el("div", "abs token", root);
  const core = el("div", "token-core", token);

  // the walk fills the beat and the last hand-off lands on counter.word
  const t0 = b.vstart + 0.5;
  const tEnd = cue(b, s.counter.word);
  const step = (tEnd - MOVE - t0) / (STOPS.length - 1);
  const stopTime = (i) => t0 + i * step;

  laneNames.forEach((n, i) => {
    tl.fromTo(laneBgs[i], { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power2.inOut" }, b.start + 0.05 * i);
    popIn(n, b.start + 0.1 + i * 0.06, { opacity: 0, x: -30 });
    if (LANES[i].word) tl.fromTo(n, { scale: 1 }, { scale: 1.12, duration: 0.2, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }, cue(b, ...LANES[i].word));
  });
  stepBars.forEach((bar) => tl.set(bar, { scaleX: 0 }, 0));
  dots.forEach((d) => tl.set(d, { scale: 0 }, 0));
  segs.forEach((sg) => {
    const len = sg.getTotalLength();
    sg.style.strokeDasharray = `${len}`;
    sg.style.strokeDashoffset = `${len}`;
  });
  const springs = [];
  const applyTicker = () => {
    stack.style.transform = `translateY(${-springs.reduce((a, q) => a + q.p, 0) * TICK_H}px)`;
  };
  tl.fromTo(token, { x: pts[0].x - TOKEN_R, y: pts[0].y - TOKEN_R, scale: 0 }, { scale: 1, duration: 0.4, ease: "power3.out" }, t0 - 0.3);
  tl.to(laneBgs[laneIdx[STOPS[0][1]]], { opacity: LANE_ACTIVE, duration: 0.3 }, t0);
  let activeStep = -1;
  STOPS.forEach(([stepId, role], i) => {
    const t = stopTime(i);
    const arrive = i === 0 ? t : t + MOVE;
    if (i > 0) {
      const p = pts[i];
      const q = pts[i - 1];
      tl.fromTo(token, { x: q.x - TOKEN_R, y: q.y - TOKEN_R }, { x: p.x - TOKEN_R, y: p.y - TOKEN_R, duration: MOVE, ease: "power2.inOut", immediateRender: false }, t);
      tl.to(core, { backgroundColor: col(LANES[laneIdx[role]].color), duration: 0.15 }, t + MOVE - 0.1);
      tl.to(segs[i - 1], { strokeDashoffset: 0, duration: MOVE, ease: "power2.inOut" }, t);
      const prev = STOPS[i - 1][1];
      if (prev !== role) {
        tl.to(laneBgs[laneIdx[prev]], { opacity: LANE_BASE, duration: 0.2 }, t + 0.1);
        tl.to(laneBgs[laneIdx[role]], { opacity: LANE_ACTIVE, duration: 0.2 }, t + 0.1);
        const sp = { p: 0 };
        springs.push(sp);
        tl.to(sp, { p: 1, duration: 0.35, ease: "back.out(1.8)", onUpdate: applyTicker }, arrive - 0.1);
      }
    }
    tl.fromTo(dots[i], { scale: 0 }, { scale: 1, duration: 0.2, ease: "power3.out", immediateRender: false }, arrive);
    const si = stepIdx[stepId];
    if (si !== activeStep) {
      if (activeStep >= 0) tl.to(stepBars[activeStep], { scaleX: 0, duration: 0.2, ease: "power2.in" }, t);
      const done = stepId === s.doneStep;
      tl.to(stepLabels[si], { color: done ? C.good : C.ink, duration: 0.2 }, arrive - 0.1);
      tl.fromTo(stepBars[si], { scaleX: 0, backgroundColor: done ? C.good : C.ink }, { scaleX: 1, duration: 0.3, ease: "power3.out", immediateRender: false }, arrive - 0.1);
      activeStep = si;
    }
  });
  tl.to([stack, of], { color: C.good, duration: 0.3 }, tEnd);
  applyTicker();
}

// counters: big numbers count up and land on their spoken words.
// scene: {eyebrow, title, items: [{value, label, word, color, of?, ofWord?, chip?: {text, word}}]}
// count-up motion ported from catalog block count-up: one text row per frame, sine.inOut, landing pulse.
function countUp(node, from, to, landAt, dur) {
  const frames = Math.max(1, Math.round(dur * D.fps));
  const ease = gsap.parseEase("sine.inOut");
  for (let f = 0; f <= frames; f++) {
    tl.set(node, { textContent: String(Math.round(from + (to - from) * ease(f / frames))) }, landAt - dur + (dur * f) / frames);
  }
  tl.to(node, { scale: 1.07, duration: 0.15, ease: "power3.out" }, landAt);
  tl.to(node, { scale: 1, duration: 0.15, ease: "power2.out" }, landAt + 0.15);
}
function sceneCounters(root, b) {
  const s = b.scene;
  head(root, s.eyebrow, s.title);
  const row = el("div", "abs", root, { left: 0, top: "264px", width: "1920px", display: "flex", justifyContent: "center", alignItems: "flex-start", gap: "144px" });
  s.items.forEach((it) => {
    const c = el("div", "", row, { display: "flex", flexDirection: "column", alignItems: "center" });
    const line = el("div", "t-display", c, { color: col(it.color), whiteSpace: "nowrap" });
    const num = el("span", "", line, { display: "inline-block", minWidth: String(it.value).length * 0.62 + "em", textAlign: "center" }, "0");
    el("div", "t-body mute", c, { marginTop: "16px" }, it.label);
    const land = wordAt(b, it.word);
    const dur = Math.min(1.1, land - b.start - 0.2);
    tl.set(c, { opacity: 0 }, 0);
    popIn(c, land - dur - 0.35);
    countUp(num, 0, it.value, land, dur);
    if (it.of !== undefined) {
      const of = el("span", "", line, { fontSize: "0.5em" }, ` / ${it.of}`);
      tl.set(of, { opacity: 0 }, 0);
      tl.to(of, { opacity: 1, duration: 0.3 }, cue(b, it.ofWord));
    }
    if (it.chip) {
      const chip = el("div", "chip-tag", c, { marginTop: "24px", background: C.good }, it.chip.text);
      tl.set(chip, { opacity: 0 }, 0);
      popIn(chip, cue(b, it.chip.word), { opacity: 0, y: 0, scale: 0.6 });
    }
  });
}

// chips: a grid of short labelled cards, each later tagged.
// scene: {eyebrow, title ("{n}" = item count, in accent), items: [..], tag, cols, in: [fromWord, toWord], tagIn: [fromWord, toWord]}
function sceneChips(root, b) {
  const s = b.scene;
  const [pre, post] = s.title.split("{n}");
  const h = head(root, s.eyebrow, "");
  h.textContent = "";
  el("span", "", h, {}, pre);
  if (post !== undefined) {
    el("span", "", h, { color: C.blue }, String(s.items.length));
    h.appendChild(document.createTextNode(post));
  }
  const COLS = s.cols || 4, W = 408, H = 176, G = 24;
  const left = (1920 - (COLS * W + (COLS - 1) * G)) / 2;
  const chips = s.items.map((label, i) => {
    const c = el("div", "abs card", root, { left: left + (i % COLS) * (W + G) + "px", top: 216 + Math.floor(i / COLS) * (H + G) + "px", width: W + "px", height: H + "px", padding: "20px 24px", display: "flex", flexDirection: "column", justifyContent: "space-between" });
    const top = el("div", "", c, { display: "flex", gap: "16px", alignItems: "baseline" });
    el("div", "t-label tnum", top, { fontFamily: "var(--mono)", fontWeight: 700, color: C.blue, flex: "none" }, String(i + 1).padStart(2, "0"));
    el("div", "t-body", top, {}, label);
    const tag = s.tag ? el("div", "chip-tag", c, { alignSelf: "flex-start", background: C.good }, s.tag) : null;
    return { c, tag };
  });
  tl.set(chips.flatMap((k) => [k.c, k.tag].filter(Boolean)), { opacity: 0 }, 0);
  const spread = (list, [w0, w1], from) => {
    const a = cue(b, w0);
    const z = cue(b, w1);
    list.forEach((n, i) => popIn(n, a + ((z - a) * i) / Math.max(1, list.length - 1), from));
  };
  spread(chips.map((k) => k.c), s.in, { opacity: 0, y: 0, scale: 0.8 });
  if (s.tag) spread(chips.map((k) => k.tag), s.tagIn, { opacity: 0, y: 0, scale: 0.6 });
}

window.SCENES = { retype: sceneRetype, merge: sceneMerge, lanes: sceneLanes, counters: sceneCounters, chips: sceneChips };
