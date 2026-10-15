"""Sound cues and music under the voice, synthesised with numpy: no sample files, no licences, no API.

    python3 sound.py <teaser dir> [--moods]   (ffmpeg on PATH; reads hf/data.js, hf/renders/raw.mp4, briefs/*.json)

Writes <teaser>/soundtrack.wav and <teaser>/teaser.mp4 (video copied, audio = voice + cues + music, loudnorm).
The sounds and the music follow kamwoh's infrasel-video mix.py (the team's reference cut); the timing comes from
the build, not from a person:
  a cut ticks, a push / wipe / zoom / morph whooshes, a camera move across a world cut whooshes softly,
  a type beat lands on a thud, a break shimmers, each brief's anchor word pops (a change on screen), and the end
  card plays a two-note success. Pops keep a gap and a cap a beat, so they never chatter.
Music (music.py): a mood (tempo, key, progression, instruments) played softly in act one (to the first break) and
in full in act two. It ducks under the voice and holds the duck through short pauses.
Over speech a cue sits at least UNDER_DB under the voice around it, so it never masks a word.
direction.json "sound": {"cues": true, "bed": true, "cue_gain": 1.0, "bed_gain": 1.0, "mood": "calm-tech", "seed": 0}
turns parts off, scales them, and picks the music. --moods writes music/<mood>.mp4 for every mood, for a person to
pick by ear: python3 sound.py <teaser dir> --moods
"""
import json
import pathlib
import subprocess
import sys
import wave

import numpy as np

from music import MOODS, music

SR = 48000
POP_GAP = 0.9  # s between two pops
POP_MAX = 4  # pops a beat
POP_SKIP = 0.3  # s after a beat start: the transition sound owns that moment
SWEEP = {"push", "wipe", "zoom", "morph"}
VOICE_PEAK = 0.9
MUSIC_LEVEL = 0.30  # music peak against the voice peak, before the duck
FX_LEVEL = 0.8
UNDER_DB = 12.0  # a cue over speech sits at least this far under the voice around it
DUCK = 0.55  # the music drops by this share while the voice speaks
DUCK_HOLD = 0.6  # s: the duck holds through pauses shorter than this


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, attack=0.005, decay=1.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t * decay)


def tone(f, dur, decay, partials=((1, 1.0),), attack=0.005):
    t = np.arange(int(dur * SR)) / SR
    return (sum(a * np.sin(2 * np.pi * f * h * t) for h, a in partials) * env(len(t), attack, decay)).astype(np.float32)


def noise(dur, seed):
    return np.random.default_rng(seed).standard_normal(int(dur * SR)).astype(np.float32)


def lowpass(x, k=8):
    return np.convolve(x, np.ones(k) / k, "same").astype(np.float32)


def cat(*sigs):
    """Sum signals of different lengths (zero-padded)."""
    n = max(len(x) for x in sigs)
    return sum(np.pad(x, (0, n - len(x))) for x in sigs).astype(np.float32)


def bank():
    """name -> mono float signal at its own level. Seeded, so every run makes the same sounds."""
    b = {}
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    b["pop"] = (np.sin(2 * np.pi * (500 + 900 * t / 0.12) * t) * env(n, 0.002, 40) * 0.5).astype(np.float32)
    b["tick"] = cat(tone(1800, 0.05, 90), 0.4 * tone(3600, 0.04, 120)) * 0.35
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    b["whoosh"] = lowpass(noise(0.6, 1), 14) * np.sin(np.pi * t / 0.6) ** 2 * 0.7
    b["soft-whoosh"] = b["whoosh"] * 0.5
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    b["thud"] = (np.sin(2 * np.pi * (90 * np.exp(-t * 6)) * t) * env(n, 0.002, 9) * 0.7).astype(np.float32)
    shimmer = sum(tone(hz(m), 1.8, 2.2, ((1, 1), (2.76, 0.25)), attack=0.02) for m in (84, 88, 91, 96))
    b["shimmer"] = shimmer * 0.12 + lowpass(noise(1.8, 2), 3) * env(int(1.8 * SR), 0.3, 3) * 0.05
    b["success"] = cat(tone(hz(76), 0.5, 7, ((1, 1), (2, 0.15))), np.pad(tone(hz(83), 0.6, 6, ((1, 1), (2, 0.15))), (int(0.09 * SR), 0))) * 0.22
    return {k: v.astype(np.float32) for k, v in b.items()}


def scene_words(scene):
    """Words a template scene reveals on (in, em.word, events[].word, items[].word): its visible changes."""
    out = []
    def walk(x, key=None):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, str) and key in ("in", "word"):
            out.append(x)
    walk(scene or {})
    return out


def word_time(beat, word, after):
    """The first time `word` is spoken in this beat at or after `after` (absolute s); None when not spoken."""
    want = word.lower().strip(".,!?;:'\"")
    for w in beat.get("words", []):
        if w["s"] >= after - 1e-6 and w["w"].lower().strip(".,!?;:'\"") == want:
            return w["s"]
    return None


