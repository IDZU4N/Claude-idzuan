"""Garis masa suntingan: Majlis Pertunangan Melayu.
Semua masa sumber (saat) diambil daripada transkrip + semakan bingkai sebenar. Tiada adegan direka."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from engine import Scene, Seg, Shot, C, SYNC, P


# ---------- pembantu perancangan bidikan mengikut masa sumber ----------
def focus(z, px, py):
    """Titik minat (px,py) pecahan bingkai -> parameter push (z, cx, cy)."""
    def cl(v):
        return max(0.0, min(1.0, v))
    cx = cl((z * px - 0.5) / (z - 1)) if z > 1 else 0.5
    cy = cl((z * py - 0.5) / (z - 1)) if z > 1 else 0.5
    return (z, cx, cy)


class F:  # kilang bidikan
    def __init__(self, fn, photo=False):
        self.fn, self.photo = fn, photo

    def make(self, dur, dis):
        return self.fn(dur, dis)


def SY(z=None, px=0.5, py=0.4, stab=False):
    def fn(dur, dis):
        kw = {}
        if z:
            kw["push"] = focus(z, px, py)
        return SYNC(_SRC[0], dur, dis=dis, stab=stab, **kw)
    return F(fn)


def CU(src, ss, stab=False):
    return F(lambda dur, dis: C(src, ss, dur, dis=dis, stab=stab))


def PH(name, **kw):
    return F(lambda dur, dis: P(name, dur, dis=dis, **kw), photo=True)


_SRC = [None]


def plan(seg, cuts):
    """cuts: [(t_akhir_masa_sumber, F), ...]. Bidikan terakhir disambung hingga akhir segmen."""
    _SRC[0] = seg.src
    ends, facs = [], []
    for t, f in cuts:
        if t >= seg.b - 0.8:
            ends.append(seg.b)
            facs.append(f)
            break
        if t <= seg.a + 0.8 or (ends and t <= ends[-1] + 0.8):
            continue
        ends.append(t)
        facs.append(f)
    else:
        ends.append(seg.b)
        facs.append(SY())
    b = [seg.a] + ends
    b[-1] = seg.b
    n = len(facs)
    dis = [0.0] * n
    for i in range(1, n):
        if facs[i].photo or facs[i - 1].photo:
            dis[i] = 0.5
    shots = []
    for i in range(n):
        d = (b[i + 1] - b[i]) + (dis[i + 1] if i + 1 < n else 0.0)
        shots.append(facs[i].make(d, dis[i]))
    return shots


def speech(name, src, a, b, cuts=None, d_in=0.45, music="duck", gain=0.0, bus="dlg"):
    seg = Seg(src, a, b, bus=bus, gain=gain)
    shots = plan(seg, cuts or [])
    sc = Scene(name, [seg], shots, d_in=d_in, music=music)
    return sc


def build():
    scenes = []
    A = scenes.append

    # ===== 1. PEMBUKAAN (muzik sahaja): perincian cincin, hantaran, hiasan =====
    A(Scene("pembukaan", [],
            [C("IMG_2113", 0.0, 7.5), C("IMG_2114", 7.2, 7.5, dis=0.8), C("IMG_2107", 0.5, 6.5, dis=0.8),
             C("IMG_2133", 50.4, 6.2, dis=0.8), C("IMG_2111", 0.8, 5.6, dis=0.8)],
            d_in=0, music="full", dur=31.0))

    # ===== 2. KETIBAAN =====
    segs = [Seg("IMG_2126", 0.0, 9.8, bus="amb", snap_edges=False, xf=0.4, gain=-3),
            Seg("IMG_2128", 2.0, 13.5, bus="amb", snap_edges=False, xf=0.4, gain=-3),
            Seg("IMG_2103", 0.0, 19.0, bus="amb", snap_edges=False, xf=0.4, gain=-3),
            Seg("IMG_2104", 1.5, 16.5, bus="amb", snap_edges=False, xf=0.4, gain=-3),
            Seg("IMG_2106", 5.0, 15.5, bus="amb", snap_edges=False, xf=0.4, gain=-3)]
    shots = [SYNC("IMG_2126", segs[0].dur, stab=True),
             SYNC("IMG_2128", segs[1].dur, dis=0.4, stab=True),
             SYNC("IMG_2103", segs[2].dur, dis=0.4, stab=True),
             SYNC("IMG_2104", segs[3].dur, dis=0.4, stab=True),
             SYNC("IMG_2106", segs[4].dur, dis=0.4, stab=True)]
    A(Scene("ketibaan", segs, shots, d_in=1.0, music="full"))

    # ===== 3. SUASANA SEBELUM MAJLIS (muzik) =====
    A(Scene("bersiap", [],
            [P("IMG_2102", 5.5, dis=0.8), C("IMG_2110", 3.6, 6.0, dis=0.8), C("IMG_2125", 29.0, 8.0, dis=0.6)],
            d_in=0.9, music="full", dur=18.5))

    # ===== 4. DOA PEMBUKA (audio asal sahaja) =====
    A(speech("doa_pembuka", "IMG_2130", 4.1, 37.0, [(20.0, SY(1.25, 0.65, 0.35))], d_in=1.0, music="off"))

    # ===== 5. ALU-ALUAN PEMUDAHCARA (landasan suara) =====
    E = (1.35, 0.58, 0.33)
    A(speech("aluan_1", "IMG_2131", 0.9, 68.7, [
        (9.3, SY()),
        (16.2, PH("IMG_2129", z0=1.0, z1=1.06, c0=(0.5, 0.35), c1=(0.5, 0.35))),
        (29.0, SY(1.3, 0.58, 0.33)),
        (31.8, CU("IMG_2111", 7.4)),
        (46.3, SY()),
        (53.9, PH("IMG_2137", z0=1.0, z1=1.06, c0=(0.5, 0.85), c1=(0.5, 0.8))),
        (68.7, SY(1.3, 0.58, 0.33)),
    ], d_in=1.0))
    A(speech("aluan_2", "IMG_2131", 73.1, 344.9, [
        (76.0, SY()),
        (84.3, SY(1.5, 0.35, 0.3)),            # tuan rumah di sebelah kanan pemudahcara
        (101.2, SY()),
        (122.4, SY(1.3, 0.58, 0.33)),
        (134.2, SY()),
        (139.0, CU("IMG_2126", 1.2)),
        (150.0, PH("IMG_2135", mode="fit", z0=1.0, z1=1.07)),
        (171.4, SY()),
        (182.9, SY(1.3, 0.58, 0.33)),
        (205.9, SY()),
        (220.2, SY(1.35, 0.6, 0.3)),
        (233.1, SY(1.5, 0.33, 0.3)),           # pengerusi surau / tuan rumah
        (250.8, SY()),
        (258.0, CU("IMG_2110", 4.0)),
        (265.6, SY()),
        (277.2, SY(1.5, 0.74, 0.3)),           # pembantu (tekong) berjubah merah
        (296.3, SY()),
        (313.2, SY(1.6, 0.20, 0.28)),          # imam berbaju hijau
        (319.4, SY()),
        (324.0, CU("IMG_2107", 1.0)),
        (328.2, PH("IMG_2148", mode="fill", z0=1.0, z1=1.08, c0=(0.5, 0.64), c1=(0.5, 0.60))),
        (344.9, SY(1.25, 0.6, 0.33)),
    ], d_in=0.45))

    # ===== 6. WAKIL BERBICARA, ADAT BERTUKAR KATA =====
    W = (1.45, 0.90, 0.30)
    A(speech("wakil_salam", "IMG_2131", 351.4, 396.0, [(366.0, SY()), (396.0, SY(1.45, 0.9, 0.3))], d_in=0.7))
    A(speech("wakil_pantun", "IMG_2131", 467.3, 505.0, [(480.0, SY(1.3, 0.75, 0.3)), (505.0, SY())], d_in=0.55))
    A(speech("hajat", "IMG_2131", 509.8, 562.2, [], d_in=0.55))
    A(speech("adat_melayu", "IMG_2131", 565.7, 612.2, [
        (579.0, SY(1.3, 0.58, 0.33)),
        (592.4, SY()),
        (599.8, CU("IMG_2111", 0.8)),
        (607.0, CU("IMG_2113", 6.4)),
    ], d_in=0.55))
    A(speech("sirih_pinang", "IMG_2131", 619.5, 627.8, [], d_in=0.5))
    A(speech("bunga_rampai", "IMG_2131", 631.3, 646.0, [(638.0, CU("IMG_2114", 15.5)), (646.0, SY())], d_in=0.5))
    A(speech("bunga_rampai_pantun", "IMG_2131", 664.0, 676.9, [(676.9, SY(1.3, 0.58, 0.33))], d_in=0.45))

    # ===== 7. BUNGA RAMPAI DI KALANGAN PEREMPUAN, SOAL JAWAB PINANGAN =====
    A(speech("bunga_rampai_tetamu", "IMG_2132", 13.6, 35.0, [], d_in=0.8))
    A(speech("bau_bunga_rampai", "IMG_2132", 47.9, 62.0, [], d_in=0.5))
    A(speech("soal_jawab", "IMG_2132", 137.1, 218.9, [(152.5, SY()), (170.0, SY(1.3, 0.58, 0.33)), (190.0, SY())], d_in=0.8))

    # ===== 8. CINCIN =====
    A(speech("cincin", "IMG_2133", 14.9, 64.2, [], d_in=0.8))
    A(speech("peranan_perempuan", "IMG_2133", 68.2, 83.3, [], d_in=0.5))
    A(speech("syarat_1", "IMG_2133", 86.9, 171.8, [(110.0, SY(1.3, 0.58, 0.33)), (140.0, SY()), (160.0, SY(1.3, 0.58, 0.33))], d_in=0.55))
    # (tarikh & tempat hajat sengaja tidak dimasukkan: maklumat peribadi yang tidak diminta untuk dipaparkan)

    # ===== 9. PERBINCANGAN AKHIR, HANTARAN, SEJARAH, PENGISYTIHARAN =====
    A(speech("syarat_inkar_a", "IMG_2139", 144.0, 172.8, [], d_in=0.8))
    A(speech("syarat_inkar_b", "IMG_2139", 217.5, 259.9, [(240.0, SY(1.3, 0.58, 0.33))], d_in=0.55))
    A(speech("kesaksian", "IMG_2139", 262.8, 284.8, [], d_in=0.5))
    A(speech("hantaran", "IMG_2139", 358.7, 423.9, [
        (368.6, CU("IMG_2107", 3.5)),
        (383.0, SY()),
        (392.0, CU("IMG_2114", 14.0)),
        (400.0, SY()),
        (408.0, CU("IMG_2111", 1.0)),
    ], d_in=0.6))
    A(speech("sejarah_kampung", "IMG_2139", 471.0, 514.5, [], d_in=0.55))
    A(speech("pengisytiharan", "IMG_2139", 514.9, 535.0, [], d_in=0.55))
    A(speech("pantun_penutup", "IMG_2139", 547.0, 611.9, [(578.0, SY(1.3, 0.58, 0.33)), (591.8, SY())], d_in=0.55))

    # ===== 10. DOA (audio asal penuh) =====
    A(speech("doa", "IMG_2140", 0.5, 112.5, [], d_in=1.2, music="off"))

    # ===== 11. PENUTUP MAJLIS LELAKI =====
    A(speech("penutup_a", "IMG_2141", 0.8, 22.9, [], d_in=1.0))
    A(speech("penutup_b", "IMG_2141", 103.8, 113.8, [], d_in=0.6))

    # ===== 12. SARUNG CINCIN, REAKSI KELUARGA (audio asal + muzik) =====
    s144 = Seg("IMG_2144", 0.0, 35.5, bus="amb", snap_edges=False, gain=-2)
    A(Scene("sarung_cincin", [s144],
            [SYNC("IMG_2144", 35.5)], d_in=1.4, music="full"))
    A(Scene("reaksi", [],
            [P("IMG_2145", 6.0, dis=0.0), P("IMG_2146", 5.5, dis=1.0), P("IMG_2150", 6.0, dis=1.0),
             P("IMG_2151", 5.5, dis=1.0), P("IMG_2149", 6.0, dis=1.0, mode="fit")],
            d_in=1.0, music="full", dur=26.0))
    s157 = Seg("IMG_2157", 0.0, 8.0, bus="amb", snap_edges=False, xf=0.4, gain=-3)
    s158 = Seg("IMG_2158", 2.0, 10.8, bus="amb", snap_edges=False, xf=0.4, gain=-3)
    A(Scene("potret_keluarga", [s157, s158],
            [SYNC("IMG_2157", s157.dur), SYNC("IMG_2158", s158.dur, dis=0.4)], d_in=1.0, music="full"))
    A(Scene("potret_foto", [],
            [P("IMG_2154", 6.0, dis=0.0, mode="fit", z0=1.0, z1=1.07), P("IMG_2155", 6.5, dis=1.0, z0=1.0, z1=1.06,
                                                                           c0=(0.5, 0.4), c1=(0.5, 0.4))],
            d_in=1.0, music="full", dur=11.5))

    # ===== 13. SUASANA SELEPAS MAJLIS =====
    s143 = Seg("IMG_2143", 0.0, 13.0, bus="amb", snap_edges=False, gain=-4)
    s163 = Seg("IMG_2163", 0.0, 12.0, bus="amb", snap_edges=False, xf=0.5, gain=-3)
    s168 = Seg("IMG_2168", 20.5, 31.0, bus="amb", snap_edges=False, xf=0.5, gain=-3)
    A(Scene("selepas_majlis", [s143, s163, s168],
            [SYNC("IMG_2143", s143.dur, stab=True), SYNC("IMG_2163", s163.dur, dis=0.5), SYNC("IMG_2168", s168.dur, dis=0.5)],
            d_in=1.2, music="full"))

    # ===== 14. PENUTUP LEMBUT =====
    A(Scene("penutup", [],
            [P("IMG_2156", 9.0, dis=0.0, z0=1.06, z1=1.0, c0=(0.5, 0.45), c1=(0.5, 0.45))],
            d_in=1.6, music="full", dur=9.0))
    return scenes
