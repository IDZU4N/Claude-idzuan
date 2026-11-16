"""Enjin suntingan: garis masa -> audio (numpy) + video (ffmpeg, per bingkai) -> MP4.
Audio ialah penentu (pengacara sebagai landasan). Video disusun mengikut panjang audio."""
import os, sys, json, math, subprocess, hashlib
import numpy as np
import soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
import cine, photos

S = cine.S
SR = 48000
FPSN, FPSD = 30000, 1001
FPS = FPSN / FPSD
W, H = 1920, 1080
MEZ = f"{S}/mez"
PROC = f"{S}/proc"
os.makedirs(MEZ, exist_ok=True)
os.makedirs(PROC, exist_ok=True)


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg gagal: " + " ".join(map(str, cmd))[:300] + "\n" + r.stderr[-800:])
    return r


# ---------------------------------------------------------------- audio sumber
_cache = {}
_gain = {}

AF = ("highpass=f=85,afftdn=nr=9:nf=-40:nt=w,"
      "equalizer=f=3200:t=q:w=1.2:g=1.5,lowpass=f=13500,"
      "acompressor=threshold=0.09:ratio=2.2:attack=20:release=300:makeup=1.5")


def proc_audio(name):
    out = f"{PROC}/{name}.wav"
    if not os.path.exists(out):
        src = [f for f in (f"{S}/src/{name}.mov", f"{S}/src/{name}.MOV") if os.path.exists(f)][0]
        sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "2", "-ar", str(SR), "-af", AF,
            "-c:a", "pcm_f32le", out])
    return out


def load(name):
    if name not in _cache:
        x, sr = sf.read(proc_audio(name), dtype="float32", always_2d=True)
        assert sr == SR
        x = x.T.copy()
        # gandaan statik daripada RMS bingkai bertutur (tiada 'pumping')
        m = x.mean(axis=0)
        fr = 4800
        n = len(m) // fr
        rms = np.sqrt((m[: n * fr].reshape(n, fr) ** 2).mean(axis=1) + 1e-12)
        db = 20 * np.log10(rms)
        act = db[db > (db.max() - 22)]
        lvl = np.mean(act) if len(act) else db.max()
        g = 10 ** ((-23.0 - lvl) / 20)
        g = min(g, 6.0)
        _gain[name] = g
        _cache[name] = x * g
    return _cache[name]


# ---------------------------------------------------------------- titik potong pada celah perkataan
_words = {}


def words(name):
    if name not in _words:
        for sz in ("medium", "small"):
            p = f"{S}/tr/{name}.{sz}.json"
            if os.path.exists(p):
                d = json.load(open(p))
                w = []
                for s in d["segs"]:
                    for a, b, t in s["w"]:
                        w.append((a, b))
                _words[name] = w
                break
        else:
            _words[name] = []
    return _words[name]


