"""One-beat sandboxes for parallel scene designers, and the merge back into the film.

    python3 scene_sandbox.py make  <teaser dir> <hf bin dir> b01 b02 ...   # work/<id>/ per custom beat
    python3 scene_sandbox.py merge <teaser dir>                            # sandbox scene fields -> beats.timed.json

make: each work/<id>/ holds a copy of the template (hf/), that beat's voice, links to media/ and shots/frames/,
direction.json, and a beats.timed.json with only that beat (its transition removed: the seams are checked after
the merge, in the full film). A designer writes <teaser>/<id>.js, copies it into the sandbox and builds there.
merge: copies each sandbox beat's scene object (the fields its designer added) into <teaser>/beats.timed.json,
for custom beats only, and prints which beats changed.
"""
import json
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets/hf"


def make(teaser, bin_dir, ids):
    beats = {b["id"]: b for b in json.loads((teaser / "beats.timed.json").read_text())}
    for i in ids:
        if i not in beats:
            raise SystemExit(f"no beat {i} in beats.timed.json")
        box = teaser / "work" / i
        (box / "voice").mkdir(parents=True, exist_ok=True)
        (box / "shots").mkdir(exist_ok=True)
        shutil.copytree(TEMPLATE, box / "hf", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        shutil.copytree(bin_dir, box / "hf/.bin", dirs_exist_ok=True, symlinks=True)
        shutil.copy2(teaser / "voice" / f"{i}.wav", box / "voice")
        for name, target in (("media", teaser / "media"), ("shots/frames", teaser / "shots/frames")):
            link = box / name
            if target.exists() and not link.exists():
                link.symlink_to(target)
        (box / "shots/tour.json").write_text('{"beats": []}')
        if (teaser / "direction.json").exists():
            shutil.copy2(teaser / "direction.json", box)
        beat = {k: v for k, v in beats[i].items() if k != "in"}
        (box / "beats.timed.json").write_text(json.dumps([beat], indent=1))
        print(f"{box}")


def merge(teaser):
    path = teaser / "beats.timed.json"
    beats = json.loads(path.read_text())
    for b in beats:
        box = teaser / "work" / b["id"] / "beats.timed.json"
        if (b.get("scene") or {}).get("type") != "custom" or not box.exists():
            continue
        scene = json.loads(box.read_text())[0]["scene"]
        if scene != b["scene"]:
            print(f"{b['id']}: {sorted(k for k in scene if scene.get(k) != b['scene'].get(k))}")
            b["scene"] = scene
    path.write_text(json.dumps(beats, indent=1))


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("make", "merge"):
        sys.exit(__doc__)
    if sys.argv[1] == "make":
        make(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4:])
    else:
        merge(Path(sys.argv[2]))
