#!/usr/bin/env python3
"""VGC-FT01 preview builder: portrait footage -> 16:9 explainer, code only (Python + ffmpeg + Pillow).

Timeline (source timecodes refer to source/footage_original.mov):
  HOOK   VO intro over treatment b-roll + TikTok clip (original audio muted)
  SPEAK  speaker, ORIGINAL audio kept, numbered point labels  (src 29.5-78.0, 138.7-148.0)
  OUTRO  VO outro over walk-away b-roll, then CTA/logo card
Run:  python3 -I scripts/build_preview.py            (writes out/preview_v01.mp4, never overwrites)
"""
import os, re, subprocess, sys, json
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/source/footage_original.mov"
VO_IN, VO_OUT = f"{ROOT}/source/vo_intro_v01.mp3", f"{ROOT}/source/vo_outro_v01.mp3"
B = f"{ROOT}/build"
os.makedirs(B, exist_ok=True)
W, H, FPS = 1920, 1080, 30
FB = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FX = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
BLUE, YEL, NAVY, WHITE = (29, 63, 201), (242, 210, 27), (9, 16, 48), (255, 255, 255)


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)[:400]); print(r.stderr[-1500:]); sys.exit(1)
    return r


def dur(path):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout)


def fr(sec):  # snap to whole frames
    return round(sec * FPS) / FPS


# ---------------------------------------------------------------- timeline
VO1, VO2 = fr(dur(VO_IN)), fr(dur(VO_OUT))
A0, A1, D0, D1 = 29.5, 78.0, 138.7, 148.0            # speaker segments (source time)
# (src_start, duration, punch, label)   punch 1.0 = full frame, >1 = direct punch-in
LABELS = {
    1: "MULA RASA SAKIT", 2: "CUBA URUT, MAKIN TERUK", 3: "MRI & CADANGAN OPERASI", 4: "LAST IKHTIAR",
    5: "JUMPA TERAPI TOK WAN", 6: "3 MINGGU TAK BOLEH BERJALAN", 7: "NAIK KERUSI RODA",
    8: "SELEPAS RAWATAN PERTAMA, BOLEH DRIVE", 9: "PERASAAN TAKUT", 10: "TERIMA KASIH TERAPI TOK WAN"}
shots = []   # dicts: ss, d, P, label, part
def add(ss, d, P, label=None, part="", k=1.0):   # k > 1 = very slight slow-down to fit the VO length
    shots.append(dict(ss=ss, d=fr(d), P=P, label=label, part=part, k=k))
# HOOK
# hook: only scenes WITHOUT the speaker (no lip-sync clash) and without burned-in captions, then the TikTok clip
add(97.6, 2.75, 1.0, part="hook"); add(102.45, 3.3, 1.12, part="hook"); add(110.35, 1.8, 1.0, part="hook")
add(7.35, VO1 - fr(2.75) - fr(3.3) - fr(1.8), 1.0, part="hook", k=1.02)
# SPEAK  (label shot boundaries follow the burned-in captions that I read)
cuts = [(29.5, 36.0, 1.0, None), (36.0, 40.0, 1.12, 1), (40.0, 48.0, 1.0, 2), (48.0, 54.0, 1.12, 3),
        (54.0, 60.5, 1.0, 4), (60.5, 64.0, 1.12, 5), (64.0, 69.5, 1.0, 6), (69.5, 72.9, 1.12, 7),
        (72.9, 78.0, 1.0, 8), (138.7, 142.0, 1.0, 9), (142.0, 148.0, 1.12, 10)]
for ss, e, P, lb in cuts:
    add(ss, e - ss, P, lb, "speak")
# OUTRO visuals (VO plays; original audio muted)
# outro visuals: only the door-exit scene (speaker not talking), then branded keyword card (no lip-sync clash with VO)
add(155.5, 3.7, 1.0, part="outro")
t = 0.0
for s in shots:
    s["t0"] = t; t += s["d"]
