"""python3 -m pytest -q test_fetch_assets.py   (no network: urllib.request.urlopen is mocked by URL route)"""
import hashlib
import json
import urllib.error
import urllib.request

import pytest

import fetch_assets as fa
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "assets/hf"))
import media_build as mb  # noqa: E402

SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24">'
       b'<path fill="none" stroke="currentColor" d="M1 1h22"/></svg>')
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
LUCIDE = {"lucide": {"name": "Lucide", "author": {"name": "Lucide Contributors"},
                     "license": {"title": "ISC", "spdx": "ISC", "url": "https://lucide.dev/license"}}}


class FakeResp:
    def __init__(self, body, ctype):
        self.body, self.headers = body, {"Content-Type": ctype}

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def net(monkeypatch):
    """routes: [(url substring, body | Exception, content type)]; asked: every URL requested."""
    routes, asked = [], []

    def urlopen(req, timeout=None):
        url = req.full_url
        asked.append(url)
        assert "storyteller-video" in req.get_header("User-agent")
        for sub, body, ctype in routes:
            if sub in url:
                if isinstance(body, Exception):
                    raise body
                return FakeResp(body if isinstance(body, bytes) else json.dumps(body).encode(), ctype)
        raise urllib.error.URLError(f"no route for {url}")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fa.time, "sleep", lambda s: None)
    return routes, asked


def icon_routes(routes):
    routes.extend([
        ("api.iconify.design/search", {"icons": ["material-symbols:road", "lucide:road", "tabler:road"]}, "application/json"),
        ("collections?prefixes=lucide", LUCIDE, "application/json"),
        ("api.iconify.design/lucide/road.svg", SVG, "image/svg+xml"),
    ])


def ov(title, lic, url, tags=()):
    return {"title": title, "license": lic, "license_version": "2.0", "license_url": f"https://cc/{lic}",
            "creator": "OregonDOT", "creator_url": "https://flickr/odot", "url": url,
            "foreign_landing_url": url + ".html", "tags": [{"name": t} for t in tags]}


def run(tmp_path, items, *extra):
    spec = tmp_path / "media.json"
    spec.write_text(json.dumps(items))
    return fa.main([str(tmp_path / "teaser"), str(spec), *extra])


def credits(tmp_path):
    return json.loads((tmp_path / "teaser/media/credits.json").read_text())


ROAD = {"id": "road", "kind": "icon", "query": "road", "depicts": "a road"}
PHOTO = {"id": "fix", "kind": "photo", "query": "asphalt road repair", "depicts": "a crew repairs asphalt"}


# ---- licence gate ----
@pytest.mark.parametrize("raw", ["cc0", "CC0 1.0", "pdm", "Public domain", "by", "CC BY 2.0", "CC-BY-4.0", "MIT", "ISC",
                                 "Apache-2.0", "Apache 2.0"])
def test_gate_accepts_open_licences(raw):
    assert mb.gate(raw)[0]


@pytest.mark.parametrize("raw", ["by-nc", "by-nd", "by-sa", "CC BY-SA 4.0", "by-nc-sa", "GFDL", "", "All rights reserved"])
def test_gate_rejects_nc_nd_sa_and_unknown(raw):
    assert not mb.gate(raw)[0]


# ---- sanitizer ----
def test_sanitizer_strips_script_on_attributes_and_external_href():
    dirty = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1em" '
             'onload="alert(1)" viewBox="0 0 24 24"><script>alert(2)</script><defs><path id="p" d="M0 0"/></defs>'
             '<a href="https://evil.example/x"><path fill="#ff0000" onclick="x()" d="M1 1"/></a>'
             '<use href="#p"/><use xlink:href="https://evil.example/s.svg#a"/><image href="http://evil.example/i.png"/>'
             '<rect style="fill:url(https://evil.example/f)" stroke="red" width="4" height="4"/>'
             '<foreignObject><div>x</div></foreignObject></svg>')
    out = mb.sanitize_svg(dirty)
    for bad in ("script", "alert", "onload", "onclick", "evil.example", "foreignObject", "<image", 'width="1em"'):
        assert bad not in out
    assert 'href="#p"' in out
    assert "#ff0000" not in out and 'fill="currentColor"' in out and 'stroke="currentColor"' in out
    assert 'width="4"' in out  # shape geometry stays; only the root size goes
    assert "ns0:" not in out


