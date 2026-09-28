"""Render a Markdown story into one HTML page (and optionally a PDF) from the CSS and JS in assets/.

Adapted from the html-report skill's md_to_html.py.

For **authored** documents (proposals, progress reports, design notes) the
Markdown is the source of truth and the HTML is derived — so the `.md` and the
`.html` cannot drift, and Claude reads the ~3k-token `.md` instead of the
~26k-token `.html`. (For **generated** reports the build script is the source
and emits both; use `html_to_md.py` for that direction.)

    python3 md_to_html.py report.md              # -> report.html (+ report.pdf if the doc asks)
    python3 md_to_html.py report.md --pdf        # force a PDF for this run
    python3 md_to_html.py report.md --no-pdf     # skip it for this run

Per-document config lives in YAML frontmatter, so one script serves every
document:

    ---
    title: Give the html-report skill an output-target model
    font: serif                   # serif (default) | sans -- sans for dashboards
    layout: essay                 # essay (default) | wide -- wide for catalogues
    kicker: PROPOSAL              # optional eyebrow above the title
    dek: One sentence that states the finding.   # optional standfirst
    subtitle: Proposal · 2026-08-07 · Yann       # byline under the title
    theme: auto          # auto (default, OS + toggle) | light | dark (forced, no toggle)
    toc: true
    pdf: false           # internal — no client deliverable
    ---

The skill's components stay available inside the Markdown two ways:

  * **raw HTML blocks pass straight through** — stat grids, hand-built SVG
    figures, tab groups;
  * **`attr_list` decorates existing Markdown** — `{: .callout .warn }` on the
    line under a paragraph turns it into a callout, no HTML needed.

`attr_list` cannot attach attributes to a Markdown table (the attribute line is
swallowed as an extra row), so tables use a marker comment instead, which this
script stamps onto the next table:

    <!-- table: id=types sortable -->

    | Type | Score |
    |------|-------|

Bare words become `data-*` flags (`sortable` -> `data-sortable`); `id=` and
`class=` are set directly; any other `key=value` becomes `data-key="value"`.

A second marker promotes a blockquote into a margin note, which is what makes
the wide-screen layout carry information rather than air:

    <!-- sidenote: Sample -->

    > 2,701 line crops, detection held constant.

CSS and JS are not duplicated here — they are extracted at build time from the
skill's own reference files, so a theme edit propagates without touching this
script.
"""

from __future__ import annotations

import argparse
import html
import re
import shlex
import subprocess
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("error: markdown not installed. run: pip install markdown")

try:
    from bs4 import BeautifulSoup, Comment, NavigableString
except ImportError:
    sys.exit("error: beautifulsoup4 not installed. run: pip install beautifulsoup4")


SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"

THEMES = ("auto", "light", "dark")
FONTS = ("serif", "sans")
LAYOUTS = ("essay", "wide")



# ──────────────────────────────────────────────────────────────────────────
# Asset extraction — the reference .md files are the single source of truth
# ──────────────────────────────────────────────────────────────────────────

def _asset(name: str) -> str:
    """Read one stylesheet or script from assets/; a missing file stops the build."""
    path = ASSETS / name
    if not path.exists():
        raise SystemExit(f"error: {path} missing — cannot build")
    return path.read_text(encoding="utf-8")


def load_assets() -> dict[str, str]:
    # Order matters: layout consumes the theme's --measure, the story devices
    # restyle components, and print comes last so it wins the cascade.
    return {
        "theme_css": _asset("base/theme.css"),
        "layout_css": _asset("base/layout.css"),
        "component_css": _asset("base/components.css"),
        "widget_css": _asset("base/widgets.css"),
        "devices_css": _asset("story-devices.css"),
        "print_css": _asset("base/print.css"),
        "toolkit_js": _asset("base/toolkit.js"),
        "motion_js": _asset("motion.js"),  # a no-op when the page has no [data-motion-root]
    }


