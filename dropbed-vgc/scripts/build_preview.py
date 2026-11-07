#!/usr/bin/env python3
"""VGC-FT01 Drop Bed - preview builder (Python + numpy + Pillow + ffmpeg, no paid services).

Style: Glass Interface (translucent panels, one focus at a time, calm synth bed).
Footage is kept WHOLE (no cuts, original voice untouched, no speed change). Source is 375.28s;
a 4.72s CTA end card (frozen last frame) brings the output to 380s.

Run from the project folder:   python3 -I scripts/build_preview.py
Writes out/preview_vNN.mp4 (next free number, never overwrites).
"""
import os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/source/footage_original.mov"
B = f"{ROOT}/build/p"; os.makedirs(B, exist_ok=True); os.makedirs(f"{ROOT}/out", exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100
SRC_DUR, TOTAL = 375.28, 380.0
FB, FX = "/usr/share/fonts/opentype/inter/Inter-Bold.otf", "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
BG, TXT, ACC = (16, 41, 69), (242, 251, 255), (140, 223, 255)       # brief palette (temporary theme)
PHONE_DISPLAY, PHONE_SPOKEN = "013-508 8792", "0135088792"

# (start, end, small label, main text)  - source time == output time (no cuts)
PANELS = [
    (0.4, 4.6, "DROP BED", "Laras tulang belakang & kaki"),
    (10.0, 15.0, "POSTUR", "Betulkan postur tulang belakang"),
    (15.0, 23.0, "KETINGGIAN KATIL", "Laras tinggi, pinggang terapi tak lenguh"),
    (39.0, 50.0, "BANTAL KEPALA", "Senang bernafas, ada ruang tisu"),
    (58.5, 72.0, "5 LARAS", "Setting ikut kawasan, sampai lutut & buku lali"),
    (79.5, 85.0, "KEPALA", "Bahagian kepala pun boleh dilaras"),
    (86.0, 99.0, "PELARASAN DROP", "Tekan, bahagian naik. Kuasa boleh ditambah"),
    (118.0, 124.5, "TANPA FORCE", "Pembetulan tulang berlaku dengan baik"),
    (173.0, 183.0, "L1 - L5 - SACRUM", "Laras ikut segmen tulang belakang"),
    (203.5, 213.5, "PELVIS - LUTUT", "Laras bahagian pelvis & lutut"),
    (221.5, 228.5, "KAKI", "Boleh dipanjangkan untuk pelanggan tinggi"),
    (240.5, 250.5, "JIMAT TENAGA", "Tak perlu guna tenaga yang banyak"),
    (254.5, 265.0, "KEPALA & LEHER", "Laras sudut ikut keperluan"),
    (320.0, 331.0, "KEPALA SAMPAI KAKI", "Hanya guna Drop Bed"),
    (342.0, 353.0, "TMJ - C1 hingga C4", "Rahang & leher atas"),
    (366.5, 375.2, "NAK TAHU LEBIH DETAIL?", f"Hubungi {PHONE_DISPLAY}"),
]
END_CARD = (SRC_DUR, TOTAL)


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)[:300]); print(r.stderr[-2000:]); sys.exit(1)
    return r


def fit(draw, text, path, size, maxw):
    while size > 30:
        f = ImageFont.truetype(path, size)
        if draw.textlength(text, font=f) <= maxw:
            return f
        size -= 2
    return ImageFont.truetype(path, size)


def wrap(draw, text, path, size, maxw):
    words, lines, cur = text.split(), [], ""
    f = ImageFont.truetype(path, size)
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    return f, lines


