# Script: the on-ramp beat sheet

Write `beats.json` before any visual: 9-14 beats, one idea each. Each beat: `id`, `kind` (`motion` or `ui`),
`caption` (on-screen words), `text` (spoken: numbers and acronyms spelled as said), `speed` (Kokoro, about 0.9-1.0; 0.9 for the key claims),
optional `hold` and `in` (`references/direction.md`), and a `scene` object (`references/scenes.md`). The video is an
on-ramp, not a summary: it gives the viewer the frame (the one thing the report is about, its parts, how they move)
and the route into the report.

## The checklist

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
8. Vary the tempo by the idea, not by a clock: a 3-5 s beat for a punch line or a list item (let a `statement`
   scene carry the words on screen and keep the voice line to one short sentence), an 8-12 s beat for a mechanism, and one held beat (1.2-2.5 s of silence) after the key picture. Pace 140-155 words a minute overall;
   the key claims are the slowest beats. Measure it from the word times.
9. Close on the report's route: which chapters to read to act, to check, to learn.

## Two gates before any voice

1. `python3 scripts/jargon_check.py beats.json terms.txt`: seed `terms.txt` with the report's glossary and its private
   meanings (claim, memo, pots). It must PASS: no sentence with 2+ new names, 5 names at most, every sentence 20 words
   or fewer. Install `wordfreq` first (`pip install wordfreq`): without it only acronyms and `terms.txt` words are
   flagged.
2. A cold read: a fresh subagent gets only the captions and must say what each name is from the text alone, or "NOT
   DEFINED". Fix every NOT DEFINED, then voice.

`scripts/check_variety.py beats.json direction.json` runs after the direction step (it needs the scene types).

## Voice

`python scripts/tts_beats.py <teaser dir>` writes one WAV per beat and `beats.timed.json` with word times, aligning
caption words to spoken ones ("245" spans "two hundred and forty-five"). It needs Python 3.10-3.12 with
`kokoro>=0.9.4` and `soundfile`. Check the reading: run Whisper on the WAVs, or listen once,
or at least read each beat's `spoken_words` in `beats.timed.json` for numbers and names said wrong. Fix
a misread name with an inline phoneme in `text`, using misaki's US set: `[Jalan](/ʤˈɑlɑn/)` (the caption keeps the
plain word); respell only acronyms ("SQL" as "sequel"). Re-check the pace and re-run `check_variety.py` on
`beats.timed.json` (the measured lengths replace the estimate).

Fix the script and the data before you compose: a fix round on a composed video re-reads a large context and can
cost more than the first build.