# ──────────────────────────────────────────────────────────────────────────
# Frontmatter — md.Meta values arrive as lists of strings
# ──────────────────────────────────────────────────────────────────────────

def meta_str(meta: dict, key: str, default: str = "") -> str:
    val = meta.get(key)
    if not val:
        return default
    return " ".join(str(v) for v in val).strip() or default


_COMMENT_RE = re.compile(r"\s+#.*$")


def _decomment(value: str) -> str:
    """Strip a trailing `# …` comment from a config value.

    `meta` is not a YAML parser, so `theme: auto  # auto | light | dark` arrives
    with the comment attached. Only applied to the enumerated/boolean settings —
    a title or subtitle may legitimately contain a '#'.
    """
    return _COMMENT_RE.sub("", value).strip()


def meta_choice(meta: dict, key: str, choices: tuple[str, ...], default: str) -> str:
    raw = _decomment(meta_str(meta, key, default)).lower() or default
    if raw not in choices:
        raise SystemExit(f"error: frontmatter '{key}: {raw}' unknown (use {' | '.join(choices)})")
    return raw


_TRUE = {"true", "yes", "1", "on"}
_FALSE = {"false", "no", "0", "off", "none", ""}


def meta_bool(meta: dict, key: str, default: bool) -> bool:
    """Parse a frontmatter flag.

    `md.Meta` returns `['false']` for `pdf: false`, which is truthy — so the
    value must be parsed, never truth-tested.
    """
    raw = _decomment(meta_str(meta, key)).lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return default if raw == "" else False
    raise SystemExit(f"error: frontmatter '{key}: {raw}' is not a boolean (use true/false)")


# ──────────────────────────────────────────────────────────────────────────
# Table marker comments
# ──────────────────────────────────────────────────────────────────────────

_MARKER_RE = re.compile(r"^\s*table:\s*(.*)$", re.S)
_SIDENOTE_RE = re.compile(r"^\s*sidenote:?\s*(.*)$", re.S)

# An id is interpolated into a CSS selector (`#id`) for the filter input, so it
# must be a plain identifier — a stray '(' or '.' would break querySelector and
# abort the whole toolkit script.
_SAFE_ID_RE = re.compile(r"^[A-Za-z][\w-]*$")

# Marker keys become attribute names, so the same shape applies. Without this a
# fallback whitespace split can emit nonsense like `data-don't=""`.
_SAFE_NAME_RE = re.compile(r"^[A-Za-z][\w-]*$")


def _tokenise(spec: str, raw_comment: str) -> list[str]:
    """Split a marker body, tolerating an unbalanced quote (e.g. "don't")."""
    try:
        return shlex.split(spec)
    except ValueError:
        print(f"warning: unbalanced quote in table marker, splitting on whitespace: "
              f"{raw_comment.strip()}", file=sys.stderr)
        return spec.split()


def apply_sidenote_markers(soup: BeautifulSoup) -> None:
    """`<!-- sidenote: LABEL -->` turns the NEXT blockquote into a margin note.

    A margin note is the whole reason an HTML report is worth more than the
    Markdown it came from: it puts a caveat, a sample size or a definition
    beside the sentence it qualifies instead of interrupting it. Authors should
    not have to drop into raw HTML for that, so it gets the same marker grammar
    the tables already use.

    At narrow widths and on paper the aside flows back inline, so one source
    serves both -- see references/layout.md.
    """
    for comment in list(soup.find_all(string=lambda s: isinstance(s, Comment))):
        m = _SIDENOTE_RE.match(str(comment))
        if not m:
            continue
        quote = comment.find_next("blockquote")
        if quote is None:
            print(f"warning: sidenote marker with no blockquote after it: "
                  f"{str(comment).strip()}", file=sys.stderr)
            comment.extract()
            continue
        quote.name = "aside"
        quote["class"] = "sidenote"
        label = m.group(1).strip()
        if label:
            tag = soup.new_tag("span")
            tag["class"] = "sn-label"
            tag.string = label
            quote.insert(0, tag)
        comment.extract()


