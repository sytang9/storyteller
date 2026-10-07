# Motion craft: scenes that look made by a motion designer

Read this before you write a custom scene module (`fn(root, beat)` in `window.SCENES`). It turns the motion brief in
`direction.md` into code. The worked example is `assets/hf/examples/craft-example.js`: a total splits into two parts.
Tags: **[E]** a study or a measurement, **[R]** a HyperFrames (HF) rule, **[T]** taste: practitioner convention, no
study behind it. Paths in brackets point to the author's research notes, which are not shipped with the skill (sources at the end).

## 0. The beginner look, in our own code

- One move for everything. `popIn` is opacity 0 to 1, y 24 to 0, 0.5 s, `ENTER`. `keyLabel` does the same at y 12.
- One rhythm: cards stagger a flat 0.1 s in DOM order (`scenes.js` `sceneRetype`), not by importance or distance.
- Layout tweens: `sceneMerge` tweens `left` and `width`. These snap to whole pixels and stutter on slow tails [R] (HA `adapters/gsap-transforms-and-perf.md`).
- Small, flat frames: in an early trial's contact sheet most beats fill under half the frame, with thin cards and 24 px labels.
- HF names it: "If every element enters from `y: 30, opacity: 0`, the scene has no choreography" [R] (HC `video-composition.md`).

## 1. Set, then change (the rule a critic scored first)

- **The set is there from frame 1, and it looks finished.** The ground, the shared world (road, map), the heading
  and any actor already known from an earlier beat are on screen when the beat starts, so a `push` or `wipe`
  lands on a composed frame. Never pre-place scaffolding: no hollow pins, blank windows, empty sign panels or
  empty dashed boxes. Something that needs its cue arrives whole, with its icon and label, on that cue. A critic
  scored both failures: a frame that opens empty, and a frame full of placeholders, read as unfinished.
- **Hand over the set.** When the next beat shares the world (the same road, the same map), place it where the
  last beat left it; never rebuild it from nothing.
- **Seams are part of the scene.** Clear your labels and kickers before your beat ends, so they never print over
  the next beat's; land a morphing word in its final slot, not across a shape; show a card's sub-text only after
  its morphing name has landed.
- **Whole digits only.** A rolling number sits in a slot with `overflow: hidden` and a line height equal to the
  glyph height, so no half digit shows; small labels (chapter numbers) mask in instead of rolling.

## 2. Choreography

- **Lead.** One element carries the beat's change: the biggest shape, or the number on its spoken word. It moves first and furthest. "The element that moves first is perceived as most important" [R] (HC `motion-principles.md`).
- **Overlap.** A follower starts when its lead is 60-80% done. A queue reads as a slideshow; full overlap reads as one blob [R] (HA `rules/waterfall-entry.md`: "overlap, don't queue").
- **Offsets by distance.** Order followers by distance from the lead's landing point, not by DOM order. Keep a group's whole stagger at 0.5 s or less [R] (HA `rules-index.md`).
- **One focal mover**, plus one secondary at most; a group that moves alike counts as one. Observers track 8 slow objects but 1 fast one [E, read in a snippet only] (KT section 7).
- **Settle order.** The mover lands, then its label, then its number. Text holds still 0.8 s or more after it lands [T] (KT section 7).
- **Announce, then change.** A cut line, a mark or a dim comes just before a morph [T] (KT section 8).
- **No move at the cut.** The first move starts 0.1-0.3 s into the beat [R] (HC `motion-principles.md`).

```js
const land = cue(b, s.word); // the lead lands 0.3 s before its word
const LEAD_DUR = 0.9, FOLLOW = 0.7; // followers start at 70% of the lead
tl.set(lead, { scaleX: 0, transformOrigin: "0% 50%" }, 0);
tl.fromTo(lead, { scaleX: 0 }, { scaleX: 1, duration: LEAD_DUR, ease: ENTER, immediateRender: false }, land - LEAD_DUR);
followers.sort((p, q) => p.dist - q.dist).forEach((f) => // nearest first, +0.05 s per 400 px
  tl.fromTo(f.node, { yPercent: 120 }, { yPercent: 0, duration: 0.6, ease: ENTER, immediateRender: false },
    land - LEAD_DUR * (1 - FOLLOW) + f.dist / 8000));
```

## 3. Entrance vocabulary by role

