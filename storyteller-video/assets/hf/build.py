"""Build step for the data-driven teaser template.

Reads the report's beat and tour data, copies media into the project, writes
data.js (the timeline data the composition consumes), stamps the root duration
and the <audio> clips into index.html, and writes the WebVTT captions.

Usage: python3 build.py [--src ..] [--beats beats.timed.json] [--direction ../direction.json] [--vtt teaser.vtt] [--captions keywords|full]
  src      = folder holding voice/ and shots/ (default: the parent folder)
  direction = the look and tempo defaults (default: <src>/direction.json if present, else the paper look)
  beats    = the beat file with a `scene` object per beat (default: the one next to this script)
  vtt      = caption file name, written into src (always written, in both caption modes)
  captions = full (default: burned captions in the reserved bottom band, plus scene.labels) or keywords (labels only)
"""

import argparse
import json
import re
import shutil
from pathlib import Path

HOLD = 0.35  # default silence after a beat's voice (s); a beat or direction.json "hold" overrides it
TRANSITIONS = {"calm", "fade", "cut", "push", "zoom", "wipe"}  # index.html applies them at the boundary
VOICE_LEAD = 0.15  # voice starts this long after the beat start (s)
TAIL = 1.2  # hold after the last voice clip (s)
PHRASE_MAX = 80  # 2 lines x ~42 chars, minus slack
SENTENCE_MIN = 20  # break after . : ; once a phrase has this many chars
COMMA_MIN_SHORT = 40  # break after a comma (caption fits in one phrase anyway)
COMMA_MIN_LONG = 25  # break after a comma (caption is longer than PHRASE_MAX)
SHOW_LEAD = 0.1  # a phrase appears this long before its first word
HIDE_BEFORE_NEXT = 0.15  # the last phrase of a beat clears this long before the next beat

HERE = Path(__file__).resolve().parent


def split_phrases(words, caption):
    comma_min = COMMA_MIN_LONG if len(caption) > PHRASE_MAX else COMMA_MIN_SHORT
    phrases, cur = [], []
    text = lambda ws: " ".join(w["w"] for w in ws)
    for i, w in enumerate(words):
        if cur and len(text(cur + [w])) > PHRASE_MAX:
            phrases.append(cur)
            cur = []
        cur.append(w)
        n = len(text(cur))
        rest = words[i + 1 :]
        if not rest:
            break
        if (w["w"][-1] in ".:;" and n >= SENTENCE_MIN) or (w["w"][-1] == "," and n >= comma_min):
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)
    return phrases


def find_word(words, token, nth=0):
    hits = [w for w in words if re.sub(r"[^\w']", "", w["w"]).lower() == token.lower()]
    if len(hits) <= nth:
        raise SystemExit(f"focus word {token!r} (#{nth}) not in caption")
    return hits[nth]


def load_scene(beat, base):
    """The beat's scene object; a "data" key names a JSON file whose fields are merged in."""
    scene = dict(beat.get("scene") or {})
    if "type" not in scene:
        raise SystemExit(f"beat {beat['id']}: scene.type missing")
    if "data" in scene:
        scene = {**json.loads((base / scene.pop("data")).read_text()), **scene}
    return scene


def check_words(beat, scene, words):
    """Fail fast on a label or ui word that is not in the caption."""
    for lab in scene.get("labels", []):
        w = lab["word"] if isinstance(lab["word"], list) else [lab["word"]]
        find_word(words, *w)
    if "click" in scene:
        find_word(words, scene["click"])


def copy_module(scene, base):
    """A custom scene's module (a plain <file>.js next to the beats file); returns its script path.
    A module outside this folder is copied into custom/ so the composition can load it."""
    name = scene.get("module")
    if not name or Path(name).name != name or not name.endswith(".js"):
        raise SystemExit(f"custom scene needs module: a plain <file>.js name, got {name!r}")
    src = (base / name).resolve()
    if not src.is_file():
        raise SystemExit(f"custom scene module not found: {src}")
    if src.parent == HERE:
        return name
    (HERE / "custom").mkdir(exist_ok=True)
    shutil.copy2(src, HERE / "custom" / name)
    return "custom/" + name


def load_direction(path, out=HERE):
    """direction.json: {look, override?, transition?, hold?}. Returns the defaults and writes <out>/theme.css."""
    direction = json.loads(path.read_text()) if path and path.is_file() else {"look": "paper"}
    presets = json.loads((HERE / "presets.json").read_text())
    look = direction.get("look", "paper")
    if look not in presets or look.startswith("_"):
        raise SystemExit(f"direction.json look {look!r} not in presets.json: {sorted(k for k in presets if k[0] != '_')}")
    tokens = {**presets[look], **direction.get("override", {})}
    tokens.pop("mood", None)
    fallback = {"sans": "system-ui, sans-serif", "display": "system-ui, sans-serif", "mono": "ui-monospace, monospace"}
    lines = [f'  --{k}: "{v}", {fallback[k]};' if k in fallback else f"  --{k}: {v};" for k, v in tokens.items()]
    (out / "theme.css").write_text(f"/* generated by build.py from direction.json (look: {look}); do not edit */\n:root {{\n" + "\n".join(lines) + "\n}\n")
    default_in = direction.get("transition", "calm")
    if default_in not in TRANSITIONS:
        raise SystemExit(f"direction.json transition {default_in!r} not in {sorted(TRANSITIONS)}")
    return {"look": look, "in": default_in, "hold": float(direction.get("hold", HOLD))}