def apply_table_markers(soup: BeautifulSoup) -> None:
    """`<!-- table: id=x sortable filter="Filter…" -->` configures the next table.

    `filter` is not an attribute on the table — the toolkit reads `[data-filter]`
    on an *input* holding a CSS selector — so it emits a filter box before the
    table and points it at the table's id, generating one if needed.
    """
    auto_id = 0
    for comment in list(soup.find_all(string=lambda s: isinstance(s, Comment))):
        m = _MARKER_RE.match(str(comment))
        if not m:
            continue
        table = comment.find_next("table")
        if table is None:
            print(f"warning: table marker with no table after it: {str(comment).strip()}",
                  file=sys.stderr)
            comment.extract()
            continue

        filter_placeholder: str | None = None
        for token in _tokenise(m.group(1), str(comment)):
            key, sep, value = token.partition("=")
            key = key.strip().strip(",;")          # tolerate "sortable, filter=…"
            if not key:
                continue
            if key == "filter":
                filter_placeholder = value if sep else ""
                filter_placeholder = filter_placeholder or "Filter…"
                continue
            if not _SAFE_NAME_RE.match(key):
                print(f"warning: ignoring unusable table-marker token {token!r} in "
                      f"{str(comment).strip()}", file=sys.stderr)
                continue
            if key in ("id", "class"):
                table[key] = value
                if key == "id" and not _SAFE_ID_RE.match(value):
                    print(f"warning: table id {value!r} is not a plain identifier — "
                          f"'#{value}' will not work as a CSS selector", file=sys.stderr)
            else:
                table[f"data-{key}"] = value

        if filter_placeholder is not None:
            tid = table.get("id") or ""
            if not _SAFE_ID_RE.match(tid):
                if tid:
                    print(f"warning: table id {tid!r} is not a plain identifier; "
                          f"generating one for the filter box", file=sys.stderr)
                auto_id += 1
                tid = f"report-table-{auto_id}"
                table["id"] = tid
            box = soup.new_tag("input")
            box["data-filter"] = f"#{tid}"
            box["class"] = "filter-input"
            box["placeholder"] = filter_placeholder
            table.insert_before(box)

        comment.extract()


# ──────────────────────────────────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────────────────────────────────

def render_markdown(text: str) -> tuple[str, dict]:
    md = markdown.Markdown(
        extensions=["extra", "meta", "toc", "sane_lists"],
        extension_configs={"toc": {"anchorlink": False}},
    )
    body = md.convert(text)
    return body, getattr(md, "Meta", {}) or {}


def _lift_leading_h1(soup: BeautifulSoup) -> str:
    """Pop a leading <h1> out of the body and return its text.

    A Markdown document's first heading is its title. Leaving it in the body
    while the header shows a fallback prints the document's name twice — once
    as the filename, once as the real title. Only a *leading* h1 is taken; one
    further down is a genuine section heading and stays put.
    """
    for node in soup.children:
        if isinstance(node, NavigableString):
            if str(node).strip():
                return ""
            continue
        if getattr(node, "name", None) != "h1":
            return ""
        # get_text(strip=True) strips each fragment and concatenates, so an
        # inline tag eats the space beside it: `# `x` — y` becomes "x— y".
        # Take the raw text and collapse runs of whitespace instead.
        text = re.sub(r"\s+", " ", node.get_text()).strip()
        node.extract()
        return text
    return ""


def _mark_label_paragraphs(soup: BeautifulSoup) -> None:
    """Tag `**Label.** body` paragraphs so the theme can promote the label.

    CSS cannot express "starts with a bolded run": `:first-child` ignores text
    nodes, so `strong:first-child` also matched a paragraph whose first *element*
    happened to be an emphasised word mid-sentence -- which then rendered as a
    block and broke the sentence across three lines. Only the DOM knows the
    difference, so the decision is made here and CSS keys on the class.
    """
    for para in soup.find_all("p"):
        first = next((c for c in para.children if not (isinstance(c, NavigableString)
                                                       and not str(c).strip())), None)
        if getattr(first, "name", None) == "strong":
            para["class"] = para.get("class", []) + ["step"]