def panel_png(i, small, main, big=False):
    pw, ph = (980, 420) if big else (960, 0)
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    msize = 64 if big else 54
    f_main, lines = wrap(d0, main, FX, msize, pw - 110)
    f_small = fit(d0, small, FB, 34 if not big else 40, pw - 110)
    lh = int(msize * 1.18)
    if not big:
        ph = 50 + 44 + 14 + lh * len(lines) + 46
    sc = 2                                                   # supersample for crisp edges
    im = Image.new("RGBA", (pw * sc, ph * sc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw * sc - 1, ph * sc - 1], radius=40 * sc, fill=BG + (225,),
                        outline=ACC + (120,), width=2 * sc)
    sheen = Image.new("RGBA", im.size, (0, 0, 0, 0))                    # composite, do not overwrite
    ImageDraw.Draw(sheen).rounded_rectangle([2 * sc, 2 * sc, pw * sc - 3 * sc, ph * sc // 2], radius=38 * sc,
                                            fill=(255, 255, 255, 16))
    im = Image.alpha_composite(im, sheen); d = ImageDraw.Draw(im)
    d.rounded_rectangle([46 * sc, 46 * sc, 54 * sc, (ph - 46) * sc], radius=4 * sc, fill=ACC + (255,))
    fs = ImageFont.truetype(FB if True else FB, f_small.size * sc)
    fm = ImageFont.truetype(FX, f_main.size * sc)
    y = 44
    d.text((82 * sc, y * sc), small, font=fs, fill=ACC + (255,))
    y += f_small.size + 18
    for ln in lines:
        d.text((82 * sc, y * sc), ln, font=fm, fill=TXT + (255,))
        y += lh
    im = im.resize((pw, ph), Image.LANCZOS)
    p = f"{B}/panel_{i:02d}.png"; im.save(p)
    return p, pw, ph


# ------------------------------------------------------------------ audio (procedural)
def note(f): return 440.0 * 2 ** ((f - 69) / 12)

def make_audio(path):
    n = int(TOTAL * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(7)
    # chord pad: Am9 - Fmaj7 - Cmaj7 - G6, 12s each, slow crossfade
    chords = [[57, 60, 64, 71], [53, 57, 60, 64], [48, 55, 59, 64], [55, 59, 62, 64]]
    pad = np.zeros(n)
    seg = 12.0
    for k in range(int(TOTAL / seg) + 2):
        ch = chords[k % 4]; s0 = k * seg - 2.0
        env = np.clip((t - s0) / 3.0, 0, 1) * np.clip((s0 + seg + 3.0 - t) / 3.0, 0, 1)
        for m in ch:
            for det in (-0.07, 0.07):
                fr = note(m) * 2 ** (det / 12)
                pad += env * (np.sin(2 * np.pi * fr * t) + 0.25 * np.sin(2 * np.pi * 2 * fr * t)) * 0.05
    pad *= 0.6 + 0.4 * np.sin(2 * np.pi * t / 24.0 - 1.0) ** 2        # slow breathing
    # soft pluck arpeggio (90 BPM eighths), thinner in the body, fuller at the ends
    arp = np.zeros(n); step = 60 / 90 / 2
    for k in range(int(TOTAL / step)):
        tt = k * step
        if 14 < tt < 360 and k % 2: continue
        ch = chords[int(tt // seg) % 4]; m = ch[k % 4] + 12
        i0 = int(tt * SR); L = int(0.5 * SR); x = np.arange(min(L, n - i0)) / SR
        arp[i0:i0 + len(x)] += np.sin(2 * np.pi * note(m) * x) * np.exp(-x * 7) * 0.05
    # air: low-passed noise, rises into the end card
    noise = rng.standard_normal(n); air = np.convolve(noise, np.ones(40) / 40, mode="same") * 0.02
    air *= 0.5 + 0.5 * np.clip((t - 366) / 9, 0, 1)
    music = pad + arp + air
    music *= np.clip(t / 2.0, 0, 1) * np.clip((TOTAL - t) / 3.0, 0, 1)
    # SFX on the same cues as the visuals: soft tap + airy pop at each panel, riser into end card
    sfx = np.zeros(n)
    for (a, b, *_ ) in PANELS:
        i0 = int(a * SR); x = np.arange(int(0.25 * SR)) / SR
        pop = np.sin(2 * np.pi * (700 + 500 * np.exp(-x * 30)) * x) * np.exp(-x * 24) * 0.5
        sw = np.convolve(rng.standard_normal(len(x)), np.ones(12) / 12, mode="same") * np.exp(-x * 14) * 0.25
        sfx[i0:i0 + len(x)] += pop + sw
    i0 = int((SRC_DUR - 2.0) * SR); x = np.arange(int(2.6 * SR)) / SR
    sfx[i0:i0 + len(x)] += np.sin(2 * np.pi * (300 + 700 * (x / 2.6) ** 2) * x) * (x / 2.6) ** 2 * 0.18
    st = lambda m: np.stack([m, m], 1)
    music_i, sfx_i = (st(music) * 32767).astype(np.int16), (st(sfx) * 32767).astype(np.int16)
    for name, arr in (("music", music_i), ("sfx", sfx_i)):
        with wave.open(f"{B}/{name}.wav", "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(arr.tobytes())


def main():
    n = 1
    while os.path.exists(f"{ROOT}/out/preview_v{n:02d}.mp4"): n += 1
    out = f"{ROOT}/out/preview_v{n:02d}.mp4"

    make_audio(None)
    items = [(a, b, *panel_png(i, s, m)) for i, (a, b, s, m) in enumerate(PANELS)]
    ec = panel_png(99, "NAK DAPATKAN DROP BED?", f"Hubungi {PHONE_DISPLAY}", big=True)
    items.append((END_CARD[0] + 0.15, END_CARD[1], *ec))

    inputs = ["-i", SRC, "-i", f"{B}/music.wav", "-i", f"{B}/sfx.wav"]
    fc = [f"[0:v]scale={W}:{H}:flags=lanczos,unsharp=5:5:0.6,tpad=stop_mode=clone:stop_duration={TOTAL - SRC_DUR:.2f},fps={FPS}[v0]"]
    fc.append(f"[v0]drawbox=x=0:y=0:w=iw:h=ih:color=0x102945@0.62:t=fill:enable='gte(t,{SRC_DUR})'[v1]")
    last = "v1"
    for k, (a, b, p, pw, ph) in enumerate(items):
        idx = 3 + k; D = b - a
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{D:.2f}", "-i", p]
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st=0:d=0.35:alpha=1,fade=t=out:st={D - 0.3:.2f}:d=0.3:alpha=1,setpts=PTS+{a}/TB[p{k}]")
        big = k == len(items) - 1
        x = (W - pw) // 2
        y0 = 760 if big else 170
        fc.append(f"[{last}][p{k}]overlay=x={x}:y='{y0}+pow(1-min(1,max(0,(t-{a})/0.5)),3)*70':"
                  f"enable='between(t,{a},{b})':eof_action=pass[o{k}]")
        last = f"o{k}"
    # audio: dialogue first. music ducked by the dialogue, SFX very low, soft limiter at the end.
    fc.append(f"[0:a]aresample={SR},apad=whole_dur={TOTAL},asplit=2[sp][sc]")
    fc.append("[1:a]volume=1.0[mu]")
    fc.append("[mu][sc]sidechaincompress=threshold=0.015:ratio=10:attack=15:release=500:makeup=1[du]")
    fc.append("[du]volume=0.55[mud]")
    fc.append("[2:a]volume=0.5[sx]")
    fc.append("[sp][mud][sx]amix=inputs=3:duration=first:normalize=0:dropout_transition=0,"
              "alimiter=limit=0.89:level=disabled[a]")
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "[a]",
           "-t", f"{TOTAL}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    sh(cmd)
    print(out)


if __name__ == "__main__":
    main()
