# Scenes: the template's data contract

The template in `assets/hf/` is a HyperFrames composition that renders a narrated video from data. The code is generic. A report supplies only the files below.

## Files a report supplies

| File | Where | What |
| --- | --- | --- |
| `beats.timed.json` | next to `build.py` (or `--beats`) | ordered beats, with word times and one `scene` object each |
| `voice/<id>.wav` | `<src>/voice/` | one voice clip per beat |
| `shots/tour.json` + `shots/frames/*.png` | `<src>/shots/` | UI stills and boxes, for `ui` beats only |
| any JSON named by `scene.data` | next to the beats file | large scene data (for example `journey.json`) |
| `direction.json` | `<src>/` | the look and the tempo defaults (`references/direction.md`) |

`<src>` defaults to the parent folder of this template.

### Beat (one array item in `beats.timed.json`)

- `id`: also the voice file name. `kind`: `"motion"` or `"ui"`. `caption`: the caption text. `dur`: the voice length in seconds.
- `caption_words`: `[{w, s, e}]`, with times relative to the voice start. Captions, the highlighted word and every word cue use these times.
- `hold` (optional): seconds of silence after this beat's voice (default `direction.json` `hold`, else 0.35). A held beat (1.2-2.5 s) lets a key picture land.
- `in` (optional): the transition into this beat: `calm`, `fade`, `cut`, `push`, `zoom`, `wipe` or `morph` (default `direction.json` `transition`). See the grammar in `references/direction.md`. `morph` also needs `scene.morph` (see Transitions below).
- `scene`: `{type, ...fields}`, as described below. Every `word` field is a caption word, matched case-insensitively with punctuation removed (apostrophes stay: `Acme's` is its own word). A word pair `[w, n]` picks the nth match. A visual change lands 0.3 s before its word. A missing word stops the build with an error.
- Colours are role keys (`accent`, `blue`, `teal`, `purple`, `orange`, `good`, `ink`, `mute`); the look sets their values. Use a literal CSS colour only for a real-world colour (a road's asphalt).

### Scene types

| type | fields | what it shows |
| --- | --- | --- |
| `retype` | `eyebrow`, `title`, `source: {title, sub, word}`, `targets: [{name, color, word}]`, `tag` | A source sheet appears on `source.word`. A copy flies into each target card on that target's `word`, the card fills in, and `tag` pops. |
| `merge` | `eyebrow`, `title?`, `from: [{name, color}]`, `into`, `sub?`, `word`, `landWord`, `small?`, `hero?`, `steps?`, `tick?: [w0, w1]` | The `from` cards (in the same place as in `retype`) slide into one flat stack on `word`. The stack becomes one card named `into` and opens to full width on `landWord`. With `steps` and `tick`, the steps also tick in this beat; otherwise use `stepper` next. |
| `stepper` | `eyebrow`, `title`, `hero`, `steps: [..]`, `show`, `tick: [w0, w1]` | Adds the steps to the hero job card from `merge`. They appear on `show` and tick green, left to right, from `w0` to `w1`. |
| `custom` | `module: "<file>.js"`, `cues?`, any fields | Loads a scene function from a module next to the beats file. The module registers `window.SCENES["<file>.js"] = fn(root, beat)`. `build.py` adds the script tag (it copies the file into `custom/` when the beats file is outside this folder). Bespoke scenes never touch the core code. List the scene's change words in `cues: [{word, change}]` so `check_variety.py` sees them; a report figure in `shots/frames/` loads as `assets/frames/<file>`. |
| `lanes` | `eyebrow`, `title`, `lanes: [{id, name, color, word?}]`, `steps: [{id, name, w}]`, `stops: [[stepId, laneId]]`, `doneStep`, `counter: {label, word}` | A token walks the stops across swimlanes. Each lane pulses on its `word`. The counter counts lane changes (computed) and the last change lands on `counter.word`. The step widths `w` must sum to 1440 px or less (columns start at x 440, lanes end at 1880). |
| `counters` | `eyebrow`, `title`, `items: [{value, label, word, color, of?, ofWord?, chip?: {text, word}}]` | Up to 3 big numbers count up and land on their `word`. `of` adds "/ of" on `ofWord`, and `chip` pops on `chip.word`. |
| `chips` | `eyebrow`, `title` (`{n}` = the item count, in the accent colour), `items: [text or {text, detail}]`, `cols?` (an upper bound, default 4: the grid takes the column count that fills the free area at the largest scale), `in: [w0, w1]`, `tag?`, `tagIn?`, `numbered?`, `focus?: [indices]`, `restIn?`, `detailIn?: [w0, w1]` (a focus item may also carry `word` and `steps: {count, from, to, word, toWord}`) | A grid of short labels (12 at most, each 5 words or fewer). The cards pop from `in[0]` to `in[1]`. With `focus`, those items show in full in one centred row (headline size, their `detail` at h2 size, landing from `detailIn[0]` to `detailIn[1]`) and the rest sit below as dim chips in a centred row of up to 3 columns that enter as one group on `restIn`. Both forms use the `fill` fit (see Layout): the columns are narrowed so the widest row spans 80% of the free width at a scale of 1 or more. Up to 9 grid items keep text at 32 px or more. Index numbers show only with `numbered: true`. A focus item with `word` enters on that word; with `steps`, it shows a small step echo whose steps `from`..`to` light up from `word` to `toWord`. |
| `statement` | `eyebrow?`, `lines: [text]`, `in: [word per line]`, `em?: {text, word, style?, color?}`, `size?` | Type as the picture: one short claim set large in the display face, line by line on its words. `em.text` (inside one line) is emphasised on `em.word`: by default a block in `--em` wipes in behind it and the word turns to the ground colour (`style: "underline"` keeps the old underline). Keep it to 2-3 lines of 4 words or fewer. |
| `compare` | `eyebrow`, `title`, `left: {label, items, word, color?}`, `right: {label, items, word, color?}`, `strike?: {items, word}`, `links?: [{from, to, word}]` | The old way beside the new. The left items enter on `left.word`; the right panel wipes in on `right.word`. `strike` crosses out left items (by index); `links` draws a curve from a left item to what it became on the right. 6 items a side at most, 5 words each. An item may be `{text, color?, word?}`: `color` when one side holds two roles (a link takes its right item's colour), `word` to enter on its own word so the list builds with the voice. |
| `diagram` | `eyebrow`, `title`, `nodes: [{id, text, x, y, w?, h?, shape?, color?, word}]`, `edges: [{from, to, word, label?, dashed?, color?}]`, `focus?: {nodes, word, zoom?}` | A picture that draws itself. Nodes (`box` 300 x 96, `pill`, or `dot` with its text below) pop on their words; edges draw with an arrowhead on theirs, but never before both of their nodes have shown (`dashed` for a return or an optional path). `x, y` are node centres in scene px (0-1920, 0-900). On `focus.word` the camera pushes into those nodes (`zoom` default 1.6), the rest dim and the heading leaves. |
| `layers` | `eyebrow`, `title`, `layers: [{text, sub?, color?, word}]`, `spread?`, `focus?: {index, word}` | Layers in depth (a system's tiers, a road's courses), top layer first, 5 at most. Each drops into place on its word; without `spread` they land apart, with it they land flat and separate on `spread`. `focus` lifts one layer and dims the rest. `spread` and `focus` words must follow the last layer word. Use it only when depth is the idea. |
| `ui` | `eyebrow?`, `title?`, `focus?`, `nth?`, `click?`, `text?`, `labels?` | The tour still for this beat. Give it an `eyebrow` and a `title` that name the screen and its point, so the claim
reads with the sound off; the still then fits below the heading. The camera zooms to the tour box and settles 0.3 s before `focus` (default: the word one third of the way in). If the tour has a `before` still, a cursor click lands before `click` (default: the 2nd word). `text: {x0, y0, x1, y1}` overrides the tour's text box, to crop on word boundaries. The box gets a soft dim around it and a thin accent outline (3 px, rounded, `.ring`), so it shows on dark stills too. Labels here use `at: [x, y]` in still pixels (only `x` places them) and default to the dark tag style: they sit in a strip below the still, with a leader up to the box. The ui fit includes that strip, so the still shrinks and the labels stay above the caption band in `full` mode. |

`eyebrow` is plain text, which CSS sets in mono caps. Keep a `title` to 8 words or fewer.

Fields every scene takes:

- `labels: [{text, word, x, y, align?, color?, kind?, until?}]`: key-word labels of 2-5 words beside an object, in scene pixels (1920 x 900). `color` tints a plain label's text, or a `tag` label's ground (a `ui` label is a tag). Each lands 0.3 s before `word` and leaves on `until`. They show in both caption modes.
- `hero: "<id>"`: consecutive beats with the same id share one element (`hero(b)`) in a layer above the scenes. The object transforms across the cut, and it leaves with the last beat that names it. `heroGroup(b)` is that layer, for props that stay on screen across those beats (`retype` puts its tool cards there, `relay.js` its lanes); `heroProps(b)` is a store that hands them to the next beat.

### Events: the change inside a beat (`events.js`)

A scene builds its picture; `scene.events` keeps it moving while the voice explains it. `word` is a caption word
or `[word, n]`; `until` (a word) ends a `note`, `hero`, `lift` or `push`. Timing: `mark`, `note`, `hero`, `swap`
and `strike` start 0.3 s before their word and land within 0.5 s; `number` lands on its word; `push` starts 0.5 s
before and lands about 0.3 s after; `lift` starts on its word and lands about 0.65 s after. Text events find
their `target` by its text in the scene (case-sensitive, the first match, inside one text run; not in the heading).
One event per target: a later `swap` or `number` on the same text erases an earlier `mark`. `number` needs a
plain number as its target and never a counter's figure (the counter animates it already).

| kind | fields | what it shows |
| --- | --- | --- |
| `mark` | `target`, `style?` (`sweep`, `underline`, `circle`), `color?` | A highlight drawn on a phrase as it is spoken |
| `note` | `target`, `text`, `side?` (`above`, `below`, `left`, `right`), `color?`, `until?` | A 1-4 word tag with a drawn arrow to the phrase. The arrow tip stops 6 scene px outside the phrase; after the build, a check logs a console error when a tip lands more than 12 frame px from its target's edge (diagram edges too) |
| `lift` | `x`, `y`, `size?` (96), `text?`, `color?`, `until?` | The spoken word leaves the caption band and lands in the scene at (x, y) in the display face; the band word dims. (x, y) are scene px before the fit, so check the landed frame and move it if it covers a label |
| `hero` | `text`, `x`, `y`, `size?` (128, twice the heading), `color?`, `until?` | A big word in the display face at (x, y) |
| `swap` | `target`, `to`, `color?` | The phrase rolls out and `to` rolls in, in place (old/new, before/after) |
| `strike` | `target`, `to?` | A line through the phrase; `to` appears beside it |
| `number` | `target` (a plain number), `to`, `dur?` | The number counts to `to`, landing on the word |
| `push` | `target`, `zoom?` (1.5), `until?` | The camera pushes in on the phrase's box; `until` brings it back |

Rules: one mover at a time; text that must be read holds still for 0.8 s or more after it lands; at most one new
text item every 2 s. A `push` moves the picture, so nothing else moves during it; it zooms less than asked when the
target would leave the free area, so aim it at a target near mid-frame, one a beat. A `lift` lives above the
scene (it does not follow a `push`), so do not combine the two in one beat. A `ui` still takes no text events;
time its `labels` (with `until`) instead. `check_variety.py` fails a beat with more than 3.0 s of voice and no
change on screen; the order of what to add is in `references/direction.md`.

Layout and transitions (`index.html` assembly):

- Fit: each scene's body (everything except the heading) is scaled up and centred in the free area below the heading. It grows to 1.6x (`FIT_MAX`), or further, to 2x (`FIT_HARD`), until its box spans 60% (`FIT_FILL`) of the free width or height; it never passes the free area itself. A scene's own wrapper should hug its content (a full-width wrapper keeps the scene at 1x). The free area is y 216 to 1024 in keywords mode (the whole frame, with a quiet bottom margin) or to 876 in full mode (above the caption band). Content wider than the area keeps its size. Beats that share a hero share one fit, so shared objects line up. ui scenes fit the whole frame with a 40 px margin.
- Fill: a scene that sets `root.dataset.fit = "fill"` (the `chips` grids; a custom module may too) is scaled up or down so that it spans `FILL_W` (80%) of the free width, or the free height if that is smaller, at most 2x, and centred in the free area. `FREE` (the free area's width and height) and `FILL_W` are globals, so a scene can pick a layout that keeps its smallest text at 32 px or more after the scale.
- Transitions: each beat's `in` picks how it replaces the one before, at the boundary. `calm`: the old scene exits (0.3 s, ease-in), then the new one enters (0.4 s, ease-out). `fade`: a 0.5 s crossfade. `cut`: a hard cut. `push`: the new scene pushes the old one off to the left (0.7 s). `zoom`: a camera dive: the old scene accelerates toward the viewer and cuts out at its peak, then the new one settles (0.6 s; the two never share the screen; `scene.zoomAt: "x% y%"` on the new beat picks the point of the old frame to dive into). `wipe`: the new scene wipes in from the left (0.6 s). `morph`: a match cut, below. Beats that share a hero keep it across any transition; give them `fade` or `calm`.
- Morph (`in: "morph"`, `scene.morph: {from, to}`): `from` is text in the previous beat and `to` is text in this beat (each found like an event `target`: case-sensitive, the first match in the scene, heading included, inside one text run). The `from` text leaves its scene and travels (0.8 s, `MOVE`), rescaling and recolouring, to where the `to` text settles; it starts 0.2 s before the boundary. The rest of the old scene clears in 0.2 s (gone by the boundary) and the new scene builds round the traveller. On landing, the traveller hands over to the real `to` text in a 0.2 s crossfade, so the two texts may differ ("A home" into "a home"). Both ends are measured in frame px after the fit, at the boundary and where the new text settles. Use it when one object carries over between adjacent beats; one or two a video, never a default.
- Look: `build.py` writes `theme.css` from `direction.json` (`presets.json` holds the looks). Scenes read colours from the tokens (`C.ink`, `C.accent`, ...); the display face (`t-display`, `t-num`, `t-h1`, `t-h2`) and the body face come from the look. Never hard-code a colour in a scene.

Motion vocabulary (`index.html`, `motion.js`): `ENTER` (0.05, 0.7, 0.1, 1) for small state changes, `EXIT` (0.3, 0, 0.8, 0.15) for exits and `MOVE` (0.2, 0, 0, 1) for moves, from GSAP CustomEase. Entrances pick a speed by distance and role: `ARRIVE` (expo.out, 0.7 s) for text, numbers and cards, `SMALL` (power4.out, 0.4 s) for tags, icons, dots and fades, and `CAM` (power2.inOut) for camera pushes. A follower (a card's text, a number's label) starts with `FOLLOW` (35%) of its leader still to run. No linear, bounce or back easing, and no decorative 3D tilt (`layers` is the one 3D type, for a real depth idea).

Entrances (`motion.js`): `reveal(node, at, role, opts?)` returns the time the node lands. Roles: `text` (the node rises out of a mask the size of its own box: clip-path plus yPercent), `number` (the same slide, longer, power4.out), `card` (the box grows out of its anchor edge by a clip, so its text never squashes; its text children follow; `opts.from`: `left`, `right`, `top` or `bottom`, default `left` for a wide box and `bottom` otherwise), `line` (an SVG path draws on; a div rule scales out from its start edge) and `icon` (scales from 0.6 and settles). Every scene type uses them: statement lines, labels and note tags are `text`; counters are `number` with a `text` label; chips, compare rows, diagram boxes, retype cards and the ui still are `card`; rails are `line`; dots, tags and chips' ticks are `icon`. `popIn(node, at, from?)` still works: without `from` it is `reveal` with a role guessed from the node; with `from` the node returns to the neutral value of each named property only (a CSS centring translate survives), at `ARRIVE` for moves of 24 px or more and `SMALL` otherwise.

Fonts and measuring: the whole build runs after every bundled face has loaded (`loadFonts()` then the assembly; the timeline registers last). Text measured in a fallback font is 10-30 px off, which put note arrows, wrapped words and the fit in the wrong place. A custom module may measure text at build time; it needs nothing extra.

### `shots/tour.json`

`{beats: [{id, after, box: {x0, y0, x1, y1}, text?: {...}, size: [w, h], before?: {img, click: {x, y}}}]}`. `size` is the still's own pixel size, at any resolution and aspect, and every coordinate is in those pixels, so a report's own screenshots need no padding or resize step. The opening view shows the whole still, centred in the 16:9 card (letterboxed when its aspect differs); the zoom view stays inside the still. A small still is upscaled by the zoom, so its text gets soft: prefer 2x captures. `box` is the whole block to frame, and `text` is the text that the zoom centres on (it falls back to `box`). `scripts/record_tour.cjs` writes this file from a `tour.spec.json`.

## Build and render

```bash
cd <teaser>/hf
python3 build.py                      # options: --src .. --beats beats.timed.json --direction ../direction.json --vtt teaser.vtt --captions keywords|full
python3 -m pytest -q test_build.py    # phrase splitter, look contrast, direction.json
export HYPERFRAMES_NO_TELEMETRY=1 PATH=$PWD/.bin:$PATH
npx --yes hyperframes@0.8.126 check   # needs 0 errors
npx --yes hyperframes@0.8.126 render --quality delivery --output renders/raw.mp4
.bin/ffmpeg -y -i renders/raw.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 192k ../teaser.mp4
.bin/ffmpeg -y -ss 11.8 -i ../teaser.mp4 -frames:v 1 -q:v 3 ../poster.jpg
```

Captions: `--captions full` (the default) burns the phrase captions into the reserved bottom band, where no scene content goes, and keeps the `labels`. `--captions keywords` burns no sentence text; the headlines and `labels` carry the story, and the bottom 180 px stay free for a player's captions. Both modes write the VTT.

`build.py` writes `data.js`, copies the voice clips and stills into `assets/`, stamps the root duration and the `<audio>` tags into `index.html`, and writes `<src>/<vtt>`. Timing: each beat starts `hold` s after the previous voice ends. The voice starts 0.15 s into its beat. The video ends 1.2 s after the last voice clip. The transition straddles the boundary.

## Code map (do not edit for a new report)

- `index.html`: helpers (`el`, `svgEl`, `cue`, `wordAt`, `head`, `col`, `keyLabel`, `hero`, `heroGroup`, `heroProps`), the fit constants, the assembly (transitions, the fit per group) and the captions.
- `motion.js`: entrances (`reveal`, `popIn`, `drawLine`), the ease and speed pairs, `loadFonts`, the fit (`boxOf`, `fitParams`), the arrow check (`addArrow`, `checkArrows`) and the `morph` transition.
- `ui.js`: the `ui` scene and the press ripple.
- `events.js`: the event track (`runEvents` per scene, `finishEvents` for pushes and lifts after the fit).
- `scenes.js`, `scenes-extra.js`: one function for each motion type, registered in `window.SCENES`. To add a type, write `fn(root, beat)` that reads `beat.scene`, then register it.
- `presets.json`: the looks. `theme.css`: written by `build.py` (the default is the paper look).
- `style.css`: the type spec tokens (`t-display`, `t-num`, `t-h1`, `t-h2`, `t-body`, `t-label`, `t-eyebrow`), the bundled fonts and the layout.
- `assets/fonts/`: woff2 files for every look (Inter, JetBrains Mono, Fraunces, Bebas Neue, Space Grotesk, Source Serif 4, IBM Plex Sans and Mono; OFL, licences included). No network font is needed.

## Reuse for another report

1. Copy `assets/hf/` to `<report>/teaser/hf/` (it ships with no report data).
2. Write the beat sheet and the voice clips. Get word times from the TTS or an aligner as `caption_words`.
3. Add a `scene` object to each beat. Pick a type from the table and use only words that the caption contains.
4. For `ui` beats, record the tour into `<src>/shots/`.
5. Run the build and render commands. Then look at one frame per beat (`ffmpeg -ss <t> -frames:v 1`) before you ship.