def test_sanitizer_rejects_doctype_and_entities():
    with pytest.raises(ValueError):
        mb.sanitize_svg('<!DOCTYPE svg [<!ENTITY x "y">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>')


# ---- icons ----
def test_icon_search_picks_preferred_set_and_records_licence(tmp_path, net):
    icon_routes(net[0])
    assert run(tmp_path, [ROAD]) == 0
    rec = credits(tmp_path)["assets"][0]
    body = (tmp_path / "teaser/media/road.svg").read_bytes()
    assert rec["icon"] == "lucide:road" and rec["license"] == "ISC" and rec["source"] == "iconify"
    assert rec["sha256"] == hashlib.sha256(body).hexdigest()
    assert rec["file"] == "media/road.svg" and rec["depicts"] == "a road" and rec["query"] == "road"
    assert rec["author"] == "Lucide Contributors" and rec["credit_text"]


def test_icon_set_with_closed_licence_is_refused(tmp_path, net, capsys):
    net[0].append(("collections?prefixes=foo", {"foo": {"name": "Foo", "author": {"name": "F"},
                                                        "license": {"title": "GPL", "spdx": "GPL-3.0"}}}, "application/json"))
    assert run(tmp_path, [{**ROAD, "query": "foo:road"}]) == 1
    assert not (tmp_path / "teaser/media/road.svg").exists()
    assert "road" in capsys.readouterr().err


# ---- photos and illustrations ----
def test_openverse_pick_passes_the_gate_and_logs_rejections(tmp_path, net):
    results = [ov("Asphalt road repair", "by-nc", "https://img/nc.jpg"),
               ov("Road repair asphalt crew", "by-sa", "https://img/sa.jpg"),
               ov("Ambulance", "cc0", "https://img/amb.jpg"),
               ov("Crew patching a road", "by", "https://img/by.jpg", tags=["asphalt", "repair"])]
    net[0].extend([("api.openverse.org", {"results": results}, "application/json"),
               ("https://img/by.jpg", JPEG, "image/jpeg")])
    assert run(tmp_path, [PHOTO]) == 0
    c = credits(tmp_path)
    rec = c["assets"][0]
    assert rec["file"] == "media/fix.jpg" and rec["source"] == "openverse" and rec["license"] == "CC BY 2.0"
    assert rec["attribution_required"] and "OregonDOT" in rec["credit_text"]
    assert {r["license"] for r in c["rejected"]} == {"by-nc", "by-sa"}
    assert all(r["id"] == "fix" and r["reason"] for r in c["rejected"])
    assert "license=cc0%2Cpdm%2Cby" in next(u for u in net[1] if "openverse" in u)  # filtered at the source too


def test_commons_fallback_when_openverse_has_no_open_candidate(tmp_path, net):
    page = {"query": {"pages": {"1": {"title": "File:Pothole.jpg", "imageinfo": [{
        "thumburl": "https://upload/pothole.jpg", "descriptionurl": "https://commons/File:Pothole.jpg",
        "extmetadata": {"LicenseShortName": {"value": "Public domain"}, "LicenseUrl": {"value": ""},
                        "Artist": {"value": '<a href="u">Road <b>Crew</b></a>'},
                        "ObjectName": {"value": "Pothole repair"}}}]}}}}
    net[0].extend([("api.openverse.org", {"results": [ov("Road repair", "by-nd", "https://img/nd.jpg")]}, "application/json"),
               ("commons.wikimedia.org", page, "application/json"),
               ("https://upload/pothole.jpg", JPEG, "image/jpeg")])
    assert run(tmp_path, [PHOTO]) == 0
    rec = credits(tmp_path)["assets"][0]
    assert rec["source"] == "commons" and rec["author"] == "Road Crew" and rec["license"] == "Public domain"


def test_network_error_fails_that_asset_loudly_and_writes_no_half_file(tmp_path, net, capsys):
    icon_routes(net[0])
    net[0].extend([("api.openverse.org", {"results": [ov("asphalt road repair", "by", "https://img/by.jpg")]}, "application/json"),
               ("https://img/by.jpg", urllib.error.URLError("connection reset"), "")])
    assert run(tmp_path, [PHOTO, ROAD]) == 1
    media = tmp_path / "teaser/media"
    assert sorted(p.name for p in media.iterdir()) == ["credits.json", "road.svg"]
    err = capsys.readouterr().err
    assert "fix" in err and "connection reset" in err
    assert [a["id"] for a in credits(tmp_path)["assets"]] == ["road"]


