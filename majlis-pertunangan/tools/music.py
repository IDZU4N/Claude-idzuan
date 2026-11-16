"""Gubahan instrumental asli (bebas hak cipta): pad hangat, petikan gaya gambus, rebana halus.
Skala Hijaz pada A: A Bb C# D E F G. Tempo perlahan (~64 bpm)."""
import numpy as np, soundfile as sf, sys
from scipy.signal import lfilter, butter, sosfilt, fftconvolve

SR = 48000
rng = np.random.default_rng(7)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, order=2):
    sos = butter(order, fc / (SR / 2), "low", output="sos")
    return sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = butter(order, fc / (SR / 2), "high", output="sos")
    return sosfilt(sos, x)


def env(n, a, r, sus=1.0):
    e = np.ones(n) * sus
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, sus, na) ** 1.5
    e[-nr:] = np.linspace(sus, 0, nr) ** 1.5
    return e


def pad_note(f, dur, a=3.0, r=3.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det, amp in ((-3.5, 1.0), (0.0, 1.0), (3.5, 0.9)):
        ff = f * 2 ** (det / 1200)
        ph = 2 * np.pi * ff * t + rng.uniform(0, 6.28)
        vib = 0.0015 * np.sin(2 * np.pi * 0.23 * t + rng.uniform(0, 6))
        w = np.sin(ph + vib * 30) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
        out += amp * w
    out = lp(out, 1500) * env(n, a, r)
    return out / 3.0


def pluck(f, dur=3.0, vel=0.7, bright=0.5):
    N = int(SR / f)
    n = int(dur * SR)
    x = np.zeros(n)
    burst = rng.uniform(-1, 1, N + 2)
    burst = lp(burst, 3000 + 4000 * bright)
    x[: N + 2] = burst
    a = np.zeros(N + 3)
    a[0] = 1.0
    g = 0.9965
    a[N] = -0.5 * g
    a[N + 1] = -0.5 * g
    y = lfilter([1.0], a, x)
    y = lp(y, 2600 + 2400 * bright)
    y *= np.exp(-np.arange(n) / (SR * 1.6))
    # vibrato halus pada ekor
    return vel * y / (np.abs(y).max() + 1e-9)


def drum_dum(vel=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 70 + 80 * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t * 9)
    y += 0.25 * lp(rng.uniform(-1, 1, n), 900) * np.exp(-t * 30)
    return vel * y


def drum_tak(vel=0.6):
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    y = hp(lp(rng.uniform(-1, 1, n), 4200), 900) * np.exp(-t * 28)
    y += 0.4 * np.sin(2 * np.pi * 220 * t) * np.exp(-t * 30)
    return vel * y


def reverb_ir(sec=2.8, decay=2.2):
    n = int(sec * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((2, n)) * np.exp(-t * decay)
    ir[:, : int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    for c in range(2):
        ir[c] = lp(ir[c], 5500)
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


def place(buf, x, start, pan=0.0):
    i = max(0, int(start * SR))
    if i >= buf.shape[1]:
        return
    j = min(buf.shape[1], i + len(x))
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    buf[0, i:j] += x[: j - i] * l
    buf[1, i:j] += x[: j - i] * r


# A Hijaz: A3=57
A = 57
HIJ = [0, 1, 4, 5, 7, 8, 10, 12]  # A Bb C# D E F G A
CHORDS = [  # nada pad (midi) bagi tiap 8 saat
    [A - 12, A, A + 7, A + 12],             # Am (drone A + E)
    [A - 12, A, A + 5, A + 10],             # A - D - G
    [A - 12 + 5, A + 5, A + 12, A + 17],    # D
    [A - 12, A, A + 4, A + 7],              # A (C#)
    [A - 12 + 1, A + 1, A + 8, A + 13],     # Bb
    [A - 12, A, A + 7, A + 12],             # kembali ke A
]
# frasa petikan: (mula-beat, nota-darjah-Hijaz, panjang)
MOTIF = [
    [(0, 7, 2), (2, 5, 1), (3, 4, 1), (4, 2, 2), (6, 1, 1), (7, 0, 1)],
    [(0, 0, 2), (2, 1, 1), (3, 2, 1), (4, 4, 2), (6, 5, 1), (7, 4, 1)],
    [(0, 5, 2), (2, 4, 1), (3, 2, 1), (4, 1, 3), (7, 0, 1)],
    [(0, 0, 1), (1, 2, 1), (2, 4, 2), (4, 5, 2), (6, 7, 2)],
]


def compose(total_sec, drums_on=lambda t: False, pluck_on=lambda t: True, seed=7):
    global rng
    rng = np.random.default_rng(seed)
    n = int(total_sec * SR)
    buf_pad = np.zeros((2, n))
    buf_pl = np.zeros((2, n))
    buf_dr = np.zeros((2, n))
    bar = 8.0
    nbars = int(total_sec / bar) + 1
    for b in range(nbars):
        ch = CHORDS[b % len(CHORDS)]
        for k, m in enumerate(ch):
            x = pad_note(midi(m), bar + 5.0)
            place(buf_pad, x * (0.8 if k == 0 else 0.6), b * bar - 1.5 if b else 0.0, pan=(-0.4 + 0.27 * k))
    beat = 60.0 / 64
    for b in range(nbars):
        t0 = b * bar
        if not pluck_on(t0):
            continue
        mo = MOTIF[b % len(MOTIF)] if (b % 2 == 0) else []
        for (bt, deg, ln) in mo:
            oct_ = 12 if deg < 7 else 0
            m = A + 12 + HIJ[deg % 8] if deg < 8 else A + 24
            f = midi(A + 12 + HIJ[deg] if deg < 8 else A + 24)
            x = pluck(f, 3.2, vel=0.55 + 0.1 * rng.random(), bright=0.45)
            place(buf_pl, x, t0 + bt * beat + rng.uniform(-0.01, 0.01), pan=0.25)
        # nada rendah penyokong
        if b % 2 == 0:
            x = pluck(midi(A - 12), 4.0, vel=0.5, bright=0.2)
            place(buf_pl, x, t0, pan=-0.2)
    # rebana
    pattern = [("d", 0), ("t", 1.5), ("t", 2.0), ("d", 3.0), ("t", 3.5)]
    cycle = 4 * beat
    for c in range(int(total_sec / cycle) + 1):
        t0 = c * cycle
        if not drums_on(t0):
            continue
        for kind, bt in pattern:
            x = drum_dum(0.85) if kind == "d" else drum_tak(0.5)
            place(buf_dr, x, t0 + bt * beat, pan=-0.1 if kind == "d" else 0.2)
    ir = reverb_ir()
    def wet(x, mix):
        w = np.stack([fftconvolve(x[0], ir[0])[:n], fftconvolve(x[1], ir[1])[:n]])
        return (1 - mix) * x + mix * w
    mix = wet(buf_pad, 0.35) * 0.55 + wet(buf_pl, 0.38) * 0.9 + wet(buf_dr, 0.25) * 0.55
    # lembut: tapis rendah sedikit, hadkan
    peak = np.abs(mix).max()
    mix = mix / (peak + 1e-9) * 0.7
    return mix.astype(np.float32)


if __name__ == "__main__":
    total = float(sys.argv[2])
    out = sys.argv[1]
    m = compose(total, drums_on=lambda t: (t < 70) or (t > total - 90), pluck_on=lambda t: True)
    sf.write(out, m.T, SR, subtype="PCM_24")
    print("ok", m.shape)
