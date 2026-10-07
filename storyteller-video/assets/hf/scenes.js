// Generic motion scene TYPES. Each is fn(root, beat): it reads beat.scene (data from beats.timed.json),
// builds DOM in root and adds tweens to the shared tl. Nothing report-specific lives here.
// Helpers from index.html: el, svgEl, tl, C, col, cue, wordAt, head, hero, keyLabel, ENTER, EXIT, MOVE;
// from motion.js: reveal (entrances by role), popIn, FOLLOW.
// The assembly centres each scene's content vertically, so tops here only set the internal layout.

// ---- shared card row: used by retype and merge so the cards sit in the same place in both ----
const CARD_W = 400;
const CARD_H = 440;
const CARD_GAP = 100;
const CARD_TOP = 232;
const ROW_RIGHT = 1920 - 100;
const cardX = (i, n) => ROW_RIGHT - (n - i) * CARD_W - (n - 1 - i) * CARD_GAP;
const BAR_W = [0.85, 0.6, 0.75, 0.5];

function toolCards(parent, items, tag, small) {
  return items.map((t, i) => {
    const card = el("div", "abs card", parent, { left: cardX(i, items.length) + "px", top: CARD_TOP + "px", width: CARD_W + "px", height: CARD_H + "px" });
    el("div", "abs", card, { left: 0, top: 0, width: "100%", height: "12px", background: col(t.color) });
    el("div", "abs " + (small ? "t-body mute" : "t-h2"), card, { left: "32px", top: "40px", width: CARD_W - 64 + "px" }, t.name);
    // sub: a small plain-purpose line under the name, for names a newcomer cannot decode
    if (t.sub) el("div", "abs t-label mute", card, { left: "32px", top: (small ? 84 : 104) + "px", width: CARD_W - 64 + "px" }, t.sub);
    const bars = BAR_W.map((w, k) => el("span", "abs bar", card, { left: "32px", top: 200 + k * 40 + "px", width: (CARD_W - 64) * w + "px" }));
    const chip = tag ? el("div", "abs chip-tag", card, { left: "32px", bottom: "32px", background: C.orange }, tag) : null;
    return { card, bars, tag: chip };
  });
}

// retype: one source document is copied by hand into each target tool in turn.
// scene: {eyebrow, title, source: {title, sub, word}, targets: [{name, sub?, color, word}], tag?, small?, toolsWord?}
//   small: tool names in body size; toolsWord: the cards enter on this word (default: the scene start)
//   hero: the tool cards live in the hero's layer, so a following merge with the same hero folds these same cards
const PAPER = { w: 210, h: 280 };
function paperSheet(parent, src, x, y) {
  const p = el("div", "abs", parent, { left: x + "px", top: y + "px", width: PAPER.w + "px", height: PAPER.h + "px", background: C.surface, border: `3px solid ${C.ink}`, borderRadius: "8px", transformOrigin: "50% 50%" });
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
  const tools = toolCards(s.hero ? heroGroup(b) : root, s.targets, s.tag, s.small);
  if (s.hero) heroProps(b).tools = tools;
  tools.forEach((t) => {
    if (t.tag) tl.set(t.tag, { opacity: 0 }, 0);
    t.bars.forEach((bar) => tl.set(bar, { scaleX: 0 }, 0));
  });
  const toolsAt = s.toolsWord ? cue(b, s.toolsWord) : b.start + 0.15;
  tools.forEach((t, i) => reveal(t.card, toolsAt + i * 0.1, "card", { from: "top" })); // grows down from its colour bar
  popIn(paper, cue(b, s.source.word), { opacity: 0, y: 0, scale: 0.7 });
  // a copy of the source flies into each target in turn and lands on that target's word
  // one copy in the air at a time: a flight never starts before the previous one lands
  const lands = s.targets.map((target) => cue(b, target.word));
  s.targets.forEach((target, i) => {
    const at = lands[i];
    const FLY = Math.min(0.55, i ? at - lands[i - 1] - 0.02 : 0.55);
    const copy = paperSheet(s.hero ? heroGroup(b) : root, s.source, px, py); // above the cards it flies into
    [copy, ...copy.querySelectorAll("*")].forEach((m) => m.setAttribute("data-layout-allow-overlap", "")); // flies over the cards on purpose
    const dx = cardX(i, n) + CARD_W / 2 - (px + PAPER.w / 2);
    tl.set(copy, { opacity: 0 }, 0);
    tl.set(copy, { opacity: 1, x: 0, y: 0, scale: 1 }, at - FLY);
    tl.to(copy, { x: dx, duration: FLY, ease: MOVE }, at - FLY);
    tl.to(copy, { y: -120, duration: FLY / 2, ease: "sine.out", yoyo: true, repeat: 1 }, at - FLY);
    tl.to(copy, { scale: 0.35, duration: FLY, ease: EXIT }, at - FLY);
    tl.to(copy, { opacity: 0, duration: 0.15, ease: EXIT }, at - 0.1);
    const t = tools[i];
    // the card fills in line by line: the retyping itself
    t.bars.forEach((bar, k) =>
      tl.fromTo(bar, { scaleX: 0, backgroundColor: C.line }, { scaleX: 1, backgroundColor: C.mute, duration: 0.2, ease: ENTER, immediateRender: false }, at + k * 0.1),
    );
    if (t.tag) reveal(t.tag, at - 0.05, "icon");
  });
}

