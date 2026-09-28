"""Render a report at several viewports and report what actually happened.

    python3 check_layout.py report.html
    python3 check_layout.py report.html --viewports 1920x1080,1280x800,390x844
    python3 check_layout.py report.html --json

Companion to `check_typography.py`, which measures ONE viewport's reading
rhythm. This one measures GEOMETRY across many, because that is where reports
break: a layout that is correct at the author's window size and wrong at the
reader's is the single most common defect in a self-contained HTML report, and
nothing in the CSS tells you it happened.

**Two tiers, and the split is the point.** Both reference skills this one learns
from draw the same line: gate on defects, report on taste. huashu-design's
`verify.py` exits non-zero only when Playwright or the file is missing -- console
errors are reported, not gated -- and its only hard PASS/FAIL numbers are video
artefact facts. diagram-design's `verify-geometry.py` gates a clipped label and
says why in its own docstring: "paint order is what makes this a defect rather
than a stylistic choice."

So:

  ERROR      an objective defect. Nobody chooses sideways scroll, an element
             wider than the window, text under a sticky panel, a runtime
             exception, contrast below AA, or a PDF that ships the screen chrome.
             These exit 1.
  ADVISORY   a departure from the house calibration. Line length, leading,
             paragraph ratios, how much of the window the content spans -- all
             tuned against measured documents, and all things a deliberate design
             may reasonably differ on. These are printed with the house number
             beside the measured one and do NOT fail the run.

`--strict` promotes advisories to errors, for a build that wants the house style
enforced rather than described.

Checks, per viewport:

  overflow        ERROR     the document never scrolls sideways
  runaway block   ERROR     no element renders wider than the viewport
  rail overlap    ERROR     nothing out of flow sits on top of the text
  script          ERROR     no uncaught JavaScript error
  clipped label   ERROR     no SVG <text> runs past its figure's viewBox (it gets cut off)
  body size       ERROR     running text is at least 14px (accessibility floor,
                            not a size preference)
  measure         ADVISORY  the reading column stays inside 45-140 rendered
                            characters (skipped for layout: wide)
  fill            ADVISORY  content spans a sane share of the window, >=1400px only
  orphan          ADVISORY  a grid of N boxes does not leave 1 alone on the last row

And once, theme-independent of viewport:

  contrast        ERROR     text, muted text and links reach WCAG AA on their own
                            ground, in BOTH the light and the dark palette
  print block     ERROR     the document actually carries print rules

Exit 1 when an ERROR is found (or, with --strict, any advisory). Advisories
alone leave the exit code at 0.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME_CANDIDATES = (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)

DEFAULT_VIEWPORTS = "1920x1080,1440x900,1280x800,1024x768,768x1024,390x844"

# Rendered characters per line. The floor matters as much as the ceiling: a
# column under ~45 characters breaks prose into a ragged ribbon. The ceiling is
# past the 45-90 guideline on purpose -- see check_typography.py, which owns the
# conditional rule (a long measure must also carry the leading to match). This
# check only catches a column that is grossly wrong.
MIN_CHARS, MAX_CHARS = 45, 140
# 14px, and catalogue mode deliberately sits just above it (~14.6-15.7px).
MIN_BODY_PX = 14.0
# Share of the window that must carry content, measured as the span from the
# leftmost laid-out edge to the rightmost. Checked ONLY at >=1400px, where the
# margin rail exists and using it is the author's choice: a document with margin
# notes spans about 46% of a 1920px window, one with nothing in the margin spans
# 31%. Below 1400 there is a single column and the measure governs its width, so
# the number carries no signal.
WCAG_AA_NORMAL = 4.5
WCAG_AA_LARGE = 3.0

PROBE = r"""
<script>
(function () {
  var errs = [];
  addEventListener("error", function (e) { errs.push(String(e.message)); });

  function rect(el) { var b = el.getBoundingClientRect(); return {x: b.x, y: b.y, w: b.width, h: b.height, r: b.right, b: b.bottom}; }
  function overlaps(a, b) { return a.x < b.r - 1 && b.x < a.r - 1 && a.y < b.b - 1 && b.y < a.b - 1; }
  function sel(el) {
    if (!el) return "?";
    var s = el.tagName.toLowerCase();
    if (el.id) return s + "#" + el.id;
    if (el.className && typeof el.className === "string") s += "." + el.className.trim().split(/\s+/).slice(0, 2).join(".");
    return s;
  }
  // Chrome serialises a color-mix() result as `color(srgb 0.87 0.91 0.96)` --
  // components already in 0..1 -- and everything else as `rgb(r, g, b)` in
  // 0..255. Dividing the first form by 255 reports a near-black luminance and
  // invents contrast failures that are not there. Detect the form, do not assume.
  function lum(c) {
    var m = c.match(/[\d.]+/g); if (!m) return null;
    var unit = /^color\(/.test(c.trim()) ? 1 : 255;
    var v = m.slice(0, 3).map(function (x) { x = x / unit; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
  }
  function ratio(fg, bg) {
    var a = lum(fg), b = lum(bg); if (a === null || b === null) return null;
    return +(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05))).toFixed(2);
  }
  // Walk up for the first ancestor that actually paints a background.
  function ground(el) {
    for (var n = el; n && n !== document.documentElement; n = n.parentElement) {
      var c = getComputedStyle(n).backgroundColor;
      if (c && !/rgba\(0, 0, 0, 0\)|transparent/.test(c)) return c;
    }
    return getComputedStyle(document.body).backgroundColor || "rgb(255,255,255)";
  }

  function contrastSet() {
    var out = {};
    var body = document.querySelector(".report-grid p, p") || document.body;
    var muted = document.querySelector(".muted, .byline, figcaption, .sidenote");
    // Not a contents link: the drawer sits inside .report-grid and its links are
    // styled for a panel, so measuring one reports the drawer's contrast and
    // never the body text's.
    // The contents drawer lives inside .report-grid and its links are styled for
    // a panel, so `li a` would measure the drawer's contrast, never the body's.
    var link = document.querySelector(".report-grid p a[href], .report-grid li:not(.toc li) a[href]")
      || [...document.querySelectorAll("a[href]")].find(function (a) { return !a.closest(".toc"); });
    var pairs = [["text", body, false], ["muted", muted, true], ["link", link, false]];
    pairs.forEach(function (p) {
      if (!p[1]) return;
      var cs = getComputedStyle(p[1]);
      out[p[0]] = {ratio: ratio(cs.color, ground(p[1])),
                   need: p[2] || parseFloat(cs.fontSize) >= 24 ? 3.0 : 4.5,
                   px: +parseFloat(cs.fontSize).toFixed(1)};
    });
    return out;
  }

  function measure() {
    var vw = document.documentElement.clientWidth;
    var out = {vw: vw, vh: innerHeight, violations: []};
    // tier: "error" for an objective defect, "advisory" for a departure from the
    // house calibration. The caller decides what to do with each.
    var V = function (kind, detail, tier) {
      out.violations.push({kind: kind, detail: detail, tier: tier || "error"});
    };

    // 1. document-level sideways scroll
    out.docW = document.documentElement.scrollWidth;
    if (out.docW > vw + 1) V("overflow", "document scrolls sideways: " + out.docW + "px in " + vw + "px");

    // 2. any single element wider than the window. overflow-x containers are
    //    legal (they scroll their own content); their CHILDREN are not measured.
    var worst = null;
    Array.prototype.forEach.call(document.querySelectorAll("body *"), function (el) {
      var cs = getComputedStyle(el);
      if (cs.position === "fixed" || cs.display === "none") return;
      if (el.closest("[style*='overflow-x'], .scroll-x, pre, .toc, details.evidence")) return;
      var r = rect(el);
      if (r.w > vw + 1 && (!worst || r.w > worst.w)) worst = {w: Math.round(r.w), s: sel(el)};
    });
    if (worst) V("runaway", worst.s + " renders " + worst.w + "px wide in " + vw + "px");

    // 3. reading measure, in RENDERED characters -- `ch` is the width of "0"
    var ps = Array.prototype.slice.call(document.querySelectorAll(".report-grid p, p, li"))
      .filter(function (p) { return p.textContent.trim().length > 120 && p.clientWidth > 80; })
      .sort(function (a, b) { return b.textContent.length - a.textContent.length; });
    if (ps.length) {
      var p = ps[0], cs = getComputedStyle(p);
      var cv = document.createElement("canvas").getContext("2d");
      cv.font = cs.fontStyle + " " + cs.fontWeight + " " + cs.fontSize + " " + cs.fontFamily;
      var t = p.textContent.trim().slice(0, 800);
      var avg = cv.measureText(t).width / t.length;
      out.colPx = Math.round(p.clientWidth);
      out.chars = Math.round(p.clientWidth / avg);
      out.bodyPx = +parseFloat(cs.fontSize).toFixed(1);
      // In catalogue mode (layout: wide) the cap does not apply -- a long column
      // is legitimate there BECAUSE almost nothing wraps. The genre check that
      // proves it lives in check_typography.py; enforcing the cap here as well
      // just failed every correct catalogue at every viewport.
      out.layout = document.documentElement.getAttribute("data-layout") || "essay";
      if (out.layout !== "wide") {
        if (out.chars > MAXC) V("measure", out.chars + " characters per line (max " + MAXC + ")", "advisory");
        if (out.chars < MINC) V("measure", out.chars + " characters per line (min " + MINC + ")", "advisory");
      }
      if (out.bodyPx < MINPX) V("body size", "running text renders at " + out.bodyPx + "px (min " + MINPX + ")");
    }

    // 4. a sticky/absolute rail sitting ON the text rather than beside it
    var rails = Array.prototype.slice.call(document.querySelectorAll(".toc, .sidenote, aside"));
    var blocks = Array.prototype.slice.call(document.querySelectorAll(
      ".report-grid > p, .report-grid > h2, .report-grid > table, .report-grid > .full, .report-grid > .wide, .report-grid > figure, .report-grid > .stat-grid, .report-grid > .compare"));
    rails.forEach(function (rail) {
      var rcs = getComputedStyle(rail);
      // A floated margin note is out of flow too: it can hang past its own
      // wrapper into the row below and land on a full-width table.
      if (rcs.position !== "sticky" && rcs.position !== "fixed"
          && rcs.position !== "absolute" && rcs.cssFloat === "none") return;
      var rr = rect(rail);
      for (var i = 0; i < blocks.length; i++) {
        if (blocks[i].contains(rail) || rail.contains(blocks[i])) continue;
        if (overlaps(rr, rect(blocks[i]))) { V("rail overlap", sel(rail) + " sits on " + sel(blocks[i])); break; }
      }
    });

    // 5. How much of the window carries anything at all -- measured as the SPAN
    //    from the leftmost content edge to the rightmost, across every direct
    //    child including the rails. Not the widest single block: a report that
    //    fills a wide screen does it by using the margins, not by stretching
    //    one paragraph. This is the check that fails a narrow ribbon of text
    //    centred in a 1920px window, which is the defect it exists for.
    var lo = Infinity, hi = -Infinity, grid = document.querySelector(".report-grid") || document.body;
    Array.prototype.forEach.call(grid.children, function (el) {
      if (getComputedStyle(el).position === "fixed" || !el.offsetParent && el.tagName !== "NAV") return;
      var r = rect(el);
      if (r.w < 2 || r.w > vw + 1) return;
      if (r.x < lo) lo = r.x;
      if (r.r > hi) hi = r.r;
    });
    out.fill = hi > lo ? +((hi - lo) / vw).toFixed(3) : 0;
    // Only meaningful at >=1400px, the one width where the margin rail exists
    // and the author's use of it is the variable. Below that there is a single
    // column and the READING MEASURE governs its width, so a low share carries
    // no signal -- a 555px serif column in a 1265px window is 44% and exactly
    // what it should be. Narrow-viewport defects are caught by the overflow and
    // runaway checks instead.
    //
    // This threshold was 0.62 at 1080-1399 while a left rail existed. Deleting
    // the rail changed what the number means, so the check was rescoped rather
    // than left to fail correct documents -- a stale check is worse than none.
    var need = vw >= 1400 ? 0.42 : 0;
    if (need && out.fill < need) V("fill", "content spans " + Math.round(out.fill * 100) + "% of a " + vw
      + "px window (house target " + Math.round(need * 100) + "%)", "advisory");

    // 6. a wrapped grid that leaves one box alone on the last row
    Array.prototype.forEach.call(document.querySelectorAll(".stat-grid, .keyfacts, .compare"), function (g) {
      var kids = Array.prototype.slice.call(g.children).filter(function (k) { return k.offsetParent !== null; });
      if (kids.length < 3) return;
      var rows = {};
      kids.forEach(function (k) { var y = Math.round(rect(k).y); rows[y] = (rows[y] || 0) + 1; });
      var ys = Object.keys(rows).map(Number).sort(function (a, b) { return a - b; });
      if (ys.length > 1 && rows[ys[ys.length - 1]] === 1 && rows[ys[0]] > 1) {
        // A lone last item that spans the full width is deliberate emphasis,
        // not an orphan. Only a short one left dangling is the defect.
        var last = kids[kids.length - 1], gw = rect(g).w;
        if (rect(last).w < gw * 0.9)
          V("orphan", sel(g) + " leaves 1 of " + kids.length + " alone on its last row", "advisory");
      }
    });

    // 6b. SVG text past the viewBox edge is cut off: a defect, not a choice
    Array.prototype.forEach.call(document.querySelectorAll("svg[viewBox]"), function (svg) {
      // screen boxes, so a rotated label is measured as drawn, not before its transform
      if (getComputedStyle(svg).overflow === "visible") return;
      var s = svg.getBoundingClientRect();
      if (!s.width) return;
      Array.prototype.some.call(svg.querySelectorAll("text"), function (t) {
        var b = t.getBoundingClientRect();
        if (!b.width) return false;
        if (b.left < s.left - 1 || b.top < s.top - 1 || b.right > s.right + 1 || b.bottom > s.bottom + 1) {
          V("clipped label", '"' + t.textContent.trim().slice(0, 40) + '" runs past the viewBox of ' + sel(svg));
          return true;
        }
      });
    });

    // 7. contrast, both palettes -- the toggle must not ship a broken second theme
    var was = document.documentElement.getAttribute("data-theme");
    document.documentElement.setAttribute("data-theme", "light");
    out.contrastLight = contrastSet();
    document.documentElement.setAttribute("data-theme", "dark");
    out.contrastDark = contrastSet();
    if (was === null) document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", was);

    out.errors = errs.slice(0, 3);
    if (errs.length) V("script", errs.length + " uncaught error(s): " + errs[0]);
    document.title = "LAYOUT:" + JSON.stringify(out);
  }

  function go() { setTimeout(measure, 120); }
  if (document.readyState === "complete") go(); else addEventListener("load", go);
})();
</script>
"""


def find_chrome(explicit: str | None) -> str:
    if explicit:
        return explicit
    for c in CHROME_CANDIDATES:
        found = shutil.which(c) or (c if Path(c).exists() else None)
        if found:
            return found
    sys.exit("No Chrome/Chromium found. Pass --chrome /path/to/chrome.")


def run_viewport(html_path: Path, chrome: str, w: int, h: int) -> dict:
    src = html_path.read_text(encoding="utf-8")
    probe = (PROBE.replace("MAXC", str(MAX_CHARS)).replace("MINC", str(MIN_CHARS))
                  .replace("MINPX", str(MIN_BODY_PX)))
    probed = src.replace("</body>", probe + "</body>") if "</body>" in src else src + probe

    # Keep the temp file beside the original so relative assets still resolve.
    tmp = html_path.parent / f".layoutcheck-{w}-{html_path.name}"
    tmp.write_text(probed, encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory() as td:
            out = subprocess.run(
                [chrome, "--headless", "--disable-gpu", "--no-sandbox",
                 f"--user-data-dir={td}", "--virtual-time-budget=4000",
                 f"--window-size={w},{h}", "--dump-dom", tmp.resolve().as_uri()],
                capture_output=True, text=True, timeout=120,
            ).stdout
    finally:
        tmp.unlink(missing_ok=True)

    m = re.search(r"LAYOUT:(\{.*?\})</title>", out, re.S)
    if not m:
        return {"vw": w, "violations": [{"kind": "render", "detail": "the page did not report back — is it valid HTML?"}]}
    return json.loads(m.group(1))


def check_contrast(d: dict) -> list[dict]:
    bad = []
    for theme in ("Light", "Dark"):
        for role, got in (d.get("contrast" + theme) or {}).items():
            r, need = got.get("ratio"), got.get("need", WCAG_AA_NORMAL)
            if r is not None and r < need:
                bad.append({"kind": "contrast", "tier": "error",
                            "detail": f"{theme.lower()} theme: {role} is {r}:1 at {got['px']}px (AA needs {need}:1)"})
    return bad


def check_print_block(html_path: Path) -> list[dict]:
    src = html_path.read_text(encoding="utf-8")
    if "@media print" not in src:
        return [{"kind": "print", "tier": "error",
                 "detail": "no @media print block — the PDF will carry the screen chrome"}]
    tail = src[src.index("@media print"):]
    missing = [n for n in (".toc", "data-theme-toggle") if n not in tail]
    if missing:
        return [{"kind": "print", "tier": "error",
                 "detail": f"print block never hides {', '.join(missing)}"}]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path)
    ap.add_argument("--viewports", default=DEFAULT_VIEWPORTS, help=f"default: {DEFAULT_VIEWPORTS}")
    ap.add_argument("--chrome", default=None)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true",
                    help="fail on advisories too — for a build that wants the house style "
                         "enforced rather than described")
    a = ap.parse_args()

    if not a.html.is_file():
        sys.exit(f"No such file: {a.html}")
    chrome = find_chrome(a.chrome)

    try:
        sizes = [tuple(int(n) for n in v.lower().split("x")) for v in a.viewports.split(",")]
    except ValueError:
        sys.exit("--viewports wants a list like 1920x1080,768x1024")

    results, violations = [], []
    for w, h in sizes:
        d = run_viewport(a.html, chrome, w, h)
        d["_label"] = f"{w}x{h}"
        results.append(d)
        violations += [dict(v, at=d["_label"]) for v in d.get("violations", [])]

    # Contrast and print rules are viewport-independent; report them once, from
    # the widest run, so six viewports do not print the same failure six times.
    once = check_contrast(results[0]) + check_print_block(a.html)
    violations = [v for v in violations if v["kind"] != "contrast"] + once

    errors = [v for v in violations if v.get("tier", "error") == "error"]
    advisories = [v for v in violations if v.get("tier") == "advisory"]

    if a.json:
        print(json.dumps({"file": str(a.html), "viewports": results,
                          "errors": errors, "advisories": advisories}, indent=2))
        return 1 if errors or (a.strict and advisories) else 0

    print(f"\n{a.html.name}")
    hdr = f"  {'viewport':>10}  {'column':>7}  {'chars':>5}  {'body':>6}  {'fill':>5}   result"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for d in results:
        vs = d.get("violations", [])
        ne = len([v for v in vs if v.get("tier", "error") == "error"])
        na = len(vs) - ne
        n = ne
        col = f"{d.get('colPx', '-')}px" if d.get("colPx") else "-"
        chars = d.get("chars", "-")
        body = f"{d.get('bodyPx', '-')}px" if d.get("bodyPx") else "-"
        fill = f"{round(d.get('fill', 0) * 100)}%" if d.get("fill") else "-"
        verdict = ("PASS" if not ne else f"{ne} ERROR" + ("" if ne == 1 else "S"))
        if na:
            verdict += f" · {na} advisory" + ("" if na == 1 else "s")
        print(f"  {d['_label']:>10}  {col:>7}  {str(chars):>5}  {body:>6}  {fill:>5}   {verdict}")

    c = results[0]
    for theme in ("Light", "Dark"):
        got = c.get("contrast" + theme) or {}
        if got:
            bits = ", ".join(f"{k} {v['ratio']}:1" for k, v in got.items() if v.get("ratio"))
            print(f"  {theme.lower()+' contrast':>10}  {bits}")

    def dump(label, items):
        print(f"\n  {len(items)} {label}:\n")
        for v in items:
            where = f"[{v['at']}] " if "at" in v else ""
            print(f"    {v['kind']:<14} {where}{v['detail']}")

    if errors:
        dump("ERROR(S) — objective defects", errors)
    if advisories:
        dump("advisory(s) — departures from the house calibration, not defects", advisories)
        if not a.strict:
            print("\n  Advisories do not fail the run. A deliberate design may differ from the")
            print("  house numbers; --strict promotes them to errors for a build gate.")

    if errors or (a.strict and advisories):
        print()
        return 1
    if not advisories:
        print("\n  PASS — no defects and no departures at any tested viewport.\n")
    else:
        print("\n  PASS — no defects.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