| role | move | duration |
| --- | --- | --- |
| text line, label | mask reveal: a clipping slot, the line rises `yPercent` 120 to 0 | 0.5-0.7 s |
| number | roll: one digit column per place, most significant digit lands first (example `rollNumber`) | 0.6-0.9 s |
| bar, node, shape | scale from its anchor: a bar from its baseline or start edge, a node from its centre | by distance (3) |
| line, edge, arrow | draw on: `strokeDashoffset` from length to 0; the head shows at the end | 0.3-0.5 s |
| container, panel | grow from the edge it grows from: `clip-path: inset()`, which keeps corners true | by distance |
| icon, dot, chip | pop: scale 0.6 to 1 with rotation -8 to 0, no overshoot | 0.35-0.45 s |
| context, furniture | opacity only | 0.3 s |

- Exits run at 40-60% of the entrance time, with an ease-in, toward where attention goes next. "A card takes 0.4s to appear but 0.25s to disappear" [R] (HC `motion-principles.md`).
- Exit only when the state stops being true (`until`); the beat transition does every other exit.
- No `back`, `elastic` or `bounce`: "Smooth beats bouncy" [R] (FE `motion-language.md` Part 2). No blur-in on text [T].

```js
const slot = el("div", "abs", root, { left: "120px", top: "760px", overflow: "hidden", paddingBottom: "0.12em" });
const line = el("div", "t-h2", slot, { whiteSpace: "nowrap" }, s.label); // the slot clips; the line moves
tl.set(line, { yPercent: 120 }, 0);
tl.fromTo(line, { yPercent: 120 }, { yPercent: 0, duration: 0.6, ease: ENTER, immediateRender: false }, cue(b, s.word));
tl.fromTo(line, { yPercent: 0 }, { yPercent: 120, duration: 0.25, ease: EXIT, immediateRender: false }, cue(b, s.until));
tl.set(path, { strokeDasharray: len, strokeDashoffset: len }, 0); // len: known, or getTotalLength() once at build
tl.fromTo(path, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: 0.45, ease: MOVE, immediateRender: false }, at);
tl.fromTo(panel, { clipPath: "inset(0px 1680px 0px 0px round 24px)" }, { clipPath: "inset(0px 0px 0px 0px round 24px)",
  duration: 0.9, ease: ENTER, immediateRender: false }, at); // scaleX would squash the rounded corners
tl.fromTo(icon, { scale: 0.6, rotation: -8, opacity: 0 }, { scale: 1, rotation: 0, opacity: 1, duration: 0.4, ease: ENTER, immediateRender: false }, at);
```

## 4. Easing and timing

| motion | ease | duration |
| --- | --- | --- |
| arrival, short travel (under 200 px) | `ENTER` (0.05, 0.7, 0.1, 1), or `power3.out` | 0.35-0.6 s |
| arrival, long travel; a hero landing | `ENTER`, `expo.out` or `power4.out` | 0.7-1.0 s |
| move between two places on screen | `MOVE` (0.2, 0, 0, 1), or `power2.inOut` | 0.3 s + distance / 2400 px, at most 1.0 s |
| group slide that makes room | slow-fast-slow chain: `power3.in`, `none`, `power4.out` [R] (HA `rules/nudge-curve.md`) | 0.5-0.6 s |
| camera push, pan, world move | `power2.inOut` | 0.8-1.2 s |
| exit | `EXIT`, or `power2.in` | 0.2-0.3 s |
| colour or tier change | `MOVE`, or `power1.inOut` | 0.3-0.4 s |
| seam inside a beat | out `power3.in` 0.2 s, hard swap, in `expo.out` 0.5 s, same direction [R] (FE `cut-catalog.md`) | 0.7 s |

- `.out` for entrances, `.in` for exits, `.inOut` for moves. "Ease-in for entrances feels sluggish. Ease-out for exits feels reluctant" [R] (HC `motion-principles.md`).
- Duration grows with distance; the distance formula above is our convention [T]. The slowest motion in a scene runs about 3x the fastest, and at most 2 tweens share one ease and duration [R] (HC `motion-principles.md`).
- Evidence for easing is thin: one study (n = 40) found custom Bezier curves beat simple easing on retention [E, weak] (KT section 3).
- Beginner tells: linear on everything; one 0.5 s ease-out on everything; the same stagger in every scene; exits as slow as entrances.

## 5. Continuity

