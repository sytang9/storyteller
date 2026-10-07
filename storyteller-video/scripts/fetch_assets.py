"""Fetch open-licence icons, illustrations and photos named in media.json into <teaser>/media/, with credits.json.

    python3 fetch_assets.py <teaser dir> media.json [--offline]

media.json: [{"id": "road", "kind": "icon"|"illustration"|"photo", "query": "road" | "lucide:construction", "depicts": "..."}]
  icon                  Iconify (no key). "set:name" is taken as is; a plain word searches ICON_SETS in that order.
  photo, illustration   Openverse (no key); Wikimedia Commons when no Openverse result passes the gate.
Every candidate passes media_build.gate (CC0, PDM, CC BY, MIT, ISC, Apache-2.0). NC, ND, SA and unknown licences go
to "rejected" in credits.json. An asset whose file still matches its sha256 is not fetched again.
--offline checks media.json against the cache and fetches nothing. Exit code 1 when any asset fails.
"""
import argparse
import hashlib
import html
import json
import os
import ipaddress
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "assets/hf"))  # media_build ships with the template
from media_build import gate, licence_code, sanitize_svg  # noqa: E402

UA = "storyteller-video-fetch/1.0 (open-licence media for narrated explainer videos; Python urllib)"
# preference order; licences read live on 2026-10-07: ISC, MIT, MIT, Apache-2.0, Apache-2.0 (still gated per run)
ICON_SETS = ["lucide", "tabler", "ph", "material-symbols", "mdi"]
KINDS = {"icon", "photo", "illustration"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")  # the id becomes a file name
ICON_RE = re.compile(r"^[a-z0-9-]+:[a-z0-9-]+$")
TIMEOUT = 30  # s per request
MAX_BYTES = 15 * 1024 * 1024
SVG_MAX_BYTES = 1024 * 1024  # an icon is a few kB; a larger one is not an icon
CANDIDATES = 20  # Openverse results read per asset
ICON_SEARCH_LIMIT = 64
GAP = {"api.openverse.org": 3.1}  # s between calls; Openverse allows 20/min without a key
GAP_DEFAULT = 1.0
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
ICONIFY = "https://api.iconify.design"
OPENVERSE = "https://api.openverse.org/v1/images/"
OPENVERSE_LICENCES = "cc0,pdm,by"
COMMONS = "https://commons.wikimedia.org/w/api.php"


class FetchError(Exception):
    pass


_last_call = {}


def _polite(host: str) -> None:
    wait = _last_call.get(host, 0.0) + GAP.get(host, GAP_DEFAULT) - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def check_public(url: str) -> None:
    """Download URLs come from third-party API results: only https, and never a private, loopback or link-local host
    (the fetch must not reach the local network, a tailnet or a cloud metadata address)."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise FetchError(f"{url}: only https URLs are fetched")
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(parts.hostname, 443)}
    except OSError as e:
        raise FetchError(f"{url}: cannot resolve {parts.hostname}: {e}") from e
    for a in addrs:
        ip = ipaddress.ip_address(a.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise FetchError(f"{url}: {parts.hostname} resolves to a non-public address ({ip})")


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_public(newurl)  # every hop, not only the first URL
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_CheckedRedirect)


def http_get(url: str, limit: int = None) -> tuple[bytes, str]:
    """(body, content type). Any network or HTTP problem becomes a FetchError that names the URL."""
    limit = limit or MAX_BYTES
    check_public(url)
    _polite(urllib.parse.urlsplit(url).hostname or "")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with _opener.open(req, timeout=TIMEOUT) as resp:
            body = resp.read(limit + 1)
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} from {url}") from e
    except OSError as e:  # URLError, timeouts, resets
        raise FetchError(f"network error on {url}: {getattr(e, 'reason', e)}") from e
    if len(body) > limit:
        raise FetchError(f"{url} is larger than {limit} bytes")
    return body, ctype


def get_json(url: str, params: dict) -> dict:
    return json.loads(http_get(url + "?" + urllib.parse.urlencode(params))[0])


def _text(s: str) -> str:
    """Plain text from Commons metadata, which holds HTML."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, body: bytes) -> None:
    """Never leaves a half file: write beside it, then rename in one step."""
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(body)
    os.replace(tmp, path)


# ---- icons ----
def pick_icon(query: str) -> str:
    if ":" in query:
        return query
    hits = get_json(f"{ICONIFY}/search", {"query": query, "limit": ICON_SEARCH_LIMIT, "prefixes": ",".join(ICON_SETS)})
    hits = [h for h in hits.get("icons", []) if ICON_RE.match(h)]
    for prefix in ICON_SETS:  # one consistent style beats the API's cross-set ranking
        for h in hits:
            if h.startswith(prefix + ":"):
                return h
    raise FetchError(f"no icon for {query!r} in {ICON_SETS}")


def fetch_icon(item: dict, sets: dict) -> tuple[bytes, str, dict]:
    icon = pick_icon(item["query"])
    prefix, name = icon.split(":")
    if prefix not in sets:
        found = get_json(f"{ICONIFY}/collections", {"prefixes": prefix})
        if prefix not in found:
            raise FetchError(f"icon set {prefix!r} not found on Iconify")
        sets[prefix] = found[prefix]
    info = sets[prefix]
    lic, author = info.get("license", {}), info.get("author", {})
    label = lic.get("spdx") or lic.get("title", "")
    ok, code = gate(label)
    if not ok:
        raise FetchError(f"icon set {prefix}: {code}")
    set_name = info.get("name", prefix)
    set_name = set_name if "icon" in set_name.lower() else set_name + " icons"  # "Tabler Icons", "Lucide icons"
    url = f"{ICONIFY}/{prefix}/{name}.svg"
    body, _ = http_get(url, limit=SVG_MAX_BYTES)
    try:
        sanitize_svg(body.decode())
    except (ValueError, UnicodeDecodeError) as e:
        raise FetchError(f"{url} is not a usable svg: {e}") from e
    rec = {"source": "iconify", "icon": icon, "title": icon, "source_url": f"https://icon-sets.iconify.design/{prefix}/",
           "download_url": url, "author": author.get("name", "unknown"), "author_url": author.get("url"),
           "license": label, "license_url": lic.get("url"), "attribution_required": code == "by",
           "credit_text": f"{set_name} by {author.get('name', 'unknown')} ({label})"}
    return body, "svg", rec


# ---- photos and illustrations ----
def openverse(item: dict):
    # filter at the source so all CANDIDATES are usable (unfiltered, 15 of 20 road photos were BY-NC-ND);
    # pick_images still gates each result, in case an upstream licence label drifts
    params = {"q": item["query"], "page_size": CANDIDATES, "mature": "false", "license": OPENVERSE_LICENCES}
    if item["kind"] == "illustration":
        params["category"] = "illustration"
    for r in get_json(OPENVERSE, params).get("results", []):
        code, version = r.get("license", ""), r.get("license_version") or ""
        label = (code.upper() if code in ("cc0", "pdm") else "CC " + code.upper()) + (" " + version if version else "")
        yield {"source": "openverse", "title": r.get("title") or "Untitled", "author": r.get("creator") or "unknown",
               "author_url": r.get("creator_url"), "license": label, "license_url": r.get("license_url"),
               "source_url": r.get("foreign_landing_url"), "download_url": r.get("url"),
               "tags": [t.get("name", "") for t in r.get("tags") or []]}


def commons(item: dict):
    filetype = "drawing" if item["kind"] == "illustration" else "bitmap"
    params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 10,
              "gsrsearch": f"{item['query']} filetype:{filetype}", "prop": "imageinfo",
              "iiprop": "url|extmetadata", "iiurlwidth": 1920}
    pages = get_json(COMMONS, params).get("query", {}).get("pages", {})
    for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        info = (p.get("imageinfo") or [{}])[0]
        if not (info.get("thumburl") or info.get("url")):
            continue  # a malformed page must not end the search
        meta = lambda k: _text(info.get("extmetadata", {}).get(k, {}).get("value", ""))
        yield {"source": "commons", "title": meta("ObjectName") or p["title"].removeprefix("File:"),
               "author": meta("Artist") or "unknown", "author_url": None, "license": meta("LicenseShortName"),
               "license_url": meta("LicenseUrl") or None, "source_url": info.get("descriptionurl"),
               "download_url": info.get("thumburl") or info.get("url"), "tags": []}


