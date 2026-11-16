"""Grafik teks: tajuk pembukaan, nama pemudahcara, ucapan penutup (PNG RGBA 1920x1080)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SERIF_B = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SERIF_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
CREAM = (246, 234, 212)
GOLD = (214, 178, 112)
W, H = 1920, 1080


def spaced(draw, xy, text, font, fill, spacing=0, anchor="l"):
    x, y = xy
    widths = [draw.textlength(c, font=font) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    if anchor == "m":
        x -= total / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=font, fill=fill)
        x += w + spacing
    return total


def gradient_bottom(strength=170, height=520):
    g = np.zeros((H, W, 4), dtype=np.uint8)
    ramp = (np.linspace(0, 1, height) ** 1.6 * strength).astype(np.uint8)
    g[H - height:, :, 3] = ramp[:, None]
    g[..., :3] = (18, 12, 8)
    return Image.fromarray(g, "RGBA")


def with_shadow(layer, blur=6, offset=(0, 3), alpha=140):
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    a = layer.split()[3].point(lambda v: min(255, int(v * alpha / 255)))
    sh.putalpha(a)
    sh_img = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    black = Image.new("RGBA", layer.size, (0, 0, 0, 255))
    sh_img.paste(black, offset, a)
    sh_img = sh_img.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(sh_img, layer)


def title_card(path):
    base = gradient_bottom(190, 620)
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    f1 = ImageFont.truetype(SERIF, 92)
    f2 = ImageFont.truetype(SERIF_I, 38)
    t1 = "MAJLIS PERTUNANGAN"
    w1 = spaced(d, (W / 2, 770), t1, f1, CREAM, spacing=14, anchor="m")
    d.line([(W / 2 - 150, 888), (W / 2 + 150, 888)], fill=GOLD + (255,), width=2)
    t2 = "Adat yang diwarisi turun-temurun"
    spaced(d, (W / 2, 910), t2, f2, GOLD, spacing=3, anchor="m")
    out = Image.alpha_composite(base, with_shadow(txt))
    out.save(path)


def lower_third(path, name, role):
    base = gradient_bottom(150, 360)
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    f1 = ImageFont.truetype(SERIF_B, 52)
    f2 = ImageFont.truetype(SERIF, 30)
    x = 120
    d.rectangle([x, 880, x + 5, 880 + 100], fill=GOLD + (255,))
    d.text((x + 28, 876), name, font=f1, fill=CREAM)
    spaced(d, (x + 30, 940), role.upper(), f2, GOLD, spacing=5)
    out = Image.alpha_composite(base, with_shadow(txt, blur=5))
    out.save(path)


def end_card(path, text):
    base = gradient_bottom(160, 420)
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    f = ImageFont.truetype(SERIF_I, 64)
    spaced(d, (W / 2, 880), text, f, CREAM, spacing=4, anchor="m")
    out = Image.alpha_composite(base, with_shadow(txt))
    out.save(path)
