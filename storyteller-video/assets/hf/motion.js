// Motion and framing: role-aware entrances, the fit, the arrow check and the morph match cut. Loaded after the helpers in
// index.html; every function adds to the shared tl when the assembly calls it.
// Helpers from index.html: el, tl, D, MOVE, EXIT, and the fit constants (FIT_*, FILL_*, FRAME_H, CONTENT_H, UI_MARGIN).

// Two arrival speeds and a camera curve, picked by distance and role (one look for everything reads as a template):
const ARRIVE = { duration: 0.7, ease: "expo.out" }; // text, numbers, cards: a long arrival that settles slowly
const SMALL = { duration: 0.4, ease: "power4.out" }; // tags, icons, dots, fades: short and quiet
const CAM = "power2.inOut"; // camera moves ease in and out, so the frame never jumps
const FOLLOW = 0.35; // a follower starts this share of its leader's duration before the leader lands

// every bundled face, loaded before any layout is measured. fonts.ready alone resolves at once when no text uses a
// face yet, and a fallback font is 10-30 px off: arrows, the fit and wrapped words were measured wrong.
const loadFonts = () =>
  Promise.all([...document.fonts].map((f) => f.load().catch(() => console.error(`font ${f.family} ${f.weight} failed to load`)))).then(() => document.fonts.ready);

const drawLine = (path, at, dur = 0.4) => {
  const len = path.getTotalLength();
  path.style.strokeDasharray = `${len}`;
  path.style.strokeDashoffset = `${len}`;
  tl.to(path, { strokeDashoffset: 0, duration: dur, ease: MOVE }, at);
};

// text mask: the node rises out of a slot the size of its own box. The clip moves with the node, so its inset runs
// in lockstep with yPercent (both linear in the same eased progress); 25% / 10% pads keep ascenders and underlines.
const MASK_FROM = "inset(-125% -6% 90% -6%)";
const MASK_TO = "inset(-25% -6% -10% -6%)";
function maskIn(n, at, m) {
  tl.set(n, { opacity: 0 }, 0);
  tl.fromTo(n, { opacity: 0 }, { opacity: 1, duration: 0.12, ease: "none", immediateRender: false }, at);
  tl.fromTo(n, { yPercent: 100, clipPath: MASK_FROM }, { yPercent: 0, clipPath: MASK_TO, ...m, immediateRender: false }, at);
  tl.set(n, { clipPath: "none" }, at + m.duration);
  return at + m.duration;
}

// card: the box grows out of its anchor edge (a clip, so its text never squashes) and its text follows with overlap
const CARD_CLIP = { left: "0% 100% 0% 0%", right: "0% 0% 0% 100%", top: "0% 0% 100% 0%", bottom: "100% 0% 0% 0%" };
const FOLLOW_FROM = { left: { x: -32 }, right: { x: 32 }, top: { y: -24 }, bottom: { y: 24 } };
function cardIn(n, at, o) {
  const edge = o.from || (n.offsetWidth > 1.6 * n.offsetHeight ? "left" : "bottom");
  const r = getComputedStyle(n).borderRadius || "0px";
  const m = { ...ARRIVE, ...(o.duration ? { duration: o.duration } : {}) };
  tl.set(n, { opacity: 0 }, 0);
  tl.set(n, { opacity: 1 }, at);
  tl.fromTo(n, { clipPath: `inset(${CARD_CLIP[edge]} round ${r})` }, { clipPath: `inset(0% 0% 0% 0% round ${r})`, ...m, immediateRender: false }, at);
  tl.set(n, { clipPath: "none" }, at + m.duration);
  // followers: direct children that carry text; tags and bars have their own entrances
  const kids = [...n.children].filter((c) => c.textContent.trim() && !c.matches(".chip-tag, .bar, svg"));
  kids.forEach((c) => tl.set(c, FOLLOW_FROM[edge], 0));
  kids.forEach((c, i) => tl.fromTo(c, FOLLOW_FROM[edge], { x: 0, y: 0, ...m, immediateRender: false }, at + m.duration * (1 - FOLLOW) + i * 0.06));
  return at + m.duration;
}