def plan(data, briefs):
    """[(t, sound, gain, semitones)], sorted. Pure: the tests drive it with small data."""
    cues = []
    beats = data["beats"]
    for i, b in enumerate(beats):
        start = float(b["start"])
        prev = beats[i - 1] if i else None
        if prev:
            kind = b.get("in", "calm")
            if kind == "cut":
                cues.append((start, "tick", 0.6, 0))
            elif kind in SWEEP:
                cues.append((start - 0.3, "whoosh", 0.7, 0))
            elif b.get("world") and prev.get("world") and b["world"].get("view") != prev["world"].get("view"):
                cues.append((start - 0.1, "soft-whoosh", 0.8, 0))  # the camera moves across the cut
        if b.get("kind") == "break":
            cues.append((start + 0.05, "shimmer", 1.0, 0))
            continue
        if (b.get("scene") or {}).get("type_beat"):
            cues.append((start + 0.05, "thud", 1.0, 0))
        brief = briefs.get(b["id"])
        words = [a["word"] for a in brief.get("anchor_words", [])] if brief else scene_words(b.get("scene"))
        last, n, after = -9.0, 0, start + POP_SKIP
        for w in words:
            t = word_time(b, w, after)
            if t is None or t - last < POP_GAP:
                continue
            cues.append((t, "pop", 0.6, 0))
            last, n, after = t, n + 1, t
            if n == POP_MAX:
                break
    if data.get("end"):
        cues.append((float(data["end"]["start"]) + 0.2, "success", 0.8, 0))
    return sorted(cues)


def pitch(sig, semis):
    if not semis:
        return sig
    r = 2 ** (semis / 12)
    idx = np.arange(0, len(sig) - 1, r)
    return np.interp(idx, np.arange(len(sig)), sig).astype(np.float32)


def place(buf, t, sig, gain):
    i = max(0, int(t * SR))
    j = min(len(buf), i + len(sig))
    if j > i:
        buf[i:j] += sig[: j - i] * gain


def fit_under(voice, t, sig):
    """Gain (<= 1) that keeps sig UNDER_DB below the voice it lands on; 1 over silence."""
    i = max(0, int(t * SR))
    w = voice[i : i + len(sig)]
    v = np.sqrt(np.mean(w**2)) if len(w) else 0.0
    c = np.sqrt(np.mean(sig[: len(w)] ** 2)) if len(w) else 0.0
    if v < 1e-3 or c == 0:
        return 1.0
    return float(min(1.0, v * 10 ** (-UNDER_DB / 20) / c))


def act_switch(data):
    """Where act two starts: the first break, or 0 when the video has none."""
    return next((float(b["start"]) for b in data["beats"] if b.get("kind") == "break"), 0.0)


def duck(voice):
    """1 where the voice is quiet, 1 - DUCK while it speaks; the duck holds through pauses under DUCK_HOLD."""
    hop = int(0.01 * SR)
    loud = np.abs(voice[: len(voice) // hop * hop]).reshape(-1, hop).max(axis=1) > 0.02 * VOICE_PEAK / 0.9
    hold = int(DUCK_HOLD / 0.01) | 1
    talking = np.convolve(loud.astype(float), np.ones(hold), "same") > 0
    eased = np.convolve(talking.astype(float), np.ones(30) / 30, "same")
    return np.interp(np.arange(len(voice)), np.arange(len(eased)) * hop, 1 - DUCK * eased).astype(np.float32)


def read_wav(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).mean(axis=1)


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def main(teaser, out_mp4=None, over=None):
    over = over or {}
    teaser = pathlib.Path(teaser)
    hf = teaser / "hf"
    js = (hf / "data.js").read_text()
    data = json.loads(js[js.index("{") : js.rindex("}") + 1])
    direction = json.loads((teaser / "direction.json").read_text()) if (teaser / "direction.json").exists() else {}
    opts = {"cues": True, "bed": True, "cue_gain": 1.0, "bed_gain": 1.0, "mood": "calm-tech", "seed": 0, **direction.get("sound", {}), **over}
    if opts["mood"] not in MOODS:
        raise SystemExit(f"sound.mood {opts['mood']!r} not in {sorted(MOODS)}")
    briefs = {p.stem: json.loads(p.read_text()) for p in (teaser / "briefs").glob("*.json")} if (teaser / "briefs").is_dir() else {}
    raw = hf / "renders" / "raw.mp4"
    if not raw.exists():
        raise SystemExit(f"{raw} missing: render first (hyperframes render --output renders/raw.mp4)")
    voice_wav = hf / "renders" / "voice.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-vn", "-ac", "1", "-ar", str(SR), str(voice_wav)], check=True)
    voice = read_wav(voice_wav)
    voice *= VOICE_PEAK / (np.max(np.abs(voice)) + 1e-9)
    mix = voice.copy()
    cues = plan(data, briefs)
    if opts["cues"]:
        sounds, fx = bank(), np.zeros_like(voice)
        for t, name, gain, semis in cues:
            sig = pitch(sounds[name], semis) * gain * FX_LEVEL * opts["cue_gain"]
            place(fx, t, sig, fit_under(voice, t, sig))
        mix += fx
    if opts["bed"]:
        mix += music(len(voice) / SR, act_switch(data), opts["mood"], opts["seed"]) * MUSIC_LEVEL * opts["bed_gain"] * duck(voice)
    out_mp4 = pathlib.Path(out_mp4 or teaser / "teaser.mp4")
    out = out_mp4.with_suffix(".wav") if out_mp4.name != "teaser.mp4" else teaser / "soundtrack.wav"
    write_wav(out, mix / max(1.0, np.max(np.abs(mix))))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-i", str(out), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(out_mp4)], check=True)
    if out_mp4.name != "teaser.mp4":
        out.unlink()  # a mood variant keeps only its video
    kinds = {}
    for _, name, _, _ in cues:
        kinds[name] = kinds.get(name, 0) + 1
    print(f"{len(cues)} cues ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))}); music {opts['mood'] + ', act two at ' + format(act_switch(data), '.1f') + ' s' if opts['bed'] else 'off'} -> {out_mp4}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--moods"):
        raise SystemExit(__doc__)
    if len(sys.argv) == 3:
        (pathlib.Path(sys.argv[1]) / "music").mkdir(exist_ok=True)
        for name in MOODS:
            main(sys.argv[1], pathlib.Path(sys.argv[1]) / "music" / f"{name}.mp4", {"mood": name})
    else:
        main(sys.argv[1])
