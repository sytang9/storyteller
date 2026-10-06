"""One frame per beat, taken just before the beat hands over, and a contact sheet of them.

    python3 qc_sheet.py <teaser dir> [video]     (video default: <teaser dir>/teaser.mp4)

Reads <teaser dir>/hf/data.js (written by build.py) and writes <teaser dir>/qc/<id>.png (640 px wide) and
qc/sheet.png (4 frames a row). The frame time is the beat's end minus SETTLE: late enough that the scene is fully
built, early enough that the next transition (at most 0.35 s before the boundary) has not started.
Needs ffmpeg on PATH.
"""
import json
import subprocess
import sys
from pathlib import Path

SETTLE = 0.6  # s before the boundary
PER_ROW = 4
WIDTH = 640


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def main(teaser, video=None):
    teaser = Path(teaser)
    video = Path(video) if video else teaser / "teaser.mp4"
    data = json.loads((teaser / "hf/data.js").read_text().split("=", 1)[1].strip().rstrip(";"))
    qc = teaser / "qc"
    qc.mkdir(exist_ok=True)
    frames = []
    for b in data["beats"]:
        t = max(b["start"], b["end"] - SETTLE)
        out = qc / f"{b['id']}.png"
        ffmpeg("-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={WIDTH}:-1", str(out))
        frames.append(out)
        print(f"{b['id']} {t:.2f}s")
    # pad the last row with a copy of the last frame's size in black, so hstack gets equal inputs
    rows = [frames[i : i + PER_ROW] for i in range(0, len(frames), PER_ROW)]
    row_files = []
    for k, row in enumerate(rows):
        inputs = [a for f in row for a in ("-i", str(f))]
        pad = PER_ROW - len(row)
        graph = "".join(f"[{i}]" for i in range(len(row)))
        if pad:
            graph = f"[{len(row) - 1}]split=2[last][blank];[blank]drawbox=c=black:t=fill,split={pad}" + "".join(f"[p{j}]" for j in range(pad)) + ";"
            graph += "".join(f"[{i}]" for i in range(len(row) - 1)) + "[last]" + "".join(f"[p{j}]" for j in range(pad))
        graph += f"hstack=inputs={PER_ROW}" if len(row) + pad > 1 else "null"
        out = qc / f"_row{k}.png"
        ffmpeg(*inputs, "-filter_complex", graph, str(out))
        row_files.append(out)
    inputs = [a for f in row_files for a in ("-i", str(f))]
    ffmpeg(*inputs, "-filter_complex", f"vstack=inputs={len(row_files)}" if len(row_files) > 1 else "null", str(qc / "sheet.png"))
    for f in row_files:
        f.unlink()
    print(f"{qc / 'sheet.png'}: {len(frames)} beats")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:3])