def _demote_headings(soup: BeautifulSoup) -> int:
    """Shift the heading tree down one level when `#` was used per section.

    A Markdown document whose title is the frontmatter and whose sections are
    each `# Section` leaves several <h1>s once the leading title h1 is lifted.
    That breaks three things at once: the TOC (built from h2/h3), the section
    rhythm (--gap-section is keyed to h2), and the outline itself, which now
    claims six documents in one page.

    Shifting the whole tree keeps every relative level intact and gives the page
    exactly one h1 — the title in the header. Returns how many were moved.
    """
    if len(soup.find_all("h1")) < 2:
        return 0
    moved = 0
    for level in (5, 4, 3, 2, 1):          # bottom-up, or h1->h2 would be re-demoted
        for tag in soup.find_all(f"h{level}"):
            tag.name = f"h{level + 1}"
            moved += 1
    return moved


def build_page(md_path: Path, body: str, meta: dict) -> tuple[str, bool]:
    """Return (html, wants_pdf)."""
    subtitle = meta_str(meta, "subtitle")
    theme = meta_choice(meta, "theme", THEMES, "auto")
    # A serif body is the strongest single signal that a page is an article
    # someone wrote. Authored documents default to it; a generated dashboard
    # should set `font: sans`.
    font = meta_choice(meta, "font", FONTS, "serif")
    # A GENRE decision, not a width preference. `wide` is for catalogues and
    # long tables, where nothing wraps; `essay` is for an argument.
    layout = meta_choice(meta, "layout", LAYOUTS, "essay")
    want_toc = meta_bool(meta, "toc", True)
    want_pdf = meta_bool(meta, "pdf", False)

    soup = BeautifulSoup(body, "html.parser")
    apply_sidenote_markers(soup)
    apply_table_markers(soup)

    # Frontmatter wins; then the document's own leading h1; the filename last.
    title = meta_str(meta, "title")
    leading_h1 = _lift_leading_h1(soup)
    title = title or leading_h1 or md_path.stem

    _mark_label_paragraphs(soup)
    moved = _demote_headings(soup)
    if moved:
        print(f"note: the document uses '#' per section; demoted {moved} heading(s) "
              f"so the page has one h1 and the TOC can see the sections", file=sys.stderr)

    body = str(soup)

    a = load_assets()

    # The theme toggle only exists in the auto theme; forced themes have no
    # dual palette for it to switch between. Density applies to every theme.
    # `light`/`dark` FORCE a palette by stamping data-theme and dropping the
    # toggle; `auto` follows the OS and offers it.
    forced = "" if theme == "auto" else f' data-theme="{theme}"'
    theme_btn = ('<button class="rb-btn" data-theme-toggle '
                 'aria-label="Toggle light/dark theme">theme</button>') if theme == "auto" else ""
    # The contents button only exists if there are contents to open.
    toc_btn = ('<button class="rb-btn" data-toc-toggle aria-expanded="false" '
               'aria-label="Open the contents">contents</button>') if want_toc else ""
    bar = f'<div class="reader-bar">{toc_btn}{theme_btn}</div>'
    kicker = (f'<p class="kicker">{html.escape(meta_str(meta, "kicker"))}</p>'
              if meta_str(meta, "kicker") else "")
    dek = f'<p class="dek">{html.escape(meta_str(meta, "dek"))}</p>' if meta_str(meta, "dek") else ""
    sub = f'<p class="byline">{html.escape(subtitle)}</p>' if subtitle else ""

    # <main> IS the grid rather than wrapping it. The document needs its landmark,
    # and a wrapper cannot supply one here: `.report-grid > *` matches direct
    # children only, so an extra level would collapse the whole document into a
    # single grid item and every block-spacing rule would stop resolving.
    # Adopted from an earlier sidebar-breakpoint fix, which
    # no longer applies -- this layout has no sidebar -- but whose landmark
    # observation survived the rewrite intact.
    #
    # The header goes INSIDE the grid, and the body is NOT wrapped in a further level.
    # Both are documented rules of this grid (references/interactivity.md) that this
    # helper was breaking: a header above .report-grid sits at the container edge while
    # the body starts after the TOC, so the page reads as tilted right -- measured at
    # 1920px, the h1 began at x=24 against x=669 for every other block. And
    # `.report-grid > *` matches DIRECT children only, so one <main> collapses the whole
    # document into a single grid item and `.full` blocks can never sit under their
    # own heading.
    header = (f'<header>\n  {kicker}\n  <h1>{html.escape(title)}</h1>\n'
              f'  {dek}\n  {sub}\n</header>')

    # The grid always wraps the document -- it is what supplies the reading
    # column, the sidenote rail and the breakpoint ladder. `toc: false` drops
    # the nav, not the layout.
    # The nav is a fixed-position drawer on screen and a block at the top in
    # print, so it goes after the header: that is the print reading order.
    nav = '<nav class="toc" data-toc></nav>\n' if want_toc else ""
    main = f'<main class="report-grid">\n{bar}\n{header}\n{nav}{body}\n</main>'

    page = f"""<!doctype html>
<html lang="en"{forced} data-font="{font}" data-layout="{layout}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{_inner(a["theme_css"], "style")}</style>
<style>{_inner(a["layout_css"], "style")}</style>
<style>{_inner(a["component_css"], "style")}</style>
<style>{_inner(a["widget_css"], "style")}</style>
<style>{a["devices_css"]}</style>
<style>{_inner(a["print_css"], "style")}</style>
</head><body>
{main}
<script>{_inner(a["toolkit_js"], "script")}</script>
<script>{a["motion_js"]}</script>
</body></html>
"""
    return page, want_pdf


