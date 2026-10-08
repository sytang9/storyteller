---
name: storyteller-video
description: Builds a 60-110 s narrated explainer or teaser video for a finished storyteller report or brief, with a local Kokoro voice and a HyperFrames render, then embeds it in the report. Use when the user asks for a video, teaser or narrated walkthrough of a report, or says yes when storyteller offers one. Token-heavy; build only on an explicit yes.
---

# Storyteller video

A narrated video that frames a report: the one thing it is about, its parts, how they move, and where to read next.
It is an on-ramp, not a summary. When clarity and length conflict, clarity wins. Everything runs locally and free:
Kokoro-82M voice (Apache-2.0), Playwright stills, HyperFrames (Apache-2.0) with GSAP, ffmpeg.

## Suggest, ask, then build

1. Suggest a video only when the story has a mechanism or flow that moves (a job passing between roles, a pipeline,
   a before/after), or a real app the reader must picture. Never for a short or simple report.
2. Name the 2-4 scenes you would show and offer two levels with their costs (the render itself is about 1 min):
   - **Template scenes**: 5-12M tokens processed, 15-30 min. Clear, but it looks like a template.
   - **Bespoke scenes** (a custom scene per beat, one designer subagent each, a critic and one fix round): about
     55-60M tokens processed and 60-70 min. This is the level that looks made by a motion designer.
3. Build only on a yes, at the level the user picks.

## Who does what

The main thread writes the script and the direction: they need the whole report in context and decide everything
after them. Fresh subagents do the work that needs a clean context, and hand off through files:

| Step | Who | Output |
| --- | --- | --- |
| 1. Script | main thread | `beats.json` (`references/script.md`); gates: `jargon_check.py`, then a cold-read subagent |
| 2. Direction | main thread | `direction.md` + `direction.json` with 3-4 grounds, 2 type beats and a break (`references/direction.md`); gate: `check_variety.py` |
| 3. Voice | main thread | `voice/*.wav`, `beats.timed.json` (`scripts/tts_beats.py`) |
| 3b. Events | main thread | `scene.events` on each beat, so no beat sits still for 3 s (`references/scenes.md`, Events); re-run `check_variety.py` on `beats.timed.json` |
| 4. Screens | main thread | `shots/` from `scripts/record_tour.cjs` (`ui` beats only, below) |
| 4b. Media | main thread | `media.json` from the metaphor table, then `scripts/fetch_assets.py`: open-licence icons, and a photo only where the real object is the point (`references/media.md`); look at every photo |
| 5. Bespoke scenes | briefs by the main thread, then one subagent per scene, in parallel, each in its own sandbox (`references/scene-worker.md`, `scripts/scene_sandbox.py`) | `<id>.js` custom module + its frames; packet: the beat, its word times, `direction.md`, `references/motion-craft.md` (the pro motion rules and `assets/hf/examples/craft-example.js`), `references/scenes.md`, the media ids |
| 6. Compose and render | main thread | `teaser.mp4`, `teaser.vtt`, `poster.jpg`; gate: `scripts/frame_scan.py` (no strobe, no empty frames) |
| 7. Critic | fresh subagent, frames only; then a fresh fixer per flagged scene (`references/scene-worker.md`) | `qc/sheet.png` from `scripts/qc_sheet.py`, then `qc/critic.json`; fix the 3 worst, two rounds at most (`references/critic.md`) |
| 8. Embed | main thread | the report rebuilt with the video in it (`references/critic.md`) |

Do not add roles beyond these: script, direction and scene design depend on each other, and agents that split them
make conflicting choices. Do not use Blender, Remotion or a paid API; the template covers 3D (`layers`) and the
HyperFrames catalog covers the rest.

## Screens (`ui` beats)

Write `tour.spec.json`: `base`, `login` (users file path and user, never a password), `start`, `allow_writes_to`
(login and token refresh only), `zoom`, and per beat `do` (`top`, `click` a button's accessible name, `open` [button,
text that must become visible], `scroll_to` a text) and `target` (the texts the voice names). Run
`NODE_PATH=<node_modules with playwright> node scripts/record_tour.cjs tour.spec.json beats.timed.json shots`. It
blocks every other write, waits for scrolling to stop, and saves 2x stills with block and text boxes. Draw each box
on its still and look before you compose. Never log in to a live production system; use a test stack.

## Compose and render

```bash
cp -r <skill>/assets/hf <teaser>/hf && cd <teaser>/hf
python3 build.py --beats ../beats.timed.json          # reads ../direction.json; --captions full is the default
python3 -m pytest -q test_build.py
export HYPERFRAMES_NO_TELEMETRY=1 PATH=$PWD/.bin:$PATH  # hf/.bin: symlinks to ffmpeg + ffprobe when not on PATH
npx --yes hyperframes@0.8.126 check                    # 0 errors: render does not stop on a scene error, it ships a blank video
npx --yes hyperframes@0.8.126 render --quality delivery --output renders/raw.mp4
ffmpeg -y -i renders/raw.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 192k ../teaser.mp4
```

Full captions overlay the narration on the bottom of each scene, over a soft fade in that beat's ground: the
ground runs to the frame edge and moves with its transition, and scene content stays above y 876.
`--captions keywords` shows only the 2-5 word labels. Keep full captions for any video that may play on mute:
keyword-only captions lose much of the argument. Scene types, fields, transitions and the layout rules: `references/scenes.md`. GSAP loads from a CDN
at render time. A draft render (`--quality draft`) of a 30 s cut takes about 20 s; use it for checks.

## Length

About 60-110 s. A video that runs long because each beat explains one idea is fine; one that runs long because beats
carry two ideas is not: split them.

## Rules

- Fix the data and the script before you compose: a fix round on a composed video re-reads a large context and
  can cost more than the first build.
- Measure boxes on the settled page; click by accessible name (a button's aria-label can differ from its text).
- A block wider than 65% of the screen is framed around its text, at about 1.15x the text width.
- One zoom per `ui` beat, landing 0.3 s before the anchor word, held to the end of the beat.
- An even tempo reads as monotone: `check_variety.py` fails a sheet whose longest beat is under 2x the shortest,
  or whose cuts use one transition kind.