HOOK_END = sum(s["d"] for s in shots if s["part"] == "hook")
SPEAK_END = HOOK_END + sum(s["d"] for s in shots if s["part"] == "speak")
OUTRO_T0 = SPEAK_END
CARD_T0 = t; CARD_D = fr(17.7) - fr(3.7); CTA_T0 = CARD_T0 + CARD_D
CTA_MAIN = fr(VO2 + OUTRO_T0 - CTA_T0); END_D = fr(5.0); CTA_D = CTA_MAIN + END_D   # CTA card + 5 s logo end card
TOTAL = CTA_T0 + CTA_D
print(f"VO intro {VO1:.2f}s | speaker {SPEAK_END-HOOK_END:.2f}s | VO outro {VO2:.2f}s | total {TOTAL:.2f}s")


# ---------------------------------------------------------------- image assets (Pillow)
def font(p, s): return ImageFont.truetype(p, s)

def wrap(draw, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=f) <= maxw: cur = trial
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

def label_png(n, text, path):
    f = font(FX, 46); d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = wrap(d0, text, f, 400); lh = 58
    w, h = 580, max(120, 40 + lh * len(lines))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 22, fill=(*NAVY, 225))
    d.rounded_rectangle([0, 0, 12, h - 1], 6, fill=YEL)
    cy = h // 2
    d.ellipse([34, cy - 38, 110, cy + 38], fill=YEL)
    nf = font(FX, 44); d.text((72, cy), str(n), font=nf, fill=NAVY, anchor="mm")
    y = (h - lh * len(lines)) // 2 + lh // 2 - 2
    for ln in lines:
        d.text((132, y), ln, font=f, fill=WHITE, anchor="lm"); y += lh
    im.save(path); return im.size

