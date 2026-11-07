#!/usr/bin/env python3
"""Original, code-generated sad underscore (soft piano + string pad + low bass, A minor, 64 BPM).
No samples, no third-party music. Output: source/music_sad_v01.wav (stereo 44.1 kHz, ~120 s).
Run: python3 -I scripts/make_music.py
"""
import os, wave
import numpy as np

SR = 44100
BPM = 64.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
BARS = 32
TOTAL = BARS * BAR + 2.5                      # + tail for reverb/fade
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(7)                # reproducible

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

L = np.zeros(int(TOTAL * SR)); R = np.zeros_like(L)

def put(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i < 0: sig = sig[-i:]; i = 0               # note starting before t=0: trim the lead-in
    n = min(len(sig), len(L) - i)
    if n <= 0: return
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    L[i:i + n] += sig[:n] * gain * l; R[i:i + n] += sig[:n] * gain * r

def piano(m, dur, vel):
    f = hz(m); n = int((dur + 1.2) * SR); t = np.arange(n) / SR
    tau = 0.8 + 2.4 * (110.0 / max(f, 110.0)) ** 0.6
    sig = np.zeros(n)
    for k, a in enumerate([1.0, 0.55, 0.32, 0.2, 0.12, 0.08, 0.05], start=1):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        sig += a * np.sin(2 * np.pi * fk * t) * np.exp(-t * (k - 1) * 0.55 / tau)
    env = np.exp(-t / tau) * (1 - np.exp(-t / 0.006))
    hold = int(dur * SR)
    rel = np.ones(n); rel[hold:] = np.exp(-(np.arange(n - hold)) / (0.25 * SR))     # soft release after note length
    return sig * env * rel * vel

def pad(ms, dur, vel):
    n = int((dur + 2.4) * SR); t = np.arange(n) / SR; sig = np.zeros(n)
    for m in ms:
        for det in (-0.07, 0.0, 0.07):                              # gentle detune = string ensemble feel
            f = hz(m) * 2 ** (det / 12)
            sig += np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    sig *= 1 + 0.06 * np.sin(2 * np.pi * 0.23 * t)                   # slow swell
    att, relt = 1.4, 1.8
    env = np.minimum(1, t / att) * np.minimum(1, np.maximum(0, (dur + relt - t) / relt))
    return sig * env * vel / (3 * len(ms))

def bass(m, dur, vel):
    f = hz(m); n = int((dur + 0.6) * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(1, t / 0.04) * np.exp(-t / (dur * 0.9)) * np.minimum(1, np.maximum(0, (dur + 0.5 - t) / 0.5))
    return sig * env * vel

# i - VI - III - VII in A minor: Am F C G
CHORDS = [dict(pad=[57, 60, 64], arp=[57, 64, 69, 64], root=33, mel=[(76, 0, 3), (74, 3, 1)]),
          dict(pad=[53, 57, 60], arp=[53, 60, 65, 60], root=29, mel=[(72, 0, 2), (69, 2, 2)]),
          dict(pad=[55, 60, 64], arp=[48, 55, 60, 55], root=36, mel=[(76, 0, 2), (72, 2, 2)]),
          dict(pad=[55, 59, 62], arp=[55, 62, 67, 62], root=31, mel=[(74, 0, 3), (71, 3, 1)])]

for bar in range(BARS):
    c = CHORDS[bar % 4]; t0 = bar * BAR
    # arc: 0-3 sparse intro | 4-15 steady | 16-27 fuller (melody doubled up) | 28-31 resolve and thin out
    sparse, full, outro = bar < 4, 16 <= bar < 28, bar >= 28
    put(pad(c["pad"], BAR, 0.55 if not outro else 0.45), t0 - 0.2, pan=0.0, gain=1.0)
    put(bass(c["root"], BAR, 0.35 if not sparse else 0.28), t0, pan=-0.1)
    if sparse:
        put(piano(c["arp"][0] + 12, 3, 0.30 + 0.04 * (bar % 2)), t0 + 0.5 * BEAT, pan=0.1)
    else:
        for b, m in enumerate(c["arp"]):
            if outro and b > 1: continue
            put(piano(m, BEAT * 1.6, (0.26 if not full else 0.30) * (1.0 if b == 0 else 0.8)), t0 + b * BEAT, pan=-0.25 + 0.1 * b)
        if 4 <= bar < 28:
            for m, bt, d in c["mel"]:
                put(piano(m + (12 if full and bar % 4 == 3 else 0), d * BEAT, 0.38), t0 + bt * BEAT + 0.02, pan=0.25)
        if outro and bar == 28 + 3:
            put(piano(81, 5, 0.20), t0 + 0.2, pan=0.3)                   # last high A, left to ring

# reverb: synthetic stereo IR (dark, ~2.8 s)
def make_ir(seed):
    r = np.random.default_rng(seed); n = int(2.8 * SR); t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t / 0.75)
    k = np.ones(24) / 24; ir = np.convolve(ir, k, mode="same")             # tame highs
    ir[:int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR)); return ir / np.sqrt(np.sum(ir ** 2))

def conv(x, ir):
    n = len(x) + len(ir) - 1; N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:len(x)]

wetL, wetR = conv(L, make_ir(1)), conv(R, make_ir(2))
L2 = 0.72 * L + 0.40 * wetL; R2 = 0.72 * R + 0.40 * wetR
# master: fades, soft clip, peak normalise
t = np.arange(len(L2)) / SR
fade = np.minimum(1, t / 3.0) * np.minimum(1, np.maximum(0, (TOTAL - 0.1 - t) / 4.5))
L2 *= fade; R2 *= fade
pk = max(abs(L2).max(), abs(R2).max()); L2 = np.tanh(L2 / pk * 1.2) / np.tanh(1.2) * 0.8; R2 = np.tanh(R2 / pk * 1.2) / np.tanh(1.2) * 0.8
os.makedirs(f"{ROOT}/source", exist_ok=True)
out = f"{ROOT}/source/music_sad_v01.wav"
if os.path.exists(out):
    n = 2
    while os.path.exists(f"{ROOT}/source/music_sad_v{n:02d}.wav"): n += 1
    out = f"{ROOT}/source/music_sad_v{n:02d}.wav"
pcm = (np.stack([L2, R2], axis=1) * 32767).astype("<i2")
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("WROTE", out, f"{len(L2)/SR:.1f}s")
