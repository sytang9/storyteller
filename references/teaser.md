# Teaser video (optional, only after the user says yes)

A 60-90 s narrated video for the first screen. It shows what the page cannot: a mechanism in motion and the
real screens, timed to a voice. Stills of the page's own figures do not help; they only repeat the page.

## Suggest, ask, then build

1. After delivering the story, decide whether a teaser would explain faster than the page. Suggest it only when
   the story has a mechanism or flow that moves (a job passing between roles, a pipeline, a before/after), or a
   real app the reader must picture. Never for a short or simple report.
2. Name the 2-4 scenes you would show, and state the cost honestly: the first two builds took 4-9M tokens
   processed and 12-25 min of agent time (the render itself is under a minute). With the template, a report
   needs only data, so it should cost less; that is not measured yet. Ask whether to build it.
3. Build only on a yes. Otherwise stop; the page is complete without it.

## Build

Everything is local and free: Kokoro-82M voice (Apache-2.0), Playwright stills, HyperFrames render (Apache-2.0),
ffmpeg. Work in `<report>/teaser/`. The fixed parts live in this skill; per report you write only data.

1. **Beat sheet first** (`beats.json`). One beat per idea, 8-12 beats, 60-90 s. Each beat: `id`, `kind`
   (`motion` or `ui`), `caption` (what the viewer reads), `text` (what the voice says: numbers and acronyms
   spelled as spoken), and for motion beats a `scene` object (types in `assets/teaser/TEMPLATE.md`).
   - Plain words a newcomer understands: "one pothole repair on a named road", never an internal id like "job 4521".
   - Each beat names one thing the viewer sees at that moment. If the screen cannot show it, cut it.
   - Every number comes from the report's ledger.
2. **Voice:** `python scripts/teaser/tts_beats.py <teaser dir>` writes one WAV per beat and `beats.timed.json`
   with word times; a caption word that is spoken differently ("245") gets the span of its spoken words.
   Listen once, or run Whisper on the WAVs; respell a misread name in `text` (e.g. "SQL" as "sequel").
3. **Real screens** (only for `ui` beats): write `tour.spec.json`: `base`, `login` (users file path and user,
   never a password in the spec), `start` path, `allow_writes_to` (login and token refresh only), `zoom`, and per
   beat `do` (`top`, `click` a button name, `open` [button, text that must become visible], `scroll_to` a text)
   and `target` (the texts the voice names). Then
   `NODE_PATH=<node_modules with playwright> node scripts/teaser/record_tour.cjs tour.spec.json beats.timed.json shots`.
   It blocks every other write, waits for scrolling to stop, and saves 2x stills with the block and text boxes.
   Check one still per beat with its box drawn before you compose.
4. **Compose and render:** copy `assets/teaser/` to `<teaser>/hf/`. The voice step already left `voice/` and
   `beats.timed.json` in `<teaser>/` (the `scene` objects ride along from `beats.json`; put any `scene.data` file
   beside it). Scene types and fields are in `assets/teaser/TEMPLATE.md`. Then in `hf/`:
   `python3 build.py --beats ../beats.timed.json`, and `npx --yes hyperframes@0.8.126 check` (0 errors)
   and `render`, with `ffmpeg` and `ffprobe` on PATH (a `.bin/` of links is enough). Normalise to -16 LUFS with
   ffmpeg `loudnorm`. The render takes about 30 s for 75 s of video. GSAP loads from a CDN at render time.
5. **Check:** look at one frame per beat (a mid-zoom frame for `ui` beats): the named thing is visible and
   readable, nothing covers the captions, no private data shows (blur it in the still if it does).

## Embed

```html
<figure class="teaser"><video controls preload="none" playsinline poster="teaser/poster.jpg">
<source src="teaser/teaser.mp4" type="video/mp4">
<track kind="captions" src="teaser/teaser.vtt" srclang="en" label="English (also burned in)">
</video><figcaption>{{The takeaway, and how long the video runs}}</figcaption></figure>
```

Place it after the answer box. The MP4 stays a sidecar file (8-18 MB); never inline it. Captions are burned in, so
the track is off by default.

## Rules learned the hard way

- Fix the data before you compose: each fix round on a composed video re-reads a large context and costs more
  than the first build.
- Measure on the settled page: wait for scrolling to stop, or the boxes miss their target.
- A wide block (over 65% of the screen) is framed around its text, at about 1.15x the text width; otherwise
  the zoom barely moves.
- One zoom per beat, landing 0.3 s before the anchor word; hold it to the end of the beat.
