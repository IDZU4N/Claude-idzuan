"""Penyediaan gambar HEIC (profil warna betul) dan pemaparan Ken Burns halus ke 1920x1080."""
import io, os, subprocess, math, sys
import numpy as np
from PIL import Image, ImageOps, ImageCms, ImageFilter
import pillow_heif

pillow_heif.register_heif_opener()
S = "/tmp/claude-0/-home-user-Claude-idzuan/40cc26e7-f05a-5110-a3e3-f8b3e013b2fd/scratchpad"
W, H = 1920, 1080
FPS = 30000 / 1001
SRGB = ImageCms.createProfile("sRGB")


def load_photo(name, maxside=3400):
    p = f"{S}/src/{name}.HEIC"
    im = Image.open(p)
    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            im = ImageCms.profileToProfile(im, src, SRGB, outputMode="RGB")
        except Exception as e:
            print("icc gagal", name, e, file=sys.stderr)
    im.thumbnail((maxside, maxside), Image.LANCZOS)
    return grade_photo(im)


def grade_photo(im, target=124.0):
    a = np.asarray(im.resize((256, int(256 * im.height / im.width))), dtype=np.float32)
    y = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]).mean()
    g = math.log(target / 255) / math.log(max(y, 40) / 255)
    g = min(1.12, max(0.86, g))
    x = np.arange(256) / 255.0
    curve = np.interp(x, [0, 0.2, 0.55, 0.82, 1.0], [0.025, 0.19, 0.54, 0.80, 0.93])
    lut = (np.power(curve, 1.0 / (1.0 / g)) if False else np.power(x, g))  # gamma
    lut = np.interp(lut, [0, 0.2, 0.55, 0.82, 1.0], [0.025, 0.19, 0.54, 0.80, 0.93])
    lut8 = np.clip(lut * 255, 0, 255).astype(np.uint8)
    r = lut8
    # kehangatan halus: sedikit naik merah, turun biru
    rl = np.clip(lut * 255 * 1.010, 0, 255).astype(np.uint8)
    bl = np.clip(lut * 255 * 0.985, 0, 255).astype(np.uint8)
    rch, gch, bch = im.split()
    return Image.merge("RGB", (rch.point(rl), gch.point(r), bch.point(bl)))


def smooth(t):
    return t * t * (3 - 2 * t)


def kb_frames(im, dur, mode="auto", z0=1.0, z1=1.08, c0=(0.5, 0.5), c1=(0.5, 0.5), bgblur=True):
    """Hasilkan bingkai RGB (W,H). 'fit' = latar kabur + gambar penuh (menegak); 'fill' = isi 16:9."""
    n = int(round(dur * FPS))
    iw, ih = im.size
    portrait = ih > iw * 0.95
    if mode == "auto":
        mode = "fit" if portrait else "fill"
    if mode == "fit":
        bg = im.copy()
        sc = max(W / iw, H / ih)
        bg = bg.resize((int(iw * sc) + 1, int(ih * sc) + 1), Image.BILINEAR)
        l, t = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(38))
        bg = Image.eval(bg, lambda v: int(v * 0.62))
        fh = int(H * 0.94)
        fw = int(fh * iw / ih)
        fgbase = im
    for i in range(n):
        u = smooth(i / max(1, n - 1))
        z = z0 + (z1 - z0) * u
        cx = c0[0] + (c1[0] - c0[0]) * u
        cy = c0[1] + (c1[1] - c0[1]) * u
        if mode == "fill":
            # kotak 16:9 dalam gambar, zum z (lebih besar = lebih dekat)
            bw = iw / z
            bh = bw * H / W
            if bh > ih:
                bh = ih / z
                bw = bh * W / H
            x0 = (iw - bw) * cx
            y0 = (ih - bh) * cy
            frame = im.transform((W, H), Image.EXTENT, (x0, y0, x0 + bw, y0 + bh), Image.BICUBIC)
        else:
            zz = z
            bw = iw / zz
            bh = ih / zz
            x0 = (iw - bw) * cx
            y0 = (ih - bh) * cy
            fgw = int(fw)
            fgh = int(fh)
            fg = im.transform((fgw, fgh), Image.EXTENT, (x0, y0, x0 + bw, y0 + bh), Image.BICUBIC)
            frame = bg.copy()
            frame.paste(fg, ((W - fgw) // 2, (H - fgh) // 2))
        yield frame.tobytes()


def render_photo(name, out, dur, **kw):
    im = load_photo(name)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", "30000/1001", "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "14", "-g", "1", "-pix_fmt", "yuv420p", "-vf", "setsar=1", "-r", "30000/1001", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in kb_frames(im, dur, **kw):
        p.stdin.write(fr)
    p.stdin.close()
    p.wait()
    return out
