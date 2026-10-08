# Direction: one look, one grammar, one metaphor per beat

The direction step fixes the choices once, after the script is locked and before any scene
exists. Write two files in the teaser folder:

- `direction.md` (60 lines at most): the page every scene worker and the critic read.
- `direction.json`: what `build.py` reads: `{"look": "<preset>", "override": {token: value}?, "transition": "<primary>", "hold": 0.35, "end"?: {title, sub?, dur?}}`.

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

## Text: size, colour, emphasis, figures

- Every label is 28 px or more at 1080p and keeps 4.5:1 against what is behind it; a label over a road, a map or a
  photo gets its own ground. Kickers use the body face in tracked caps, not a second type voice.
- Step text back by colour, not opacity: to push a label into the background, fade the shapes around it and turn
  the text from ink to mute; a dimmed figure stops at 0.8. `hyperframes check` reads each text's own colour and
  ignores the opacity of its parents, so text faded to 0.4-0.5 passes the check while it measures about 2-4:1.
- Emphasis is a block, not a colour: `statement` em (default `style: "block"`) wipes a block in the look's `--em`
  colour (default ink) behind the word and turns the word to the ground colour. It stands out on dark and light
  looks and borrows no role colour. A custom scene that emphasises a word does the same. A thin underline or a
  colour change alone reads as faint.
- Figures: if the display face's digits are hard to read (a flagged "1" reads as "i"), set `"num"` in the look
  (`night` uses Inter). The display face then takes its digits from it everywhere, with no scene code. Numbers in
  custom scenes use the `t-num` or `t-display` class, never a hard-coded font.
- End card: `direction.json` `"end": {"title": "<report name>", "sub": "<where to find it>", "dur"?: 3}` adds a
  card after the last voice. Use it for any video that leaves the report page.

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
3.0 s of voice and no change on screen. It also needs 3 grounds, 2 type beats and, past 60 s, one break (below).
It must PASS before any compose.

## Grounds, type beats and breaks

One look sets the faces and the colour roles; the ground under each beat may change. A video on one ground for its
whole length reads as one long slide.
- **Grounds**: `direction.json` `"grounds": {"<name>": {bg, ink, mute, surface?, line?, em?, pattern?}}`, and each
  beat names one in `scene.ground` (none = the look's own). Plan 3-4 per video: the look's ground, its light or dark
  opposite, a full-bleed field in one role colour (the role then means "this beat is about <role>"; use a lighter or darker shade of the role, not its exact hex, so a thin mark in that role on the next beat does not read as a leftover of the field), and a pattern
  (`dots`, `grid`, `stripes`). Change ground per act, or to mark a turn in the argument; never 3 beats in a row on one.
  `build.py` fails a ground whose ink or mute is under 4.5:1 on its bg.
- **Type beats** (`scene.type_beat: true`, at least 2): the words are the picture. One to three words fill the frame
  width (sliced, stacked, built from shapes or particles, rolled), on a field or pattern ground, with no diagram.
  Put them on the claim the viewer must remember and on the turn ("Same roads?").
- **Breaks** (`"kind": "break"`, `"dur"` 0.5-3.0 s, no caption): a silent graphic beat between acts (a shape that
  morphs, a pattern that wipes, the next act's word). Any video over 60 s has one.

## Motion brief (for any scene you or a subagent design)

- Per scene: the one-sentence message, the anchor words, and the one change of state each motion shows.
- One focal point; one mover at a time; the persistent object transforms instead of cutting. A visual change lands
  0.2-0.3 s before its word; hold the resolved frame about 0.8 s. Use the whole frame.
- Reveal on the voice cue, mostly in the second half of a scene; stillness beats aimless motion.
- Ban by name: ambient drift, glow, glass, particles, bounce, linear easing, text gradients, purple-blue AI gradients,
  decorative 3D tilt, everything fading in at once, three readouts at once, labels over the text they name, jargon on
  decorative items, flashing emphasis (emphasise by size or colour). Your first draft will repeat your own default
  styles: check it against this list and fix before you show it.
