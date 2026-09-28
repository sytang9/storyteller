"""Render an html-report file to PDF with headless Chrome.

Chrome is the renderer because it is the same engine the report was designed
in: the print stylesheet, CSS variables, grid layout and inline SVG all behave
exactly as they do in the browser's own Print dialog. No extra Python
dependency, no second rendering engine to keep in sync.

Linked local images (`asset/…`) resolve fine over `file://`, so a report does
NOT need base64 inlining to produce a PDF.

Usage:
    python build_pdf.py report.html [-o report.pdf] [--chrome /path/to/chrome]

Or from Python:
    from build_pdf import html_to_pdf
    html_to_pdf(Path("report.html"))
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# First match on PATH wins; absolute paths are probed with os.access.
CHROME_CANDIDATES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
)


class ChromeNotFound(RuntimeError):
    pass


def find_chrome(explicit: str | None = None) -> str:
    """Return a usable Chrome/Chromium executable, or raise ChromeNotFound."""
    if explicit:
        found = shutil.which(explicit) or (explicit if os.access(explicit, os.X_OK) else None)
        if not found:
            raise ChromeNotFound(f"{explicit} is not an executable Chrome binary")
        return found
    for cand in CHROME_CANDIDATES:
        found = shutil.which(cand)
        if found:
            return found
        if os.path.isabs(cand) and os.access(cand, os.X_OK):
            return cand
    raise ChromeNotFound(
        "no Chrome/Chromium found. Install one, or pass --chrome /path/to/chrome. "
        "Tried: " + ", ".join(CHROME_CANDIDATES)
    )


def html_to_pdf(
    html_path: Path,
    pdf_path: Path | None = None,
    chrome: str | None = None,
    virtual_time_budget: int = 10000,
    timeout: int = 180,
) -> Path:
    """Print `html_path` to `pdf_path` (default: same basename, .pdf).

    `virtual_time_budget` is how long Chrome lets the page's own JS settle
    before printing — the toolkit script builds the TOC and expands every
    <details> on `beforeprint`, so printing too early loses content.
    """
    html_path = html_path.resolve()
    if not html_path.exists():
        raise FileNotFoundError(html_path)
    pdf_path = (pdf_path or html_path.with_suffix(".pdf")).resolve()

    exe = find_chrome(chrome)

    # Remove any earlier PDF first. Chrome writes nothing when it fails, so a
    # stale file left in place would be indistinguishable from a fresh one — and
    # this function's whole job is to guarantee the client never gets a PDF that
    # is older than the report it was built from.
    try:
        pdf_path.unlink()
    except FileNotFoundError:
        pass

    with tempfile.TemporaryDirectory(prefix="html-report-chrome-") as profile:
        base = [
            exe,
            "--headless",
            "--disable-gpu",
            f"--user-data-dir={profile}",
            "--run-all-compositor-stages-before-draw",
            f"--virtual-time-budget={virtual_time_budget}",
            f"--print-to-pdf={pdf_path}",
        ]
        # Chrome refuses to sandbox as root (containers, CI).
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            base.insert(1, "--no-sandbox")

        url = html_path.as_uri()

        # --no-pdf-header-footer is the current flag; older builds spell it
        # --print-to-pdf-no-header. Try the modern one, fall back once.
        attempts = [
            base[:1] + ["--no-pdf-header-footer"] + base[1:] + [url],
            base[:1] + ["--print-to-pdf-no-header"] + base[1:] + [url],
        ]

        last: subprocess.CompletedProcess[str] | None = None
        for cmd in attempts:
            last = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if last.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0:
                return pdf_path
            # A non-zero exit may still have left a truncated file behind; drop
            # it so the next attempt — and the caller — cannot mistake it for output.
            try:
                pdf_path.unlink()
            except FileNotFoundError:
                pass

    stderr = (last.stderr or "").strip() if last else ""
    rc = last.returncode if last else "?"
    raise RuntimeError(
        f"chrome produced no PDF for {html_path} (exit {rc})\n{stderr[-2000:]}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Render an html-report to PDF via headless Chrome.")
    ap.add_argument("input", type=Path, help="Source .html report")
    ap.add_argument("-o", "--output", type=Path, default=None, help="Output path (default: <input>.pdf)")
    ap.add_argument("--chrome", default=None, help="Explicit Chrome/Chromium binary")
    ap.add_argument("--virtual-time-budget", type=int, default=10000,
                    help="ms Chrome lets page JS settle before printing (default 10000)")
    args = ap.parse_args()

    if not args.input.exists():
        sys.exit(f"error: {args.input} not found")

    try:
        out = html_to_pdf(args.input, args.output, args.chrome, args.virtual_time_budget)
    except (ChromeNotFound, RuntimeError, subprocess.TimeoutExpired) as exc:
        sys.exit(f"error: {exc}")

    print(f"wrote {out}  ({out.stat().st_size / 1024:,.0f} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
