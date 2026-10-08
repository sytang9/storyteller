# Critic, cold viewer, then embed

## Frames

`python3 scripts/qc_sheet.py <teaser dir>` takes one frame per beat 0.6 s before it hands over (the scene is fully
built and the next transition has not started) and writes `qc/<id>.png` and `qc/sheet.png`. Look at the sheet
yourself first: the named thing is visible and readable in a 640 px wide frame, and no private data shows (blur it
in the still).

`python3 scripts/frame_scan.py <video> hf/data.js` reads every frame and fails on a one-frame flash (a seek bug
that blanks frames reads as a strobe; a contact sheet cannot show it) and on a scene area left empty for over 0.5 s.
Run it on every render before the critic.

## The critic (a fresh subagent, frames only)

Run it after the scripts pass. Give it `qc/sheet.png`, the per-beat frames, `direction.md` and `beats.timed.json`,
and nothing from the build. It returns JSON, one object per failed item: beat id, item number, a one-line evidence
quote, the fix. Fix the 3 worst, re-render, and stop after two rounds.

| # | Item | Pass rule |
| --- | --- | --- |
| 1 | Anchor visible | The thing the voice names is on screen and readable in a 640 px wide frame |
| 2 | One focal point | A squint test puts the anchor first; no second competing focus |
| 3 | Motion = state change | Each moving item shows a change the voice names |
| 4 | Silent claim | With sound off, the headline and labels still state the claim |
| 5 | No screen reading | Labels are 2-5 words and do not repeat the voice sentence |
| 6 | Hero continuity | The persistent object transforms across cuts; it is not redrawn |
| 7 | Metaphor fit | The picture matches its row in the metaphor table; it is not a default card grid |
| 8 | Direction match | Palette, type, shapes and colour roles follow `direction.md` |
| 9 | Variety | On the sheet no 3 neighbours share one layout or one ground; one held beat exists; colour fills a large area on at least a third of the frames; at least 2 frames where the words are the picture |
| 10 | Bans | No item from the ban list appears |
| 11 | Defects | No overlap, clipping, off-frame text, or label over the text it names |

## Cold viewer (for a video that leaves the team)

A fresh subagent sees the frames only, states the claim and lists what confused it; then it reads the script. Fix
what it gets wrong.

## Embed

Embed the video in the report itself: add the block below to the report's source right after the answer box, add
one changelog line, rebuild the page, and run the storyteller skill's `check_layout.py` (a video without the
storyteller CSS scrolls the page sideways at its native 1920 px). Never make a separate preview page. The MP4 stays a
sidecar file in `teaser/` (8-20 MB); never inline it. Captions are burned in, so the track stays off by default:

```html
<figure class="teaser"><video controls preload="none" playsinline poster="teaser/poster.jpg">
<source src="teaser/teaser.mp4" type="video/mp4">
<track kind="captions" src="teaser/teaser.vtt" srclang="en" label="English (also burned in)">
</video><figcaption>{{The takeaway, and how long the video runs}}</figcaption></figure>
```

After delivery, keep in `teaser/` only the sources (`beats.json`, `beats.timed.json`, `direction.md`,
`direction.json`, `voice/`, `shots/`, `hf/` without `renders/`, `qc/` and copied assets) and the three outputs
(`teaser.mp4`, `teaser.vtt`, `poster.jpg`). Delete render scratch and earlier cuts, so the docs folder does not grow.
