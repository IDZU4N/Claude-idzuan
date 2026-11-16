"""Hasilkan filem akhir. Penggunaan: make.py audio | video | all"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, soundfile as sf, pyloudnorm as pn
from scipy.signal import butter, sosfiltfilt
import engine
from engine import *
import timeline, titles, music, vrender

OUT = f"{S}/out"
os.makedirs(OUT, exist_ok=True)
stage = sys.argv[1] if len(sys.argv) > 1 else "all"

scenes = timeline.build()
total = layout(scenes)
print("jumlah %.2f s" % total, flush=True)
n = int(math.ceil(total * SR))

# ------------------------------------------------------------------ AUDIO
if stage in ("audio", "all"):
    dlg, amb, _ = build_audio(scenes, total)
    dlg, amb = dlg[:, :n], amb[:, :n]
    mpath = f"{S}/music/bed_{int(total)}.wav"
    if not os.path.exists(mpath):
        m = music.compose(total + 8, drums_on=lambda t: (t < 40) or (t > total - 75), pluck_on=lambda t: True)
        sf.write(mpath, m.T, SR, subtype="PCM_24")
    mus, _sr = sf.read(mpath, dtype="float32", always_2d=True)
    mus = mus.T[:, :n]
    if mus.shape[1] < n:
        mus = np.pad(mus, ((0, 0), (0, n - mus.shape[1])))
    # aras muzik sasaran per pemandangan (dB), kemudian dilicinkan
    tgt = np.full(n, -60.0, dtype=np.float32)
    LEVEL = {"full": -9.0, "duck": -12.0, "off": -60.0}
    for sc in scenes:
        i0 = int(sc.t0 * SR)
        i1 = min(n, int((sc.t0 + sc.alen) * SR))
        tgt[i0:i1] = LEVEL[sc.music]
    k = int(1.6 * SR)
    ker = np.ones(k, dtype=np.float32) / k
    tgt = np.convolve(np.pad(tgt, (k // 2, k // 2), mode="edge"), ker, mode="valid")[:n]
    duck = duck_curve(dlg, n, floor_db=-14.0, attack=0.15, release=1.0)
    musgain = 10 ** (tgt / 20) * duck
    # kesan masuk perlahan awal dan keluar akhir
    fade_in = np.minimum(1, np.arange(n) / (2.0 * SR)) ** 1.5
    fade_out = np.minimum(1, (n - np.arange(n)) / (4.0 * SR)) ** 1.5
    mix = dlg + amb * 0.62 + mus * (musgain * fade_in * fade_out)[None, :]
    # kelantangan bersepadu -16 LUFS (YouTube), had puncak lembut
    meter = pn.Meter(SR)
    lufs = meter.integrated_loudness(mix.T)
    mix *= 10 ** ((-16.0 - lufs) / 20)
    thr = 0.80
    a = np.abs(mix)
    over = a > thr
    mix = np.where(over, np.sign(mix) * (thr + (1 - thr) * np.tanh((a - thr) / (1 - thr))), mix)
    mix[:, -int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    print("LUFS asal %.1f -> %.1f, puncak %.3f" % (lufs, meter.integrated_loudness(mix.T), np.abs(mix).max()), flush=True)
    sf.write(f"{OUT}/audio_mix.wav", mix.T, SR, subtype="PCM_24")
    # simpan bas berasingan untuk suntingan semula
    sf.write(f"{OUT}/stem_dialog.wav", dlg.T, SR, subtype="PCM_24")
    sf.write(f"{OUT}/stem_ambien.wav", amb.T, SR, subtype="PCM_24")
    sf.write(f"{OUT}/stem_muzik.wav", (mus * (musgain * fade_in * fade_out)[None, :]).T, SR, subtype="PCM_24")

# ------------------------------------------------------------------ VIDEO
if stage in ("video", "all"):
    all_shots = [s for sc in scenes for s in sc.shots]
    frames, lines = vrender.build_video(all_shots, f"{OUT}/concat.txt", tag="main")
    print("bingkai", frames, "jangkaan", total * FPS, flush=True)
    titles.title_card(f"{OUT}/t_title.png")
    titles.lower_third(f"{OUT}/t_emcee.png", "Tuan Haji Alfadhilah", "Pemudahcara")
    titles.end_card(f"{OUT}/t_end.png", "Terima kasih")
    emc = [sc for sc in scenes if sc.name == "aluan_1"][0]
    fin = [sc for sc in scenes if sc.name == "penutup"][0]
    overlays = [(f"{OUT}/t_title.png", 2.0, 9.5, 1.2, 1.2),
                (f"{OUT}/t_emcee.png", emc.t0 + 2.5, emc.t0 + 9.0, 0.8, 0.8),
                (f"{OUT}/t_end.png", fin.t0 + 1.5, total - 1.0, 1.0, 1.0)]
    out = f"{OUT}/majlis_pertunangan_1080p.mp4"
    vrender.encode_final(f"{OUT}/concat.txt", f"{OUT}/audio_mix.wav", out, overlays=overlays, total_s=total, crf=18)
    print("siap", out)

json.dump([{"scene": s.name, "t0": round(s.t0, 3), "dur": round(s.alen, 3), "music": s.music,
            "audio": [{"src": g.src, "a": g.a, "b": g.b, "bus": g.bus} for g in s.audio],
            "shots": [{"kind": h.kind, "src": h.src, "ss": round(h.ss, 3), "dur": round(h.dur, 3), "sync": h.sync, "dis": h.dis}
                      for h in s.shots]} for s in scenes],
          open(f"{OUT}/timeline.json", "w"), indent=1, ensure_ascii=False)