- **Persistent object.** Beats that share `scene.hero` share one node above the scenes (`hero(b)`, `heroGroup(b)`, `heroProps(b)` in `index.html`). The object transforms across the cut. Use it when one object lives for 2-3 beats [T] (MSG T4).
- **Match cut by colour field.** The focal object grows past every frame edge. The next beat (`in: "cut"`) opens on that colour and shrinks it into its own object. The example's `handoff` is the send side. The receive side:

```js
const field = el("div", "abs", root, { left: "120px", top: "300px", width: "1680px", height: "480px", background: col(s.from), borderRadius: "24px" });
tl.set(field, { scaleX: 3, scaleY: 6 }, 0); // larger than the frame at the cut: the colour carries over
tl.fromTo(field, { scaleX: 3, scaleY: 6 }, { scaleX: 1, scaleY: 1, duration: 0.8, ease: "power3.inOut", immediateRender: false }, b.start + 0.1);
```

- **Carry colour.** A role colour keeps one meaning for the whole video (`direction.md`). A part that changes role tweens its colour (0.3-0.4 s); it does not cut.
- **Carry position.** Put the next key object where the last one ended. Beats with one hero share one fit, so equal scene px land on equal frame px. Different fits do not match; use the hero layer when position must match.
- **Persistent world.** Build one wide `world` div (for example 3 x 1920 px) and move it with `x` between stations. Text holds still while the camera moves [R] (HA `rules/viewport-change.md`; KT section 7).

## 6. Composition for motion

- Lay out at full scene size (1920 x 900 px). Make the content span 80% or more of the 1680 px working width. The fit scales up 1.3x at most, so a small layout stays small (`FIT_MAX` in `index.html`).
- Big shapes: bars and fields 120-200 px thick; a colour field may fill 30-60% of the frame. Separate objects by fill, not by 2 px borders. A stroke that must show is 3-4 px [R] (HC `video-composition.md`: borders 2-4 px, padding 60-140 px).
- Scale contrast: one element per scene is at least 2x the next tier. Hero to body is 1.6x for calm looks, 2.1x by default, 3x for `poster` [T] (KT section 6). Signalling by size helps recall, d = 0.38 [E] (MSG T6).
- Three depth tiers: focal (opacity 1, role colour), context (opacity 0.4-0.5 or `mute`; scale 0.9 when receded), furniture (eyebrow, axes, ticks: `mute`, 24 px). Move the tiers when the subject changes; the example dims the total at the split. Opacity tiers come from Manim practice [T] (MSG T8). Blur a receded layer only rarely: set 2-4 px, do not tween it.
- Negative space is a choice: anchor content to an edge and leave one side open. "Centered-and-floating is a web pattern" [R] (HC `motion-principles.md`).
- Type at 1080p (`style.css`): `t-display` 200, `t-num` 128, `t-h1` 64, `t-h2` 48, `t-body` 32, `t-label` 24 px. Body text stays 32 px or more after the fit; nothing goes under 24 px. HF's video table agrees: headlines 64-120, body 28-42, labels 18-24 [R] (HC `video-composition.md`).

## 7. Texture and finish

- Shadow tiers per look [T]. `paper` and `forest` give lifted objects `0 2px 0 rgb(0 0 0 / .06), 0 16px 32px rgb(0 0 0 / .08)`. `editorial` uses one soft tier. `poster` uses a hard offset, `8px 8px 0 var(--ink)`. `night` and `blueprint` use no shadow; they separate by value steps and 3 px rules. Use at most two tiers a scene, resting and lifted. A lift changes the tier and moves y -8 px; it never glows.
- Grain [T, untested in our renders]: a look-level choice, not a per-scene one. When used, it is one static SVG `feTurbulence` overlay with a fixed `seed`, opacity 3-6%, never animated. H.264 can smear fine grain; check a rendered frame.
- Banned (`direction.md`): glow, particles, ambient drift, breathing, bounce, glass, purple-blue gradients, text gradients. HF docs suggest radial glows, ambient motion and "subtle jitter" (HC `video-composition.md`, FE `motion-language.md`); we do not follow them.
- Labels attach to their object: 16-24 px gap, anchored by the edge that faces away from the object. A label on the right part uses `right:`; one on the left uses `left:`. Then no text width is needed. The label moves with its object: make it a child, or use one tween. Draw a leader only when the label cannot touch the object.
- Arrows: compute the ends from shape geometry (constants), not from text width. Stop the tip 8 px outside the target's box. Draw the shaft, then show the head as the shaft completes. Measure a text target once at build (`sceneBox` in `events.js`), never in a tween callback.
- Fonts: HF says to measure after `document.fonts.ready` [R] (HA `rules/viewport-change.md`). Our `index.html` builds synchronously, so a module cannot wait. In a headless Chrome test, `document.fonts.status` was still `loading` after the build. Text widths measured at build can therefore use fallback metrics [E, one local test]. Anchor by edge when you can, and check any text-measured arrow on a rendered frame.

