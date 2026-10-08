"""Check a beat sheet for variety of picture, tempo and cut before any voice or render.

    python3 check_variety.py beats.json [direction.json]

Works on beats.json (beat length estimated from the spoken words) or beats.timed.json (the measured voice length).
Each rule prints PASS or FIX; the exit code is 1 when any rule says FIX.
  type runs    no 3 neighbouring beats with the same scene type (ui counts as a type)
  type share   no motion type on more than 25% of the beats (at least 2 allowed); ui tours are exempt
  tempo        the longest beat is at least 2x the shortest, and at least one beat holds (hold >= 1.2 s)
  cuts         at least 2 transition kinds; the most used kind is at least half of the cuts, morphs aside (one primary)
  look         direction.json names a look (the template's presets.json lists them)
  stillness    beats.timed.json only: no 3.0 s stretch of voice with no change on screen (any word-timed field in
               the scene or its events counts; a ui beat counts its zoom and click)
"""
import json
import math
import sys
from collections import Counter

RUN_MAX = 2  # neighbours of one type
SHARE_MAX = 0.25
SPREAD_MIN = 2.0  # longest/shortest beat; below this the video reads as one even tempo
HELD_MIN = 1.2  # s of silence after the voice
WORDS_PER_S = 2.4  # Kokoro at speed 0.8-0.9, for beats without a measured length
HOLD_DEFAULT = 0.35  # build.py's default
PRIMARY_MIN = 0.5
STILL_MAX = 3.0  # s of voice with nothing new on screen
EVENT_KINDS = {"hero", "lift", "mark", "swap", "strike", "number", "note", "push"}  # assets/hf/events.js
CONTINUOUS = {"lanes"}  # scene types that keep moving between their cue words (the lanes token walk)
CUE_KEYS = {"cues", "word", "until", "landWord", "show", "toWord", "ofWord", "restIn", "spread", "in", "tick", "tagIn", "detailIn", "focus", "click"}


def scene_type(b):
    """ui, a template type, or custom:<module>: each bespoke scene is its own layout."""
    s = b.get("scene") or {}
    if b.get("kind") == "ui":
        return "ui"
    return f"custom:{s.get('module')}" if s.get("type") == "custom" else s.get("type", "?")


def length(b, hold):
    spoken = b.get("dur") or len((b.get("text") or b.get("caption", "")).split()) / WORDS_PER_S
    return spoken + float(b.get("hold", hold))


def cue_words(node, key=None):
    """Every caption word that times a change: a "word" string, a [word, n] pair, or a list of either."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from cue_words(v, k)
    elif isinstance(node, list):
        if len(node) == 2 and isinstance(node[0], str) and isinstance(node[1], int):
            if key in CUE_KEYS:
                yield node[0], node[1]
        else:
            for v in node:
                yield from cue_words(v, key)
    elif isinstance(node, str) and key in CUE_KEYS:
        yield node, 0


def norm(w):
    return "".join(c for c in w.lower() if c.isalnum() or c == "'")


def still_gaps(b):
    """The longest stretch of the voice with no timed change, in s."""
    words = b["caption_words"]
    scene = dict(b.get("scene") or {})
    events = scene.pop("events", [])
    bad = [e.get("kind") for e in events if e.get("kind") not in EVENT_KINDS]
    if bad:
        raise SystemExit(f"beat {b['id']}: unknown event kinds {bad} (known: {sorted(EVENT_KINDS)})")
    times = []
    for w, n in cue_words({**scene, "events": events}):
        hits = [x for x in words if norm(x["w"]) == norm(w)]
        if len(hits) > n:
            times.append(hits[n]["s"])
    if b.get("kind") == "ui" and "focus" not in scene:  # the zoom lands a third of the way in by default
        times.append(words[len(words) // 3]["s"])
    if scene.get("type") in CONTINUOUS and len(times) > 1:  # moving all the way from its first cue to its last
        lo, hi = min(times), max(times)
        times += [lo + k * 1.5 for k in range(int((hi - lo) / 1.5) + 1)]
    edges = sorted([0.0, b["dur"], *times])
    return max(z - a for a, z in zip(edges, edges[1:]))


def check(beats, direction):
    """Returns [(rule, ok, detail)]."""
    hold = float(direction.get("hold", HOLD_DEFAULT))
    default_in = direction.get("transition", "calm")
    types = [scene_type(b) for b in beats]
    out = []

    runs = [i for i in range(len(types) - RUN_MAX) if len(set(types[i : i + RUN_MAX + 1])) == 1]
    out.append(("type runs", not runs, ", ".join(f"{beats[i]['id']}..{beats[i + RUN_MAX]['id']} all {types[i]}" for i in runs) or "ok"))

    cap = max(2, math.floor(SHARE_MAX * len(beats)))
    heavy = {t: n for t, n in Counter(types).items() if t != "ui" and n > cap}
    out.append(("type share", not heavy, ", ".join(f"{t} on {n} beats (max {cap})" for t, n in heavy.items()) or f"ok (max {cap} a type)"))

    lens = [length(b, hold) for b in beats]
    held = [b["id"] for b in beats if float(b.get("hold", hold)) >= HELD_MIN]
    spread = max(lens) / min(lens)
    ok = spread >= SPREAD_MIN and held
    out.append(("tempo", bool(ok), f"longest/shortest {spread:.2f} (min {SPREAD_MIN}); held beats: {', '.join(held) or 'none'}"))

    cuts = Counter(b.get("in", default_in) for b in beats[1:])
    # a morph is a match cut chosen by the content (an object carries over), not part of the cut grammar
    grammar = {k: n for k, n in cuts.items() if k != "morph"}
    top = max(grammar.values(), default=0)
    ok = len(cuts) >= 2 and top >= PRIMARY_MIN * sum(grammar.values())
    out.append(("cuts", ok, ", ".join(f"{k} {n}" for k, n in cuts.most_common())))

    out.append(("look", bool(direction.get("look")), direction.get("look") or "direction.json has no look"))

    if all("caption_words" in b for b in beats):
        still = [(b["id"], still_gaps(b)) for b in beats]
        bad = [f"{i} {g:.1f} s" for i, g in still if g > STILL_MAX]
        out.append(("stillness", not bad, ", ".join(bad) or f"ok (max {max(g for _, g in still):.1f} s)"))
    return out


def main(beats_file, direction_file=None):
    beats = json.load(open(beats_file))
    direction = json.load(open(direction_file)) if direction_file else {}
    results = check(beats, direction)
    for rule, ok, detail in results:
        print(f"{'PASS' if ok else 'FIX '} {rule:<10} {detail}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
