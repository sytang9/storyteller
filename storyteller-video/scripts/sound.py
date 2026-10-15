"""Sound cues and a music bed under the voice, synthesised with numpy: no sample files, no licences, no API.

    python3 sound.py <teaser dir>          (ffmpeg on PATH; reads hf/data.js, hf/renders/raw.mp4, briefs/*.json)

Writes <teaser>/soundtrack.wav and <teaser>/teaser.mp4 (video copied, audio = voice + cues + bed, loudnorm).
Cues follow what the picture does, so they come from the build, not from a person:
  a cut ticks, a push / wipe / zoom / morph whooshes, a camera move across a world cut whooshes softly,
  a type beat lands on a low hit, a break resets (the bed drops out), each brief's anchor word pops (a change on
  screen), and the end card chimes. Pops rise in pitch inside a beat and keep a gap, so they never chatter.
Over speech a cue sits at least UNDER_DB under the voice around it, so it never masks a word.
direction.json "sound": {"cues": true, "bed": true, "cue_gain": 1.0, "bed_gain": 1.0} turns parts off or scales them.
"""
import json
import pathlib
import subprocess
import sys
import wave

import numpy as np

SR = 48000
POP_GAP = 0.9  # s between two pops
POP_MAX = 4  # pops a beat
POP_SKIP = 0.3  # s after a beat start: the transition sound owns that moment
SWEEP = {"push", "wipe", "zoom", "morph"}
CUE_DB = -14.0  # cue peak against full scale, before cue_gain
BED_DB = -26.0  # bed level against full scale, before bed_gain and the duck
UNDER_DB = 12.0  # a cue over speech sits at least this far under the voice around it
DUCK = 0.6  # the bed drops by this share while the voice speaks
CHORDS = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G (MIDI); a break moves up a fourth


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t * decay)


def tone(f, dur, decay, attack=0.004, partials=((1, 1.0), (2, 0.25))):
    t = np.arange(int(dur * SR)) / SR
    return env(len(t), attack, decay) * sum(a * np.sin(2 * np.pi * f * k * t) for k, a in partials)


def noise(dur, seed):
    return np.random.default_rng(seed).standard_normal(int(dur * SR))


def smooth(x, k):
    return np.convolve(x, np.ones(k) / k, mode="same")


def bank():
    """name -> mono float signal, peak 1. Seeded, so every run makes the same sounds."""
    b = {}
    b["tick"] = smooth(noise(0.04, 1), 4) * env(int(0.04 * SR), 0.0005, 160) + 0.3 * tone(1900, 0.04, 140)
    n = int(0.55 * SR)
    sweep = np.sin(np.linspace(0, np.pi, n)) ** 2  # rises and falls
    b["whoosh"] = smooth(noise(0.55, 2), 24) * sweep
    b["soft-whoosh"] = smooth(noise(0.7, 3), 48) * np.sin(np.linspace(0, np.pi, int(0.7 * SR))) ** 3
    b["hit"] = tone(55, 0.9, 5, partials=((1, 1), (2, 0.4), (3, 0.1))) + 0.25 * smooth(noise(0.9, 4), 32) * env(int(0.9 * SR), 0.001, 18)
    b["reset"] = tone(hz(45), 1.6, 2.2, attack=0.02, partials=((1, 1), (1.5, 0.3), (2, 0.2))) + 0.15 * smooth(noise(1.6, 5), 96) * env(int(1.6 * SR), 0.2, 2)
    b["pop"] = tone(hz(76), 0.18, 26, partials=((1, 1), (2, 0.15)))
    chime = [tone(hz(m), 1.4, 3.2, partials=((1, 1), (2, 0.2), (3, 0.05))) for m in (72, 76, 79)]
    b["chime"] = sum(np.pad(c, (int(i * 0.08 * SR), 0))[: len(chime[0])] for i, c in enumerate(chime))
    return {k: (v / np.max(np.abs(v))).astype(np.float32) for k, v in b.items()}


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
                cues.append((start - 0.1, "soft-whoosh", 0.5, 0))  # the camera moves across the cut
        if b.get("kind") == "break":
            cues.append((start + 0.05, "reset", 0.9, 0))
            continue
        if (b.get("scene") or {}).get("type_beat"):
            cues.append((start + 0.05, "hit", 0.8, 0))
        brief = briefs.get(b["id"])
        words = [a["word"] for a in brief.get("anchor_words", [])] if brief else scene_words(b.get("scene"))
        last, n, after = -9.0, 0, start + POP_SKIP
        for w in words:
            t = word_time(b, w, after)
            if t is None or t - last < POP_GAP:
                continue
            cues.append((t, "pop", 0.45, 2 * n))  # each pop a whole tone higher: the beat builds
            last, n, after = t, n + 1, t
            if n == POP_MAX:
                break
    if data.get("end"):
        cues.append((float(data["end"]["start"]) + 0.2, "chime", 0.7, 0))
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