def pick_images(item: dict, rejected: list):
    """The open candidate whose title (counted twice) and tags share the most words with the query; API order breaks
    ties. Keyword overlap is a weak relevance signal: look at the pick before it ships (references/media.md)."""
    words = set(re.findall(r"\w+", item["query"].lower()))
    hits = lambda text: len(words & set(re.findall(r"\w+", text.lower())))
    score = lambda c: 2 * hits(c["title"]) + hits(" ".join(c["tags"]))
    any_passed = False
    for search in (openverse, commons):
        passed = []
        try:
            found = list(search(item))
        except FetchError as e:  # a rate limit or outage on one source falls through to the next
            rejected.append({"id": item["id"], "title": "", "source_url": None, "license": "", "reason": f"{search.__name__}: {e}"})
            continue
        for c in found:
            if not c.get("download_url"):
                continue
            ok, why = gate(c["license"])
            if ok:
                passed.append(c)
            else:
                rejected.append({"id": item["id"], "title": c["title"], "source_url": c["source_url"],
                                 "license": licence_code(c["license"]), "reason": why})
        any_passed = any_passed or bool(passed)
        yield from sorted(passed, key=score, reverse=True)  # lazily: Commons is asked only if no Openverse pick downloads
    if not any_passed:
        raise FetchError(f"no open-licence {item['kind']} for {item['query']!r} on Openverse or Commons")


