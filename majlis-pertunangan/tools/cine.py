"""Penggredan warna sinematik sederhana, dikira per klip daripada statistik sebenar."""
import json, math, os

S = "/tmp/claude-0/-home-user-Claude-idzuan/40cc26e7-f05a-5110-a3e3-f8b3e013b2fd/scratchpad"
STATS = json.load(open(S + "/stats.json"))
TARGET_Y = 124.0   # purata luma sasaran (agak hangat dan intim, tidak gelap)


def clamp(x, a, b):
    return max(a, min(b, x))


def grade_filter(name, extra_warm=0.015):
    st = STATS.get(name)
    if not st:
        return "null"
    y = st["YAVG"]
    # gamma per klip supaya pendedahan seragam (had +-0.18)
    g = math.log(TARGET_Y / 255.0) / math.log(max(y, 40) / 255.0)
    g = clamp(g, 0.84, 1.18)
    # imbangan putih ringan daripada purata U/V (U 123, V 133 dianggap neutral)
    v_off = st["VAVG"] - 133.5
    u_off = st["UAVG"] - 123.5
    rm = clamp(-0.0045 * v_off, -0.05, 0.05) + extra_warm
    bm = clamp(-0.0045 * u_off, -0.05, 0.05) - extra_warm
    # reduce highlight pada klip terang (pakaian putih tidak terlalu terang)
    hi = 0.93 if st.get("YHIGH", 190) < 200 else 0.90
    curves = f"curves=all='0/0.025 0.20/0.19 0.55/0.54 0.82/0.80 1/{hi}'"
    return (f"eq=gamma={g:.3f}:saturation=1.0,"
            f"colorbalance=rm={rm:.3f}:bm={bm:.3f}:rh={extra_warm/2:.3f}:bh={-extra_warm/2:.3f},"
            f"{curves}")
