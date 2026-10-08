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

from media_build import collect_media, gate

HOLD = 0.35  # default silence after a beat's voice (s); a beat or direction.json "hold" overrides it
TRANSITIONS = {"calm", "fade", "cut", "push", "zoom", "wipe", "morph"}  # index.html applies them at the boundary
VOICE_LEAD = 0.15  # voice starts this long after the beat start (s)
TAIL = 1.2  # hold after the last voice clip (s)
END_DUR = 3.0  # the optional end card (direction.json "end")
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
    """Fail fast on a label, ui or event word that is not in the caption."""
    for lab in scene.get("labels", []):
        w = lab["word"] if isinstance(lab["word"], list) else [lab["word"]]
        find_word(words, *w)
    if "click" in scene:
        find_word(words, scene["click"])
    for ev in scene.get("events", []):
        for key in ("word", "until"):
            if key in ev:
                find_word(words, *(ev[key] if isinstance(ev[key], list) else [ev[key]]))


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


SAFE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")  # beat ids become file names and HTML attributes
TOKEN_KEY = re.compile(r"[a-z][a-z0-9-]*")
# token values go into a stylesheet: only colours, lengths, plain keywords, and font names from style.css
TOKEN_VALUE = re.compile(r"#[0-9a-fA-F]{3,8}|-?\d+(\.\d+)?(px|em|rem|%)?|[a-z-]+|[A-Za-z0-9 ]+")
FONT_KEYS = {"sans", "display", "mono", "num"}
HEX = re.compile(r"#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}")
ROLE_KEYS = {"accent", "blue", "teal", "purple", "orange", "good"}
GROUND_KEYS = {"bg", "ink", "mute", "surface", "line", "em"} | ROLE_KEYS  # colour tokens a ground may set for its beats
PATTERNS = {"dots", "grid", "stripes"}  # index.html draws them in the ground's line colour
BREAK_DUR = (0.5, 3.0)  # a silent chapter break, s


def check_tokens(tokens):
    """direction.json is written from report data, so a token may not carry CSS of its own (a "}" or url())."""
    fonts = set(re.findall(r'@font-face \{ font-family: "([^"]+)"', (HERE / "style.css").read_text()))
    for k, v in tokens.items():
        if not TOKEN_KEY.fullmatch(k) or not TOKEN_VALUE.fullmatch(str(v)):
            raise SystemExit(f"look token {k!r}: {v!r} is not a plain colour, length, keyword or name")
        if k in FONT_KEYS and v not in fonts:
            raise SystemExit(f"look token {k!r}: font {v!r} has no @font-face in style.css")


def contrast(a, b):
    """WCAG contrast ratio of two #rgb / #rrggbb colours."""
    def lum(h):
        h = h.lstrip("#")
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check_grounds(grounds):
    """direction.json "grounds": named grounds a beat can stand on, inside the one look. Each sets bg, ink and mute
    (plus surface, line, em) and may add a pattern; text on it must stay readable (4.5:1)."""
    for name, g in grounds.items():
        if not SAFE_ID.fullmatch(name):
            raise SystemExit(f"ground {name!r}: use lowercase letters, digits, - and _")
        missing = {"bg", "ink", "mute"} - set(g)
        if missing:
            raise SystemExit(f"ground {name!r} needs {sorted(missing)}")
        for k, v in g.items():
            if k == "pattern":
                if v not in PATTERNS:
                    raise SystemExit(f"ground {name!r}: pattern {v!r} not in {sorted(PATTERNS)}")
            elif k not in GROUND_KEYS or not HEX.fullmatch(str(v)):
                raise SystemExit(f"ground {name!r}: {k!r}: {v!r} must be one of {sorted(GROUND_KEYS)} as a #hex colour")
        for k in ("ink", "mute"):
            if contrast(g[k], g["bg"]) < 4.5:
                raise SystemExit(f"ground {name!r}: {k} on bg is {contrast(g[k], g['bg']):.1f}:1, needs 4.5:1")
        for k in ROLE_KEYS & set(g):  # a light ground retunes the roles a dark look made pale
            if contrast(g[k], g["bg"]) < 3:
                raise SystemExit(f"ground {name!r}: role {k} on bg is {contrast(g[k], g['bg']):.1f}:1, needs 3:1")


