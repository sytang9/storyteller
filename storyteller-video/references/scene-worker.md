# Scene worker: the packet for one bespoke scene

At the bespoke level, the main thread writes one brief per custom beat, then runs one fresh subagent per scene
in parallel. Each works in its own one-beat sandbox and returns a file path. The main thread merges, assembles,
renders and runs the critic. A fix round sends each flagged scene to a fresh fixer with the critic's items.

## The brief (`briefs/<id>.json`, written by the main thread)

`{id, module, message, duration, voice, transition_in, anchor_words: [{word, t, change}], composition, world_in,
world_out, media, colours, type, must_not}`. Times are seconds from the beat start (from `beats.timed.json`).
Every brief has a change every 1.5-3 s of voice and at least one big state change. `direction.md` gets a "world"
section (the one shared set, its coordinates and colours) so parallel scenes look like one film. Copy each
brief's change words into the beat's `scene.cues`, so `check_variety.py` sees them.

## Sandboxes and the merge

```bash
python3 <skill>/scripts/scene_sandbox.py make <teaser> <dir with ffmpeg, ffprobe> b01 b02 ...
# ... scene workers run in parallel ...
python3 <skill>/scripts/scene_sandbox.py merge <teaser>      # their scene fields -> beats.timed.json
```

## The worker prompt (give it to each subagent with <teaser>, <skill>, <id>, <sandbox>)

You design and code ONE bespoke scene for a narrated explainer video. It must look like a professional motion
designer made it, not a beginner: big compositions that fill the frame, choreographed motion (lead and followers,
overlap, a different entrance for each role), real state changes timed to the voice, and type with scale contrast.
Parallel designers build the other scenes. Your scene must fit their shared world (direction.md "world" section).

Read first, in this order:
1. Your brief: <teaser>/briefs/<id>.json. It is the contract: the message, the anchor words with times, the composition,
   world_in/world_out, the media, the colours, the type and must_not.
2. <teaser>/direction.md (the look, colour roles, the world, the transition grammar, bans) and <teaser>/direction.json.
3. The skill: <skill>/references/motion-craft.md (the pro rules) and <skill>/assets/hf/examples/craft-example.js
   (a worked example). Then <skill>/references/scenes.md: the custom scene contract, helpers, events and the layout/fit
   rules. Then <skill>/references/media.md (iconEl, imageEl).
4. The helpers you may use, in <sandbox>/hf/index.html, motion.js, media.js and events.js: el, svgEl, tl, C, col,
   cue, wordAt, popIn, reveal, drawLine, head, keyLabel, hero/heroGroup/heroProps, iconEl, imageEl, and the eases
   ENTER, EXIT and MOVE. Read the code; do not guess signatures.

Write your module as <teaser>/<id>.js. It registers window.SCENES["<id>.js"] = function (root, b) {...}, which reads
b.scene (the fields already in your beat in beats.timed.json; you may add fields to YOUR beat's scene in the
sandbox beats file, and must list them in your status). Seek-safe rules: every tween on the shared `tl`; no
Date.now, Math.random or rAF; tween only transforms, opacity and clip-path (no width, height, left or top tweens);
the finished set (ground, shared world, heading, actors already known) is on screen from frame 1, never empty
placeholders, and each cue-bound thing arrives whole on its anchor word (motion-craft.md section 1); a change every 1.5-3 s of voice; your labels and kickers are gone by the
beat's end. If a morph is in world_in/world_out, the
named text must exist as a plain text element (the template's morph finds it by text).

Test in your sandbox <teaser>/work/<id>/ (a one-beat build of the template, with your voice, the media and the map
frames already linked):
- cp <teaser>/<id>.js <sandbox>/<id>.js (the custom module sits next to the beats file)
- cd <sandbox>/hf && export HYPERFRAMES_NO_TELEMETRY=1 PATH=$PWD/.bin:$PATH
- python3 build.py --beats ../beats.timed.json
- npx --yes hyperframes@0.8.126 check   (0 errors; fix warnings that are yours)
- npx --yes hyperframes@0.8.126 render --quality draft --output renders/draft.mp4
- take frames at the beat start + 0.1, 0.5 and 1.0 s, at each anchor word + 0.6 s and at the end: ffmpeg -ss <t> -i renders/draft.mp4 -frames:v 1 -vf scale=960:-1 ../qc/<t>.png
- LOOK at every frame. Fix overlap, clipping, off-frame text, unreadable sizes, anything that looks generic or
  static, anything that breaks must_not. Iterate until it is good. Run motion-craft.md's beginner-vs-pro checklist
  on your own scene, and fix what fails.
Edit only <teaser>/<id>.js and files inside your sandbox. Never edit the skill or another scene's files.

When done, write <sandbox>/status.json: {"status": "DONE"|"DONE_WITH_CONCERNS"|"BLOCKED", "module": "<teaser>/<id>.js",
"scene_fields_added": {...}, "frames": [paths], "checklist": "which pro rules you applied", "concerns": [...]}.
Return one line: the status.json path.

## The fix prompt (a fresh fixer per flagged scene, with that scene's critic items)

A critic watched the assembled film and scored it 5/10 pro, 6/10 clarity. The system (one road world, colour roles,
colour-field cut, km axis) is good; execution reads beginner: beats open on empty frames, seams overlap, number
rolls glitch. The single change it asked for: build each beat's set so every incoming transition lands on a
composed frame (road, actors, heading, empty slots in place from frame 1); only the change animates on its word.

Read <skill>/references/motion-craft.md section 1 ("Set, then change") and the checklist (section 9), your brief
<teaser>/briefs/<id>.json, <teaser>/direction.md, and your current module <teaser>/<id>.js. Your critic items are below.
Fix them and anything else section 1 or the checklist flags in your scene.

Rules: edit only <teaser>/<id>.js and your sandbox <teaser>/work/<id>/ (its beats.timed.json holds your scene fields;
change fields there if needed and list them). Keep the voice, timing, colours and the brief's message. Labels
and kickers of your scene must be gone by your beat's end (the next beat may push or wipe in over you).
Test exactly as in <teaser>/work/WORKER.md (cp module into sandbox, build.py, hyperframes check 0 errors, draft render,
frames at the beat start +0.1, +0.5, +1.0 s, at each anchor word +0.6 s and at the end; LOOK at them).
Write <sandbox>/status_fix1.json {"status", "fixed": [...], "fields_changed": {...}, "frames": [...],
"concerns": [...]} and return one line with its path.
