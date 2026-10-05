# Teaser video (optional, only after the user says yes)

A 60-110 s narrated video for the first screen; when clarity and length conflict, clarity wins. It is an on-ramp, not a summary: it gives the viewer the frame (the
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
2. Plain words first (ELI5, full STE: sentences of 20 words or fewer, simple approved words). A definition does not
   fix jargon; replacing it does. So cut a term, or say it by what it does ("the company that maintains the road");
   keep at most 4-5 report names aloud, each glossed in the sentence that first uses it. Ids, serials and decision
   numbers stay off the voice ("one open question: should X sit inside Y?", not "decision 13").
3. At most one new name or number per sentence. A label shows the plain word first and the report's term second,
   once ("bill (claim)"), so the report still reads as a second look. Few numbers, each from the ledger.
4. One running example and one persistent object (the job, the request) from the first scene to the last.
5. A paired analogy if it maps, with one beat for where it breaks ("unlike a relay, the baton can go back").
6. State the reader's likely doubt and answer it once with evidence (a refutation, not a feature list).
7. The voice gives the "why"; the picture gives the detail. The voice never reads the screen aloud.
8. Pace 140-155 words a minute; the key claims are the slowest beats. Measure it from the word times.
9. Close on the report's route: which chapters to read to act, to check, to learn.

**Two gates before any voice:** `python3 scripts/teaser/jargon_check.py beats.json terms.txt` (seed `terms.txt` with
the report's glossary and its private meanings, such as claim, memo, pots; it must PASS: no sentence with 2+ new
names, 5 names at most, every sentence 20 words or fewer; `pip install wordfreq` adds a rare-word check). Then a
cold read: a fresh subagent gets only the captions and must say what each name is from the text alone, or "NOT
DEFINED". Fix every NOT DEFINED, then voice.

## Build

Everything is local and free: Kokoro-82M voice (Apache-2.0), Playwright stills, HyperFrames render (Apache-2.0),
ffmpeg. Work in `<report>/teaser/`; per report you write only data and, at the bespoke level, `custom` scene modules.

1. **Voice:** `python scripts/teaser/tts_beats.py <teaser dir>` writes one WAV per beat and `beats.timed.json`
   with word times, aligning caption words to spoken ones ("245" spans "two hundred and forty-five"). Run Whisper
   on the WAVs or listen once. Fix a misread name with an inline phoneme in `text`, using misaki's US set:
   `[Jalan](/ʤˈɑlɑn/)` (the caption keeps the plain word); respell only acronyms ("SQL" as
   "sequel"). Re-check the pace.
2. **Real screens** (`ui` beats only): write `tour.spec.json`: `base`, `login` (users file path and user, never a
   password), `start`, `allow_writes_to` (login and token refresh only), `zoom`, and per beat `do` (`top`, `click`
   a button's accessible name, `open` [button, text that must become visible], `scroll_to` a text) and `target`
   (the texts the voice names). Run
   `NODE_PATH=<node_modules with playwright> node scripts/teaser/record_tour.cjs tour.spec.json beats.timed.json shots`.
   It blocks every other write, waits for scrolling to stop, and saves 2x stills with block and text boxes. Draw
   each box on its still and look before you compose.
3. **Compose:** copy `assets/teaser/` to `<teaser>/hf/`, then `python3 build.py --beats ../beats.timed.json`
   (`--captions full` is the default: the narration burned into the reserved bottom band, which no scene uses, plus
   2-5 word labels beside objects from `scene.labels`; `keywords` shows the labels only). For bespoke scenes write a `custom` module and brief it as below.
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
- Embed it in the report itself: add the block below to the report's source right after the answer box, add one
  changelog line, and rebuild the page. Never make a separate preview page. The MP4 stays a sidecar file in
  `teaser/` (8-20 MB); never inline it. Captions are burned in, so the track stays off by default:

```html
<figure class="teaser"><video controls preload="none" playsinline poster="teaser/poster.jpg">
<source src="teaser/teaser.mp4" type="video/mp4">
<track kind="captions" src="teaser/teaser.vtt" srclang="en" label="English (also burned in)">
</video><figcaption>{{The takeaway, and how long the video runs}}</figcaption></figure>
```

After delivery, keep in `teaser/` only the sources (`beats.json`, `beats.timed.json`, `voice/`, `shots/`, `hf/`
without `renders/`, `qc/` and copied assets) and the three outputs (`teaser.mp4`, `teaser.vtt`, `poster.jpg`).
Delete render scratch and earlier cuts, so the docs folder does not grow.

## Rules learned the hard way

- Fix the data and the script before you compose: a fix round on a composed video re-reads a large context and
  can cost more than the first build.
- Measure boxes on the settled page; click by accessible name (a button's aria-label can differ from its text).
- A block wider than 65% of the screen is framed around its text, at about 1.15x the text width.
- One zoom per beat, landing 0.3 s before the anchor word, held to the end of the beat.