function lineIn(n, at, o) {
  if (n instanceof SVGGeometryElement) {
    tl.set(n, { opacity: 0 }, 0); // a zero-length dash with a round cap still draws a dot
    tl.set(n, { opacity: 1 }, at);
    drawLine(n, at, o.duration || 0.5);
    return at + (o.duration || 0.5);
  }
  const tall = n.offsetHeight > n.offsetWidth;
  const k = tall ? "scaleY" : "scaleX";
  tl.set(n, { [k]: 0, transformOrigin: tall ? "50% 0%" : "0% 50%" }, 0);
  tl.to(n, { [k]: 1, duration: o.duration || 0.6, ease: MOVE }, at);
  return at + (o.duration || 0.6);
}

function iconIn(n, at, o) {
  tl.set(n, { opacity: 0, scale: 0.6 }, 0);
  tl.fromTo(n, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, ...SMALL, ...(o.duration ? { duration: o.duration } : {}), immediateRender: false }, at);
  return at + SMALL.duration;
}

const REVEALS = {
  text: (n, at, o) => maskIn(n, at, { ...ARRIVE, ...(o.duration ? { duration: o.duration } : {}) }),
  number: (n, at, o) => maskIn(n, at, { duration: o.duration || 0.8, ease: "power4.out" }),
  card: cardIn,
  line: lineIn,
  icon: iconIn,
};
// a role from the node itself, for popIn callers that name none
function roleOf(n) {
  if (n instanceof SVGGeometryElement) return "line";
  if (n.matches(".card, .dim-chip")) return "card";
  if (n.offsetWidth <= 140 && n.offsetHeight <= 140) return "icon";
  return /^[\s\d.,%/+-]+$/.test(n.textContent) ? "number" : "text";
}
// reveal(node, at, role, opts): the entrance for what the node is. Returns the time it lands.
//   role: text | number | card | line | icon (default: guessed by roleOf); opts: {from: left|right|top|bottom, duration}
function reveal(n, at, role, o = {}) {
  const r = REVEALS[role || roleOf(n)];
  if (!r) throw new Error(`reveal: no role "${role}" (${Object.keys(REVEALS).join(", ")})`);
  return r(n, at, o);
}

// popIn(node, at, from?): the old entrance. Without `from` it is reveal() with a guessed role. With `from`, the node
// returns to the neutral value of each property named, and only those, so a CSS centring translate survives; the
// speed follows the distance.
const NEUTRAL = { opacity: 1, x: 0, y: 0, xPercent: 0, yPercent: 0, scale: 1, scaleX: 1, scaleY: 1, rotation: 0 };
function popIn(n, at, from) {
  if (!from) return reveal(n, at);
  const to = Object.fromEntries(Object.keys(from).filter((k) => k in NEUTRAL).map((k) => [k, NEUTRAL[k]]));
  const travel = Math.max(Math.abs(from.x || 0), Math.abs(from.y || 0), 100 * Math.abs(1 - (from.scale ?? 1)));
  const m = travel >= 24 ? ARRIVE : SMALL;
  tl.set(n, from, 0);
  tl.fromTo(n, from, { ...to, ...m, immediateRender: false }, at);
  return at + m.duration;
}

// measuring seeks the timeline at build time; rewind() leaves it as if never rendered. Without it, a fromTo that
// was reverted and is then jumped over in one seek (the renderer starts each chunk with one jump) loses the props
// that only its `from` names, such as a pushed-in scene's opacity.
function rewind() {
  tl.seek(0);
  tl.invalidate();
}

