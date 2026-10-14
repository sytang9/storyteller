# World: one shared set, built once

A world is the one set the video keeps returning to: the place, the machine or the idea the story moves through.
One subagent builds it once as `world.js`, before any scene designer starts. Scene designers then choreograph
changes inside it; they never redraw it. The world gives continuity (the viewer never leaves the place) and saves
tokens (no designer re-implements the set from coordinates).

## Pick the world from the topic

| Topic | World | Views (examples) |
| --- | --- | --- |
| A place or field operation | the map, the road network, the site | `wide-region`, `close-site` |
| A process or pipeline | the stations and the belt that joins them | `wide-pipeline`, `close-step-3` |
| A software system | the services, queues and stores as one diagram | `wide-system`, `close-queue` |
| A research paper | the method as a machine: input, model, loss, output; or the data space, a loss landscape, a matrix | `wide-method`, `close-loss`, `close-weights` |
| A product | the app shell with its real screens on its panels | `wide-app`, `close-panel` |

Use 2D (DOM and SVG) by default. Use 3D (Three.js) when depth carries meaning: a pull-out over many units, a
surface such as a loss landscape, a stack of layers, a city or site. A world without a view change is a slide; plan
at least one wide view and one close view.

## Contract (`world.js`, next to `direction.json`)

```js
(function () {
  window.WORLD = {
    views: { wide: { x: 960, y: 540, zoom: 1 }, close: { x: 1400, y: 700, zoom: 2.4 } }, // numbers only
    build(layer, ctx) { /* once: draw the set into layer; put named objects in WORLD.objects */ },
    objects: {},                       // id -> node (2D) or THREE.Object3D (3D), for scene modules to animate
    data: {},                          // values several beats show (cell values, scores), defined once
    render(t, cam) { /* 3D only: draw one frame from the time and the camera; no clock of its own */ },
    state(name, at, beat) { /* optional: add tweens on tl for a state change, such as a colour switch */ },
  };
})();
```

- **2D**: the template moves the set: the frame centre looks at view `(x, y)` at `zoom`. Draw in a 1920 x 1080
  world space (or larger; views pick the part).
- **3D**: `direction.json` `world.three: true` loads Three.js (global `THREE`). `build` sets the camera keys its
  views use on `ctx.CAM` (for example `az`, `el`, `dist`) and creates `new THREE.WebGLRenderer({canvas,
  preserveDrawingBuffer: true})`. `render(t, cam)` places the camera from `cam` and calls `renderer.render`.
- **Seek safety**: every change is a tween on the shared `tl` (camera, objects, materials as plain numbers). No
  `Date.now`, `Math.random` or animation loop: a seek must draw the same frame every time. Seed any random layout.
- **Colours**: draw with the ground tokens as CSS variables (`var(--ink)`, `var(--surface)`, `var(--accent)`), not
  `C` hex values. The template sets each world beat's ground on the world layer, so one set reads on a dark beat
  and on a paper beat. A 3D world clears to transparent; the layer paints the ground behind the canvas.

## Beats and the world (`direction.json` and `beats.json`)

- `direction.json`: `"world": {"file": "world.js", "three"?: true, "ground"?: "<ground>", "states"?: {"<name>":
  {"filter"?: "grayscale(1) brightness(0.9)"}}}`. `ground` is the named ground every world beat stands on, so its
  captions and text match the set.
- A beat on the world: `scene.world: {"view": "<view>", "shot": "wide|mid|close", "state"?: "<name>"}`. Its
  scene root is transparent; its module draws only what changes (labels, a moving token, a highlight).
- **Camera**: the first world beat after a beat off the world opens on its view; two world beats in a row move the
  camera across the cut. Plan the views as a route: wide, then in, then back out.
- **States**: a named filter, or a `state` hook, changes the whole world at a turn: "before" desaturated and
  "with the system" in colour, "baseline" against "proposed", "untrained" against "trained".
- **Protagonist**: `direction.json` `"protagonist": "<one thing>"` (a pothole, a request, one sample, one token).
  It lives in the world and appears in at least half the voiced beats (`scene.protagonist: true`).
- **World state between beats**: changes to world objects persist. Each brief states `world_in` and `world_out`
  (for example "W empty" -> "W holds three pairs"). A scene sets its `world_in` with `tl.set` at `b.worldAt` (its
  start, or 0.6 s earlier after a beat off the world, when the set shows under the outgoing scene) and leaves the world in its `world_out` by its end.
- **Shared values**: the worked example that several beats show (the example sentence, a matrix's numbers, a
  score) lives once in `WORLD.data`, set by the world builder. Beats read it; they never invent their own, or
  the set jumps at a cut or a word changes. Keep the numbers on screen where the story computes: a blind A/B
  scored a world cut 6 against 8 on sound-off clarity when its update step lost the digits the old cut showed.
- **Grounds on the world**: a world beat may name its own `ground`; the set changes colour across the cut. The
  variety check counts a world beat by its ground and state, not its view: three views of the set on one ground
  read as one picture. Rotate grounds or states along the route, and mix in beats off the world (type beats,
  breaks, `ui` tours).

## The world builder (a subagent, before the scene designers)

Give it `direction.md`, `beats.timed.json`, this file and an example (`assets/hf/examples/world-2d.js` or
`world-3d.js`). It writes `world.js`, builds and renders one frame per view in a one-beat sandbox, and LOOKS at them.
It returns the views, the object ids and what each object is. The main thread copies that list into every scene
brief, so designers animate named objects instead of guessing coordinates.
