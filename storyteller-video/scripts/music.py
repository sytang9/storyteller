"""Procedural music beds in a few moods, synthesised with numpy (no sample files, no licences, no API).

A mood fixes the tempo, the key, a chord progression and the instruments; a seed varies the voicing and the
arpeggio pattern inside it, so two videos in one mood still differ. The voices and the drum sounds follow kamwoh's
infrasel-video mix.py (the team's reference cut).

Two acts: act one (to the first break) plays the mood softly (pad and a sparse arpeggio, no bass, no drums); act two
plays it in full. No sub-bass anywhere: the lowest note is the bass at about 65-110 Hz.
"""
import numpy as np

SR = 48000

# chords are scale degrees of the key (0 = the root chord), triads built in the mood's scale
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
DORIAN = [0, 2, 3, 5, 7, 9, 10]
MOODS = {
    "calm-tech": {"bpm": 100, "root": 48, "scale": MAJOR, "prog": [0, 5, 3, 4], "lead": "pluck", "drums": "soft"},
    "curious": {"bpm": 92, "root": 50, "scale": DORIAN, "prog": [0, 3, 0, 6], "lead": "bell", "drums": "light"},
    "warm-keys": {"bpm": 76, "root": 53, "scale": MAJOR, "prog": [0, 4, 5, 3], "lead": "keys", "drums": "none"},
    "pulse": {"bpm": 112, "root": 52, "scale": MINOR, "prog": [0, 5, 2, 6], "lead": "pluck", "drums": "drive"},
    "ambient": {"bpm": 70, "root": 51, "scale": MAJOR, "prog": [0, 1, 5, 3], "lead": "bell", "drums": "none"},
    "bright": {"bpm": 120, "root": 55, "scale": MAJOR, "prog": [0, 4, 5, 3], "lead": "keys", "drums": "soft"},
}
ARPS = [[0, 1, 2, 1, 0, 1, 2, 1], [0, 2, 1, 2, 0, 2, 1, 3], [2, 1, 0, 1, 2, 3, 2, 1]]  # chord-tone steps, eighth notes
LEADS = {
    "pluck": (((1, 1), (3, 0.12), (5, 0.04)), 7.0),
    "bell": (((1, 1), (2.76, 0.25), (5.4, 0.08)), 4.0),
    "keys": (((1, 1), (2, 0.45), (3, 0.2), (4, 0.08)), 3.5),
}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t * decay)


def tone(f, dur, decay, partials=((1, 1.0),), attack=0.005):
    t = np.arange(int(dur * SR)) / SR
    return (sum(a * np.sin(2 * np.pi * f * h * t) for h, a in partials) * env(len(t), attack, decay)).astype(np.float32)


def place(buf, t, sig, gain):
    i = max(0, int(t * SR))
    j = min(len(buf), i + len(sig))
    if j > i:
        buf[i:j] += sig[: j - i] * gain


def triad(mood, degree, rng):
    """MIDI notes of a chord on this scale degree; the seed picks root position or an inversion."""
    sc, root = mood["scale"], mood["root"]
    notes = [root + sc[(degree + k) % 7] + 12 * ((degree + k) // 7) for k in (0, 2, 4)]
    inv = int(rng.integers(0, 3))
    return sorted(n + 12 * (i < inv) for i, n in enumerate(notes))


def drums(out, tb, beat, style, rng):
    if style == "none":
        return
    tk = np.arange(int(0.25 * SR)) / SR
    kick = (np.sin(2 * np.pi * (45 + 80 * np.exp(-tk * 30)) * tk) * env(len(tk), 0.001, 14)).astype(np.float32)
    hiss = rng.standard_normal(int(0.05 * SR)).astype(np.float32)
    shaker = np.convolve(np.diff(hiss, prepend=0), np.ones(2) / 2, "same") * env(len(hiss), 0.001, 70)
    kicks = {"light": (0,), "soft": (0, 2), "drive": (0, 1, 2, 3)}[style]
    for q in kicks:
        place(out, tb + q * beat, kick, 0.3)
    for e in range(1, 8, 2):
        place(out, tb + e * beat / 2, shaker, 0.05 if style != "light" else 0.03)


def music(dur, switch, mood="calm-tech", seed=0):
    """A bed `dur` s long, act two from `switch` s, peak 1 and a 3 s fade at the end."""
    m = MOODS[mood]
    rng = np.random.default_rng(seed)
    arp = ARPS[int(rng.integers(0, len(ARPS)))]
    partials, decay = LEADS[m["lead"]]
    n = int(dur * SR)
    out = np.zeros(n + 4 * SR, np.float32)
    beat = 60 / m["bpm"]
    bar = 4 * beat
    for k in range(int(dur / bar) + 2):
        tb = k * bar
        full = tb >= switch
        ch = triad(m, m["prog"][k % len(m["prog"])], rng)
        place(out, tb, sum(tone(hz(x), bar + 0.5, 0.4, ((1, 1), (2, 0.15), (3, 0.05)), attack=0.4) for x in ch), 0.035 if full else 0.03)
        steps = range(8) if full else range(0, 8, 2)  # act one: quarter notes, act two: eighth notes
        for e in steps:
            place(out, tb + e * beat / 2, tone(hz(ch[arp[e] % 3] + 12), 0.5, decay, partials), 0.06 if full else 0.045)
        if full:
            place(out, tb, tone(hz(ch[0] - 12), bar, 1.2, ((1, 1), (2, 0.4))), 0.22)
            if tb >= switch + 2 * bar:  # drums come in on act two's third bar
                drums(out, tb, beat, m["drums"], rng)
    out = out[:n]
    fo = min(n, int(3.0 * SR))
    out[n - fo :] *= np.linspace(1, 0, fo)
    return out / (np.max(np.abs(out)) + 1e-9)
