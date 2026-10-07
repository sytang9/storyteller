# Direction: one look, one grammar, one metaphor per beat

Videos made with no direction step drift to the model's default look: one palette, one card grid, one even tempo,
the same cut every time. The direction step fixes the choices once, after the script is locked and before any scene
exists. Write two files in the teaser folder:

- `direction.md` (60 lines at most): the page every scene worker and the critic read.
- `direction.json`: what `build.py` reads: `{"look": "<preset>", "override": {token: value}?, "transition": "<primary>", "hold": 0.35}`.

## direction.md

1. **Look**: one preset from the table below, and why it fits the topic and the reader. Override single tokens only
   when the report has its own colours (a client brand, a road map's legend). Never mix two looks in one video.
2. **Colour roles**: 3-5 roles, each a fixed meaning for the whole video ("orange = money owed", "teal = the
   contractor"). A colour that changes meaning between beats breaks the code the viewer just learned. The template
   also uses `good` on its own for "done": the `counters` chip, the `stepper` and `merge` ticks, and the `lanes` done
   step and counter. If `good` already means something else in your roles, override it in `direction.json`.
3. **Metaphor table**: one row per beat: the claim | what stands for what ("the bill is a dot that travels back") |
   the scene type | why not the default (`chips` or `counters` need a reason). The picture must carry the mechanism;
   a picture that is only decoration (a joke, an icon wall) costs recall.
4. **Rhythm map**: the beat lengths in seconds, the held beat (1.2-2.5 s) after the key picture, one fast run (2-3
   short beats) for a list or a sequence, and the longest beats on the mechanism.
5. **Transition grammar**: one primary kind for most cuts, one or two accents with a reason each (below).
   **Event voice**: the primary event kind and two accents for this look (below).
6. **Bans**: the standing list below, plus the defaults you see in your own first draft.

## Looks (`assets/hf/presets.json`)

| look | ground | display face | use for |
| --- | --- | --- | --- |
| `paper` | off-white, blue accent | Inter | neutral technical work; the safe default |
| `editorial` | warm cream, rust accent | Fraunces (serif) | a story about people, process, a decision |
| `poster` | cream, red accent, square corners | Bebas Neue (caps) | one big claim, a launch, a warning |
| `night` | near-black, amber accent | Space Grotesk | systems, data, pipelines |
| `forest` | pale sage, green accent | Source Serif 4 | field work, roads, places |
| `blueprint` | cobalt, yellow accent | IBM Plex Sans | engineering plans, how a system is built |

Every look keeps body text and captions at 4.5:1 or more, and role colours at 3:1 (`test_build.py` checks it).
Over a `ui` screenshot the theme does not apply; the still keeps its own colours.

## Transition grammar

| kind | says | use for |
| --- | --- | --- |
| `fade` | "and, in the same breath" | the default primary for a calm explainer |
| `cut` | "next item" | list items and a fast run; a hard cut on a beat of the voice |
| `push` | "the story moves on" | the next step in a sequence; a second primary for a process story |
| `zoom` | "now look inside" | a new chapter, or going from the whole to one part |
| `wipe` | "here is the other side" | before/after, or the answer after the question |
| `calm` | "pause" | between two unrelated topics; after the held beat |

The primary carries at least half the cuts. Use `zoom` at most twice. Beats that share a hero keep it across any
cut; give them `fade` or `calm`.

## Change rate and the event voice

A beat that builds its picture and then sits still reads as a slide. Aim for a change every 1.5-3 s of voice
(4-6 in a 9 s explain beat, 2-3 in a statement, none in the held beat), and add them in this order:

1. **Spread the scene's own reveals** across the voice: give `compare` items, diagram nodes and edges, and counters
   their own words, so the picture builds as it is explained instead of arriving at once.
2. **Change the state** where the idea changes: `swap` (old to new), `strike` with `to`, `number`, a `push` into the
   part the voice turns to.
3. **Change the size**: `lift` the key word out of the captions, or a `hero` word, at least 3 times a video. This is
   what makes the type itself move; a video of same-size labels feels flat however busy it is. Lift a word that is
   not on screen yet (a statement already shows its words large), and lift on the word the lifted text starts with.
4. **Annotate last**: `note` and `mark` support the other changes; at most 2 a beat. Annotations alone make a video
   busier, not more varied.

Each event must say what it shows; one that only fills a gap does not belong. Give each video one primary kind and
two accents, keyed to the look, and cap any one kind (except `push`) at 40% of the events; when the primary is `lift`
or `hero`, the two count together and may reach 60%:

| look | primary | accents | avoid |
| --- | --- | --- | --- |
| `paper` | `lift` | `mark` sweep, `number` | `hero` above 2x the heading size |
| `editorial` | `strike` with `to` | `lift`, `note` | italic accent words |
| `poster` | `hero` | `swap`, `lift` | long lists |
| `night` | `number` | `push`, `lift` | `hero` above 2.5x |
| `forest` | `lift` | `push`, `mark` sweep | rapid `swap` runs |
| `blueprint` | `note` | `lift`, `mark` circle | decorative type effects |

Name the primary and accents in `direction.md`.

## Variety budget (`scripts/check_variety.py`)

No 3 neighbouring beats with one scene type; no motion type on more than 25% of the beats; the longest beat at
least 2x the shortest, with one held beat; 2 or more transition kinds with one primary; a look named. Run it on
`beats.json` after this step and on `beats.timed.json` after the voice, where it also fails a beat with more than
3.0 s of voice and no change on screen. It must PASS before any compose.

## Motion brief (for any scene you or a subagent design)

- Per scene: the one-sentence message, the anchor words, and the one change of state each motion shows.
- One focal point; one mover at a time; the persistent object transforms instead of cutting. A visual change lands
  0.2-0.3 s before its word; hold the resolved frame about 0.8 s. Use the whole frame.
- Reveal on the voice cue, mostly in the second half of a scene; stillness beats aimless motion.
- Ban by name: ambient drift, glow, glass, particles, bounce, linear easing, text gradients, purple-blue AI gradients,
  decorative 3D tilt, everything fading in at once, three readouts at once, labels over the text they name, jargon on
  decorative items, flashing emphasis (emphasise by size or colour). Your first draft will repeat your own default
  styles: check it against this list and fix before you show it.
