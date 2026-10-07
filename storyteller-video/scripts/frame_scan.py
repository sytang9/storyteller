"""Scan every frame of a render for the two defects a contact sheet cannot show.

    python3 frame_scan.py <video> [beats data.js]      (ffmpeg on PATH)

- strobe: a single frame much darker or brighter than both neighbours (a blank frame from a seek bug flickers at
  several Hz and reads as a broken film; the 2026-10-07 trial had one every 6th frame for 9 s)
- empty: the scene area stays nearly uniform (no content) for more than EMPTY_MAX seconds
The caption band (the bottom 200 px) is left out, so captions do not hide either defect. Exit 1 on any hit.
"""
import json
import subprocess
import sys

W, H = 96, 44  # a small grey thumbnail per frame is enough for both checks
FPS = 30
DIP = 3.0  # mean grey level step that counts as a one-frame flash
FLAT = 2.5  # pixel spread (std) below which a frame has no content
EMPTY_MAX = 0.5  # s


def frames(video):
    cmd = ["ffmpeg", "-loglevel", "error", "-i", video, "-vf", f"crop=1920:880:0:0,scale={W}:{H},format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = W * H
    return [raw[i : i + n] for i in range(0, len(raw) - n + 1, n)]


def stats(f):
    mean = sum(f) / len(f)
    return mean, (sum((p - mean) ** 2 for p in f) / len(f)) ** 0.5


def beat_at(t, beats):
    return next((b["id"] for b in reversed(beats) if b["start"] <= t), "?")


def main(video, data_js=None):
    beats = json.loads(open(data_js).read().split("=", 1)[1].strip().rstrip(";"))["beats"] if data_js else []
    s = [stats(f) for f in frames(video)]
    hits = []
    for i in range(1, len(s) - 1):
        if abs(s[i][0] - s[i - 1][0]) > DIP and abs(s[i][0] - s[i + 1][0]) > DIP and (s[i][0] - s[i - 1][0]) * (s[i][0] - s[i + 1][0]) > 0:
            hits.append(("strobe", i / FPS))
    run = 0
    for i, (_, std) in enumerate(s):
        run = run + 1 if std < FLAT else 0
        if run == int(EMPTY_MAX * FPS) + 1:
            hits.append(("empty", (i - run + 1) / FPS))
    for kind, t in hits[:30]:
        print(f"{kind:<7} {t:7.2f} s  {beat_at(t, beats)}")
    print(f"{len(s)} frames, {sum(k == 'strobe' for k, _ in hits)} strobe, {sum(k == 'empty' for k, _ in hits)} empty: {'FIX' if hits else 'PASS'}")
    return 1 if hits else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:3]))