def snap(name, t, kind, win=0.35):
    """Ketatkan titik potong ke celah antara perkataan terdekat yang tenang.
    kind='in' : titik masuk (sebelum perkataan pertama), 'out': titik keluar (selepas perkataan terakhir)."""
    w = words(name)
    x = load(name).mean(axis=0)
    best, bs = t, 1e9
    # calon: celah antara perkataan
    gaps = []
    for i in range(len(w) - 1):
        a, b = w[i][1], w[i + 1][0]
        if b - a >= 0.04:
            gaps.append((a, b))
    for a, b in gaps:
        if a - 0.05 <= t + win and b + 0.05 >= t - win:
            # titik paling tenang dalam celah
            lo, hi = max(a, t - win), min(b, t + win)
            i0, i1 = int(lo * SR), int(hi * SR)
            seg = np.abs(x[i0:i1])
            if len(seg) < 960:
                continue
            k = 480
            en = np.convolve(seg, np.ones(k) / k, mode="same")
            j = int(np.argmin(en[k // 2: len(en) - k // 2])) + k // 2
            cand = (i0 + j) / SR
            # keutamaan: dekat dengan t, kecuali 'in' lebih rela ke awal, 'out' ke akhir
            sc = abs(cand - t)
            if (kind == "in" and cand > t) or (kind == "out" and cand < t):
                sc += 0.08
            if sc < bs:
                bs, best = sc, cand
    return round(best, 3)


# ---------------------------------------------------------------- spesifikasi
class Seg:
    """Segmen audio: sumber, masa mula/akhir sumber, bas ('dlg' atau 'amb'), gandaan dB."""
    def __init__(self, src, a, b, bus="dlg", gain=0.0, snap_edges=True, fi=0.0, fo=0.0, xf=0.035):
        self.src = src
        self.a = snap(src, a, "in") if snap_edges and bus == "dlg" else a
        self.b = snap(src, b, "out") if snap_edges and bus == "dlg" else b
        self.bus, self.gain, self.fi, self.fo, self.xf = bus, gain, fi, fo, xf

    @property
    def dur(self):
        return self.b - self.a


class Shot:
    def __init__(self, kind, src, dur, ss=0.0, sync=False, dis=0.0, stab=False, **kw):
        self.kind, self.src, self.dur, self.ss, self.sync, self.dis, self.stab = kind, src, dur, ss, sync, dis, stab
        self.kw = kw
        self.start = 0.0   # masa global (s)


def C(src, ss, dur, dis=0.0, stab=False, **kw):
    return Shot("clip", src, dur, ss=ss, dis=dis, stab=stab, **kw)


def SYNC(src, dur, dis=0.0, **kw):
    return Shot("clip", src, dur, sync=True, dis=dis, **kw)


def P(name, dur, dis=0.6, **kw):
    return Shot("photo", name, dur, dis=dis, **kw)


class Scene:
    def __init__(self, name, audio, shots, d_in=0.8, music="duck", note="", dur=None):
        self.name, self.audio, self.shots, self.d_in, self.music, self.note = name, audio, shots, d_in, music, note
        self.fixed_dur = dur
        self.t0 = 0.0
        self.alen = 0.0
        self.seg_t = []  # (scene_t_start, seg)


def layout(scenes):
    """Tentukan masa global audio dan video. Audio ialah penentu panjang pemandangan."""
    t = 0.0
    prev_end = 0.0
    for si, sc in enumerate(scenes):
        # panjang audio pemandangan
        tt = 0.0
        sc.seg_t = []
        for i, sg in enumerate(sc.audio):
            if i > 0:
                tt -= sg.xf
            sc.seg_t.append((tt, sg))
            tt += sg.dur
        if not sc.audio and sc.fixed_dur:
            tt = sc.fixed_dur
        sc.alen = tt
        sc.t0 = prev_end - (sc.d_in if si > 0 else 0.0)
        prev_end = sc.t0 + sc.alen
        # susun bidikan di dalam pemandangan
        vt = 0.0
        for i, shot in enumerate(sc.shots):
            if i > 0:
                vt -= shot.dis
            shot.start = sc.t0 + vt
            shot._scene_t = vt
            vt += shot.dur
        vlen = vt
        d = sc.alen - vlen
        if abs(d) > 0.02:
            last = sc.shots[-1]
            if last.dur + d < 0.8:
                raise RuntimeError(f"Pemandangan {sc.name}: audio {sc.alen:.2f}s vs video {vlen:.2f}s (terlalu jauh)")
            last.dur += d
            vlen += d
        if si == 0:
            pass
        # peta masa sumber untuk bidikan sync
        for shot in sc.shots:
            if shot.sync:
                st = shot._scene_t
                for (ts, sg) in sc.seg_t:
                    if ts - 1e-6 <= st < ts + sg.dur + 1e-6 and sg.src == shot.src:
                        shot.ss = sg.a + (st - ts)
                        break
                else:
                    raise RuntimeError(f"SYNC tanpa segmen audio sepadan: {sc.name} {shot.src} @ {st:.2f}")
    total = prev_end
    return total


# ---------------------------------------------------------------- audio akhir
def build_audio(scenes, total, music_path=None, music_gain_db=-17.0):
    n = int(math.ceil(total * SR)) + SR
    dlg = np.zeros((2, n), dtype=np.float32)
    amb = np.zeros((2, n), dtype=np.float32)
    duck_src = np.zeros(n, dtype=np.float32)  # tanda ada ucapan/doa
    for sc in scenes:
        for (ts, sg) in sc.seg_t:
            x = load(sg.src)[:, int(sg.a * SR): int(sg.b * SR)].copy()
            ln = x.shape[1]
            x *= 10 ** (sg.gain / 20)
            fi = max(sg.fi, 0.0)
            fo = max(sg.fo, 0.0)
            # sambungan: kemasukan/keluar bersilang
            xfi = int(min(sg.xf, 0.5) * SR) if ts > 0 or True else 0
            if sg is sc.audio[0]:
                xfi = int(sc.d_in * SR) if scenes.index(sc) > 0 else 0
            if sg is sc.audio[-1] and scenes.index(sc) < len(scenes) - 1:
                nxt = scenes[scenes.index(sc) + 1]
                xfo = int(nxt.d_in * SR)
            else:
                xfo = int(sg.xf * SR)
            fin = max(xfi, int(fi * SR))
            fout = max(xfo, int(fo * SR))
            env = np.ones(ln, dtype=np.float32)
            if fin > 0:
                k = min(fin, ln // 2)
                env[:k] = np.sin(np.linspace(0, np.pi / 2, k)) ** 1.0
            if fout > 0:
                k = min(fout, ln // 2)
                env[-k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 1.0
            x *= env
            i0 = int((sc.t0 + ts) * SR)
            tgt = dlg if sg.bus == "dlg" else amb
            tgt[:, i0: i0 + ln] += x[:, : n - i0]
            if sg.bus == "dlg":
                duck_src[i0: i0 + ln] = np.maximum(duck_src[i0: i0 + ln], env[: n - i0])
    return dlg, amb, duck_src


def speech_activity(dlg, thresh_db=-44, fr=0.02):
    m = dlg.mean(axis=0)
    k = int(fr * SR)
    nfr = len(m) // k
    r = np.sqrt((m[: nfr * k].reshape(nfr, k) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(r) > thresh_db, k


def duck_curve(dlg, n, floor_db, attack=0.12, release=0.9, thresh_db=-46):
    act, k = speech_activity(dlg, thresh_db)
    # perluas aktiviti (jeda pendek antara perkataan masih 'ucapan')
    a = act.astype(np.float32)
    hold = int(0.35 / 0.02)
    ker = np.ones(hold, dtype=np.float32)
    a = np.clip(np.convolve(a, ker, mode="full")[: len(a)], 0, 1)
    # lengkung lancar
    g = np.zeros(len(a), dtype=np.float32)
    cur = 0.0
    ca = 1 - math.exp(-0.02 / attack)
    cr = 1 - math.exp(-0.02 / release)
    for i, v in enumerate(a):
        cur += (v - cur) * (ca if v > cur else cr)
        g[i] = cur
    gain_db = floor_db * g
    out = np.repeat(10 ** (gain_db / 20), k)
    if len(out) < n:
        out = np.concatenate([out, np.full(n - len(out), out[-1] if len(out) else 1.0)])
    return out[:n].astype(np.float32)
