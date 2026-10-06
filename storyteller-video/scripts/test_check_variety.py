"""python3 -m pytest -q test_check_variety.py"""
from check_variety import check


def beat(i, kind="motion", type_="chips", words=20, **kw):
    return {"id": f"b{i:02d}", "kind": kind, "text": " ".join(["word"] * words), "scene": {"type": type_}, **kw}


def rules(beats, direction=None):
    return {rule: ok for rule, ok, _ in check(beats, direction or {"look": "night", "transition": "fade"})}


def varied():
    types = ["statement", "diagram", "ui", "compare", "counters", "ui", "diagram", "layers"]
    bs = [beat(i, "ui" if t == "ui" else "motion", t, words=8 + 4 * (i % 4)) for i, t in enumerate(types)]
    bs[3]["hold"] = 1.6
    bs[5]["in"] = "zoom"
    return bs


def test_varied_sheet_passes():
    assert all(rules(varied()).values())


def test_three_neighbours_of_one_type_fail():
    bs = varied()
    bs[1]["scene"]["type"] = bs[2]["scene"]["type"] = bs[3]["scene"]["type"] = "chips"
    bs[2]["kind"] = "motion"
    assert not rules(bs)["type runs"]


def test_ui_tours_are_exempt_from_share_but_not_runs():
    bs = [beat(i, "ui", "ui") if i % 2 else beat(i, type_=t) for i, t in enumerate(["statement", "", "diagram", "", "compare", "", "layers", ""])]
    r = rules(bs)
    assert r["type share"] and r["type runs"]


def test_one_type_on_most_beats_fails_share():
    bs = varied()
    for i in (0, 3, 7):
        bs[i]["scene"]["type"] = "diagram"
    assert not rules(bs)["type share"]


def test_even_tempo_and_no_held_beat_fail():
    bs = [beat(i, type_=t, words=20) for i, t in enumerate(["statement", "diagram", "compare", "counters"])]
    assert not rules(bs)["tempo"]


def test_measured_length_wins_over_the_word_estimate():
    bs = [beat(i, type_=t, words=20, dur=d) for i, (t, d) in enumerate([("statement", 3.0), ("diagram", 9.0), ("compare", 6.0)])]
    bs[1]["hold"] = 1.5
    assert rules(bs)["tempo"]


def test_one_cut_kind_fails_and_no_primary_fails():
    bs = varied()
    bs[5].pop("in")
    assert not rules(bs)["cuts"]
    for b, k in zip(bs[1:], ["push", "zoom", "wipe", "cut", "fade", "calm", "push"]):
        b["in"] = k
    assert not rules(bs)["cuts"]


def test_missing_look_fails():
    assert not rules(varied(), {"transition": "fade"})["look"]
