"""Inline figures and maps into a story source, then render it with render.py.

    python3 build_story.py story.src.md      # -> story.md -> story.html

`<!-- FIG:name [kind] -->` is replaced by figs/name.svg in a <figure class="full" data-kind="kind">.
`<!-- MAP:name [height] -->` embeds figs/name.html (any self-contained interactive page) full-width, 86% of the screen tall, with a
full-screen link, plus
figs/name.png for print; the snapshot is taken with Playwright when it is missing.
A `*Caption.*` line right after either marker becomes the <figcaption>.
Each chapter (`<section class="acc-*">` + `<p class="chapter-no">NN<span>..</span></p>` + heading) gets an
anchor, and a numbered chapter menu goes at `<!-- MENU -->`, or before the first chapter.
Each evidence drawer's <summary> gets a kicker (unless it has a .kick span) and a count of its tables,
pictures and notes.
Missing files stop the build instead of leaving a gap.
"""
import pathlib
import re
import subprocess
import sys

RENDER = pathlib.Path(__file__).resolve().parent / "render.py"
MARK = re.compile(r"^<!-- (FIG|MAP):([\w-]+)(?: ([\w-]+))? -->\n(?:\*(.+?)\*\n)?", re.M)


OLD_CONTROLLER = re.compile(r"<script data-diagram-controls>.*?</script>", re.S)
CHAPTER = re.compile(r'<section class="(acc-[\w-]+)"[^>]*>\s*<p class="chapter-no">(\d+)<span>(.*?)</span></p>\s*#{2,3} (.+)')


def add_menu(body: str) -> str:
    """Anchor every chapter opener and put a numbered menu of chapters before the first one."""
    items = CHAPTER.findall(body)
    if not items:
        return body
    for _, num, _, _ in items:
        body = body.replace(f'<p class="chapter-no">{num}<span>', f'<p class="chapter-no" id="ch-{num}">{num}<span>', 1)
    lis = "".join(f'<li class="{acc}"><a href="#ch-{num}"><span class="n">{num}</span><span>{head.strip()}</span></a></li>'
                  for acc, num, _, head in items)
    menu = f'<ol class="chapter-menu" aria-label="Chapters">{lis}</ol>\n\n'
    if "<!-- MENU -->" in body:
        return body.replace("<!-- MENU -->", menu, 1)
    first = body.index(CHAPTER.search(body).group(0))
    return body[:first] + menu + body[first:]


DRAWER = re.compile(r'(<details class="evidence"[^>]*>\s*<summary>)(.*?)(</summary>)(.*?)(?=</details>)', re.S)


def dress_drawers(body: str) -> str:
    """Give each evidence drawer a kicker (default "Under the hood") and a count of what is inside."""
    def dress(m: re.Match) -> str:
        head, label, close, inside = m.groups()
        m2 = re.match(r'\s*(<span class="kick">.*?</span>)\s*(.*)', label, re.S)
        kick, title = m2.groups() if m2 else ('<span class="kick">Under the hood</span>', label)
        label = f'{kick} <span class="t">{title.strip()}</span>'
        n = {"table": len(re.findall(r"^\|[ :-]*-{3}", inside, re.M)) + inside.count("<table"),
             "picture": len(re.findall(r"<img|<figure|!\[", inside)),
             "note": len(re.findall(r"^(?:[-*]|\d+\.) ", inside, re.M))}
        count = " · ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in n.items() if v)
        return head + label + (f' <span class="count">{count}</span>' if count else "") + close + inside
    return DRAWER.sub(dress, body)


def snapshot(html: pathlib.Path, png: pathlib.Path) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(html.resolve().as_uri())
        pg.wait_for_timeout(1500)
        pg.screenshot(path=str(png))
        b.close()


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1]).resolve()
    figs = src.parent / "figs"
    text = src.read_text()
    need = {"FIG": ".svg", "MAP": ".html"}
    missing = [f"{n}{need[k]}" for k, n, _, _ in MARK.findall(text) if not (figs / f"{n}{need[k]}").exists()]
    if missing:
        sys.exit(f"missing in {figs}: {', '.join(missing)}")

    def inline(m: re.Match) -> str:
        kind, name, opt, cap = m.groups()
        caption = f"\n<figcaption>{cap}</figcaption>" if cap else ""
        if kind == "FIG":
            dk = f' data-kind="{opt}"' if opt else ""
            return f'<figure class="full"{dk}>\n{(figs / f"{name}.svg").read_text().strip()}{caption}\n</figure>\n'
        png = figs / f"{name}.png"
        if not png.exists():
            snapshot(figs / f"{name}.html", png)
        style = f' style="height:{opt}px"' if opt and opt.isdigit() else ""
        return (f'<figure class="full map-fig" data-kind="map">\n<iframe class="map" src="figs/{name}.html" title="{cap or name}" loading="lazy"{style}></iframe>\n'
                f'<a class="map-open" href="figs/{name}.html" target="_blank" rel="noopener">Open the map full screen</a>\n'
                f'<img class="map-print" src="figs/{name}.png" alt="{cap or name}">{caption}\n</figure>\n')

    body = dress_drawers(add_menu(MARK.sub(inline, text)))
    body = OLD_CONTROLLER.sub("", body)  # render.py ships one motion controller; a second copy would bind twice
    stem = src.name.removesuffix(".src.md").removesuffix(".md")
    out = src.with_name(f"{stem}.md")
    if out == src:
        sys.exit("name the source <name>.src.md so the rendered .md does not overwrite it")
    out.write_text(body)
    subprocess.run([sys.executable, str(RENDER), str(out)], check=True)


if __name__ == "__main__":
    main()
