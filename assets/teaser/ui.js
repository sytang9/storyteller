// The ui scene (generic, driven by tour data) and the press ripple. The functions use tl when the assembly calls them.
// Helpers from index.html: el, svgEl, tl, C, LEAD, popIn, keyLabel, ENTER, EXIT, MOVE.
// ================= ui scene (generic, driven by tour data) =================
const SHOT_W = 1568;
const SHOT_H = 882;
const SHOT_LEFT = 176; // .shot position in style.css
const SHOT_TOP = 9;
const BOX_PAD = 0.04; // pad the box by this share of the still width on each side
const DIM_PAD = 0.015; // the dimmed hole hugs the box more tightly than the zoom region
const WIDE = 0.65; // a padded box wider than this share of the still frames its text instead
const TEXT_SPAN = 1.15; // ...with a view this many times the text width
const ZOOM_MIN_W = 0.4; // ...but at least this share of the still width
const BOX_EXTRA_H = 0.08; // view height is at least the box height plus this share of the still height
const ZOOM_DUR = 1.0;
function padBox(box, [sw, sh], pad = BOX_PAD) {
  const p = sw * pad;
  return { x0: Math.max(0, box.x0 - p), y0: Math.max(0, box.y0 - p), x1: Math.min(sw, box.x1 + p), y1: Math.min(sh, box.y1 + p) };
}
// the 16:9 view the camera fills the card with (fill 1.0), clamped inside the still
function zoomView(box, text, [sw, sh]) {
  const pb = padBox(box, [sw, sh]);
  let w = pb.x1 - pb.x0;
  let cx = (pb.x0 + pb.x1) / 2;
  if (w > sw * WIDE) {
    w = Math.max(TEXT_SPAN * (text.x1 - text.x0), sw * ZOOM_MIN_W);
    cx = (text.x0 + text.x1) / 2;
  }
  const h = Math.min(sh, Math.max((w * 9) / 16, box.y1 - box.y0 + sh * BOX_EXTRA_H));
  w = Math.min(sw, (h * 16) / 9);
  const vh = (w * 9) / 16;
  const x = Math.min(Math.max(cx - w / 2, 0), sw - w);
  const y = Math.min(Math.max((box.y0 + box.y1) / 2 - vh / 2, 0), sh - vh);
  return { x, y, w, h: vh };
}
const RING_INSET = 4; // the outline stays this far inside the card when the box runs past the settled view
const RING_R = 16; // corner radius of the outline and of the dim's hole, in card pixels at the settled view
const SPOT_BLUR = 40; // the dim's soft edge, in card pixels at the settled view
function sceneUi(root, b) {
  const u = b.ui;
  const [sw, sh] = u.size; // the still's own pixels: any resolution and aspect
  const shot = el("div", "abs card shot", root);
  const cam = el("div", "abs cam", shot, { width: sw + "px", height: sh + "px" });
  cam.setAttribute("data-layout-allow-overflow", ""); // the camera moves the still inside the card
  // the opening view shows the whole still, centred in the card (letterboxed when its aspect is not 16:9)
  const s0 = Math.min(SHOT_W / sw, SHOT_H / sh);
  const x0 = (SHOT_W - sw * s0) / 2;
  const y0 = (SHOT_H - sh * s0) / 2;
  const img = (src) => Object.assign(el("img", "", cam, { width: sw + "px", height: sh + "px" }), { src, alt: "" });
  img(u.after);
  const pb = padBox(u.box, u.size, DIM_PAD);
  const spot = el("div", "abs spot", cam, { left: pb.x0 + "px", top: pb.y0 + "px", width: pb.x1 - pb.x0 + "px", height: pb.y1 - pb.y0 + "px" });
  tl.set(cam, { x: x0, y: y0, scale: s0 }, 0);
  tl.set(spot, { opacity: 0 }, 0);
  popIn(shot, b.start, { opacity: 0, y: 30, scale: 0.98 });
  let free = b.start + 0.5;
  if (u.before) {
    const before = img(u.before);
    const press = u.clickAt - LEAD;
    pressRipple(shot, x0 + u.click.x * s0, y0 + u.click.y * s0, press);
    tl.fromTo(before, { opacity: 1 }, { opacity: 0, duration: 0.35, ease: "power1.inOut", immediateRender: false }, press + 0.15);
    free = press + 0.6;
  }
  // the zoom settles LEAD s before the anchor word and holds to the end of the beat
  const land = u.focusAt - LEAD;
  const start = Math.min(Math.max(free, land - ZOOM_DUR), land - 0.5);
  const v = zoomView(u.box, u.text, u.size);
  const s1 = SHOT_W / v.w;
  tl.fromTo(cam, { x: x0, y: y0, scale: s0 }, { x: -v.x * s1, y: -v.y * s1, scale: s1, duration: land - start, ease: MOVE, immediateRender: false }, start);
  // the dim lives in still pixels: divide by the zoom so its corners and edge look the same on any still size
  Object.assign(spot.style, { borderRadius: RING_R / s1 + "px", boxShadow: `0 0 ${SPOT_BLUR / s1}px ${2 * Math.max(sw, sh)}px rgba(29, 35, 48, 0.34)` });
  // the dim alone vanishes on a dark still, so a thin accent outline marks the box too. It sits in card pixels at the
  // settled view (outside the camera), so its stroke keeps one width whatever the zoom.
  const cx = (x) => Math.min(Math.max((x - v.x) * s1, RING_INSET), SHOT_W - RING_INSET);
  const cy = (y) => Math.min(Math.max((y - v.y) * s1, RING_INSET), SHOT_H - RING_INSET);
  const ring = el("div", "abs ring", shot, { left: cx(pb.x0) + "px", top: cy(pb.y0) + "px", width: cx(pb.x1) - cx(pb.x0) + "px", height: cy(pb.y1) - cy(pb.y0) + "px" });
  tl.set(ring, { opacity: 0 }, 0);
  tl.to([spot, ring], { opacity: 1, duration: 0.5, ease: ENTER }, land - 0.25);
  uiLabels(root, b, v, s1, pb);
}

