# Look and rhythm

`assets/story-devices.css` is injected into every page by the build. Use its classes; do not restyle.

## Colour

- Wrap each story chapter in `<section class="acc-blue|acc-teal|acc-purple|acc-orange" markdown="1">`. The chapter's figures, numbers and dividers take that accent. Never repeat the previous chapter's accent.
- `--hue-green`, `--hue-red`, `--hue-amber` mean good, bad and caution only; never use them as an accent. Keep one pair (old vs new, today vs proposed) in the same two colours for the whole page.
- Meaning is never colour alone: add a word, a shape or a pattern (`.hatch`, `.ring`).

## Devices (each one replaces words; none adds them)

| Class | Use |
|---|---|
| `.display` on the page title (`<h1>` via the frontmatter title stays; use `<p class="display">` for a hero line) | one oversized claim, key word in `<em>` |
| `<p class="chapter-no">01<span>Short label</span></p>` | opens every story chapter, numbered in order |
| (automatic) chapter rail | built from the `.chapter-no[id]` markers when a story has 3+ chapters: a fixed right-edge strip of numerals, the current one marked, its h3 sub-sections as dots, the title on hover/focus (kept visible at 1400px+). Hidden below 1100px and in print. Nothing to author; keep chapter openers numbered in order. |
| `<div class="hero-num"><b>84 of 100</b><span>what it counts</span></div>` | the one number a chapter turns on |
| `<div class="card-row">` with 2–4 `<div class="card">` | parallel facts (≤20 words a card) |
| `<blockquote class="pull">` | one quotable line (≤15 words) |
| `<div class="panel tint-blue">` with a `.label` | a definition or caveat at first use (≤40 words) |
| `<ol class="steps">` / `.badge-step` | order without "first, then" |
| `<span class="legend-inline">` | a legend next to the data it explains |

## Vary the presentation

- Pick the figure kind by what the chapter shows, from the table in `figures.md`; a good fit gives variety by itself, because chapters show different things. Mark each figure `data-kind="..."`.
- Use the type scale: a large display line, hero numbers, normal body, small labels. Big type carries the point; small type carries the detail.

## Taste

- Mark each layer with type, not a box: the story is full-size body type; drawers and side notes are one step smaller, with mono labels and a faint tint.
- Separate with space first, then tone, then a hairline; a box last, and never a dashed line (it reads as a draft).
- One accent per region, with one job: the chapter's kicker, chevron and "our" row, nothing else.
- A closed label promises what is inside and is never the faintest text on the page.

## Drawer kickers and symbols

- The drawer kicker defaults to "Under the hood". To vary it, start the summary with `<span class="kick">Word</span>`, picked by what the drawer holds: *Unmasked* (a leak or a hidden cause), *The reveal* (the answer to a predict widget), *The receipts* (full tables), *Behind the curtain* (method), *Roads not taken* (rejected options), *Case file* (raw logs), *The leap* (how one result led to the next step), *Rewind* (the changelog), *Words* (the glossary). For client pages use plain words: *Method*, *Evidence*, *Data*.
- No exclamation marks: a report states and measures, it does not cheer. Symbols that carry meaning are welcome in hero numbers, cards and labels: `35 → 84`, `260×`, `≈ 3,000`, `98 vs 50`. A question mark belongs only in a short `chapter-no` label of a detective chapter ("Who leaked?"); the headline under it answers it.

## Real pictures

- Markup: `<figure class="shot"><img src="asset/name.jpg" alt="what it shows"><figcaption>What to look at, as the takeaway.</figcaption></figure>`. Two side by side: `<div class="shot-pair">` holding two such figures.
- Capture with Playwright, headless: 1440×900, plus 390×844 when the phone view matters. Crop with an element screenshot or `clip` to the part that matters rather than adding arrows; save to `asset/` as JPEG, about 1,100 px wide.
- Open only systems you are allowed to, and read only: never press a button that writes (save, submit, approve) on a live system. When unsure, abort writes with `page.route("**/*", lambda r: r.abort() if r.request.method in ("POST", "PUT", "PATCH", "DELETE") else r.continue_())`.
- Crop or blur personal data (names, emails, ID numbers, tokens) before saving.
