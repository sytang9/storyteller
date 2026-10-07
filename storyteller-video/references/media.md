# Media: icons, illustrations and photos

Scenes can show an icon, an illustration or a photo of the thing the voice names. All media is open-licence,
fetched once into `<teaser>/media/`, and inlined or copied at build time. The render never fetches anything.

## When to use an asset

- Use an asset only when it depicts the thing the voice names in that beat: "the road", "the contract", "the app".
- Do not use mood or generic stock. A decorative picture lowers recall; a picture of the named thing can help.
- Abstract nouns (budget, latency, trust) get no asset. Keep the card scene for them.
- Icons fit concrete nouns. A photo fits when the real thing matters (the equipment, the damage, the place).
- Look at every photo before it ships. The pick ranks by keyword overlap, and that signal is weak.
  "asphalt road repair" gave a road with potholes; "road repair crew paving" gave a crew at work.
  Name the subject and the action in the query.
- Refuse a photo with a readable brand, an advert, a recognisable face or a watermark.

## media.json

```json
[
  {"id": "road", "kind": "icon", "query": "road", "depicts": "a road"},
  {"id": "deal", "kind": "icon", "query": "tabler:contract", "depicts": "a signed contract"},
  {"id": "fix", "kind": "photo", "query": "road repair crew paving", "depicts": "a crew repairing a road"}
]
```

- `id`: a slug, used as the file name and in the helpers. `kind`: `icon`, `illustration` or `photo`.
- `query`: search words, or `set:name` for an exact Iconify icon. `depicts`: what the beat needs it to show.

```bash
python3 <skill>/scripts/fetch_assets.py <teaser> media.json            # fetch; exit 1 if any asset fails
python3 <skill>/scripts/fetch_assets.py <teaser> media.json --offline  # check the cache, no network
```

Icons come from Iconify (sets in this order: lucide, tabler, ph, material-symbols, mdi). Photos and illustrations
come from Openverse, then Wikimedia Commons. No key is needed. An unchanged file (same sha256) is not fetched again.
A failed asset prints its id and the reason, and writes no file.

## Licence gate

- Accept: CC0, Public Domain Mark, CC BY, MIT, ISC, Apache-2.0.
- Reject: any NC, ND or SA licence, and any unknown licence. `credits.json` lists rejected candidates.
- The gate runs twice: at fetch time, and again in `collect_media` before a build. A changed file also stops the build.
- Do not add a source whose terms bar scripted access (unDraw, Storyset, Noun Project). See the research note.

## Credit duties

`<teaser>/media/credits.json` holds one record per asset: title, author, source URL, licence, licence URL,
credit text, sha256, depicts and query.

1. End card: call `creditsCard(root)` in the last scene. It names every image and groups icon sets in one line.
2. Report changelog: add a table built from `credits.json` (title, author, licence, source URL). This is the record.
3. Public repo: commit `credits.json`. Keep CC BY photos out of the repo; the URL and sha256 let anyone fetch them again.

## Build and helpers

`build.py` adds `"media": collect_media(src, out=HERE)` to `data.js`. `index.html` loads `media.js` after the helpers.

| Helper | What it draws |
| --- | --- |
| `iconEl(parent, id, {size, color, x?, y?})` | The inlined SVG at `size` px, painted in one look role (`col(color)`) |
| `imageEl(parent, id, {w, h, fit, x?, y?, radius?})` | The image in a `w` x `h` box; `fit` is `cover` (crop) or `contain` |
| `creditsCard(root, {x?, y?, size?, color?})` | One small credits line in frame px, outside the scene fit |

Each helper returns its node, so animate it like any other node (`popIn`, `tl.to`). An unknown id throws.
Icons are sanitized: only shapes survive, with no script, no `on*` attribute and no external link.