def bed(data, n):
    """A soft pad, one chord a beat; it moves up a fourth after a break, and rests during the break itself."""
    out = np.zeros(n, np.float32)
    shift = 0
    for i, b in enumerate(data["beats"]):
        start, end = float(b["start"]), float(b["end"])
        if b.get("kind") == "break":
            shift = 5
            continue
        chord = CHORDS[i % len(CHORDS)]
        dur = end - start + 1.0  # overlaps the next chord: no gap at the cut
        t = np.arange(int(dur * SR)) / SR
        fade = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.8)
        pad = sum(np.sin(2 * np.pi * hz(m + shift) * t) + 0.2 * np.sin(2 * np.pi * hz(m + shift + 12) * t) for m in chord)
        place(out, start - 0.5, (pad * fade / 4).astype(np.float32), 1.0)
    return out


def duck(voice):
    """1 where the voice is quiet, 1 - DUCK where it speaks, eased over about 0.2 s."""
    hop = int(0.02 * SR)
    frames = np.abs(voice[: len(voice) // hop * hop]).reshape(-1, hop).mean(axis=1)
    speaking = (frames > max(1e-4, 0.1 * frames.max())).astype(np.float32)
    eased = smooth(np.pad(speaking, (10, 10), mode="edge"), 10)[10:-10]
    curve = np.interp(np.arange(len(voice)), np.arange(len(eased)) * hop, 1 - DUCK * eased)
    return curve.astype(np.float32)


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


def main(teaser):
    teaser = pathlib.Path(teaser)
    hf = teaser / "hf"
    js = (hf / "data.js").read_text()
    data = json.loads(js[js.index("{") : js.rindex("}") + 1])
    direction = json.loads((teaser / "direction.json").read_text()) if (teaser / "direction.json").exists() else {}
    opts = {"cues": True, "bed": True, "cue_gain": 1.0, "bed_gain": 1.0, **direction.get("sound", {})}
    briefs = {p.stem: json.loads(p.read_text()) for p in (teaser / "briefs").glob("*.json")} if (teaser / "briefs").is_dir() else {}
    raw = hf / "renders" / "raw.mp4"
    if not raw.exists():
        raise SystemExit(f"{raw} missing: render first (hyperframes render --output renders/raw.mp4)")
    voice_wav = hf / "renders" / "voice.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-vn", "-ac", "1", "-ar", str(SR), str(voice_wav)], check=True)
    voice = read_wav(voice_wav)
    mix = voice.copy()
    cues = plan(data, briefs)
    if opts["cues"]:
        sounds, fx = bank(), np.zeros_like(voice)
        for t, name, gain, semis in cues:
            sig = pitch(sounds[name], semis) * gain * 10 ** (CUE_DB / 20) * opts["cue_gain"]
            place(fx, t, sig, fit_under(voice, t, sig))
        mix += fx
    if opts["bed"]:
        mix += bed(data, len(voice)) * duck(voice) * 10 ** (BED_DB / 20) * opts["bed_gain"]
    out = teaser / "soundtrack.wav"
    write_wav(out, mix / max(1.0, np.max(np.abs(mix))))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-i", str(out), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(teaser / "teaser.mp4")], check=True)
    kinds = {}
    for _, name, _, _ in cues:
        kinds[name] = kinds.get(name, 0) + 1
    print(f"{len(cues)} cues ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))}); bed {'on' if opts['bed'] else 'off'} -> {teaser / 'teaser.mp4'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
