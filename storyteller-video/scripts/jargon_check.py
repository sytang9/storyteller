"""Flag jargon and long sentences in a teaser script before any voice or render.

    python3 jargon_check.py beats.json [terms.txt]

Each caption sentence prints with [word:tag] marks:
  A  an acronym (2+ capitals)            T  a word in terms.txt (the report's private meanings: claim, memo, pots)
  R  a rare word (Zipf < 3.0)            C  a word to look at (Zipf 3.0-3.8; not counted)
R and C need `pip install wordfreq`; without it only A and T are flagged, so lean on the cold read.
Pass: no sentence brings 2+ new names, at most 5 distinct new names, every sentence 20 words or fewer.
A name is new at its first use; adjacent flagged words count as one name ("New York").
"""
import json
import re
import sys

RARE, LOOK, MAX_WORDS, MAX_NAMES = 3.0, 3.8, 20, 5
try:
    from wordfreq import zipf_frequency
except ImportError:
    zipf_frequency = None


def zipf(w):
    stems = [w] + [w[: -len(s)] for s in ("s", "es", "ed", "ing") if w.endswith(s) and len(w) > len(s) + 2]
    return max(zipf_frequency(x, "en") for x in stems)


def tag(token, terms):
    w = re.sub(r"[^\w'-]", "", token).lower().removesuffix("'s")
    if not w:
        return ""
    if re.sub(r"[^\w]", "", token).isupper() and len(re.sub(r"[^\w]", "", token)) > 1:
        return "A"
    if w in terms:
        return "T"
    if zipf_frequency is None or not w.replace("-", "").isalpha():
        return ""
    z = min(zipf(p) for p in w.split("-") if p)
    return "R" if z < RARE else "C" if z < LOOK else ""


def main(beats_file, terms_file=None):
    terms = {t.strip().lower() for t in open(terms_file) if t.strip()} if terms_file else set()
    seen, crowded, long_ones = set(), 0, 0
    for beat in json.load(open(beats_file)):
        for sent in re.split(r"(?<=[.?!])\s+", beat["caption"].strip()):
            toks = sent.split()
            marks = [tag(t, terms) for t in toks]
            names, i = set(), 0
            while i < len(toks):
                if marks[i] in ("A", "T", "R"):
                    j = i
                    while j + 1 < len(toks) and marks[j + 1] in ("A", "T", "R") and not toks[j].endswith(","):
                        j += 1
                    names.add(re.sub(r"['’]s$", "", " ".join(toks[i:j + 1]).strip(".,?!:;").lower()))  # "Acme's" = "Acme"
                    i = j + 1
                else:
                    i += 1
            fresh = names - seen
            seen |= names
            crowded += len(fresh) > 1
            long_ones += len(toks) > MAX_WORDS
            flags = ("!" if len(fresh) > 1 else " ") + ("L" if len(toks) > MAX_WORDS else " ")
            print(f"{beat['id']} new={len(fresh)}{flags}", " ".join(f"[{t}:{m}]" if m else t for t, m in zip(toks, marks)))
    ok = crowded == 0 and long_ones == 0 and len(seen) <= MAX_NAMES
    print(f"\n{len(seen)} distinct names (max {MAX_NAMES}): {sorted(seen)}")
    print(f"{crowded} sentences with 2+ new names; {long_ones} sentences over {MAX_WORDS} words; "
          f"{'PASS' if ok else 'FIX'}{'' if zipf_frequency else '  (no wordfreq: rare words not checked)'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