def _inner(block: str, tag: str) -> str:
    """Strip the outer <style>/<script> wrapper off an extracted reference block."""
    m = re.match(rf"<{tag}[^>]*>(.*)</{tag}>\s*$", block.strip(), re.S)
    return m.group(1) if m else block


def convert(md_path: Path, out_path: Path | None, pdf_override: bool | None) -> None:
    body, meta = render_markdown(md_path.read_text(encoding="utf-8"))
    page, want_pdf = build_page(md_path, body, meta)

    out_path = out_path or md_path.with_suffix(".html")
    out_path.write_text(page, encoding="utf-8")
    print(f"wrote {out_path}  ({len(page):,} bytes)", file=sys.stderr)

    if pdf_override is not None:
        want_pdf = pdf_override
    if not want_pdf:
        return

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_pdf import ChromeNotFound, html_to_pdf  # noqa: E402

    try:
        pdf = html_to_pdf(out_path)
    except (ChromeNotFound, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        # SubprocessError covers TimeoutExpired, which is NOT a RuntimeError —
        # without it a slow Chrome dumps a traceback and hides the fact that the
        # HTML built fine.
        sys.exit(f"error: HTML written, PDF failed — {exc}")
    print(f"wrote {pdf}  ({pdf.stat().st_size / 1024:,.0f} KB)", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Render a Markdown story into one HTML page (+ optional PDF)."
    )
    ap.add_argument("input", type=Path, help="Source .md document")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Output path (default: <input>.html)")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--pdf", dest="pdf", action="store_true", default=None,
                     help="Build a PDF for this run, whatever the frontmatter says")
    grp.add_argument("--no-pdf", dest="pdf", action="store_false",
                     help="Skip the PDF for this run, whatever the frontmatter says")
    args = ap.parse_args()

    if not args.input.exists():
        sys.exit(f"error: {args.input} not found")

    convert(args.input, args.output, args.pdf)


if __name__ == "__main__":
    main()
