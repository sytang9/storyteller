from build import split_phrases


def words(caption):
    return [{"w": w, "s": i, "e": i + 1} for i, w in enumerate(caption.split())]


def texts(caption):
    return [" ".join(w["w"] for w in g) for g in split_phrases(words(caption), caption)]


def test_short_caption_stays_one_phrase():
    c = "In one app, the same repair is one job, with seven steps in one place."
    assert texts(c) == [c]


def test_sentence_and_comma_breaks():
    c = "We tested 245 wrong turns. Ten faults turned up, all ten are fixed, and the re-test passes 116 of 116."
    assert texts(c) == ["We tested 245 wrong turns.", "Ten faults turned up, all ten are fixed,", "and the re-test passes 116 of 116."]


def test_long_caption_breaks_at_early_comma_and_every_phrase_fits():
    c = "The history keeps every move, even the engineer's query that sent the request back once."
    out = texts(c)
    assert out[0] == "The history keeps every move,"
    assert all(len(p) <= 80 for p in out)


def test_no_word_lost():
    c = " ".join(["word"] * 60)
    assert " ".join(texts(c)) == c and all(len(p) <= 80 for p in texts(c))


import pytest
from build import check_words, copy_module


def test_label_word_must_be_in_caption():
    ws = words("One job, seven steps.")
    check_words({"id": "x"}, {"labels": [{"word": "steps"}], "click": "job"}, ws)
    with pytest.raises(SystemExit):
        check_words({"id": "x"}, {"labels": [{"word": "baton"}]}, ws)


def test_custom_module_must_be_a_plain_existing_js_file(tmp_path):
    for bad in [None, "../x.js", "x.txt", "missing.js"]:
        with pytest.raises(SystemExit):
            copy_module({"module": bad}, tmp_path)


# ---- looks (presets.json) and direction.json ----
import json
from pathlib import Path

import pytest

from build import load_direction

PRESETS = {k: v for k, v in json.loads((Path(__file__).parent / "presets.json").read_text()).items() if k[0] != "_"}


def contrast(a, b):
    def lum(h):
        c = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_every_look_keeps_text_readable(name):
    p = PRESETS[name]
    # body text and captions on the ground and on cards (WCAG AA 4.5:1); role colours carry big numbers and labels (3:1)
    for ground in ("bg", "surface"):
        assert contrast(p["ink"], p[ground]) >= 4.5, (name, "ink", ground)
        assert contrast(p["mute"], p[ground]) >= 4.5, (name, "mute", ground)
    assert contrast(p["accent"], p["on-accent"]) >= 4.5, (name, "on-accent")
    for role in ("accent", "blue", "teal", "purple", "orange", "good"):
        assert contrast(p[role], p["bg"]) >= 3, (name, role)


def test_direction_writes_theme_and_rejects_unknown_values(tmp_path):
    d = tmp_path / "direction.json"
    d.write_text(json.dumps({"look": "night", "override": {"accent": "#ff8800"}, "transition": "push", "hold": 0.5}))
    assert load_direction(d, tmp_path) == {"look": "night", "in": "push", "hold": 0.5, "end": None}
    theme = (tmp_path / "theme.css").read_text()
    assert "--accent: #ff8800;" in theme and '--display-base: "Space Grotesk Video"' in theme
    for bad in ({"look": "neon"}, {"look": "_doc"}, {"look": "paper", "transition": "spin"}, {"look": "paper", "end": {"sub": "x"}}):
        d.write_text(json.dumps(bad))
        with pytest.raises(SystemExit):
            load_direction(d, tmp_path)
    assert load_direction(tmp_path / "missing.json", tmp_path)["look"] == "paper"


def test_number_face_swaps_only_the_digits_of_the_display_face(tmp_path):
    d = tmp_path / "direction.json"
    d.write_text(json.dumps({"look": "night"}))
    load_direction(d, tmp_path)
    theme = (tmp_path / "theme.css").read_text()
    assert '--display: "Look Display"' in theme and '--num: "Inter Video"' in theme
    faces = [l for l in theme.splitlines() if l.startswith("@font-face")]
    digit = [l for l in faces if "unicode-range" in l]
    assert digit and all("inter-latin" in l for l in digit)  # digits from the number face
    assert all("space-grotesk" in l for l in faces if l not in digit)  # everything else from the display face
    d.write_text(json.dumps({"look": "paper"}))  # no "num": the display face is used as is
    load_direction(d, tmp_path)
    assert "@font-face" not in (tmp_path / "theme.css").read_text()


def test_direction_tokens_cannot_carry_css(tmp_path):
    d = tmp_path / "direction.json"
    for bad in ({"accent": "red; } body{background:url(http://x/y)} :root{--x:1"}, {"sans": 'x"; } @import url(http://x/a.css); a{--q:"'},
                {"sans": "Comic Sans"}, {"evil;key": "1"}):
        d.write_text(json.dumps({"look": "paper", "override": bad}))
        with pytest.raises(SystemExit):
            load_direction(d, tmp_path)