// press-ripple (catalog block, ported inline): decel arrival, lockstep press, two click rings, exit
function pressRipple(parent, x, y, pressAt) {
  const rings = svgEl("svg", parent, { class: "abs", width: SHOT_W, height: SHOT_H, style: "left:0;top:0;overflow:visible" });
  const rs = [1, 0.6].map(() => svgEl("circle", rings, { cx: x, cy: y, r: 16, fill: "none", stroke: C.blue, "stroke-width": 3, opacity: 0 }));
  const cur = el("div", "abs cursor", parent, { left: (-5 / 24) * 60 + "px", top: (-3 / 24) * 60 + "px", transformOrigin: `${(5 / 24) * 60}px ${(3 / 24) * 60}px` });
  cur.setAttribute("data-layout-allow-overflow", ""); // parks off-card before and after the press
  const svg = svgEl("svg", cur, { viewBox: "0 0 24 24" });
  svgEl("path", svg, { d: "M5 3 L5 19 L9 15 L12 22 L15 20.5 L11.5 14 L18 14 Z", fill: "#ffffff", stroke: C.ink, "stroke-width": 1.4, "stroke-linejoin": "round" });
  const lx = x + 3;
  const ly = y + 4;
  tl.fromTo(cur, { x: SHOT_W * 1.08, y: SHOT_H * 1.1 }, { x: lx, y: ly, duration: 0.45, ease: ENTER, immediateRender: false }, pressAt - 0.6);
  tl.set(cur, { x: SHOT_W * 1.08, y: SHOT_H * 1.1 }, 0);
  tl.to(cur, { scale: 0.93, duration: 0.12, ease: "power1.in" }, pressAt);
  tl.to(cur, { scale: 1, duration: 0.3, ease: ENTER }, pressAt + 0.14);
  rs.forEach((r, i) => {
    const at = pressAt + 0.12 + i * 0.06;
    tl.fromTo(r, { attr: { r: 16 } }, { attr: { r: 72 }, duration: 0.32, ease: ENTER, immediateRender: false }, at);
    tl.fromTo(r, { opacity: [1, 0.6][i] }, { opacity: 0, duration: 0.32, ease: "power1.in", immediateRender: false }, at);
  });
  tl.fromTo(cur, { x: lx, y: ly }, { x: SHOT_W * 1.08, y: SHOT_H * 1.1, duration: 0.4, ease: EXIT, immediateRender: false }, pressAt + 0.4);
}


// ui labels never sit on the screenshot's text: each goes in a lane below the shot card, at its anchor's x
// (scene.labels[].at[0], still pixels, through the settled camera), with a leader line up to the edge of the
// highlighted block. Labels in the lane are pushed right so they never overlap each other.
const LANE_GAP = 28; // from the card's bottom edge to the label lane
const LABEL_GAP = 24; // between neighbouring labels in the lane
function uiLabels(root, b, v, s1, pb) {
  const labels = [...(b.scene.labels || [])].sort((p, q) => p.at[0] - q.at[0]);
  const laneY = SHOT_TOP + SHOT_H + LANE_GAP;
  const edgeY = Math.min(SHOT_TOP + SHOT_H, SHOT_TOP + (pb.y1 - v.y) * s1); // bottom of the highlighted block
  let right = -Infinity;
  labels.forEach((l) => {
    const ax = SHOT_LEFT + (l.at[0] - v.x) * s1;
    const n = keyLabel(root, b, { kind: "tag", ...l, align: "left" }, ax, laneY);
    const w = n.offsetWidth;
    const x = Math.max(ax - w / 2, right + LABEL_GAP, SHOT_LEFT);
    n.style.left = x + "px";
    right = x + w;
    const leaderX = Math.min(Math.max(ax, x + 16), x + w - 16);
    const lead = el("div", "abs ui-leader", root, { left: leaderX - 1 + "px", top: edgeY + "px", height: laneY - edgeY + "px" });
    const w0 = Array.isArray(l.word) ? l.word : [l.word];
    tl.set(lead, { opacity: 0, scaleY: 0 }, 0);
    tl.to(lead, { opacity: 1, scaleY: 1, duration: 0.3, ease: ENTER }, cue(b, ...w0) - 0.1);
  });
}
