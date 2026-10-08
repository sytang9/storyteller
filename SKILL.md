---
name: storyteller
description: Turns technical work (results, investigations, studies, proposals, status updates, bloated reports) into one illustrated, plain-language HTML story a non-expert can follow, keeping every number, caveat and decision. The default for any report, write-up or summary page a person reads, eli5 versions, /html-report with /eli5, "make this readable". Not for system-book, PR reviews, dashboards, videos, fiction or Storybook.js.
---

# Storyteller

## Fixed frame, free story

Copy `assets/template.md`. The frame is fixed, in this order:

1. **The answer** (first screen): 1–2 sentences (question, answer, decision needed), a drawn overview figure naming each chapter's part in the chapters' words, and a **TL;DR row** of 3 cards (label, key number vs baseline, at most 20 words; label sets in the template).
2. **The story**: one shape (*journey*, *detective*, *before / after*, *race*, *map tour*, *recipe*) and one running example or analogy from start to end.
3. **What we're not sure about**: every caveat and unverified claim, one line each.
4. **What's next**: one step, owner, date. If the source names none, write "not yet set"; never invent one.
5. **Appendix** (collapsed): every number, all findings, full glossary, changelog.

Write the spine first, one line per chapter: what the reader believed, **but** what we found,
**therefore** what changes. Headlines come from these lines. A chapter that changes no belief goes
to the appendix; never invent an enemy. Name early any answer the reader arrives expecting; settle it where the evidence lands.
Everything on the first screen pays off in a chapter; "What's next" calls back to the overview
figure with the changed part marked. Cut vivid details that do not carry the claim.

## Layers

Each chapter: a **headline** (full takeaway sentence with its number; headlines alone tell the
story), a **figure + at most 3 sentences** each opening with a bold lead, and **side notes**
(`<aside class="sidenote">`) for the definition, caveat or supporting number. One drawer
(`<details class="evidence">`) per chapter, never nested, holds only audit material (method, full
tables, rejected options, raw logs); its summary says what is inside and why to open it. A fact the
answer, a caveat or a decision depends on stays visible.

## Pictures

- Each chapter gets its own freshly drawn SVG in `figs/` showing the mechanism or the difference, never a box of words. Captions open with the takeaway. Kind and drawing rules: `references/figures.md`.
- Things people can see (a site, an app, a document, a device) also get a real picture: reuse the source's, else capture with Playwright. One stays visible, cropped to what matters; more go in the drawer. Rules, accents and devices: `references/look.md`. No two chapters in a row look alike.
- Motion only for a real change, stepped by the reader: `references/motion.md`. One hero widget plus at most two small ones: `references/widgets.md`. The static page must still say everything.

## Words and numbers

- **Compress, never invent.** First build `ledger.json` from the sources: every number, caveat and decision, with baseline and source. Anything left out goes in `dropped` with the reason.
- **One name per thing, one thing per name**, in prose, figures and tables: no synonyms, no acronyms or run IDs where a plain name fits.
- A real case for every claim ("glare hides the name on 1 card in 5", not "weak in poor light"); a claim with none is a caveat.
- Analogy by default for a new concept: pair each part once, say where it breaks, then use the real term. Skip it for a reader who knows the concept.
- Every number is compared: baseline, denominator ("620 of 796"), certainty (range, seeds, "single run"), then what it means.
- Define each term at first use with `<dfn>`; the full glossary goes in the appendix (`<dl class="words">`), never before the story.
- Replace, don't version: newest state only, one dated changelog line per change; old copies live outside the folder.
- STE-lite for internal readers, full STE for client or outside readers. Aim for 1,500–2,000 visible words; a short source gets a shorter page, never padding.

## Build and check

```bash
S=~/.claude/skills/storyteller/scripts
python3 $S/build_story.py story.src.md          # inlines figs and maps, renders story.html (+ PDF if pdf: true)
python3 $S/check_story.py story.html --ledger ledger.json --source <original report or notes>   # 1 s
python3 $S/check_ste.py --lite story.html                 # 1 s; drop --lite for client-facing pages
python3 $S/check_svg.py figs/*.svg                                      # 1 s; accessible, script-free figures
python3 $S/check_layout.py story.html     # minutes: once, before delivery
```

Run the 1 s checks on every build, the layout check once at the end. For a new story that leaves
the team, also run the **cold-reader test**: give a fresh subagent only `story.html` and ask the
answer, how sure we are, what is unknown, what happens next, and which chapter it could skip. Fix
only what it gets wrong; skip it for revisions and internal pages.

## Optional video

After delivery, if the story has a mechanism that moves or a real screen the reader must picture,
offer a narrated video: name 2-4 scenes and give the two levels and costs from the
`storyteller-video` skill. Never for a short or simple report. Build only on a yes, with that skill.

Deliver the local file and its served link (`path2url` if the user has one). Never an Artifact.
