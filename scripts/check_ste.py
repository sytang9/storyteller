"""Check a report against the ASD-STE100 rules that can be tested mechanically.

    python3 check_ste.py <file>             # full STE: external reports, investigations, guides
    python3 check_ste.py --lite <file>      # STE-lite: internal writing, specs, contracts

Pick the tier by what the text does, not by who reads it. Full STE covers external narrative and
procedural writing: reports, investigations, runbooks, guides -- text that explains a finding or
instructs a reader. STE-lite covers internal writing and external normative documents:
specifications, requirements, API contracts, acceptance criteria -- text that defines obligations.

Full STE bans -ing forms and passive voice outright. STE-lite checks structure only: sentence
length and plain word choice. It deliberately does NOT flag hedges or long conditional sentences,
because calibrated uncertainty and causal structure are technical content, not style defects.
Defined terms (see DEFINED_TERMS) outrank the approved-word list in both tiers.
"""
import pathlib
import re
import sys

MAX_DESCRIPTIVE = 25
MAX_PROCEDURAL = 20

# STE bans -ing VERB forms. Established nouns and adjectives that end in -ing are permitted.
ING_ALLOWED = {"during", "string", "thing", "nothing", "something", "according", "following",
               "meaning", "warning", "setting", "reading", "heading", "training", "building",
               "engineering", "learning", "morning", "evening", "ring", "spring", "missing",
               "remaining", "existing", "leading", "operating", "processing"}
# words STE replaces with a simpler approved equivalent
NOT_APPROVED = {
    "utilize": "use", "utilise": "use", "leverage": "use", "commence": "start",
    "terminate": "stop", "endeavour": "try", "approximately": "about",
    "in order to": "to", "due to the fact": "because", "prior to": "before",
    "subsequent to": "after", "facilitate": "help", "obtain": "get",
    "perform": "do", "additional": "more", "assist": "help", "require": "need",
    "sufficient": "enough", "indicate": "show", "verify": "check",
}
# Defined terms outrank the approved-word list, in both tiers. Where a standard or the document's
# own glossary defines a word, simplifying it damages the document: "verification" is ISO 29148
# vocabulary and appears in every traceability row of an SRS, so "verify -> check" is wrong there.
# Add a term here only when it is genuinely defined somewhere, not merely because it reads better.
DEFINED_TERMS = {"verify"}
PASSIVE = re.compile(r"\b(is|are|was|were|be|been|being)\s+\w+(ed|en)\b", re.I)


# span included: the .kv data grids use spans as cells, and without this they concatenate
# into one long pseudo-sentence and trip the length rule.
BLOCK = r"</?(p|div|li|td|th|tr|h[1-6]|ul|ol|table|section|header|details|summary|br|pre|span)\b[^>]*>"


SEP = "\x00"


def visible_text(html):
    """Block tags become separators, so prose is not merged with table cells and headings.

    Order matters. Newlines from the *source* formatting must be collapsed to spaces, otherwise a
    sentence wrapped across two lines in the generator is measured as two short sentences and long
    sentences slip through the length check.
    """
    # svg is dropped with script/style: diagram labels are not prose, and concatenating
    # them produces one giant pseudo-sentence that trips the length rule.
    body = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " ", html, flags=re.S)
    body = re.sub(BLOCK, SEP, body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    for ent, ch in (("&middot;", "-"), ("&amp;", "&"), ("&nbsp;", " "), ("&mdash;", "-"),
                    ("&lt;", "<"), ("&gt;", ">"), ("&#9689;", " "), ("&rarr;", "->")):
        body = body.replace(ent, ch)
    body = re.sub(r"\s+", " ", body)          # collapse source line wraps FIRST
    return body.replace(SEP, "\n")            # then restore real block boundaries


def word_count(s):
    """Tokens with a letter or digit; a lone ":" left by stripped <b>/<dfn> markup is not a word."""
    return sum(1 for t in s.split() if re.search(r"\w", t))


def sentences(text):
    """Only real prose: skip headings, numbers, and table cells (short fragments)."""
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line or word_count(line) < 4:
            continue
        for raw in re.split(r"(?<=[.!?])\s+", line):
            s = raw.strip()
            # prose ends in punctuation; headings and cell values do not
            if word_count(s) >= 4 and re.search(r"[a-z]", s) and s.endswith((".", "!", "?", ";", ":")):
                yield s


# A sentence whose logic is carried by a subordinating conjunction, or a ", so" / ", but" clause link. STE-lite lets these run long:
# splitting them can hide which clause depends on which.
CONDITIONAL = re.compile(r"\b(if|unless|because|whereas|although|when|while|so that|"
                         r"rather than|only if|assuming)\b|, (so|but)\b", re.I)


if __name__ == "__main__":
    lite = "--lite" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    path = pathlib.Path(args[0])

    text = visible_text(path.read_text())
    sents = list(sentences(text))
    print(f"mode: {'STE-lite' if lite else 'full STE'}   file: {path.name}")
    print(f"sentences checked: {len(sents)}\n")

    issues = []
    for s in sents:
        n = word_count(s)
        if n > MAX_DESCRIPTIVE and not (lite and CONDITIONAL.search(s)):
            issues.append(("length", f"{n} words: {s[:110]}"))
        for bad, good in NOT_APPROVED.items():
            if bad in DEFINED_TERMS:
                continue
            if re.search(rf"\b{bad}\b", s, re.I):
                issues.append(("vocabulary", f"'{bad}' -> '{good}': {s[:90]}"))
        if lite:
            continue  # -ing forms and passive voice are full-STE rules only
        for m in re.finditer(r"\b(\w+ing)\b", s):
            w = m.group(1)
            if w.lower() not in ING_ALLOWED and not any(c.isupper() for c in w[1:]):  # skip names like RockWing
                issues.append(("-ing form", f"'{m.group(1)}': {s[:90]}"))
        if PASSIVE.search(s):
            issues.append(("passive", s[:110]))

    if not issues:
        print("PASS - no mechanical STE violations found.")
        sys.exit(0)

    by_kind = {}
    for kind, detail in issues:
        by_kind.setdefault(kind, []).append(detail)
    for kind, items in by_kind.items():
        print(f"--- {kind} ({len(items)}) ---")
        for i in items:
            print(f"  {i}")
        print()
    lengths = sorted((word_count(s) for s in sents), reverse=True)
    print(f"longest sentences: {lengths[:8]}")
    print(f"median length: {lengths[len(lengths)//2]} words")
