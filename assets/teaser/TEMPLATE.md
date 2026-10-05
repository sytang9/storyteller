# Teaser template: data contract and reuse

A HyperFrames composition that renders a narrated teaser from data. The code is generic. A report supplies only the files below.

## Files a report supplies

| File | Where | What |
| --- | --- | --- |
| `beats.timed.json` | next to `build.py` (or `--beats`) | ordered beats, with word times and one `scene` object each |
| `voice/<id>.wav` | `<src>/voice/` | one voice clip per beat |
| `shots/tour.json` + `shots/frames/*.png` | `<src>/shots/` | UI stills and boxes, for `ui` beats only |
| any JSON named by `scene.data` | next to the beats file | large scene data (for example `journey.json`) |

`<src>` defaults to the parent folder of this template.

### Beat (one array item in `beats.timed.json`)

- `id`: also the voice file name. `kind`: `"motion"` or `"ui"`. `caption`: the caption text. `dur`: the voice length in seconds.
- `caption_words`: `[{w, s, e}]`, with times relative to the voice start. Captions, the highlighted word and every word cue use these times.
- `scene`: `{type, ...fields}`, as described below. Every `word` field is a caption word, matched case-insensitively with punctuation removed. A word pair `[w, n]` picks the nth match. A visual change lands 0.3 s before its word. A missing word stops the build with an error.
- Colours are palette keys (`blue`, `teal`, `purple`, `orange`, `good`, `ink`, `mute`) or CSS colours.

### Scene types

| type | fields | what it shows |
| --- | --- | --- |
| `retype` | `eyebrow`, `title`, `source: {title, sub, word}`, `targets: [{name, color, word}]`, `tag` | A source sheet appears on `source.word`. A copy flies into each target card on that target's `word`, the card fills in, and `tag` pops. |
| `merge` | `eyebrow`, `title?`, `from: [{name, color}]`, `into`, `word`, `landWord`, `steps: [..]`, `tick: [w0, w1]` | The `from` cards (in the same place as in `retype`) fan into a 3D deck on `word`. On `landWord` the deck becomes one card named `into`. The steps tick green from `w0` to `w1`. |
| `lanes` | `eyebrow`, `title`, `lanes: [{id, name, color, word?}]`, `steps: [{id, name, w}]`, `stops: [[stepId, laneId]]`, `doneStep`, `counter: {label, word}` | A token walks the stops across swimlanes. Each lane pulses on its `word`. The counter counts lane changes (computed) and the last change lands on `counter.word`. The step widths `w` must sum to 1440 px or less (columns start at x 440, lanes end at 1880). |
| `counters` | `eyebrow`, `title`, `items: [{value, label, word, color, of?, ofWord?, chip?: {text, word}}]` | Up to 3 big numbers count up and land on their `word`. `of` adds "/ of" on `ofWord`, and `chip` pops on `chip.word`. |
| `chips` | `eyebrow`, `title` (`{n}` = the item count, in the accent colour), `items: [..]`, `cols`, `tag?`, `in: [w0, w1]`, `tagIn: [w0, w1]` | A grid of short labels (12 at most, each 5 words or fewer). The cards pop from `in[0]` to `in[1]`, and the tags pop from `tagIn[0]` to `tagIn[1]`. |
| `ui` | `focus?`, `nth?` | The tour still for this beat. The camera zooms to the tour box and settles 0.3 s before `focus` (default: the word one third of the way in). If the tour has a `before` still, a cursor click lands before the 2nd word. |

`eyebrow` is plain text, which CSS sets in mono caps. Keep a `title` to 8 words or fewer.

### `shots/tour.json`

`{beats: [{id, after, box: {x0, y0, x1, y1}, text?: {...}, size: [w, h], before?: {img, click: {x, y}}}]}`. Coordinates are still pixels (4K stills). `box` is the whole block to frame, and `text` is the text that the zoom centres on (it falls back to `box`). `scripts/teaser/record_tour.cjs` writes this file from a `tour.spec.json`.

## Build and render

```bash
cd <teaser>/hf
python3 build.py                      # options: --src .. --beats beats.timed.json --vtt teaser.vtt
python3 -m pytest -q test_build.py    # phrase splitter
export HYPERFRAMES_NO_TELEMETRY=1 PATH=$PWD/.bin:$PATH
npx --yes hyperframes@0.8.126 check   # needs 0 errors
npx --yes hyperframes@0.8.126 render --quality delivery --output renders/raw.mp4
.bin/ffmpeg -y -i renders/raw.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 192k ../teaser.mp4
.bin/ffmpeg -y -ss 11.8 -i ../teaser.mp4 -frames:v 1 -q:v 3 ../poster.jpg
```

`build.py` writes `data.js`, copies the voice clips and stills into `assets/`, stamps the root duration and the `<audio>` tags into `index.html`, and writes `<src>/<vtt>`. Timing: each beat starts 0.6 s after the previous voice ends. The voice starts 0.15 s into its beat. The video ends 1.2 s after the last voice clip. Scenes crossfade over 0.4 s.

## Code map (do not edit for a new report)

- `index.html`: helpers (`el`, `svgEl`, `cue`, `wordAt`, `popIn`, `head`, `col`), the `ui` scene, the press ripple, the assembly and the captions.
- `scenes.js`: one function for each motion type, registered in `window.SCENES`. To add a type, write `fn(root, beat)` that reads `beat.scene`, then register it.
- `style.css`: the type spec tokens (`t-display`, `t-num`, `t-h1`, `t-h2`, `t-body`, `t-label`, `t-eyebrow`), the bundled fonts and the layout.
- `assets/fonts/`: Inter and JetBrains Mono woff2 files (OFL, licences included). No network font is needed.

## Reuse for another report

1. Copy this folder to `<report>/teaser/hf/` (it ships with no report data).
2. Write the beat sheet and the voice clips. Get word times from the TTS or an aligner as `caption_words`.
3. Add a `scene` object to each beat. Pick a type from the table and use only words that the caption contains.
4. For `ui` beats, record the tour into `<src>/shots/`.
5. Run the build and render commands. Then look at one frame per beat (`ffmpeg -ss <t> -frames:v 1`) before you ship.
