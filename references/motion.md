# Moving figures and embedded maps

## Moving figure (step mode)

`render.py` adds the controller (`assets/motion.js`) and its CSS to every page, so a figure carries
no script. Mark it up like this:

```html
<div data-motion-root data-motion-mode="step" data-step-count="4" data-step-current="4" data-frame="static" tabindex="-1">
<!-- FIG:name motion -->
*Caption: what pressing Play or Next reveals.*
<div data-motion-controls role="group" aria-label="Playback controls">
<button type="button" data-motion-action="prev">Previous</button>
<button type="button" data-motion-action="play" aria-pressed="false">Play</button>
<button type="button" data-motion-action="pause" aria-pressed="true">Pause</button>
<button type="button" data-motion-action="next">Next</button>
<button type="button" data-motion-action="replay">Replay</button>
<span data-motion-status-visible aria-hidden="true">Step <span data-motion-step-label>4</span> of 4</span>
</div>
<span class="sr-only" data-motion-status role="status" aria-live="polite" aria-atomic="true"></span>
</div>
```

Inside the SVG, wrap what appears at step N in `<g data-motion-item data-step="N" aria-label="Step N: what appears">`.

- 2–6 steps, one change per step, at most two items per step; steps run 1..N with no gap.
- The controller opens on step 0: make step 0 a meaningful "before" state, and say in the caption what pressing Play reveals.
- Print, no-JS and reduced motion show the final frame, so it must carry every fact.
- At most one moving figure per three chapters, three per page.
- Keep the whole block inside the one wrapping `<div>` with blank lines around it, so Markdown passes it through untouched.

## Embedded interactive figure (map)

`<!-- MAP:name -->` embeds `figs/name.html`, any self-contained interactive page (an explorable
map, a large diagram), across the full window, with an "Open full screen" link. Add a height in px
(`<!-- MAP:name 900 -->`) when it needs more than the default. The build saves `figs/name.png` with
Playwright for print. Place a map after the TL;DR row and the menu, so the first screen still holds
the summary; the drawn overview stays on the first screen.
