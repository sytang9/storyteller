"""Media for the teaser template: the licence gate, the SVG sanitizer and collect_media() for build.py.

Self-contained (stdlib only) so it can be copied next to build.py. fetch_assets.py imports the gate from here,
so the fetch step and the render step accept exactly the same licences.

    from media_build import collect_media
    data["media"] = collect_media(src, out=HERE)   # {"icons": {id: svg}, "images": {id: path}, "credits": [...]}
"""
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# canonical licence codes we publish without a human check (research/open_media.md, licence gate)
ACCEPTED = {"cc0", "pdm", "by", "mit", "isc", "apache-2.0"}
ALIASES = {"public-domain": "pdm", "public-domain-mark": "pdm", "pd": "pdm", "apache": "apache-2.0"}

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
# shapes and paint servers only: no script, style, image, foreignObject or animation can survive
SVG_TAGS = {"svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "defs", "clipPath", "mask",
            "linearGradient", "radialGradient", "stop", "use", "symbol", "title", "desc", "a"}
KEEP_PAINT = {"none", "currentcolor", "transparent"}
LOCAL_URL = re.compile(r"url\(\s*['\"]?#")

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)


def licence_code(raw: str) -> str:
    """'CC BY-SA 4.0', 'cc0', 'Public domain', 'Apache-2.0' -> 'by-sa', 'cc0', 'pdm', 'apache-2.0'."""
    s = re.sub(r"[\s_]+", "-", (raw or "").strip().lower())
    s = re.sub(r"-\d+(\.\d+)*$", "", s)  # the version never changes the verdict
    s = s[3:] if s.startswith("cc-") else s
    return ALIASES.get(s, s)


def gate(raw: str) -> tuple[bool, str]:
    """(True, code) for a licence we accept, else (False, reason)."""
    code = licence_code(raw)
    if code in ACCEPTED:
        return True, code
    if {"nc", "nd", "sa"} & set(code.split("-")):
        return False, f"{code}: NC, ND and SA licences are not allowed"
    return False, f"unknown licence {raw!r}"


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _svg_tag(tag: str) -> str:
    """The local name of an element in the SVG namespace; '' for any other namespace."""
    prefix = f"{{{SVG_NS}}}"
    return tag[len(prefix):] if tag.startswith(prefix) else ""


def _clean(node: ET.Element) -> None:
    for child in list(node):
        if _svg_tag(child.tag) not in SVG_TAGS:
            node.remove(child)
            continue
        _clean(child)
    for key, val in list(node.attrib.items()):
        name, low = _local(key).lower(), val.strip().lower()
        # every url( must point inside the icon (#id); one local reference must not carry an external one along
        external_url = "url(" in low and not all(re.match(r"\s*['\"]?#", part) for part in low.split("url(")[1:])
        drop = name in ("style", "class") or name.startswith("on") or "javascript:" in low  # style could size or position the icon over the frame
        if drop or external_url or (name == "href" and not low.startswith("#")):
            del node.attrib[key]
        elif name in ("fill", "stroke") and low not in KEEP_PAINT and not low.startswith("url(#"):
            node.attrib[key] = "currentColor"  # one colour per icon, set by the look role in media.js


def sanitize_svg(text: str) -> str:
    """An icon SVG safe to inline: allowlisted shapes only, no on* or external links, painted in currentColor."""
    if re.search(r"<!(DOCTYPE|ENTITY)", text, re.I):
        raise ValueError("svg with a DOCTYPE or ENTITY is refused")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError(f"svg does not parse: {e}") from e
    if _svg_tag(root.tag) != "svg":
        raise ValueError(f"root is {root.tag}, not an svg element")
    try:
        _clean(root)
    except RecursionError as e:
        raise ValueError("svg is nested too deep") from e
    for key in ("width", "height"):
        root.attrib.pop(key, None)  # media.js sizes the icon
    return ET.tostring(root, encoding="unicode")


def _checked_file(src: Path, a: dict) -> Path:
    """The asset's file, after the render gate: open licence, a credit where one is owed, an unchanged file."""
    ok, why = gate(a.get("license", ""))
    if not ok:
        raise SystemExit(f"media {a.get('id')}: {why}")
    if why == "by" and not a.get("credit_text"):  # from the licence itself: a hand-edited flag cannot waive the credit
        raise SystemExit(f"media {a['id']}: attribution required but credit_text is empty")
    f = (src / a["file"]).resolve()
    if f.parent != (src / "media").resolve() or not f.is_file():
        raise SystemExit(f"media {a['id']}: file {a['file']!r} is not in {src / 'media'}")
    if hashlib.sha256(f.read_bytes()).hexdigest() != a.get("sha256"):
        raise SystemExit(f"media {a['id']}: sha256 differs from credits.json; re-run fetch_assets.py")
    return f


def collect_media(src: Path, out: Path | None = None) -> dict:
    """Read <src>/media/credits.json; inline icons, copy images into <out>/assets/media/ (out: the template folder)."""
    src = Path(src)
    out = Path(out) if out else src / "hf"
    media = {"icons": {}, "images": {}, "credits": []}
    path = src / "media/credits.json"
    if not path.is_file():
        return media
    assets = json.loads(path.read_text())["assets"]
    for a in assets:
        f = _checked_file(src, a)
        if a["kind"] == "icon":
            media["icons"][a["id"]] = sanitize_svg(f.read_text())
            continue
        (out / "assets/media").mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out / "assets/media" / f.name)
        media["images"][a["id"]] = "assets/media/" + f.name
    media["credits"] = assets
    return media
