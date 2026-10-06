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
- `in` (optional): the transition into this beat: `calm`, `fade`, `cut`, `push`, `zoom` or `wipe` (default `direction.json` `transition`). See the grammar in `references/direction.md`.
- `scene`: `{type, ...fields}`, as described below. Every `word` field is a caption word, matched case-insensitively with punctuation removed (apostrophes stay: `Acme's` is its own word). A word pair `[w, n]` picks the nth match. A visual change lands 0.3 s before its word. A missing word stops the build with an error.
- Colours are role keys (`accent`, `blue`, `teal`, `purple`, `orange`, `good`, `ink`, `mute`); the look sets their values. Use a literal CSS colour only for a real-world colour (a road's asphalt).

### Scene types

| type | fields | what it shows |
| --- | --- | --- |
| `retype` | `eyebrow`, `title`, `source: {title, sub, word}`, `targets: [{name, color, word}]`, `tag` | A source sheet appears on `source.word`. A copy flies into each target card on that target's `word`, the card fills in, and `tag` pops. |
| `merge` | `eyebrow`, `title?`, `from: [{name, color}]`, `into`, `sub?`, `word`, `landWord`, `small?`, `hero?`, `steps?`, `tick?: [w0, w1]` | The `from` cards (in the same place as in `retype`) slide into one flat stack on `word`. The stack becomes one card named `into` and opens to full width on `landWord`. With `steps` and `tick`, the steps also tick in this beat; otherwise use `stepper` next. |
| `stepper` | `eyebrow`, `title`, `hero`, `steps: [..]`, `show`, `tick: [w0, w1]` | Adds the steps to the hero job card from `merge`. They appear on `show` and tick green, left to right, from `w0` to `w1`. |
| `custom` | `module: "<file>.js"`, any fields | Loads a scene function from a module next to the beats file. The module registers `window.SCENES["<file>.js"] = fn(root, beat)`. `build.py` adds the script tag (it copies the file into `custom/` when the beats file is outside this folder). Bespoke scenes never touch the core code. |
| `lanes` | `eyebrow`, `title`, `lanes: [{id, name, color, word?}]`, `steps: [{id, name, w}]`, `stops: [[stepId, laneId]]`, `doneStep`, `counter: {label, word}` | A token walks the stops across swimlanes. Each lane pulses on its `word`. The counter counts lane changes (computed) and the last change lands on `counter.word`. The step widths `w` must sum to 1440 px or less (columns start at x 440, lanes end at 1880). |
| `counters` | `eyebrow`, `title`, `items: [{value, label, word, color, of?, ofWord?, chip?: {text, word}}]` | Up to 3 big numbers count up and land on their `word`. `of` adds "/ of" on `ofWord`, and `chip` pops on `chip.word`. |
| `chips` | `eyebrow`, `title` (`{n}` = the item count, in the accent colour), `items: [text or {text, detail}]`, `cols?` (an upper bound, default 4: the grid takes the column count that fills the free area at the largest scale), `in: [w0, w1]`, `tag?`, `tagIn?`, `numbered?`, `focus?: [indices]`, `restIn?`, `detailIn?: [w0, w1]` (a focus item may also carry `word` and `steps: {count, from, to, word, toWord}`) | A grid of short labels (12 at most, each 5 words or fewer). The cards pop from `in[0]` to `in[1]`. With `focus`, those items show in full in one centred row (headline size, their `detail` at h2 size, landing from `detailIn[0]` to `detailIn[1]`) and the rest sit below as dim chips in a centred row of up to 3 columns that enter as one group on `restIn`. Both forms use the `fill` fit (see Layout): the columns are narrowed so the widest row spans 80% of the free width at a scale of 1 or more. Up to 9 grid items keep text at 32 px or more. Index numbers show only with `numbered: true`. A focus item with `word` enters on that word; with `steps`, it shows a small step echo whose steps `from`..`to` light up from `word` to `toWord`. |
| `statement` | `eyebrow?`, `lines: [text]`, `in: [word per line]`, `em?: {text, word}`, `size?` | Type as the picture: one short claim set large in the display face, line by line on its words. `em.text` (inside one line) turns accent and gets an underline drawn on `em.word`. Keep it to 2-3 lines of 4 words or fewer. |
| `compare` | `eyebrow`, `title`, `left: {label, items, word, color?}`, `right: {label, items, word, color?}`, `strike?: {items, word}`, `links?: [{from, to, word}]` | The old way beside the new. The left items enter on `left.word`; the right panel wipes in on `right.word`. `strike` crosses out left items (by index); `links` draws a curve from a left item to what it became on the right. 6 items a side at most, 5 words each. An item may be `{text, color}` when one side holds two roles; a link takes its right item's colour. |
| `diagram` | `eyebrow`, `title`, `nodes: [{id, text, x, y, w?, h?, shape?, color?, word}]`, `edges: [{from, to, word, label?, dashed?, color?}]`, `focus?: {nodes, word, zoom?}` | A picture that draws itself. Nodes (`box` 300 x 96, `pill`, or `dot` with its text below) pop on their words; edges draw with an arrowhead on theirs (`dashed` for a return or an optional path). `x, y` are node centres in scene px (0-1920, 0-900). On `focus.word` the camera pushes into those nodes (`zoom` default 1.6), the rest dim and the heading leaves. |
| `layers` | `eyebrow`, `title`, `layers: [{text, sub?, color?, word}]`, `spread?`, `focus?: {index, word}` | Layers in depth (a system's tiers, a road's courses), top layer first, 5 at most. Each drops into place on its word; without `spread` they land apart, with it they land flat and separate on `spread`. `focus` lifts one layer and dims the rest. `spread` and `focus` words must follow the last layer word. Use it only when depth is the idea. |
| `ui` | `eyebrow?`, `title?`, `focus?`, `nth?`, `click?`, `text?`, `labels?` | The tour still for this beat. Give it an `eyebrow` and a `title` that name the screen and its point, so the claim
reads with the sound off; the still then fits below the heading. The camera zooms to the tour box and settles 0.3 s before `focus` (default: the word one third of the way in). If the tour has a `before` still, a cursor click lands before `click` (default: the 2nd word). `text: {x0, y0, x1, y1}` overrides the tour's text box, to crop on word boundaries. The box gets a soft dim around it and a thin accent outline (3 px, rounded, `.ring`), so it shows on dark stills too. Labels here use `at: [x, y]` in still pixels (only `x` places them) and default to the dark tag style: they sit in a strip below the still, with a leader up to the box. The ui fit includes that strip, so the still shrinks and the labels stay above the caption band in `full` mode. |

`eyebrow` is plain text, which CSS sets in mono caps. Keep a `title` to 8 words or fewer.

Fields every scene takes:

- `labels: [{text, word, x, y, align?, color?, kind?, until?}]`: key-word labels of 2-5 words beside an object, in scene pixels (1920 x 900). `color` tints a plain label's text, or a `tag` label's ground (a `ui` label is a tag). Each lands 0.3 s before `word` and leaves on `until`. They show in both caption modes.
- `hero: "<id>"`: consecutive beats with the same id share one element (`hero(b)`) in a layer above the scenes. The object transforms across the cut, and it leaves with the last beat that names it. `heroGroup(b)` is that layer, for props that stay on screen across those beats (`retype` puts its tool cards there, `relay.js` its lanes); `heroProps(b)` is a store that hands them to the next beat.

Layout and transitions (`index.html` assembly):

- Fit: each scene's body (everything except the heading) is scaled up (at most 1.3x) and centred in the free area below the heading: y 216 to 1024 in keywords mode (the whole frame, with a quiet bottom margin) or to 876 in full mode (above the caption band). Content wider than the area keeps its size. Beats that share a hero share one fit, so shared objects line up. ui scenes fit the whole frame with a 40 px margin.
- Fill: a scene that sets `root.dataset.fit = "fill"` (the `chips` grids; a custom module may too) is scaled up or down so that it spans `FILL_W` (80%) of the free width, or the free height if that is smaller, at most 2x, and centred in the free area. `FREE` (the free area's width and height) and `FILL_W` are globals, so a scene can pick a layout that keeps its smallest text at 32 px or more after the scale.
- Transitions: each beat's `in` picks how it replaces the one before, at the boundary. `calm`: the old scene exits (0.3 s, ease-in), then the new one enters (0.4 s, ease-out). `fade`: a 0.5 s crossfade. `cut`: a hard cut. `push`: the new scene pushes the old one off to the left (0.7 s). `zoom`: the camera flies through the old scene into the new one (0.6 s). `wipe`: the new scene wipes in from the left (0.6 s). Beats that share a hero keep it across any transition; give them `fade` or `calm`.
- Look: `build.py` writes `theme.css` from `direction.json` (`presets.json` holds the looks). Scenes read colours from the tokens (`C.ink`, `C.accent`, ...); the display face (`t-display`, `t-num`, `t-h1`, `t-h2`) and the body face come from the look. Never hard-code a colour in a scene.

Motion vocabulary (`index.html`): `ENTER` (0.05, 0.7, 0.1, 1) for entrances, `EXIT` (0.3, 0, 0.8, 0.15) for exits and `MOVE` (0.2, 0, 0, 1) for moves, from GSAP CustomEase. No linear, bounce or back easing, and no decorative 3D tilt (`layers` is the one 3D type, for a real depth idea).

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

- `index.html`: helpers (`el`, `svgEl`, `cue`, `wordAt`, `popIn`, `head`, `col`, `keyLabel`, `hero`, `heroGroup`, `heroProps`), the assembly (fit, transitions) and the captions.
- `ui.js`: the `ui` scene and the press ripple.
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