def test_non_image_download_is_refused(tmp_path, net):
    net[0].extend([("api.openverse.org", {"results": [ov("asphalt road repair", "by", "https://img/by.jpg")]}, "application/json"),
               ("https://img/by.jpg", b"<html>login</html>", "text/html")])
    assert run(tmp_path, [PHOTO]) == 1
    assert not list((tmp_path / "teaser/media").glob("fix.*"))


# ---- cache and offline ----
def test_cache_hit_by_sha256_skips_the_network(tmp_path, net):
    icon_routes(net[0])
    assert run(tmp_path, [ROAD]) == 0
    net[1].clear()
    assert run(tmp_path, [ROAD]) == 0
    assert net[1] == []
    (tmp_path / "teaser/media/road.svg").write_text("<svg/>")  # tampered: the hash no longer matches
    assert run(tmp_path, [ROAD]) == 0
    assert net[1]


def test_offline_validates_media_json_against_the_cache(tmp_path, net, capsys):
    icon_routes(net[0])
    assert run(tmp_path, [ROAD]) == 0
    net[1].clear()
    assert run(tmp_path, [ROAD], "--offline") == 0
    assert run(tmp_path, [ROAD, PHOTO], "--offline") == 1
    assert "fix" in capsys.readouterr().err
    assert run(tmp_path, [{**ROAD, "query": "lucide:construction"}], "--offline") == 1  # query changed
    assert net[1] == []


@pytest.mark.parametrize("bad", [{**ROAD, "id": "../x"}, {**ROAD, "kind": "video"}, {**ROAD, "depicts": ""},
                                 {k: v for k, v in ROAD.items() if k != "query"}])
def test_media_json_is_validated(tmp_path, net, bad):
    with pytest.raises(SystemExit):
        run(tmp_path, [bad])


# ---- collect_media ----
def write_src(tmp_path, lic="CC BY 2.0"):
    src = tmp_path / "teaser"
    (src / "media").mkdir(parents=True)
    (src / "media/road.svg").write_bytes(SVG.replace(b"<path", b'<script>x</script><path onclick="y()"'))
    (src / "media/fix.jpg").write_bytes(JPEG)
    sha = lambda p: hashlib.sha256((src / p).read_bytes()).hexdigest()
    assets = [{"id": "road", "kind": "icon", "file": "media/road.svg", "sha256": sha("media/road.svg"), "license": "ISC",
               "attribution_required": False, "credit_text": "Lucide (ISC)"},
              {"id": "fix", "kind": "photo", "file": "media/fix.jpg", "sha256": sha("media/fix.jpg"), "license": lic,
               "attribution_required": True, "credit_text": '"Fix" by OregonDOT, CC BY 2.0'}]
    (src / "media/credits.json").write_text(json.dumps({"schema": 1, "assets": assets, "rejected": []}))
    return src


def test_collect_media_returns_inlined_icons_image_paths_and_credits(tmp_path):
    src = write_src(tmp_path)
    out = tmp_path / "hf"
    m = mb.collect_media(src, out=out)
    assert set(m) == {"icons", "images", "credits"}
    assert m["icons"]["road"].startswith("<svg") and "script" not in m["icons"]["road"] and "onclick" not in m["icons"]["road"]
    assert m["images"] == {"fix": "assets/media/fix.jpg"}
    assert (out / "assets/media/fix.jpg").read_bytes() == JPEG
    assert [c["id"] for c in m["credits"]] == ["road", "fix"]


def test_collect_media_without_credits_is_empty(tmp_path):
    assert mb.collect_media(tmp_path, out=tmp_path / "hf") == {"icons": {}, "images": {}, "credits": []}


def test_collect_media_refuses_a_closed_licence_or_changed_file(tmp_path):
    with pytest.raises(SystemExit):
        mb.collect_media(write_src(tmp_path / "a", lic="CC BY-NC 2.0"), out=tmp_path / "hf")
    src = write_src(tmp_path / "b")
    (src / "media/fix.jpg").write_bytes(b"other")
    with pytest.raises(SystemExit):
        mb.collect_media(src, out=tmp_path / "hf")