## 8. Seek-safety (HyperFrames)

- Put every tween on the shared `tl`. A bare `gsap.to` does not render [R] (HC `motion-principles.md`).
- Use `fromTo` with `immediateRender: false`, plus `tl.set(node, from, 0)` so the node holds its from-state until then. Give an exit the state the node is really in (the example exits the total from 0.4, not from 1).
- No `Date.now`, `performance.now` or `Math.random`. Derive variation from the index, for example `(i * 37) % 11` [R] (HA `SKILL.md`).
- Tween transforms (`x`, `y`, `xPercent`, `yPercent`, `scale`, `rotation`), `opacity` and `clip-path`. Colour and `borderRadius` are paint-only, and HF core allows them. Never tween `left`, `top`, `width`, `height`, `fontSize` or `letterSpacing` [R] (HA `adapters/gsap-transforms-and-perf.md`).
- Measure once, at build, inside `fn`; then bake positions into constants. Never measure in `onUpdate`.
- No CSS `transition` or `@keyframes`, no `repeat: -1`, no yoyo loops for "life". Two transforms must not run on one element at once; split them across parent and child [R] (HC `motion-principles.md`).
- GSAP leaves an identity transform on a rewound node. Write the rest transform with `tl.set` at 0 so forward and rewound states match (the example does).
- Validate the data at the boundary: throw on a wrong part count or words out of order (the example does).
- Test: seek a set of times forward, then in reverse, and compare. The example's computed styles matched at 8 times; pixels differed by at most 1 px of corner antialiasing.

## 9. Checklist: beginner or pro

Run each line against your scene. A beginner answer is a fix.

0. Does the beat open on an empty frame, show an empty placeholder, or leave a label over the next beat? Show the finished set from frame 1; bring cue-bound things in whole (section 1).

1. Does every element enter with the same move? Give each role its own move (section 3).
2. Is there one lead that moves first and furthest? Name it in a comment.
3. Do followers start before the lead ends, at 20-40% overlap?
4. Is the stagger in DOM order? Order by importance or distance; 0.5 s total at most.
5. Do two things travel at once? Keep one focal mover.
6. Is there one ease and one duration everywhere? Scale durations by distance; make exits about half as long.
7. Does text fade in place? Use a mask reveal; roll the numbers; draw the lines.
8. Does anything bounce, glow, drift or breathe? Remove it.
9. Does the content fill less than 60% of the frame width? Lay out at full width, with big shapes.
10. Are there 3 tiers, and does the focal tier move when the subject changes?
11. Does an object carry into the next beat (hero, colour field, position)? If not, say why.
12. Is there a `left`, `top`, `width` or `height` tween, a clock, a random value or a bare `gsap.to`? Fix it (section 8).

## Sources

- HA `hf-ref/skills/hyperframes-animation/`: `SKILL.md`, `rules-index.md`, `adapters/gsap-easing-and-stagger.md`, `adapters/gsap-transforms-and-perf.md`, `rules/waterfall-entry.md`, `rules/nudge-curve.md`, `rules/card-morph-anchor.md`, `rules/viewport-change.md`, `rules/camera-cursor-tracking.md`.
- HC `hf-ref/skills/hyperframes-creative/references/`: `motion-principles.md`, `beat-direction.md`, `video-composition.md`, `data-in-motion.md`, `visual-styles.md`.
- FE `hf-ref/skills/faceless-explainer/references/`: `motion-language.md`, `cut-catalog.md`, `visual-design.md`. Also `hf-ref/skills/motion-graphics/references/motion-vocabulary.md`.
- KT `storyteller/research/kinetic_text.md`; MSG `storyteller/research/motion_showcase_gap.md`; `storyteller/research/video_orchestration.md` section 3.
- Web: the GSAP ease list, https://gsap.com/docs/v3/Eases/ (read). The Material motion pages did not render, so the distance rule above is convention, not a cited spec.