def beat_ground(scene, grounds, beat_id):
    """The ground a beat stands on ({vars, pattern}), or None for the look's own."""
    name = scene.get("ground")
    if not name:
        return None
    if name not in grounds:
        raise SystemExit(f"beat {beat_id}: ground {name!r} not in direction.json grounds {sorted(grounds)}")
    g = grounds[name]
    return {"vars": {k: v for k, v in g.items() if k != "pattern"}, "pattern": g.get("pattern")}


def break_beat(b):
    """A silent chapter break (kind "break") returns its length; a voiced beat returns None."""
    if b.get("kind") != "break":
        return None
    dur = b.get("dur")
    if not isinstance(dur, (int, float)) or not BREAK_DUR[0] <= dur <= BREAK_DUR[1]:
        raise SystemExit(f"beat {b.get('id')}: a break needs dur between {BREAK_DUR[0]} and {BREAK_DUR[1]} s")
    if b.get("caption") or b.get("text"):
        raise SystemExit(f"beat {b.get('id')}: a break is silent; drop its caption and text")
    return float(dur)


def safe_id(i):
    if not SAFE_ID.fullmatch(str(i)):
        raise SystemExit(f"beat id {i!r}: use lowercase letters, digits, - and _ (it becomes a file name)")
    return i


def safe_name(name):
    if Path(name).name != name or name.startswith("."):
        raise SystemExit(f"tour image {name!r} must be a plain file name in shots/frames")
    return name


def load_direction(path, out=HERE):
    """direction.json: {look, override?, transition?, hold?, end?: {title, sub?, dur?}}. Returns the defaults and
    writes <out>/theme.css."""
    direction = json.loads(path.read_text()) if path and path.is_file() else {"look": "paper"}
    presets = json.loads((HERE / "presets.json").read_text())
    look = direction.get("look", "paper")
    if look not in presets or look.startswith("_"):
        raise SystemExit(f"direction.json look {look!r} not in presets.json: {sorted(k for k in presets if k[0] != '_')}")
    tokens = {**presets[look], **direction.get("override", {})}
    tokens.pop("mood", None)
    check_tokens(tokens)
    fallback = {"sans": "system-ui, sans-serif", "display": "system-ui, sans-serif", "mono": "ui-monospace, monospace", "num": "system-ui, sans-serif"}
    faces = digit_faces(tokens) if tokens.get("num") and tokens["num"] != tokens.get("display") else ""
    if faces:  # the display face, with its digits taken from the number face
        tokens["display"], tokens["display-base"] = "Look Display", tokens["display"]
    lines = [f'  --{k}: "{v}", {fallback.get(k, fallback["display"])};' if k in fallback or k == "display-base" else f"  --{k}: {v};" for k, v in tokens.items()]
    (out / "theme.css").write_text(f"/* generated by build.py from direction.json (look: {look}); do not edit */\n{faces}:root {{\n" + "\n".join(lines) + "\n}\n")
    default_in = direction.get("transition", "calm")
    if default_in not in TRANSITIONS:
        raise SystemExit(f"direction.json transition {default_in!r} not in {sorted(TRANSITIONS)}")
    end = direction.get("end")
    if end and not end.get("title"):
        raise SystemExit("direction.json end needs a title (the report's name), and may take sub and dur")
    grounds = direction.get("grounds", {})
    check_grounds(grounds)
    return {"look": look, "in": default_in, "hold": float(direction.get("hold", HOLD)), "end": end, "grounds": grounds}


DIGITS = "U+0030-0039, U+0025"  # 0-9 and %