// merge: the cards from a retype scene slide into one flat stack, and the stack opens out into one job card.
// scene: {eyebrow, title?, from: [{name, color}], into, sub?, word, landWord, small?, hero?, steps?, tick?: [w0, w1]}
//   hero: the job card is the shared hero element (see stepper and custom scenes that continue it)
//   steps + tick: the old one-beat form; the steps appear and tick inside this beat
const JOB = { x: 140, y: CARD_TOP, w: 1640, h: CARD_H };
function jobCard(card, s) {
  Object.assign(card.style, { left: JOB.x + "px", top: JOB.y + "px", width: JOB.w + "px", height: JOB.h + "px" });
  card.classList.add("card", "job");
  el("div", "abs", card, { left: 0, top: 0, width: "100%", height: "12px", background: C.blue });
  const title = el("div", "abs t-h1", card, { left: "64px", top: "56px", whiteSpace: "nowrap" }, s.into);
  const sub = s.sub ? el("div", "abs t-body mute", card, { left: "64px", top: "140px", whiteSpace: "nowrap" }, s.sub) : null;
  return [title, sub].filter(Boolean);
}
function sceneMerge(root, b) {
  const s = b.scene;
  head(root, s.eyebrow, s.title);
  const tools = (s.hero && heroProps(b).tools) || toolCards(root, s.from, null, s.small);
  const n = tools.length;
  const merge = cue(b, s.word);
  const land = cue(b, s.landWord);
  const stackX = 960 - CARD_W / 2;
  tools.forEach((t, i) => {
    [t.card, ...t.card.querySelectorAll("*")].forEach((m) => m.setAttribute("data-layout-allow-overlap", "")); // they stack into one deck on purpose
    const off = (i - (n - 1) / 2) * 24;
    tl.fromTo(t.card, { x: 0, y: 0 }, { x: stackX - cardX(i, n) + off, y: off, duration: 0.7, ease: MOVE, immediateRender: false }, merge + i * 0.06);
  });
  // the stack becomes the job card in place, then the card opens to full width and lands on landWord
  const OPEN = 0.6;
  const swap = land - OPEN - 0.15;
  const job = s.hero ? hero(b) : el("div", "abs", root);
  job.setAttribute("data-layout-allow-overlap", "");
  const text = jobCard(job, s);
  tl.set(job, { opacity: 0 }, 0);
  tl.fromTo(job, { opacity: 0, left: stackX, width: CARD_W }, { opacity: 1, left: stackX, width: CARD_W, duration: 0.15, ease: ENTER, immediateRender: false }, swap);
  tools.forEach((t) => tl.to(t.card, { opacity: 0, duration: 0.15, ease: EXIT }, swap + 0.1));
  tl.to(job, { left: JOB.x, width: JOB.w, duration: OPEN, ease: MOVE }, swap + 0.15);
  text.forEach((n, i) => reveal(n, land - 0.2 + i * 0.12, "text"));
  if (s.steps && s.tick) addSteps(job, b, { ...s, show: s.show || s.landWord });
}

