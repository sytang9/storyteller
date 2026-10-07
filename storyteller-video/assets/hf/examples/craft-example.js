// craft-example: a total splits into its parts. Worked example for references/motion-craft.md;
// the (n) marks in the comments point to that guide's sections.
// The story in motion: one big bar arrives as the whole and its number rolls in. A cut line announces the
// split, the second part slides off and both parts take their role colours, the total steps back a tier,
// and each part's number rolls in under it. Optional handoff: one part grows into a full-frame colour field,
// so a next beat that opens on the same field (with in: "cut") reads as one object, not two scenes.
// scene: {eyebrow, title, total: {value, label, word}, parts: [{label, value, color, word}] (exactly 2),
//         splitWord, handoff?: {word, part: 0 | 1}}
// Helpers from index.html: el, svgEl, tl, C, col, cue, head, ENTER, EXIT, MOVE.
(function () {
  const X0 = 120; // the bar spans the working width, so the fit stays near 1 and the shapes stay big (5)
  const X1 = 1800;
  const GAP = 48; // the split opens this gap; the bar is laid out GAP short so the moved part ends at X1
  const BAR_W = X1 - X0 - GAP;
  const BAR_Y = 540;
  const BAR_H = 160; // a colour field, not a hairline (5)
  const RADIUS = 12;
  const TOTAL_Y = 300;
  const PART_Y = BAR_Y + BAR_H + 32;
  const ROW = "1.1em"; // one digit row in a rolling column; the slot clips to exactly one row
  const PX_PER_S = 2400; // duration grows with travel: 0.3 s plus 1 s per 2400 px, capped at 1 s (3)
  const durFor = (px) => Math.min(1, 0.3 + px / PX_PER_S);
  const FOLLOW = 0.7; // a follower starts when its lead is 70% done: a 30% overlap (1)
  const DIM = 0.4; // the context tier (5)
  const COVER = 2200; // half-extent in px that the handoff field reaches, past every frame edge at any fit

  // a tween window that lands at `land`, starts no earlier than `earliest`, and lasts at least `min` s
  const span = (land, dur, earliest, min = 0.3) => {
    const start = Math.max(earliest, land - dur);
    return [start, Math.max(min, land - start)];
  };

  // (2) text rises out of its own slot: the wrapper clips, the line moves; no fade, no drift
  function maskLine(parent, text, cls, css, slotCls = "abs") {
    const slot = el("div", slotCls, parent, { ...css, overflow: "hidden", paddingBottom: "0.12em" });
    const line = el("div", cls, slot, { whiteSpace: "nowrap" }, text);
    tl.set(line, { yPercent: 120 }, 0);
    return line;
  }
  const maskIn = (line, at, dur = 0.6) =>
    tl.fromTo(line, { yPercent: 120 }, { yPercent: 0, duration: dur, ease: ENTER, immediateRender: false }, at);

  // (2) a number rolls: each character is a column of rows in a one-row slot. Digits roll from below
  // 0 up to their digit; the columns land left to right, so the most significant digit settles first and
  // the last digit lands on `land`. Transforms only, so a seek to any frame shows the same state.
  const STEP = 0.06;
  function rollNumber(parent, value, cls, css, land, dur, earliest) {
    const box = el("div", cls, parent, { ...css, display: "flex", whiteSpace: "nowrap" });
    const chars = String(value).split("");
    chars.forEach((ch, i) => {
      const slot = el("span", "", box, { display: "inline-block", overflow: "hidden", height: ROW, lineHeight: ROW });
      const rows = /\d/.test(ch) ? "0123456789".split("") : [ch];
      const column = el("span", "", slot, { display: "block" });
      rows.forEach((r) => el("span", "", column, { display: "block", height: ROW }, r));
      const k = rows.indexOf(ch);
      const from = { yPercent: 100 / rows.length }; // one row below the slot: empty before the roll
      const [at, d] = span(land - (chars.length - 1 - i) * STEP, dur, earliest);
      tl.set(column, from, 0);
      tl.fromTo(column, from, { yPercent: (-100 * k) / rows.length, duration: d, ease: ENTER, immediateRender: false }, at);
    });
    return box;
  }

  function sceneCraftExample(root, b) {
    const s = b.scene;
    if (!s.total || !Array.isArray(s.parts) || s.parts.length !== 2) throw new Error(`beat ${b.id}: craft-example needs total and exactly 2 parts`);
    const sum = s.parts[0].value + s.parts[1].value;
    if (!(s.parts.every((p) => Number.isFinite(p.value) && p.value > 0) && sum > 0)) throw new Error(`beat ${b.id}: part values must be positive numbers`);
    head(root, s.eyebrow, s.title);
    const tTotal = cue(b, ...[].concat(s.total.word));
    const tSplit = cue(b, ...[].concat(s.splitWord));
    const tParts = s.parts.map((p) => cue(b, ...[].concat(p.word)));
    if (!(tTotal < tSplit && tSplit <= Math.min(...tParts))) throw new Error(`beat ${b.id}: words must run total, split, then parts`);
    const wA = Math.round((BAR_W * s.parts[0].value) / sum);
    const widths = [wA, BAR_W - wA];
    const earliest = b.start + 0.1; // (1) never start at the cut: give the transition a breath

    // ---- the whole: the bar is the lead; it grows from its left edge, the edge it grows from (2) ----
    const bar = el("div", "abs", root, { left: X0 + "px", top: BAR_Y + "px", width: BAR_W + GAP + "px", height: BAR_H + "px" });
    const segs = widths.map((w, i) =>
      el("div", "abs", bar, {
        left: (i ? wA : 0) + "px", top: 0, width: w + "px", height: "100%", background: C.mute,
        borderRadius: i ? `0 ${RADIUS}px ${RADIUS}px 0` : `${RADIUS}px 0 0 ${RADIUS}px`, // two halves read as one bar
      }),
    );
    // GSAP leaves an identity transform behind on rewind; writing it at 0 makes the forward and the rewound
    // state identical (computed styles checked at 8 times; only 1 px of corner antialiasing may differ) (7)
    tl.set(segs, { x: 0, scaleX: 1, scaleY: 1 }, 0);
    // clip-path, not scaleX: a scaled box squashes its rounded corners; a clip keeps them true
    const shut = `inset(0px ${BAR_W + GAP}px 0px 0px round ${RADIUS}px)`;
    const open = `inset(0px ${GAP}px 0px 0px round ${RADIUS}px)`;
    const barDur = durFor(BAR_W);
    const rollDur = 0.8;
    // the number lands on its word; the bar leads it by 30% of the bar's own run
    const [barAt] = span(tTotal - rollDur + (1 - FOLLOW) * barDur, barDur, earliest);
    tl.set(bar, { clipPath: shut }, 0);
    tl.fromTo(bar, { clipPath: shut }, { clipPath: open, duration: barDur, ease: ENTER, immediateRender: false }, barAt);

    // the total: number (tier 1 for now) and its label, a follower that starts at 70% of the roll
    const totalG = el("div", "abs", root, { left: X0 + "px", top: TOTAL_Y + "px", display: "flex", flexDirection: "column", gap: "4px" });
    rollNumber(totalG, s.total.value, "t-num", {}, tTotal, rollDur, barAt + FOLLOW * barDur);
    maskIn(maskLine(totalG, s.total.label, "t-body mute", {}, ""), tTotal - (1 - FOLLOW) * rollDur);

    // ---- the split: announce, then change (1). A cut line draws through the bar, then one part moves ----
    const moveDur = durFor(GAP);
    const [moveAt] = span(tSplit, moveDur, tTotal + 0.4);
    const cutLen = BAR_H + 64; // a straight line: its length is known, so no getTotalLength
    const svg = svgEl("svg", root, { class: "abs", width: 8, height: cutLen, style: `left:${X0 + wA - 4}px;top:${BAR_Y - 32}px;overflow:visible` });
    const cut = svgEl("path", svg, { d: `M4 0 V${cutLen}`, fill: "none", stroke: C.ink, "stroke-width": 4, "stroke-linecap": "round" });
    tl.set(cut, { strokeDasharray: cutLen, strokeDashoffset: cutLen }, 0);
    tl.fromTo(cut, { strokeDashoffset: cutLen }, { strokeDashoffset: 0, duration: 0.35, ease: MOVE, immediateRender: false }, moveAt - 0.3);
    tl.fromTo(svg, { opacity: 1 }, { opacity: 0, duration: 0.2, ease: EXIT, immediateRender: false }, moveAt + 0.1);
    // the clip has done its job; release it so the moved part (and a handoff field) can leave the box
    tl.set(bar, { clipPath: "none" }, moveAt);
    // one focal mover: only the second part travels; both take their role colours and round their cut ends
    tl.fromTo(segs[1], { x: 0 }, { x: GAP, duration: moveDur, ease: MOVE, immediateRender: false }, moveAt);
    segs.forEach((seg, i) => {
      const from = { backgroundColor: C.mute, borderRadius: i ? `0px ${RADIUS}px ${RADIUS}px 0px` : `${RADIUS}px 0px 0px ${RADIUS}px` };
      tl.fromTo(seg, from, { backgroundColor: col(s.parts[i].color), borderRadius: `${RADIUS}px`, duration: 0.4, ease: MOVE, immediateRender: false }, moveAt + i * 0.05);
    });
    // the total steps back to the context tier: the parts are the subject now (5)
    tl.fromTo(totalG, { opacity: 1 }, { opacity: DIM, duration: 0.4, ease: MOVE, immediateRender: false }, moveAt + 0.1);

    // ---- the parts: the label names the part, then its number rolls in under it and lands on the word.
    // Settle order: mover, label, number (1). Labels attach by the part's outer edge (6). ----
    const splitEnd = moveAt + moveDur;
    const LABEL_DUR = 0.6;
    const ROLL_DUR = 0.6;
    const partNodes = s.parts.map((p, i) => {
      const side = i ? { right: 1920 - X1 + "px" } : { left: X0 + "px" }; // no text width needed
      const label = maskLine(root, p.label, "t-body", { ...side, top: PART_Y + "px" });
      const [labelAt] = span(tParts[i] - ROLL_DUR * FOLLOW, LABEL_DUR, splitEnd); // the roll starts at 70% of the label
      maskIn(label, labelAt, LABEL_DUR);
      const value = rollNumber(root, p.value, "abs t-num", // the parts are the subject now: full number size
         { ...side, top: PART_Y + 52 + "px", color: col(p.color) }, tParts[i], ROLL_DUR, labelAt + FOLLOW * LABEL_DUR);
      return { value, label };
    });

    // ---- handoff (4): on its word the rest leaves fast, then one part grows past every frame edge.
    // Leave about 1 s of beat after the handoff word, or the next transition cuts the field mid-growth. ----
    if (!s.handoff) return;
    const k = s.handoff.part;
    if (k !== 0 && k !== 1) throw new Error(`beat ${b.id}: handoff.part must be 0 or 1`);
    const exitAt = cue(b, ...[].concat(s.handoff.word));
    const READ_HOLD = 0.8; // text that must be read holds still this long after it lands (8)
    if (!(exitAt >= Math.max(...tParts) + READ_HOLD)) throw new Error(`beat ${b.id}: handoff word must come at least ${READ_HOLD} s after the last part`);
    const EXIT_DUR = 0.25; // exits run at about 40% of the entrance time (3)
    const out = { opacity: 0, duration: EXIT_DUR, ease: EXIT, immediateRender: false };
    tl.fromTo(totalG, { opacity: DIM }, out, exitAt); // from the tier it is really in, not from 1 (7)
    tl.fromTo([segs[1 - k], ...partNodes.map((n) => n.value)], { opacity: 1 }, out, exitAt);
    partNodes.forEach((n) => tl.fromTo(n.label, { yPercent: 0 }, { yPercent: 120, duration: EXIT_DUR, ease: EXIT, immediateRender: false }, exitAt));
    // scale from the part's own centre (the default origin); the next scene opens on this colour field
    tl.fromTo(segs[k], { scaleX: 1, scaleY: 1 }, { scaleX: (2 * COVER) / widths[k], scaleY: (2 * COVER) / BAR_H, duration: 0.8, ease: "power3.inOut", immediateRender: false }, exitAt + 0.15);
  }

  window.SCENES = window.SCENES || {};
  window.SCENES["craft-example.js"] = sceneCraftExample;
})();
