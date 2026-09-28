# Interactive widgets

A click must pay off: about 15% of readers press even a prominent button, so the visible default always states the finding.

| Reader needs to ... | Use | Not |
|---|---|---|
| Feel a surprise ("I thought X, it is Y") | predict, then reveal | a plain chart |
| See how a setting changes the result | slider that recomputes, or a number scrubbed inside a sentence | a table |
| Compare two versions of one picture | before/after slider, or a toggle | tabs that hide one side |
| Compare 3+ cases | small multiples | tabs, animation |
| Find which part of a figure a sentence means | linked highlighting (text marker <-> figure mark) | hover tooltips |
| Follow an ordered mechanism | the step controller (motion.md) | scroll-driven state |
| Check they got it | a one-question self-check at a chapter end | a summary box |

## Shared rule: the static fallback is the default markup

The first script line runs `document.documentElement.classList.add("js")`. Controls carry
`class="js-only"` and show only under `html.js`; fallbacks carry `class="static"` and hide only under
`html.js`, so with JS off the page is still complete. `@media print` shows
the fallback and hides controls. Vanilla JS, no CDN. Keyboard works, state is never colour alone,
`aria-live` announces results, and nothing is drag-only or hover-only.

## Starter patterns (fallback in brackets)

- **Predict, then reveal** [the answer in a `<details>`]: the reader sets a guess (range input), presses "Show me", the truth draws over the guess, and one sentence states the gap: "You guessed 60; it is 35." Then ask why it differs. Predict without the reveal is the weakest form; always show and say the gap.
- **Slider** [a 3–5 row table of precomputed results, the real setting bold]: a pure function turns the setting into the result, the same numbers as the table; `<output aria-live="polite">` says it in words.
- **Linked highlighting** [numbered markers (1)(2) in text and figure]: a `<button class="ref" data-ref="k2">` in the text toggles an outline on the figure's `#k2` on focus, hover or tap.
- **Toggle** [all states stacked under their own headings]: JS turns the headings into a button row and shows one state at a time.
- **Before/after** [two labelled images side by side]: a range input clips the top image with `clip-path: inset(0 X% 0 0)`.
- **Self-check** [answer in a `<details>`]: one radio question; "Check" answers in words with the reason.
