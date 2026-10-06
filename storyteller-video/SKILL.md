---
name: storyteller-video
description: Builds a 60-110 s narrated explainer or teaser video for a finished storyteller report (or any brief) with a local Kokoro voice and a HyperFrames render, then embeds it in the report. Script first, then an art-direction pass (a look, a transition grammar, a metaphor per beat), scenes from a data-driven template, and a frame critic. Use when the user asks for a video, teaser, narrated explainer or animated walkthrough of a report, or says yes when the storyteller skill offers one. Not for the report page itself, live demos, or talking-head video. Token-heavy; build only on an explicit yes.
---

# Storyteller video

A narrated video that frames a report: the one thing it is about, its parts, how they move, and where to read next.
It is an on-ramp, not a summary. When clarity and length conflict, clarity wins. Everything runs locally and free:
Kokoro-82M voice (Apache-2.0), Playwright stills, HyperFrames (Apache-2.0) with GSAP, ffmpeg.

## Suggest, ask, then build

1. Suggest a video only when the story has a mechanism or flow that moves (a job passing between roles, a pipeline,
   a before/after), or a real app the reader must picture. Never for a short or simple report.
2. Name the 2-4 scenes you would show and offer two levels with their costs (the render itself is about 1 min):
   - **Template scenes**: 5-11M tokens processed, 15-30 min of agent time.
   - **Bespoke scenes** (custom modules for moments the types cannot show, one subagent each): 14-21M, about 30 min.
   These include the direction and critic steps; they are estimates from the last measured builds (4-9M and 19M).
3. Build only on a yes, at the level the user picks.

## Who does what

The main thread writes the script and the direction: they need the whole report in context and decide everything
after them. Fresh subagents do the work that needs a clean context, and hand off through files:

| Step | Who | Output |
| --- | --- | --- |
| 1. Script | main thread | `beats.json` (`references/script.md`); gates: `jargon_check.py`, then a cold-read subagent |
| 2. Direction | main thread | `direction.md` + `direction.json` (`references/direction.md`); gate: `check_variety.py` |
| 3. Voice | main thread | `voice/*.wav`, `beats.timed.json` (`scripts/tts_beats.py`); re-run `check_variety.py` |
| 4. Screens | main thread | `shots/` from `scripts/record_tour.cjs` (`ui` beats only, below) |
| 5. Bespoke scenes | one subagent per scene, in parallel | `<id>.js` custom module + its frames; packet: the beat, its word times, `direction.md`, the motion brief, `references/scenes.md` |
| 6. Compose and render | main thread | `teaser.mp4`, `teaser.vtt`, `poster.jpg` |
| 7. Critic | fresh subagent, frames only | `qc/sheet.png` from `scripts/qc_sheet.py`, then `qc/critic.json`; fix the 3 worst, two rounds at most (`references/critic.md`) |
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
export HYPERFRAMES_NO_TELEMETRY=1                      # ffmpeg and ffprobe on PATH
npx --yes hyperframes@0.8.126 check                    # 0 errors: render does not stop on a scene error, it ships a blank video
npx --yes hyperframes@0.8.126 render --quality delivery --output renders/raw.mp4
ffmpeg -y -i renders/raw.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 192k ../teaser.mp4
```

Full captions burn the narration into the bottom band, which no scene uses; `--captions keywords` shows only the
2-5 word labels. Scene types, fields, transitions and the layout rules: `references/scenes.md`. GSAP loads from a CDN
at render time. A draft render (`--quality draft`) of a 30 s cut takes about 20 s; use it for checks.

## Length

About 60-110 s. A video that runs long because each beat explains one idea is fine; one that runs long because beats
carry two ideas is not: split them.

## Rules learned the hard way

- Fix the data and the script before you compose: a fix round on a composed video re-reads a large context and
  can cost more than the first build.
- Measure boxes on the settled page; click by accessible name (a button's aria-label can differ from its text).
- A block wider than 65% of the screen is framed around its text, at about 1.15x the text width.
- One zoom per `ui` beat, landing 0.3 s before the anchor word, held to the end of the beat.
- An even tempo reads as monotone: the legacy-links cut ran 12 beats of 7-12 s with one cut type, and the viewer
  said every scene felt the same. `check_variety.py` now fails that sheet.
