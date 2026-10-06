"""Check a beat sheet for variety of picture, tempo and cut before any voice or render.

    python3 check_variety.py beats.json [direction.json]

Works on beats.json (beat length estimated from the spoken words) or beats.timed.json (the measured voice length).
Each rule prints PASS or FIX; the exit code is 1 when any rule says FIX.
  type runs    no 3 neighbouring beats with the same scene type (ui counts as a type)
  type share   no motion type on more than 25% of the beats (at least 2 allowed); ui tours are exempt
  tempo        the longest beat is at least 2x the shortest, and at least one beat holds (hold >= 1.2 s)
  cuts         at least 2 transition kinds; the most used kind is at least half of the cuts (one primary)
  look         direction.json names a look (the template's presets.json lists them)
"""
import json
import math
import sys
from collections import Counter

RUN_MAX = 2  # neighbours of one type
SHARE_MAX = 0.25
SPREAD_MIN = 2.0  # the legacy-links teaser measured 1.6 (7.1-11.6 s) and read as one even tempo
HELD_MIN = 1.2  # s of silence after the voice
WORDS_PER_S = 2.4  # Kokoro at speed 0.8-0.9, for beats without a measured length
HOLD_DEFAULT = 0.35  # build.py's default
PRIMARY_MIN = 0.5


def scene_type(b):
    return "ui" if b.get("kind") == "ui" else (b.get("scene") or {}).get("type", "?")


def length(b, hold):
    spoken = b.get("dur") or len((b.get("text") or b.get("caption", "")).split()) / WORDS_PER_S
    return spoken + float(b.get("hold", hold))


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
    top = cuts.most_common(1)[0][1] if cuts else 0
    ok = len(cuts) >= 2 and top >= PRIMARY_MIN * sum(cuts.values())
    out.append(("cuts", ok, ", ".join(f"{k} {n}" for k, n in cuts.most_common())))

    out.append(("look", bool(direction.get("look")), direction.get("look") or "direction.json has no look"))
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