def fetch_image(item: dict, rejected: list) -> tuple[bytes, str, dict]:
    errors = []
    for c in pick_images(item, rejected):  # best first; a dead link or a non-image tries the next candidate
        try:
            body, ctype = http_get(c["download_url"])
        except FetchError as e:
            errors.append(str(e))
            continue
        if ctype in IMAGE_TYPES:
            break
        errors.append(f"{c['download_url']} returned {ctype or 'no content type'}, not an image")
    else:
        raise FetchError(f"no candidate for {item['id']!r} downloaded: " + "; ".join(errors[:3]))
    c.pop("tags")
    c["attribution_required"] = gate(c["license"])[1] == "by"
    c["credit_text"] = f'"{c["title"]}" by {c["author"]}, {c["license"]}'
    return body, IMAGE_TYPES[ctype], c


# ---- media.json, cache, run ----
def load_items(path: Path) -> list:
    items = json.loads(path.read_text())
    if not isinstance(items, list):
        raise SystemExit(f"{path}: expected a list of assets")
    seen = set()
    for i, it in enumerate(items):
        where = f"{path} item {i}"
        if not isinstance(it, dict) or not ID_RE.fullmatch(str(it.get("id", ""))) or it["id"] in seen:
            raise SystemExit(f"{where}: id must be a unique slug [a-z0-9_-]")
        if it.get("kind") not in KINDS:
            raise SystemExit(f"{where}: kind must be one of {sorted(KINDS)}")
        for key in ("query", "depicts"):
            if not isinstance(it.get(key), str) or not it[key].strip():
                raise SystemExit(f"{where}: {key} must be a non-empty string")
        if ":" in it["query"] and (it["kind"] != "icon" or not ICON_RE.match(it["query"])):
            raise SystemExit(f"{where}: a set:name query is for icons only, as lowercase set:name")
        seen.add(it["id"])
    return items


def cached(teaser: Path, item: dict, old: dict) -> dict | None:
    """The old record when it was fetched for the same kind and query and its file is unchanged."""
    rec = old.get(item["id"])
    if not rec or rec.get("kind") != item["kind"] or rec.get("query") != item["query"]:
        return None
    f = teaser / rec["file"]
    return rec if f.is_file() and sha256(f) == rec.get("sha256") else None


def fetch(teaser: Path, item: dict, sets: dict, rejected: list) -> dict:
    if item["kind"] == "icon":
        body, ext, rec = fetch_icon(item, sets)
    else:
        body, ext, rec = fetch_image(item, rejected)
    rel = f"media/{item['id']}.{ext}"
    write_atomic(teaser / rel, body)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": item["id"], "kind": item["kind"], "file": rel, "sha256": hashlib.sha256(body).hexdigest(),
            "depicts": item["depicts"], "query": item["query"], **rec, "retrieved_at": stamp}


def offline(teaser: Path, items: list, old: dict) -> int:
    bad = 0
    for item in items:
        rec = cached(teaser, item, old)
        why = "not cached, or its query, kind or file changed" if not rec else (None if gate(rec["license"])[0] else gate(rec["license"])[1])
        if why:
            print(f"{item['id']}: {why}", file=sys.stderr)
            bad += 1
    print(f"offline: {len(items) - bad}/{len(items)} assets ready")
    return 1 if bad else 0


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("teaser", help="teaser folder; files go to <teaser>/media/")
    ap.add_argument("media_json")
    ap.add_argument("--offline", action="store_true", help="validate media.json against the cache, no network")
    args = ap.parse_args(argv)
    teaser, items = Path(args.teaser), load_items(Path(args.media_json))
    credits_path = teaser / "media/credits.json"
    doc = json.loads(credits_path.read_text()) if credits_path.is_file() else {}
    old = {a["id"]: a for a in doc.get("assets", [])}
    if args.offline:
        return offline(teaser, items, old)

    (teaser / "media").mkdir(parents=True, exist_ok=True)
    assets, rejected, sets, failed = [], [], {}, 0
    for item in items:
        rec = cached(teaser, item, old)
        if rec:
            assets.append({**rec, "depicts": item["depicts"]})
            rejected += [r for r in doc.get("rejected", []) if r["id"] == item["id"]]
            print(f"{item['id']}: cached {rec['file']} ({rec['license']})")
            continue
        try:
            rec = fetch(teaser, item, sets, rejected)
        except (FetchError, KeyError, TypeError, ValueError) as e:  # one bad asset must not stop the others
            print(f"{item['id']}: FAILED {type(e).__name__}: {e}", file=sys.stderr)
            failed += 1
            continue
        assets.append(rec)
        n_rej = sum(r["id"] == item["id"] for r in rejected)
        print(f"{item['id']}: fetched {rec['source']} {rec['title']!r} ({rec['license']}), {n_rej} rejected")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {"schema": 1, "video_id": teaser.resolve().name, "generated_at": stamp, "assets": assets, "rejected": rejected}
    write_atomic(credits_path, json.dumps(out, indent=1, ensure_ascii=False).encode())
    if failed:
        print(f"{failed} of {len(items)} assets failed; see the lines above", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
