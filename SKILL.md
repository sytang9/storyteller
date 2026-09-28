---
name: storyteller
description: The default for every report a person reads. Turns any technical work (experiment results, an investigation, a system study, a proposal, a project status, a client write-up, or an existing report that grew bloated) into one self-contained, illustrated, plain-language HTML story that a reader with zero background can follow end to end, while keeping every key number, caveat and decision. Use whenever the user asks for a report, a write-up, a summary page, a storybook, an eli5 or "5-year-old" version, "make this readable", "explain this to my boss / a non-expert", or names /html-report with /eli5 or /diagram-design. Not for pages another tool generates (system-book, PR review reports, live dashboards), fiction, marketing copy, or Storybook.js UI component stories.
---

# Storyteller

People read about a quarter of a page and hold three to five sentences at a time. So the figure
explains, words carry the takeaway and the number, the page answers first, and where paper cannot,
the reader steps through a change or tries it. Because the answer comes first, the story trades
suspense for curiosity: the reader knows the result and reads on to see how we know.

## Fixed frame, free story

Copy `assets/template.md`. The frame is the same every time, in this order:

1. **The answer** (first screen, required): 1–2 sentences (question, answer, decision needed), a drawn overview figure naming each chapter's part in the chapters' own words, and a **TL;DR row** of 3 cards (label, key number vs baseline, at most 20 words; label choices in the template). The build adds the chapter menu below.
2. **The story**: free. See below.
3. **What we're not sure about**: every caveat and unverified claim, one line each.
4. **What's next**: one step, its owner and date. If the source names none, write "not yet set"; never invent one.
5. **Appendix** (collapsed): every number, all findings, full glossary, changelog.

**The story** takes whatever shape fits the material. Pick one and keep a single running example
or analogy from start to end: *journey* (one item moves through a system), *detective* (suspects
ruled out, culprit proven), *before / after*, *race* (options on one measure), *map tour* (parts
the reader must place), *recipe* (a method someone will repeat).

## Find the story before you draw

Write the spine in your notes first, one line per chapter: what the reader believed, **but** what
we found, **therefore** what changes. The headlines come from these lines.

- A chapter that changes no belief goes to the appendix. If nothing is in conflict, show a new angle; never invent an enemy.
- If the reader arrives expecting an answer ("the bigger model must win"), say so early and settle it in the chapter where the evidence lands.
- Everything on the first screen pays off in a chapter. "What's next" calls back to the overview figure, with the changed part marked.
- A vivid detail that does not carry the claim lowers recall; cut it.

## Three visible layers, then a drawer

1. **Headline**: a full takeaway sentence with its number, from the spine. Headlines alone tell the story.
2. **Figure + at most 3 sentences**, each opening with a bold lead phrase. Words say only what the figure cannot show.
3. **Side notes** (`<aside class="sidenote">`): the definition, the caveat, the one supporting number.

A drawer (`<details class="evidence">`) holds only audit material: method, full tables, rejected
options, raw logs. Its summary says what is inside and why to open it ("How we got 85%: 3 runs,
per-run table"); the build adds a kicker before it and a count after it. If the answer, a caveat
or a decision depends on a fact, that fact stays visible. One drawer per chapter; none inside another.

## Pictures carry the story

- Each chapter gets its own freshly drawn SVG figure, of the kind that fits what it shows (a scene, a state machine, a sankey, dots of 100, a trade-off). `references/figures.md` picks the kind and shows how to draw it.
- Draw the mechanism or the difference, never a box of words. Every caption opens with its takeaway. Cover the caption and the figure still teaches; cover the figure and the caption still says what matters.
- **Real pictures for things people can see** (a website, an app, a document, a device, a place), beside the figure: the figure explains, the real picture proves. Reuse the source's screenshots or photos first, else capture them with Playwright (`references/look.md`). One real picture stays visible in such a chapter, cropped to the part that matters; more go in the drawer.
- Vary colour, size and form so no two chapters in a row look alike; `references/look.md` holds the chapter sections, the palette and the devices.
- **Motion** only for a real change (a state transition, a sequence, a mechanism, a before/after), stepped by the reader. Read `references/motion.md`.
- **One hero widget** where a reader can find the insight themselves (predict then reveal, a slider, before/after, linked highlighting, a self-check), plus at most two small ones. Read `references/widgets.md`. The static page must still say everything.

## Sentences

A storybook reads at a glance, and not because it says less. Its reader holds the frame, meets few
things with one name each, and each sentence continues the last.

- **Whole, then parts.** Name the whole first, then one part per sentence, with the actor as subject and the action as verb ("augmentation fixed rotation", not "an improvement was achieved").
- **Old, then new.** Open each sentence with something the reader already met; end on the new fact or number.
- **One name per thing, one thing per name.** A new word reads as a new thing, in prose, figures and tables alike: never swap in a synonym or reuse a word for a second thing. Say what a thing is, not its run ID.
- **A real case for every claim.** Write out the example, number or evidence each time ("glare hides the name on 1 card in 5", not "weak in poor light"); a claim with none is a caveat.
- **Write the link** (because, so, but). A split that drops it is worse than one long sentence.
- **Analogy by default** for a new concept when a familiar thing shares its causes: pair each part once ("cars are requests"), say where it breaks (a side note will do), then use the real term and number. Skip it for a reader who knows the concept.

## Words and numbers

- **Compress, never invent.** First build `ledger.json` from the sources: every number, caveat and decision, with baseline and source. Anything left out goes in `dropped` with the reason.
- Define each term where it first appears, with `<dfn>Term</dfn>`. The full glossary goes in the appendix (`<dl class="words">`), never before the story.
- Every number is compared to something: its baseline, its denominator ("620 of 796"), how sure we are (range, seeds, or "single run"). Then say what it means for the claim ("so 110 more fakes stop").
- Replace, don't version: the page shows the newest state, with one dated changelog line per change. Keep old copies outside the folder.
- **Language**: STE-lite for internal readers, full STE for anything a client or outside reader gets.
- Aim for 1,500–2,000 visible words (the `check_story` count), a 10-minute read.

## Build and check

```bash
S=~/.claude/skills/storyteller/scripts
python3 $S/build_story.py story.src.md          # inlines figs and maps, renders story.html (+ PDF if pdf: true)
python3 $S/check_story.py story.html --ledger ledger.json --source <original report or notes>   # 1 s
python3 $S/check_ste.py --lite story.html                 # 1 s; drop --lite for client-facing pages
python3 $S/check_svg.py figs/*.svg                                      # 1 s; accessible, script-free figures
python3 $S/check_layout.py story.html     # minutes: once, before delivery
```

The checks catch only objective defects (a dropped number, a missing frame part, text too small on a
phone); taste is yours, and the first draft usually has it right. Run the 1 s checks on every
build and the layout check once at the end. For a new story that leaves the team, also run the
**cold-reader test**: give a fresh subagent only `story.html` and ask what the answer is, how sure
we are, what is unknown, what happens next, and which chapter it could skip. Fix only what it gets
wrong; skip the test for revisions and internal pages.

Deliver the local file and its served link (`path2url` if the user has one). Never an Artifact.
