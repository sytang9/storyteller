"""One WAV per beat with Kokoro-82M, plus word timings mapped back onto the caption words.
    python tts_beats.py dir [voice]   (reads dir/beats.json; writes dir/voice/<id>.wav and dir/beats.timed.json)
Needs Python 3.10-3.12 with `pip install "kokoro>=0.9.4" soundfile` (Apache-2.0 weights, runs on CPU or GPU)."""
import json, re, sys
from pathlib import Path
if len(sys.argv) < 2:  # before the heavy imports: kokoro loads torch for minutes
    sys.exit(__doc__)
import numpy as np, soundfile as sf
from kokoro import KPipeline
VOICE = sys.argv[2] if len(sys.argv) > 2 else "af_heart"
d = Path(sys.argv[1]); (d / "voice").mkdir(exist_ok=True); beats = json.loads((d / "beats.json").read_text())
if any(not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", str(b.get("id", ""))) for b in beats):
    sys.exit("beat ids must be lowercase letters, digits, - and _ (each becomes a file name)")
def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def align(caps, spoken, total):
    """Time each caption word from the spoken words. A caption word that is spoken differently ("245", "NOD")
    takes the span up to the next caption word that is spoken as written."""
    out, j = [], 0
    for i, cw in enumerate(caps):
        if j < len(spoken) and norm(spoken[j]["w"]) == norm(cw):
            out.append({"w": cw, "s": spoken[j]["s"], "e": spoken[j]["e"]}); j += 1; continue
        nxt = norm(caps[i + 1]) if i + 1 < len(caps) else None
        k = j
        while k < len(spoken) and (nxt is None or norm(spoken[k]["w"]) != nxt):
            k += 1
        span = spoken[j:k] or spoken[max(0, min(j, len(spoken) - 1)):][:1]
        s0, e0 = (span[0]["s"], span[-1]["e"]) if span else (0.0, total)
        out.append({"w": cw, "s": s0, "e": e0}); j = max(k, j + (1 if not span else 0))
    return out


pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
for b in beats:
    chunks, words, off = [], [], 0.0
    for r in pipe(b["text"], voice=VOICE, speed=b.get("speed", 0.92)):
        a = np.asarray(r.audio.cpu() if hasattr(r.audio, "cpu") else r.audio); chunks.append(a)
        for t in (r.tokens or []):
            if t.start_ts is not None and re.search(r"\w", t.text):
                words.append({"w": t.text, "s": round(off + t.start_ts, 3), "e": round(off + (t.end_ts or t.start_ts), 3)})
        off += len(a) / 24000
    sf.write(d / "voice" / f"{b['id']}.wav", np.concatenate(chunks), 24000)
    b["dur"] = round(off, 3); b["spoken_words"] = words
    b["caption_words"] = align(b["caption"].split(), words, off)
(d / "beats.timed.json").write_text(json.dumps(beats, indent=1))
print(json.dumps({b["id"]: b["dur"] for b in beats}))