def subtitle_png(text, path, size=50, maxw=1500):
    f = font(FB, size); d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    if "\n" in text: lines = text.split("\n")
    else: lines = wrap(d0, text, f, maxw)
    lh = int(size * 1.3); tw = int(max(d0.textlength(l, font=f) for l in lines))
    w, h = tw + 80, lh * len(lines) + 36
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 20, fill=(0, 0, 0, 165))
    y = 18 + lh // 2
    for l in lines:
        d.text((w // 2, y), l, font=f, fill=WHITE, anchor="mm"); y += lh
    im.save(path); return im.size

def logo_asset():
    p = f"{B}/logo_frame.png"
    sh(["ffmpeg", "-v", "error", "-y", "-ss", "162.0", "-i", SRC, "-frames:v", "1", p])
    im = Image.open(p).convert("RGB"); w, h = im.size
    rows = [y for y in range(h) if sum(im.getpixel((x, y))[2] for x in range(0, w, 8)) / (w // 8) > 60]
    box = im.crop((0, rows[0], w, rows[-1] + 1)); box.save(f"{B}/logo.png"); return box

def cta_background(path, logo, centered=False, small=False):
    bg = Image.new("RGB", (W, H), NAVY); px = bg.load()
    for y in range(H):
        for x in range(0, W, 4):
            k = 1 - abs(x - W / 2) / (W / 2) * 0.55 - y / H * 0.35
            c = (int(NAVY[0] + (BLUE[0] - NAVY[0]) * k * 0.55), int(NAVY[1] + (BLUE[1] - NAVY[1]) * k * 0.55),
                 int(NAVY[2] + (BLUE[2] - NAVY[2]) * k * 0.55))
            for dx in range(4): px[x + dx, y] = c
    lw = 560 if small else (900 if centered else 700); lh = int(logo.size[1] * lw / logo.size[0])
    bg.paste(logo.resize((lw, lh), Image.LANCZOS), ((W - lw) // 2, (H - lh) // 2 if centered else (90 if small else 70)))
    bg.save(path)

def phone_png(path):
    im = Image.new("RGBA", (1500, 380), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 1499, 379], 34, fill=(*NAVY, 215), outline=YEL, width=5)
    d.text((750, 70), "HUBUNGI UNTUK PERTANYAAN SERVIS", font=font(FB, 40), fill=WHITE, anchor="mm")
    d.text((750, 205), "010-939 1557", font=font(FX, 150), fill=YEL, anchor="mm")
    d.text((750, 322), "Terapi Tok Wan  •  Cawangan Bentong", font=font(FB, 42), fill=WHITE, anchor="mm")
    im.save(path)

def keyword_png(text, path, size, width):
    f = font(FX, size); lines = text.split("\n"); lh = int(size * 1.2); h = lh * len(lines) + 50
    im = Image.new("RGBA", (width, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); y = 25 + lh // 2
    for l in lines:
        d.text((width // 2, y), l, font=f, fill=WHITE, anchor="mm"); y += lh
    d.rounded_rectangle([width // 2 - 120, h - 14, width // 2 + 120, h - 6], 4, fill=YEL)
    im.save(path); return im.size

def place_png(path):
    im = Image.new("RGBA", (1200, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 1199, 119], 24, fill=(*YEL, 255))
    d.text((600, 60), "Kawasan Industri Bentong", font=font(FX, 62), fill=NAVY, anchor="mm")
    im.save(path)


# ---------------------------------------------------------------- overlays table: (png, x, y, t_in, t_out)
overlays = []
def ov(png, x, y, a, b): overlays.append((png, x, y, a, b))

for s in shots:
    if s["label"]:
        p = f"{B}/label_{s['label']:02d}.png"; lw, lh = label_png(s["label"], LABELS[s["label"]], p)
        ov(p, 100, (H - lh) // 2 - 40, s["t0"] + 0.25, s["t0"] + s["d"] - 0.25)

VO_SUBS_IN = [(0.17, 3.95, "Pernah tak… nak bangun pun susah,\nnak berjalan pun kena tahan sakit?"),
              (4.56, 8.01, "Bila tengok orang lain boleh bergerak macam biasa,\nkita cuma berharap…"),
              (8.44, 10.34, "dapat berjalan dengan selesa pun dah cukup."),
              (10.96, 15.93, "Video ini merakamkan pengalaman seorang pelanggan\nyang pernah melalui keadaan itu."),
              (16.33, 19.93, "Dalam perkongsiannya, hampir dua minggu\ndia susah nak bangun dan berjalan."),
              (20.26, 21.64, "Sampai terpaksa merangkak.")]
VO_SUBS_OUT = [(0.17, 1.60, "Pengalaman setiap orang berbeza."),
               (1.96, 8.08, "Perkongsian ini ialah kisah peribadinya, dan kesesuaian\nrawatan perlu dinilai mengikut keadaan masing-masing."),
               (8.64, 14.25, "Buat anda yang sedang menghadapi sakit pinggang\nsehingga mengganggu aktiviti harian,"),
               (14.43, 17.67, "dapatkan pemeriksaan supaya langkah seterusnya\nsesuai dengan keadaan anda."),
               (29.69, 32.31, "Kadang-kadang, perkara yang paling kita rindukan…"),
               (32.63, 34.74, "hanyalah dapat bergerak dengan selesa semula.")]
for off, subs, tag in ((0.0, VO_SUBS_IN, "in"), (OUTRO_T0, VO_SUBS_OUT, "out")):
    for i, (a, b, txt) in enumerate(subs):
        p = f"{B}/sub_{tag}_{i}.png"; sw, sh_ = subtitle_png(txt, p)
        ov(p, (W - sw) // 2, 960 - sh_, off + a, off + b)

logo = logo_asset(); cta_background(f"{B}/cta_bg.png", logo); cta_background(f"{B}/end_bg.png", logo, centered=True); cta_background(f"{B}/card_bg.png", logo, small=True)
phone_png(f"{B}/phone.png"); place_png(f"{B}/place.png")
ov(f"{B}/phone.png", (W - 1500) // 2, 450, OUTRO_T0 + 18.52, OUTRO_T0 + 29.6)
ov(f"{B}/place.png", (W - 1200) // 2, 860, OUTRO_T0 + 27.41, OUTRO_T0 + 29.6)
KW = [(4.0, 8.0, "KESESUAIAN RAWATAN\nBERBEZA\nMENGIKUT KEADAAN"), (8.64, 14.25, "SAKIT PINGGANG\nMENGGANGGU\nAKTIVITI HARIAN?"), (14.43, 17.6, "DAPATKAN\nPEMERIKSAAN")]
for i, (a, b, txt) in enumerate(KW):
    p = f"{B}/kw_{i}.png"; kw_, kh_ = keyword_png(txt, p, 84, 1500)
    ov(p, (W - kw_) // 2, 430, OUTRO_T0 + a, OUTRO_T0 + b)


# ---------------------------------------------------------------- pass A: base shots
def shot_path(s):
    return f"{B}/shot_{int(round(s['ss']*1000))}_{int(round(s['d']*1000))}_{int(round(s['P']*100))}_{int(round(s.get('k',1.0)*1000))}.mp4"

def render_shot(i, s):
    P, ss, d, k = s["P"], s["ss"], s["d"], s.get("k", 1.0)
    fw, fh = int(540 * P) // 2 * 2, int(1080 * P) // 2 * 2
    cx, cy = (fw - 540) // 2, int((fh - 1080) * 0.2)
    fc = (f"[0:v]setpts=PTS*{k},fps={FPS},setsar=1,split=2[a][b];"
          f"[a]scale=640:-2,crop=640:360,boxblur=6:2,eq=brightness=-0.18:saturation=0.85,scale={W}:{H}:flags=bilinear[bg];"
          f"[b]scale={fw}:{fh}:flags=lanczos,crop=540:1080:{cx}:{cy}[fg];[bg][fg]overlay=690:0,format=yuv420p[v]")
    out = shot_path(s) + ".part.mp4"
    sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{ss}", "-t", f"{d / k:.4f}", "-i", SRC, "-filter_complex", fc, "-map", "[v]",
        "-an", "-r", str(FPS), "-frames:v", str(round(d * FPS)), "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", out])
    os.replace(out, shot_path(s))
    return shot_path(s)

parts = []
for i, s_ in enumerate(shots):
    pth = shot_path(s_)
    parts.append(pth if (os.environ.get("REUSE_SHOTS") and os.path.exists(pth)) else render_shot(i, s_))
for png, d_, name in ((f"{B}/card_bg.png", CARD_D, "card_base"), (f"{B}/cta_bg.png", CTA_MAIN, "cta_base"), (f"{B}/end_bg.png", END_D, "end_base")):
    sh(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-t", f"{d_}", "-i", png,
        "-vf", "format=yuv420p", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", f"{B}/{name}.mp4"])
    parts.append(f"{B}/{name}.mp4")
open(f"{B}/concat.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
base = f"{B}/video_base.mp4"
sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{B}/concat.txt", "-c", "copy", base])


# ---------------------------------------------------------------- pass C: overlays + dips
inputs, chains = ["-i", base], []
blk = [("open", f"fade=t=out:st=0:d=0.3:alpha=1"),
       ("dip1", f"fade=t=in:st={HOOK_END-0.12:.3f}:d=0.12:alpha=1,fade=t=out:st={HOOK_END:.3f}:d=0.12:alpha=1"),
       ("dipo", f"fade=t=in:st={OUTRO_T0-0.12:.3f}:d=0.12:alpha=1,fade=t=out:st={OUTRO_T0:.3f}:d=0.12:alpha=1"),
       ("dipc", f"fade=t=in:st={CARD_T0-0.12:.3f}:d=0.12:alpha=1,fade=t=out:st={CARD_T0:.3f}:d=0.12:alpha=1"),
       ("dip2", f"fade=t=in:st={CTA_T0-0.12:.3f}:d=0.12:alpha=1,fade=t=out:st={CTA_T0:.3f}:d=0.12:alpha=1"),
       ("dip3", f"fade=t=in:st={CTA_T0+CTA_MAIN-0.12:.3f}:d=0.12:alpha=1,fade=t=out:st={CTA_T0+CTA_MAIN:.3f}:d=0.12:alpha=1"),
       ("close", f"fade=t=in:st={TOTAL-0.8:.3f}:d=0.8:alpha=1")]
last = "[0:v]"
for j, (nm, fx) in enumerate(blk, start=1):
    inputs += ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}:d={TOTAL:.3f}"]
    chains.append(f"[{j}:v]format=rgba,{fx}[b{j}]")
    chains.append(f"{last}[b{j}]overlay=format=auto[bb{j}]"); last = f"[bb{j}]"
NB = len(blk)
for k, (png, x, y, a, b) in enumerate(overlays, start=NB + 1):
    inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{TOTAL:.3f}", "-i", png]
    chains.append(f"[{k}:v]format=rgba,fade=t=in:st={a:.3f}:d=0.25:alpha=1,fade=t=out:st={b-0.25:.3f}:d=0.25:alpha=1[o{k}]")
    nxt = f"[m{k}]"
    chains.append(f"{last}[o{k}]overlay=x={x}:y={y}:enable='between(t,{a:.3f},{b:.3f})'{nxt}")
    last = nxt
chains.append(f"{last}format=yuv420p[vout]")
video_ov = f"{B}/video_overlays.mp4"
sh(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(chains), "-map", "[vout]", "-t", f"{TOTAL:.3f}",
    "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", video_ov])


# ---------------------------------------------------------------- audio (measure -> gain -> limit)
def lufs(args, dual=False):
    pre_af = "pan=stereo|c0=c0|c1=c0,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=90," if dual else ""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args, "-af", pre_af + "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])

TARGET = -16.0
pieces = [("vo", VO_IN, None, None, VO1), ("spk", SRC, A0, A1 - A0, A1 - A0), ("spk", SRC, D0, D1 - D0, D1 - D0),
          ("vo", VO_OUT, None, None, VO2)]
a_in, a_chain = [], []
for i, (kind, path, ss, d, plen) in enumerate(pieces):
    pre = (["-ss", f"{ss}", "-t", f"{d}"] if ss is not None else [])
    loud = lufs([*pre, "-i", path], dual=(kind == "vo")); gain = TARGET - loud
    print(f"audio piece {i} ({kind}): measured {loud:.1f} LUFS -> gain {gain:+.1f} dB")
    a_in += [*pre, "-i", path]
    fade = 0.12
    a_chain.append(f"[{i}:a]pan=stereo|c0=c0|c1=c{'0' if kind=='vo' else '1'},aresample=44100,{'acompressor=threshold=-20dB:ratio=2.5:attack=5:release=90,' if kind=='vo' else ''}volume={gain:.2f}dB,"
                   f"alimiter=limit=0.84:level=disabled,afade=t=in:st=0:d={fade},afade=t=out:st={plen-fade:.3f}:d={fade},"
                   f"apad=whole_dur={fr(plen):.4f},atrim=0:{fr(plen):.4f}[a{i}]")
a_chain.append("".join(f"[a{i}]" for i in range(len(pieces))) + f"concat=n={len(pieces)}:v=0:a=1,apad=whole_dur={TOTAL:.3f},atrim=0:{TOTAL:.3f}[aout]")
audio = f"{B}/audio_mix.m4a"
sh(["ffmpeg", "-y", "-v", "error", *a_in, "-filter_complex", ";".join(a_chain), "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", audio])


# ---------------------------------------------------------------- mux, versioned output
os.makedirs(f"{ROOT}/out", exist_ok=True)
n = 1
while os.path.exists(f"{ROOT}/out/preview_v{n:02d}.mp4"): n += 1
out = f"{ROOT}/out/preview_v{n:02d}.mp4"
sh(["ffmpeg", "-y", "-v", "error", "-i", video_ov, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy",
    "-movflags", "+faststart", "-shortest", out])
json.dump(dict(shots=shots, overlays=overlays, total=TOTAL, outro_t0=OUTRO_T0, cta_t0=CTA_T0, hook_end=HOOK_END),
          open(f"{B}/timeline.json", "w"), indent=1)
print("WROTE", out)
