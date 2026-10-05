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