// ---- fit ----
// fit: a scene's body (everything but its heading) is scaled up and centred in the free area, so content fills the
// frame. Beats that share a hero share one fit, so the hero and its props line up across the cut.
function boxOf(nodes) {
  const box = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity };
  for (const n of nodes) {
    if (n.tagName.toLowerCase() === "svg" || !n.offsetHeight) continue;
    const w = n.offsetWidth;
    const x = n.offsetLeft + (n.classList.contains("key-label") ? (gsap.getProperty(n, "xPercent") / 100) * w : 0);
    box.x0 = Math.min(box.x0, x);
    box.y0 = Math.min(box.y0, n.offsetTop);
    box.x1 = Math.max(box.x1, x + w);
    box.y1 = Math.max(box.y1, n.offsetTop + n.offsetHeight);
  }
  return box;
}
// the fit as numbers {tx, ty, sc}: a scene px point p lands at tx + sc * p on the frame
function fitParams(box, mode) {
  if (!(box.x0 < box.x1)) return { tx: 0, ty: 0, sc: 1 };
  const isUi = mode === "ui" || mode === "ui-head";
  const top = mode === "ui" ? UI_MARGIN : FIT_TOP;
  const bottom = isUi ? CONTENT_H - UI_MARGIN : FIT_BOTTOM;
  const left = isUi ? UI_MARGIN : FIT_X;
  const bw = box.x1 - box.x0;
  const bh = box.y1 - box.y0;
  const aw = 1920 - 2 * left;
  // content already wider than the area keeps its size (it was laid out for the full width)
  const sw = bw <= aw ? aw / bw : Math.min(1, 1856 / bw);
  const grow = Math.min(FIT_HARD, Math.max(FIT_MAX, Math.min((FIT_FILL * aw) / bw, (FIT_FILL * (bottom - top)) / bh)));
  const sc = mode === "fill" ? Math.min(FILL_MAX, (FILL_W * aw) / bw, (bottom - top) / bh) : Math.min(grow, sw, (bottom - top) / bh);
  const tx = 960 - sc * (box.x0 + bw / 2);
  const ty = (top + bottom) / 2 - sc * (box.y0 + bh / 2);
  return { tx, ty, sc };
}
const fitCss = (f) => `translate(${f.tx.toFixed(1)}px, ${f.ty.toFixed(1)}px) scale(${f.sc.toFixed(4)})`;

// ---- the arrow check: an arrow tip must land within ARROW_TOL px of its target's box edge, in frame px ----
const ARROWS = [];
const ARROW_TOL = 12;
// svg: the arrow's svg; [x, y]: the tip in that svg's user units; target: a node or a function that returns one
const addArrow = (b, svg, x, y, target, at) => ARROWS.push({ b, svg, x, y, target, at });
function edgeDist(px, py, r) {
  const dx = Math.max(r.left - px, 0, px - r.right);
  const dy = Math.max(r.top - py, 0, py - r.bottom);
  if (dx || dy) return Math.hypot(dx, dy);
  return Math.min(px - r.left, r.right - px, py - r.top, r.bottom - py); // inside: the distance to the nearest edge
}
// seeks each arrow's landing time and measures the drawn frame; logs a console error per miss. Returns the list.
function checkArrows() {
  const out = ARROWS.map((a) => {
    tl.seek(a.at);
    const s = a.svg.getBoundingClientRect();
    const k = s.width / a.svg.width.baseVal.value; // the svg's user units to frame px (no rotation anywhere)
    const tgt = typeof a.target === "function" ? a.target() : a.target;
    const dist = edgeDist(s.left + a.x * k, s.top + a.y * k, tgt.getBoundingClientRect());
    const name = tgt.textContent.trim().slice(0, 40);
    if (dist > ARROW_TOL) console.error(`beat ${a.b.id}: arrow tip lands ${dist.toFixed(1)} px from its target "${name}"`);
    const shown = shownAt(tgt); // an arrow that lands before its target shows points at nothing
    if (shown < 0.99) console.error(`beat ${a.b.id}: arrow lands before its target "${name}" shows`);
    return { id: a.b.id, at: a.at, dist: Math.round(dist * 10) / 10, shown };
  });
  rewind();
  return out;
}