// stepper: the hero job card shows its ordered steps; they tick done from left to right.
// scene: {eyebrow, title, hero, steps: [..], show: word, tick: [fromWord, toWord]}
function sceneStepper(root, b) {
  const s = b.scene;
  head(root, s.eyebrow, s.title);
  addSteps(hero(b), b, s);
}
function addSteps(job, b, s) {
  const k = s.steps.length;
  const x0 = 150;
  const dx = (JOB.w - 2 * x0) / (k - 1);
  const RAIL_Y = 300;
  const track = el("span", "abs", job, { left: x0 + "px", top: RAIL_Y + "px", width: dx * (k - 1) + "px", height: "6px", background: C.line, display: "block" });
  const fill = el("span", "abs", job, { left: x0 + "px", top: RAIL_Y + "px", width: dx * (k - 1) + "px", height: "6px", background: C.good, display: "block", transformOrigin: "0% 50%" });
  const nodes = s.steps.map((name, i) => {
    const g = el("div", "abs", job, { left: x0 + i * dx - 112 + "px", top: RAIL_Y - 41 + "px", width: "224px", display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" });
    const dot = el("div", "t-h2", g, { position: "relative", width: "88px", height: "88px", borderRadius: "50%", background: C.blue, color: C.onAccent });
    const num = el("div", "abs", dot, { inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }, String(i + 1));
    const tick = svgEl("svg", dot, { viewBox: "0 0 24 24", style: "position:absolute;left:22px;top:22px;width:44px;height:44px" });
    svgEl("path", tick, { d: "M5 12.5 L9.5 17 L19 7.5", fill: "none", stroke: C.onAccent, "stroke-width": 3.4, "stroke-linecap": "round", "stroke-linejoin": "round" });
    const label = el("div", "t-body", g, { whiteSpace: "nowrap" }, name);
    return { g, dot, num, tick, label };
  });
  tl.set(nodes.map((q) => q.tick), { opacity: 0 }, 0);
  tl.set(fill, { scaleX: 0 }, 0);
  // a hero card may be on screen before this beat: the rail draws on and the steps arrive only on show
  const show = cue(b, s.show);
  reveal(track, show, "line");
  nodes.forEach((q, i) => {
    reveal(q.dot, show + i * 0.08, "icon");
    reveal(q.label, show + i * 0.08 + 0.12, "text");
  });
  const t0 = cue(b, s.tick[0]);
  const t1 = cue(b, s.tick[1]);
  const gap = (t1 - t0) / (k - 1);
  nodes.forEach((q, i) => {
    const at = t0 + i * gap;
    if (i) tl.to(fill, { scaleX: i / (k - 1), duration: Math.min(0.3, gap), ease: MOVE }, at - Math.min(0.3, gap));
    tl.to(q.dot, { backgroundColor: C.good, duration: 0.2, ease: ENTER }, at);
    tl.to(q.num, { opacity: 0, duration: 0.15, ease: EXIT }, at);
    tl.fromTo(q.tick, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.3, ease: ENTER, immediateRender: false }, at);
  });
  tl.to(job, { borderColor: C.good, duration: 0.3, ease: ENTER }, t1);
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
    reveal(n, b.start + 0.1 + i * 0.06, "text");
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
  tl.fromTo(token, { x: pts[0].x - TOKEN_R, y: pts[0].y - TOKEN_R, scale: 0 }, { x: pts[0].x - TOKEN_R, y: pts[0].y - TOKEN_R, scale: 1, duration: 0.4, ease: "power3.out" }, t0 - 0.3);
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
        tl.to(sp, { p: 1, duration: 0.35, ease: ENTER, onUpdate: applyTicker }, arrive - 0.1);
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
  // the row hugs its numbers (centred on x 960 below), so the fit frames the figures and not the whole width
  const row = el("div", "abs", root, { left: 0, top: "264px", display: "flex", alignItems: "flex-start", gap: "144px" });
  s.items.forEach((it) => {
    const c = el("div", "", row, { display: "flex", flexDirection: "column", alignItems: "center" });
    const line = el("div", "t-display", c, { color: col(it.color), whiteSpace: "nowrap" });
    const num = el("span", "", line, { display: "inline-block", minWidth: String(it.value).length * 0.62 + "em", textAlign: "center" }, "0");
    const label = el("div", "t-body mute", c, { marginTop: "16px" }, it.label);
    const land = wordAt(b, it.word);
    const dur = Math.min(1.1, land - b.start - 0.2);
    // the figure slides up out of its slot, its label follows with overlap
    const t0 = land - dur - 0.35;
    reveal(line, t0, "number");
    reveal(label, t0 + 0.8 * (1 - FOLLOW), "text");
    countUp(num, 0, it.value, land, dur);
    if (it.of !== undefined) {
      const of = el("span", "", line, { fontSize: "0.5em" }, ` / ${it.of}`);
      tl.set(of, { opacity: 0 }, 0);
      tl.to(of, { opacity: 1, duration: 0.3 }, cue(b, it.ofWord));
    }
    if (it.chip) {
      const chip = el("div", "chip-tag", c, { marginTop: "24px", background: C.good }, it.chip.text);
      tl.set(chip, { opacity: 0 }, 0);
      reveal(chip, cue(b, it.chip.word), "icon");
    }
  });
  row.style.left = (1920 - row.offsetWidth) / 2 + "px";
}

// chips: a grid of short labelled cards, each later tagged; or, with focus, a few full cards above dim chips.
// scene: {eyebrow, title ("{n}" = item count, in accent), items: [text | {text, detail}], cols, in: [fromWord, toWord],
//         tag?, tagIn?: [fromWord, toWord], numbered?: false,
//         focus?: [item indices], restIn?: word, detailIn?: [fromWord, toWord]}
//   focus: those items show in full (text + detail) in one row; the rest sit below as dim chips that enter as one group
//   a focus item may carry word (it enters on that word, in focus order) and steps (a step echo, see stepEcho)
//   restText: false draws the dim chips as wordless bars
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
  const items = s.items.map((it) => (typeof it === "string" ? { text: it } : it));
  // role: a reveal role ("card", "icon", ...) or a popIn from-state
  const spread = (list, [w0, w1], role) => {
    const a = cue(b, w0);
    const z = cue(b, w1);
    const at = (i) => a + ((z - a) * i) / Math.max(1, list.length - 1);
    list.forEach((n, i) => (typeof role === "string" ? reveal(n, at(i), role) : popIn(n, at(i), role)));
  };
  root.dataset.fit = "fill"; // the assembly scales the grid to fill the free area (FILL_W of its width)
  if (s.focus) return chipsFocus(root, b, s, items, spread);
  const W = 408, H = 176, G = 24;
  // cols is an upper bound: take the column count whose grid fills the free area at the largest scale
  const fillScale = (c) => {
    const r = Math.ceil(items.length / c);
    return Math.min(FILL_MAX, (FILL_W * FREE.w) / (c * W + (c - 1) * G), FREE.h / (r * H + (r - 1) * G));
  };
  let COLS = 1;
  for (let c = 2; c <= Math.min(s.cols || 4, items.length); c++) if (fillScale(c) > fillScale(COLS)) COLS = c;
  const left = (1920 - (COLS * W + (COLS - 1) * G)) / 2;
  const chips = items.map((it, i) => {
    const c = el("div", "abs card", root, { left: left + (i % COLS) * (W + G) + "px", top: 216 + Math.floor(i / COLS) * (H + G) + "px", width: W + "px", height: H + "px", padding: "20px 24px", display: "flex", flexDirection: "column", justifyContent: "space-between" });
    const top = el("div", "", c, { display: "flex", gap: "16px", alignItems: "baseline" });
    if (s.numbered) el("div", "t-label tnum", top, { fontFamily: "var(--mono)", fontWeight: 700, color: C.blue, flex: "none" }, String(i + 1).padStart(2, "0"));
    el("div", "t-body", top, {}, it.text);
    const tag = s.tag ? el("div", "chip-tag", c, { alignSelf: "flex-start", background: C.good }, s.tag) : null;
    return { c, tag };
  });
  tl.set(chips.flatMap((k) => [k.c, k.tag].filter(Boolean)), { opacity: 0 }, 0);
  spread(chips.map((k) => k.c), s.in, "card");
  if (s.tag) spread(chips.map((k) => k.tag), s.tagIn, "icon");
}
function chipsFocus(root, b, s, items, spread) {
  const FH = 360, FG = 40, RH = 72, RG = 24, MAX_W = 560;
  const rest = items.filter((_, k) => !s.focus.includes(k));
  const COLS = Math.max(1, Math.min(3, rest.length)); // the dim chips below
  const cols = Math.max(s.focus.length, COLS);
  // columns narrow enough that the widest row spans FILL_W of the free width at scale >= 1 (text stays >= 32 px)
  const FW = Math.min(MAX_W, Math.floor((FILL_W * FREE.w - (cols - 1) * FG) / cols));
  const rowX = (n) => (1920 - (n * FW + (n - 1) * FG)) / 2; // each row is centred on its own
  const fx = rowX(s.focus.length);
  const rx = rowX(COLS);
  const focus = s.focus.map((k, i) => {
    const it = items[k];
    const c = el("div", "abs card", root, { left: fx + i * (FW + FG) + "px", top: "224px", width: FW + "px", height: FH + "px", borderWidth: "3px", borderColor: C.ink });
    el("div", "abs t-h1", c, { left: "32px", top: "32px", width: FW - 64 + "px", textWrap: "balance" }, it.text);
    const d = it.detail ? el("div", "abs t-h2", c, { left: "32px", bottom: "28px", width: FW - 64 + "px", color: C.blue, fontWeight: 600, textWrap: "balance" }, it.detail) : null;
    if (it.steps) stepEcho(c, b, it.steps);
    return { c, d, word: it.word };
  });
  // the group is exactly as wide as its chips, so the fill measures the content and not the frame
  const group = el("div", "abs", root, { left: rx + "px", top: 224 + FH + 48 + "px", width: COLS * FW + (COLS - 1) * FG + "px", height: Math.max(0, Math.ceil(rest.length / COLS) * (RH + RG) - RG) + "px" });
  rest.forEach((it, i) =>
    s.restText === false
      ? blankChip(group, (i % COLS) * (FW + FG), Math.floor(i / COLS) * (RH + RG), FW, RH)
      : el("div", "abs dim-chip t-body", group, { left: (i % COLS) * (FW + FG) + "px", top: Math.floor(i / COLS) * (RH + RG) + "px", width: FW + "px", height: RH + "px" }, it.text),
  );
  tl.set(focus.flatMap((f) => [f.c, f.d].filter(Boolean)), { opacity: 0 }, 0);
  // focus cards enter on their own word when they name one, otherwise spread over s.in
  const timed = focus.filter((f) => f.word);
  timed.forEach((f) => reveal(f.c, cue(b, f.word), "card"));
  const untimed = focus.filter((f) => !f.word).map((f) => f.c);
  if (untimed.length) spread(untimed, s.in, "card");
  if (rest.length) reveal(group, cue(b, s.restIn), "text");
  if (s.detailIn) spread(focus.map((f) => f.d).filter(Boolean), s.detailIn, "text");
}
// a dim chip with no words (restText: false): it counts, but carries no jargon
function blankChip(parent, x, y, w, h) {
  const c = el("div", "abs dim-chip", parent, { left: x + "px", top: y + "px", width: w + "px", height: h + "px" });
  el("span", "bar", c, { width: w * 0.45 + "px", height: "12px" });
  return c;
}
// a small echo of the job's steps inside a card; steps from..to light up from word to toWord.
// steps: {count, from, to, word, toWord}
function stepEcho(card, b, st) {
  const D0 = 40, G = 20;
  const wrap = el("div", "abs", card, { left: "32px", bottom: "36px", width: st.count * D0 + (st.count - 1) * G + "px", height: D0 + 16 + "px" });
  const dots = Array.from({ length: st.count }, (_, i) =>
    el("div", "abs t-label", wrap, { left: i * (D0 + G) + "px", top: 0, width: D0 + "px", height: D0 + "px", borderRadius: "50%", border: `2px solid ${C.line}`, color: C.mute, display: "flex", alignItems: "center", justifyContent: "center" }, String(i + 1)),
  );
  const x0 = (st.from - 1) * (D0 + G);
  const bar = el("div", "abs", wrap, { left: x0 + "px", top: D0 + 10 + "px", width: (st.to - st.from) * (D0 + G) + D0 + "px", height: "4px", borderRadius: "2px", background: C.orange, transformOrigin: "0% 50%" });
  tl.set(bar, { scaleX: 0 }, 0);
  const a = cue(b, st.word);
  const z = cue(b, st.toWord);
  tl.to(bar, { scaleX: 1, duration: Math.max(0.3, z - a), ease: MOVE }, a);
  for (let i = st.from - 1; i < st.to; i++) {
    const t = a + ((z - a) * (i - st.from + 1)) / Math.max(1, st.to - st.from);
    tl.to(dots[i], { backgroundColor: C.orange, borderColor: C.orange, color: C.onAccent, duration: 0.2, ease: ENTER }, t);
  }
}

window.SCENES = { retype: sceneRetype, merge: sceneMerge, stepper: sceneStepper, lanes: sceneLanes, counters: sceneCounters, chips: sceneChips };