def digit_faces(tokens):
    """@font-face rules for "Look Display": every glyph from the display face except digits, which come from the
    number face. A display face whose "1" carries a flag (Space Grotesk) reads "150" as "ı50"; this fixes it in
    every scene that uses the display face, with no scene code."""
    css = (HERE / "style.css").read_text()
    rules = re.findall(r'@font-face \{ font-family: "([^"]+)"; src: (url\([^)]*\) format\("woff2"\)); font-weight: (\d+); \}', css)
    disp = [(src, w) for fam, src, w in rules if fam == tokens["display"]]
    num = [(src, w) for fam, src, w in rules if fam == tokens["num"]]
    if not disp or not num:
        raise SystemExit(f"num font {tokens['num']!r} or display font {tokens['display']!r} has no @font-face in style.css")
    out = [f'@font-face {{ font-family: "Look Display"; src: {src}; font-weight: {w}; }}' for src, w in disp]
    out += [f'@font-face {{ font-family: "Look Display"; src: {src}; font-weight: {w}; unicode-range: {DIGITS}; }}' for src, w in num]
    return "\n".join(out) + "\n"


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
    # every still in shots/frames ships, so a custom scene can use one (a report figure) as assets/frames/<file>
    for still in (src / "shots/frames").glob("*") if (src / "shots/frames").is_dir() else []:
        shutil.copy2(still, HERE / "assets/frames" / still.name)

    out, t, modules = [], 0.0, []
    for b in beats:
        safe_id(b["id"])  # before it is used as a file name below
        hold = float(b.get("hold", look["hold"]))
        kind_in = b.get("in", look["in"])
        if kind_in not in TRANSITIONS:
            raise SystemExit(f"beat {b['id']}: in {kind_in!r} not in {sorted(TRANSITIONS)}")
        vstart = t + VOICE_LEAD
        silent = break_beat(b)
        if silent is not None:  # a chapter break: no voice, no caption, no hold
            b, hold = {**b, "dur": silent, "caption": "", "caption_words": []}, 0.0
        words = [{"w": w["w"], "s": round(vstart + w["s"], 3), "e": round(vstart + w["e"], 3)} for w in b["caption_words"]]
        if silent is None:
            shutil.copy2(src / "voice" / f"{b['id']}.wav", HERE / "assets/voice" / f"{b['id']}.wav")
        scene = load_scene(b, beats_path.parent)
        beat = {
            "id": safe_id(b["id"]), "kind": b["kind"], "scene": scene, "caption": b["caption"],
            "start": round(t, 3), "vstart": round(vstart, 3), "dur": b["dur"],
            "end": round(t + b["dur"] + hold, 3), "in": kind_in, "words": words,
            "ground": beat_ground(scene, look["grounds"], b["id"]),
        }
        check_words(b, beat["scene"], words)
        if beat["scene"]["type"] == "custom":
            mod = copy_module(beat["scene"], beats_path.parent)
            if mod not in modules:
                modules.append(mod)
        if b["kind"] == "ui":
            s = tour[b["id"]]
            imgs = [safe_name(s["after"])] + ([safe_name(s["before"]["img"])] if s.get("before") else [])
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
    voiced = [b for b in out if b["kind"] != "break"]
    end = None
    if look["end"]:  # an end card after the last voice: the report's name and where to find it
        end = {"title": look["end"]["title"], "sub": look["end"].get("sub", ""), "start": total, "credits": []}
        total = round(total + float(look["end"].get("dur", END_DUR)), 2)
    for i, beat in enumerate(out):
        groups = split_phrases(beat["words"], beat["caption"]) if beat["words"] else []
        last_end = (out[i + 1]["start"] - HIDE_BEFORE_NEXT) if i + 1 < len(out) else (end["start"] - HIDE_BEFORE_NEXT if end else total)
        beat["phrases"] = []
        for j, g in enumerate(groups):
            # the first phrase is up from the beat start, so the band is never empty while a new scene comes in
            show = round(beat["start"] + 0.05 if j == 0 else g[0]["s"] - SHOW_LEAD, 3)
            hide = round(groups[j + 1][0]["s"] - SHOW_LEAD, 3) if j + 1 < len(groups) else round(last_end, 3)
            beat["phrases"].append({"show": show, "hide": hide, "wi": [beat["words"].index(w) for w in g]})

    # icons (inlined SVG), images and credits from <src>/media (scripts/fetch_assets.py); empty when there is none
    media = collect_media(src, out=HERE)
    owed = [c["credit_text"] for c in media.get("credits", []) if gate(c.get("license", ""))[1] == "by"]
    if owed and not end:
        raise SystemExit('media under CC BY needs a visible credit: add "end" to direction.json (the end card lists it)')
    if end:
        end["credits"] = owed
    data = {"width": 1920, "height": 1080, "fps": 30, "total": total, "captions": args.captions, "beats": out, "end": end, "media": media}
    (HERE / "data.js").write_text("// generated by build.py; do not edit\nwindow.TEASER = " + json.dumps(data, indent=1) + ";\n")

    audio = "\n".join(
        f'      <audio id="vo-{b["id"]}" src="assets/voice/{b["id"]}.wav" data-start="{b["vstart"]}" '
        f'data-duration="{b["dur"]}" data-track-index="{10 + k}"></audio>'
        for k, b in enumerate(voiced)
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
