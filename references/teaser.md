# Teaser video (optional, only after the user says yes)

A 60-95 s narrated video for the first screen. It is an on-ramp, not a summary: it gives the viewer the frame (the
one thing the report is about, its parts, how they move) and the route into the report. Stills of the page's own
figures do not help; they only repeat the page.

## Suggest, ask, then build

1. After delivering the story, decide whether a teaser would explain faster than the page. Suggest it only when
   the story has a mechanism or flow that moves (a job passing between roles, a pipeline, a before/after), or a
   real app the reader must picture. Never for a short or simple report.
2. Name the 2-4 scenes you would show and offer two levels, with measured costs (the render itself is about 1 min):
   - **Template scenes** (the fixed scene types): 4-9M tokens processed, 12-25 min of agent time.
   - **Bespoke scenes** (custom motion for the moments the types cannot show): about 19M tokens, 50 min.
3. Build only on a yes, at the level the user picks. Otherwise stop; the page is complete without it.

## Script first: the on-ramp checklist

Write `beats.json` before any visual: 9-12 beats, one idea each. Each beat: `id`, `kind` (`motion` or `ui`),
`caption` (on-screen words), `text` (spoken: numbers and acronyms spelled as said), `speed` (Kokoro, about 0.7-0.85),
and a `scene` object (types and fields in `assets/teaser/TEMPLATE.md`).

1. Sentence one states a concrete stake in the viewer's words. The claim ("what is new, in one sentence") lands by beat 2.
2. At most 7 new names, each with one meaning, the same word in voice, labels, charts and the report. Define a name
   before it carries a claim. Plain words for ids: "one pothole repair on a named road", never "job 4521".
3. At most one new name or number per sentence, and few numbers overall, each from the ledger with its baseline.
4. One running example and one persistent object (the job, the request) from the first scene to the last.
5. A paired analogy if it maps, with one beat for where it breaks ("unlike a relay, the baton can go back").
6. State the reader's likely doubt and answer it once with evidence (a refutation, not a feature list).
7. The voice gives the "why"; the picture gives the detail. The voice never reads the screen aloud.
8. Pace 140-155 words a minute; the key claims are the slowest beats. Measure it from the word times.
9. Close on the report's route: which chapters to read to act, to check, to learn.

## Build

Everything is local and free: Kokoro-82M voice (Apache-2.0), Playwright stills, HyperFrames render (Apache-2.0),
ffmpeg. Work in `<report>/teaser/`; per report you write only data and, at the bespoke level, `custom` scene modules.

1. **Voice:** `python scripts/teaser/tts_beats.py <teaser dir>` writes one WAV per beat and `beats.timed.json`
   with word times, aligning caption words to spoken ones ("245" spans "two hundred and forty-five"). Run Whisper
   on the WAVs or listen once; respell a misread name in `text` (e.g. "SQL" as "sequel"). Re-check the pace.
2. **Real screens** (`ui` beats only): write `tour.spec.json`: `base`, `login` (users file path and user, never a
   password), `start`, `allow_writes_to` (login and token refresh only), `zoom`, and per beat `do` (`top`, `click`
   a button's accessible name, `open` [button, text that must become visible], `scroll_to` a text) and `target`
   (the texts the voice names). Run
   `NODE_PATH=<node_modules with playwright> node scripts/teaser/record_tour.cjs tour.spec.json beats.timed.json shots`.
   It blocks every other write, waits for scrolling to stop, and saves 2x stills with block and text boxes. Draw
   each box on its still and look before you compose.
3. **Compose:** copy `assets/teaser/` to `<teaser>/hf/`, then `python3 build.py --beats ../beats.timed.json`
   (`--captions keywords` is the default: 2-5 word labels beside objects, from `scene.labels`; `full` burns the
   whole narration). For bespoke scenes write a `custom` module and brief it as below.
4. **Render:** `npx --yes hyperframes@0.8.126 check` (0 errors) and `render`, with `ffmpeg` and `ffprobe` on PATH,
   then ffmpeg `loudnorm` to -16 LUFS. GSAP loads from a CDN at render time.

## Motion brief (for any scene you or a subagent design)

- Per scene: the one-sentence message, the anchor words, and the one change of state each motion shows.
- One focal point; one mover at a time; the persistent object transforms instead of cutting. Scenes with text
  exit (0.3 s, ease-in) before the next enters (0.4 s, ease-out); no cross-dissolve of two texts.
- Land each motion 0.2-0.3 s before its word; hold the resolved frame about 0.8 s. Use the whole frame.
- Ban by name: ambient drift, glow, glass, gradients, particles, bounce, linear easing, everything fading in at once,
  three readouts at once, labels over the text they name, jargon on decorative items. Your first draft will
  repeat your own default styles: check it against this list and fix before you show it.

## Check, then embed

- One frame per beat, taken after its last anchor word (an earlier frame shows a half-built scene): the named thing
  is visible and readable at 360 px wide, and no private data shows (blur it in the still).
- Cold-viewer test for a teaser that leaves the team: a fresh subagent sees those frames only, states the claim and
  lists what confused it; then it reads the script. Fix what it gets wrong.
- Embed after the answer box. The MP4 stays a sidecar file (8-20 MB); never inline it. The track is the toggle:

```html
<figure class="teaser"><video controls preload="none" playsinline poster="teaser/poster.jpg">
<source src="teaser/teaser.mp4" type="video/mp4">
<track kind="captions" src="teaser/teaser.vtt" srclang="en" label="English">
</video><figcaption>{{The takeaway, and how long the video runs}}</figcaption></figure>
```

## Rules learned the hard way

- Fix the data and the script before you compose: a fix round on a composed video re-reads a large context and
  can cost more than the first build.
- Measure boxes on the settled page; click by accessible name (a button's aria-label can differ from its text).
- A block wider than 65% of the screen is framed around its text, at about 1.15x the text width.
- One zoom per beat, landing 0.3 s before the anchor word, held to the end of the beat.
