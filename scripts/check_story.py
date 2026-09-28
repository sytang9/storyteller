"""Check a rendered story page for objective defects only; taste is left to the writer.

    python3 check_story.py story.html [--ledger ledger.json] [--source old_report ...]

ERRORs (exit 1): unfilled {{placeholders}}; the frame is incomplete (answer block, TL;DR row,
chapter menu, a not-sure section, a next section); a figure without a caption; a drawer inside a
drawer; a ledger number missing from the page; a source number neither on the page nor in the
ledger's "dropped" list. The last line prints chapter, figure and visible-word counts.

ledger.json: {"numbers": [{"value": "84%", "what": "...", "baseline": "...", "source": "..."}],
              "dropped": [{"value": "0.03", "reason": "..."}]}   # value may also be a list
"""
import argparse
import copy
import json
import pathlib
import re
import sys

from bs4 import BeautifulSoup

NUM = re.compile(r"(?<![\w.])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)?x)(?![\w])")
FIXED = {"answer": r"^the answer", "unsure": r"not sure|caveat|unknown|limit", "next": r"^what'?s next|^what is next|^next"}
FRAME = re.compile(r"^(the answer|what we'?re not sure about|what we are not sure about|what'?s next|what is next|appendix|contents)$", re.I)


def norm(s):
    return re.sub(r"\s+", "", s).replace(",", "").lower()


def text_of(path):
    raw = pathlib.Path(path).read_text(errors="ignore")
    if pathlib.Path(path).suffix in (".html", ".htm"):
        soup = BeautifulSoup(raw, "html.parser")
        for t in soup(["script", "style"]):
            t.decompose()
        return soup.get_text(" ")
    raw = re.sub(r"<(style|script)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--ledger")
    ap.add_argument("--source", nargs="*", default=[])
    a = ap.parse_args()
    soup = BeautifulSoup(pathlib.Path(a.page).read_text(), "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    page = soup.get_text(" ")
    errors = []
    if "{{" in page:
        i = page.index("{{")
        errors.append(f"unfilled placeholder: …{page[i:i + 60]}…")

    h2 = soup.find_all("h2")
    found = {k: next((h for h in h2 if re.search(rx, h.get_text(" ").strip(), re.I)), None) for k, rx in FIXED.items()}
    for k, label in (("answer", "'The answer'"), ("unsure", "a what-we're-not-sure-about"), ("next", "a what's-next")):
        if not found[k]:
            errors.append(f"frame incomplete: no {label} section")
    ans = soup.find(class_="answer")
    if not ans or not ans.get_text(strip=True):
        errors.append('no answer block (<div class="answer"> with 1-2 sentences)')
    tldr = soup.find(class_="tldr")
    if not tldr or not 2 <= len(tldr.find_all("div", recursive=False)) <= 4:
        errors.append('no TL;DR row on the first screen (<div class="tldr"> with 3 cards)')

    chapters = [h for h in soup.find_all(["h2", "h3"]) if not FRAME.match(h.get_text(" ").strip())
                and not h.find_parent("details")]
    if not chapters:
        errors.append("no story chapters between the answer and the caveats")
    if len(chapters) >= 2 and not soup.find(class_="chapter-menu"):
        errors.append("no chapter menu: wrap chapters in <section class=\"acc-*\"> with a .chapter-no opener so the build makes it")
    for f in soup.find_all("figure"):
        if (f.find("svg") or f.find("img") or f.find("iframe")) and not (f.find("figcaption") and f.find("figcaption").get_text(strip=True)):
            name = f.find("title").get_text(strip=True) if f.find("title") else (f.find("img") or {}).get("alt", "?")
            errors.append(f"figure without a caption: '{name[:60]}'")
    if any(d.find_parent("details") for d in soup.find_all("details")):
        errors.append("a drawer inside a drawer (nested <details>)")

    visible = copy.copy(soup)
    # SVG text is picture, not reading load; the menu and <title> repeat headlines the build wrote
    for d in visible.find_all(["details", "nav", "svg", "title"]) + visible.find_all(class_="chapter-menu"):
        d.decompose()
    words = len(visible.get_text(" ").split())

    have, dropped = norm(page), set()
    if a.ledger:
        led = json.loads(pathlib.Path(a.ledger).read_text())
        for d in led.get("dropped", []):
            for v in d["value"] if isinstance(d["value"], list) else [d["value"]]:
                dropped.add(norm(str(v)))
        for n in led.get("numbers", []):
            if norm(str(n["value"])) not in have:
                errors.append(f"ledger number not on the page: {n['value']} ({n.get('what', '')[:50]})")
    missing = [m for s in a.source for m in sorted(set(NUM.findall(text_of(s))))
               if norm(m) not in have and norm(m) not in dropped]
    if missing:
        errors.append(f"{len(missing)} source numbers neither on the page nor in ledger 'dropped': "
                      + ", ".join(missing[:40]) + (" …" if len(missing) > 40 else ""))

    for e in errors:
        print(f"ERROR     {e}")
    print(f"\n{len(chapters)} chapters, {len(soup.find_all('figure'))} figures, {words} visible words, "
          f"{len(errors)} errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
