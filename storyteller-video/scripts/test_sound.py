"""python3 -m pytest -q test_sound.py"""
import numpy as np

from sound import POP_GAP, POP_MAX, SR, UNDER_DB, act_switch, bank, duck, fit_under, music, plan


def words(start, text, step=0.5):
    return [{"w": w, "s": start + 0.4 + i * step, "e": start + 0.4 + i * step + 0.4} for i, w in enumerate(text.split())]


def beat(id_, start, text="one two three four five six seven eight", **kw):
    n = len(text.split())
    return {"id": id_, "kind": "motion", "start": start, "end": start + 0.4 + n * 0.5, "in": "fade", "words": words(start, text), "scene": {}, **kw}


def names(cues):
    return [c[1] for c in cues]


def test_cuts_tick_sweeps_whoosh_and_fades_stay_quiet():
    data = {"beats": [beat("b1", 0), beat("b2", 5, **{"in": "cut"}), beat("b3", 10, **{"in": "wipe"}), beat("b4", 15)]}
    cues = plan(data, {})
    assert names(cues) == ["tick", "whoosh"]
    assert cues[1][0] < 10  # a whoosh leads into its cut


def test_world_camera_move_whooshes_only_when_the_view_changes():
    w = lambda v: {"view": v, "shot": "wide"}
    data = {"beats": [beat("b1", 0, world=w("wide")), beat("b2", 5, world=w("close")), beat("b3", 10, world=w("close"))]}
    assert names(plan(data, {})) == ["soft-whoosh"]


def test_anchor_pops_keep_a_gap_and_stop_at_the_cap():
    b = beat("b1", 0, text="a b c d e f g h i j k l")
    anchors = [{"word": w} for w in "a b c d e f g h i j k l".split()]
    cues = [c for c in plan({"beats": [b]}, {"b1": {"anchor_words": anchors}}) if c[1] == "pop"]
    times = [c[0] for c in cues]
    assert len(cues) == POP_MAX
    assert all(t2 - t1 >= POP_GAP for t1, t2 in zip(times, times[1:]))


def test_template_scene_words_pop_without_a_brief():
    b = beat("b1", 0, scene={"type": "statement", "in": ["three", "seven"], "em": {"text": "x", "word": "seven"}})
    assert [c[1] for c in plan({"beats": [b]}, {})] == ["pop", "pop"]


def test_break_shimmers_without_pops_and_type_beat_thuds():
    data = {"beats": [beat("b1", 0, scene={"type_beat": True, "in": ["three"]}), beat("b2", 5, kind="break")], "end": {"start": 9}}
    assert names(plan(data, {})) == ["thud", "pop", "shimmer", "success"]


def test_bank_is_the_same_every_run_and_stays_under_full_scale():
    a, b = bank(), bank()
    assert set(a) == {"tick", "whoosh", "soft-whoosh", "thud", "shimmer", "pop", "success"}
    assert all(np.array_equal(a[k], b[k]) and 0 < np.max(np.abs(a[k])) <= 1 for k in a)


def test_act_two_starts_at_the_first_break_and_music_fades_out():
    data = {"beats": [beat("b1", 0), beat("b2", 5, kind="break"), beat("b3", 9)]}
    assert act_switch(data) == 5 and act_switch({"beats": [beat("b1", 0)]}) == 0
    m = music(12.0, 5.0)
    assert len(m) == 12 * SR and abs(np.max(np.abs(m)) - 1) < 1e-5 and abs(m[-1]) < 1e-3


def test_duck_lowers_the_bed_only_while_the_voice_speaks():
    voice = np.zeros(SR * 3, np.float32)
    voice[SR // 2 : SR] = 0.5 * np.sin(np.arange(SR // 2) * 0.1)
    voice[int(1.2 * SR) : int(1.5 * SR)] = 0.5 * np.sin(np.arange(int(0.3 * SR)) * 0.1)
    d = duck(voice)
    assert d[0] > 0.95 and d[int(0.75 * SR)] < 0.5 and d[int(2.5 * SR)] > 0.95
    assert d[int(1.1 * SR)] < 0.5  # a 0.2 s pause keeps the duck: no pumping between phrases


def test_a_cue_over_speech_sits_under_the_voice_and_keeps_its_level_in_a_gap():
    voice = np.zeros(SR, np.float32)
    voice[: SR // 2] = 0.1 * np.sin(np.arange(SR // 2) * 0.1)
    cue = bank()["pop"] * 0.5
    g = fit_under(voice, 0.1, cue)
    n = len(cue)
    ratio = 20 * np.log10(np.sqrt(np.mean(voice[int(0.1 * SR) : int(0.1 * SR) + n] ** 2)) / np.sqrt(np.mean((cue * g) ** 2)))
    assert abs(ratio - UNDER_DB) < 0.1
    assert fit_under(voice, 0.8, cue) == 1.0