// ---- morph: a match cut. beat.in = "morph", scene.morph = {from: text in the previous beat, to: text in this one}.
// The matched text travels and rescales from its old frame position to the new one; the rest of the old scene
// clears fast and the new scene builds round it. Both ends are measured in frame px after the fit (buildMorphs).
const MORPHS = [];
const MORPH = { lead: 0.2, travel: 0.8 }; // the traveller takes over 0.2 s before the boundary
function morphCut(prev, root, at, b, prevBeat) {
  const m = b.scene.morph;
  if (!m || !m.from || !m.to) throw new Error(`beat ${b.id}: in "morph" needs scene.morph {from, to}`);
  // wrapped now, before the fit measures the bodies, so the measured layout is the drawn one
  MORPHS.push({ b, a: wrapText(prev, prevBeat, m.from), z: wrapText(root, b, m.to), t0: at - MORPH.lead, land: at - MORPH.lead + MORPH.travel });
  // the old scene is gone by the boundary (most of it in the first frames), so the two never double-expose
  tl.to(prev, { opacity: 0, duration: MORPH.lead, ease: "power2.out" }, at - MORPH.lead);
  tl.fromTo(root, { opacity: 0 }, { opacity: 1, duration: 0.2, ease: "power1.out", immediateRender: false }, at);
}
const FONT_PROPS = ["fontFamily", "fontWeight", "fontSize", "letterSpacing", "lineHeight", "textTransform", "fontVariantNumeric", "color"];
// a copy of a text node in the frame layer, in that node's own type, placed by its frame font size and left/middle
function twin(layer, node) {
  const cs = getComputedStyle(node);
  const n = el("div", "abs", layer, { ...Object.fromEntries(FONT_PROPS.map((k) => [k, cs[k]])), left: 0, top: 0, whiteSpace: "nowrap", transformOrigin: "0 0" }, node.textContent);
  n.setAttribute("data-layout-allow-overlap", ""); // it flies over both scenes on purpose
  const f = parseFloat(cs.fontSize);
  const at = (p) => ({ x: p.left, y: p.mid - (n.offsetHeight * p.font) / f / 2, scale: p.font / f });
  return { n, at };
}
// where a text node sits in the frame now: its left edge, its middle and its font size in frame px
function framePose(node) {
  const r = node.getBoundingClientRect();
  return { left: r.left, mid: r.top + r.height / 2, font: (parseFloat(getComputedStyle(node).fontSize) * r.width) / node.offsetWidth };
}
// the opacity a node shows with, through its ancestors
function shownAt(node) {
  let o = 1;
  for (let n = node; n && n.nodeType === 1; n = n.parentNode) o *= +getComputedStyle(n).opacity;
  return o;
}
// two twins fly the same path: the old text's type fades into the new text's type mid-flight, so a mono label
// can become a serif line without a jump; on landing the new twin sits exactly on the real text and hands over
function buildMorphs(layer) {
  MORPHS.forEach((q) => {
    tl.seek(q.t0);
    const p0 = framePose(q.a);
    q.fromRect = [p0.left, p0.mid];
    // the new text where it settles: after its own entrance, before anything later moves it
    tl.seek(Math.min(q.land + 0.6, q.b.end - 0.1));
    const p1 = framePose(q.z);
    // the new text's own container must be on screen when the twin lands, or the word floats in an empty slot
    tl.seek(q.land);
    if (shownAt(q.z.parentNode) < 0.99) console.error(`beat ${q.b.id}: morph "${q.b.scene.morph.to}" is not on screen when the traveller lands; pick text shown from the beat start`);
    const [A, Z] = [twin(layer, q.a), twin(layer, q.z)];
    q.travellers = [A.n, Z.n];
    q.traveller = Z.n;
    const fly = { duration: MORPH.travel, ease: MOVE, immediateRender: false };
    // the type change happens in a short window while the twins move fastest, so the double image barely shows
    const fade = { duration: MORPH.travel * 0.25, ease: "power1.inOut", immediateRender: false };
    tl.set([A.n, Z.n], { opacity: 0 }, 0);
    tl.set(A.n, { opacity: 1 }, q.t0);
    tl.set(q.a, { opacity: 0 }, q.t0);
    tl.fromTo(A.n, A.at(p0), { ...A.at(p1), ...fly }, q.t0);
    tl.fromTo(Z.n, Z.at(p0), { ...Z.at(p1), ...fly }, q.t0);
    tl.fromTo(A.n, { opacity: 1 }, { opacity: 0, ...fade }, q.t0 + MORPH.travel * 0.15);
    tl.fromTo(Z.n, { opacity: 0 }, { opacity: 1, ...fade }, q.t0 + MORPH.travel * 0.15);
    tl.set(q.z, { opacity: 0 }, 0);
    tl.set(q.z, { opacity: 1 }, q.land);
    tl.set(Z.n, { opacity: 0 }, q.land);
  });
  rewind();
}