def vtt_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(HERE.parent))
    ap.add_argument("--beats", default=str(HERE / "beats.timed.json"))
    ap.add_argument("--direction", default=None)
    ap.add_argument("--vtt", default="teaser.vtt")
    ap.add_argument("--captions", choices=["keywords", "full"], default="full")
    args = ap.parse_args()
    src = Path(args.src)
    beats_path = Path(args.beats)

    beats = json.loads(beats_path.read_text())
    look = load_direction(Path(args.direction) if args.direction else src / "direction.json")
    tour = {b["id"]: b for b in json.loads((src / "shots/tour.json").read_text())["beats"]}

    (HERE / "assets/voice").mkdir(parents=True, exist_ok=True)
    (HERE / "assets/frames").mkdir(parents=True, exist_ok=True)

    out, t, modules = [], 0.0, []
    for b in beats:
        hold = float(b.get("hold", look["hold"]))
        kind_in = b.get("in", look["in"])
        if kind_in not in TRANSITIONS:
            raise SystemExit(f"beat {b['id']}: in {kind_in!r} not in {sorted(TRANSITIONS)}")
        vstart = t + VOICE_LEAD
        words = [{"w": w["w"], "s": round(vstart + w["s"], 3), "e": round(vstart + w["e"], 3)} for w in b["caption_words"]]
        shutil.copy2(src / "voice" / f"{b['id']}.wav", HERE / "assets/voice" / f"{b['id']}.wav")
        beat = {
            "id": b["id"], "kind": b["kind"], "scene": load_scene(b, beats_path.parent), "caption": b["caption"],
            "start": round(t, 3), "vstart": round(vstart, 3), "dur": b["dur"],
            "end": round(t + b["dur"] + hold, 3), "in": kind_in, "words": words,
        }
        check_words(b, beat["scene"], words)
        if beat["scene"]["type"] == "custom":
            mod = copy_module(beat["scene"], beats_path.parent)
            if mod not in modules:
                modules.append(mod)
        if b["kind"] == "ui":
            s = tour[b["id"]]
            imgs = [s["after"]] + ([s["before"]["img"]] if s.get("before") else [])
            for img in imgs:
                shutil.copy2(src / "shots/frames" / img, HERE / "assets/frames" / img)
            f = beat["scene"]
            fw = find_word(words, f["focus"], f.get("nth", 0)) if "focus" in f else words[len(words) // 3]
            text = f.get("text") or s.get("text", s["box"])  # scene.text overrides the tour's text box (crop on word boundaries)
            ui = {"after": "assets/frames/" + s["after"], "box": s["box"], "text": text, "size": s["size"], "focusAt": fw["s"]}
            if s.get("before"):
                ui["before"] = "assets/frames/" + s["before"]["img"]
                ui["click"] = s["before"]["click"]
                # press lands on scene.click, or on the 2nd caption word
                ui["clickAt"] = find_word(words, f["click"])["s"] if "click" in f else words[min(1, len(words) - 1)]["s"]
            beat["ui"] = ui
        out.append(beat)
        t += b["dur"] + hold

    total = round(out[-1]["vstart"] + out[-1]["dur"] + TAIL, 2)
    for i, beat in enumerate(out):
        groups = split_phrases(beat["words"], beat["caption"])
        last_end = (out[i + 1]["start"] - HIDE_BEFORE_NEXT) if i + 1 < len(out) else total
        beat["phrases"] = []
        for j, g in enumerate(groups):
            show = round(g[0]["s"] - SHOW_LEAD, 3)
            hide = round(groups[j + 1][0]["s"] - SHOW_LEAD, 3) if j + 1 < len(groups) else round(last_end, 3)
            beat["phrases"].append({"show": show, "hide": hide, "wi": [beat["words"].index(w) for w in g]})

    data = {"width": 1920, "height": 1080, "fps": 30, "total": total, "captions": args.captions, "beats": out}
    (HERE / "data.js").write_text("// generated by build.py; do not edit\nwindow.TEASER = " + json.dumps(data, indent=1) + ";\n")

    audio = "\n".join(
        f'      <audio id="vo-{b["id"]}" src="assets/voice/{b["id"]}.wav" data-start="{b["vstart"]}" '
        f'data-duration="{b["dur"]}" data-track-index="{10 + k}"></audio>'
        for k, b in enumerate(out)
    )
    html = (HERE / "index.html").read_text()
    html = re.sub(r'(data-composition-id="main"[^>]*?data-duration=")[^"]*"', rf'\g<1>{total}"', html, count=1, flags=re.S)
    html = re.sub(r"(<!-- AUDIO:START -->\n).*?(\s*<!-- AUDIO:END -->)", lambda m: m.group(1) + audio + "\n      <!-- AUDIO:END -->", html, flags=re.S)
    scripts = "\n".join(f'    <script src="{m}"></script>' for m in modules)
    html = re.sub(r"(<!-- CUSTOM:START -->\n).*?(\s*<!-- CUSTOM:END -->)", lambda m: m.group(1) + scripts + "\n    <!-- CUSTOM:END -->", html, flags=re.S)
    (HERE / "index.html").write_text(html)

    cues = ["WEBVTT", ""]
    for b in out:
        for p in b["phrases"]:
            cues += [f"{vtt_time(p['show'])} --> {vtt_time(p['hide'])}", " ".join(b["words"][k]["w"] for k in p["wi"]), ""]
    (src / args.vtt).write_text("\n".join(cues))
    print(f"look {look['look']}, total {total}s, {sum(len(b['phrases']) for b in out)} phrases, captions {args.captions}, {len(modules)} custom modules")


if __name__ == "__main__":
    main()
