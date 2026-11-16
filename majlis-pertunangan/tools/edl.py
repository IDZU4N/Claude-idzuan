"""Jana EDL (senarai keputusan suntingan) boleh dibaca manusia + timeline.json daripada garis masa sebenar."""
import sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
import timeline
from engine import layout, S

DESC = {
    "pembukaan": "Pembukaan tenang (muzik sahaja): hiasan pelamin, hantaran, perincian cincin. Tajuk muncul.",
    "ketibaan": "Ketibaan dan pertemuan: tetamu, bersalaman, hantaran dibawa masuk dan disusun (bunyi suasana asal + muzik).",
    "bersiap": "Suasana sebelum majlis bermula: wakil-wakil bersiap/menunggu (muzik).",
    "doa_pembuka": "Pembukaan majlis: khutbah/bacaan pembuka (audio asal, tanpa muzik).",
    "aluan_1": "Aluan pemudahcara (1/2): pantun adat, salam hormat. Landasan suara pemudahcara.",
    "aluan_2": "Aluan pemudahcara (2/2): selamat datang, maaf, memperkenalkan diri, tuan rumah, pembantu, imam, menjemput wakil.",
    "wakil_salam": "Wakil rombongan membalas salam dan menyatakan kedatangan.",
    "wakil_pantun": "Berbalas pantun antara wakil dan pemudahcara.",
    "hajat": "Pemudahcara bertanya hajat; wakil menyatakan hajat merisik dan bertunang.",
    "adat_melayu": "Pemudahcara: adat yang tak lekang dek panas, tepak sirih dan pinang.",
    "sirih_pinang": "Sirih pinang disambut dan dicicip.",
    "bunga_rampai": "Bunga rampai sebagai pengiring adat.",
    "bunga_rampai_pantun": "Pantun bunga rampai (untuk anak gadis dan mak-mak janda).",
    "bunga_rampai_tetamu": "Bunga rampai di kalangan tetamu (audio asal adegan).",
    "bau_bunga_rampai": "Reaksi tetamu menghidu bunga rampai (audio asal).",
    "soal_jawab": "Adat soal jawab pinangan: siapa yang bertanya, siapa yang ditanya; pantun penerimaan.",
    "cincin": "Dua cincin: untuk merisik dan untuk bertunang; cincin diperiksa ahli keluarga perempuan (audio asal).",
    "peranan_perempuan": "Peranan orang perempuan dalam adat meminang.",
    "syarat_1": "Perbincangan: mas kahwin dan wang saksi, dan adat yang dipatuhi.",
    "syarat_inkar_a": "Perbincangan terakhir: jika berlaku inkar atau cacat celanya (1).",
    "syarat_inkar_b": "Perbincangan terakhir: barang diberi dikembalikan jika pihak perempuan mungkir; tidak jika pihak lelaki (2).",
    "kesaksian": "Semua hadirin menjadi saksi; ikhlas dan halal.",
    "hantaran": "Isi hantaran: kuih, buah-buahan, pantun buah. Visual hantaran sebenar.",
    "sejarah_kampung": "Sejarah kampung yang menghubungkan dua keluarga.",
    "pengisytiharan": "Pengisytiharan rasmi pertunangan. Bingkai dekat sebenar.",
    "pantun_penutup": "Mohon maaf dan pantun penutup; menjemput imam membaca doa.",
    "doa": "Doa penuh (audio asal; muzik dimatikan).",
    "penutup_a": "Pemudahcara menutup majlis pihak lelaki (1).",
    "penutup_b": "Penutup majlis: Wabillahi taufiq wal hidayah, salam.",
    "sarung_cincin": "Majlis pihak perempuan: cincin disarungkan, senyuman dan tawa (audio asal + muzik).",
    "reaksi": "Reaksi keluarga: pandangan mata, sebak dan senyuman (foto, gerakan halus).",
    "potret_keluarga": "Potret keluarga dirakam (video).",
    "potret_foto": "Potret keluarga (foto).",
    "selepas_majlis": "Suasana selepas majlis: bersalaman dan jamuan.",
    "penutup": "Penutup lembut: potret keluarga, ucapan terima kasih, pudar.",
}


def mmss(t):
    return "%d:%05.2f" % (int(t // 60), t % 60)


def main(outdir):
    sc = timeline.build()
    total = layout(sc)
    os.makedirs(outdir, exist_ok=True)
    rows = []
    md = ["# EDL: Majlis Pertunangan Melayu", "",
          f"Jumlah: **{mmss(total)}** ({total:.2f} s), 1920x1080, 29.97 fps, H.264 + AAC 320 kbps, -16 LUFS.", "",
          "Masa 'Mula' ialah masa garis masa akhir. 'Audio' ialah landasan audio (fail sumber, masa masuk-keluar dalam saat). "
          "'Visual' ialah bidikan: `SYNC` = visual sumber yang sama dengan audio; `CU` = sisipan tanpa suara asal; `FOTO` = gambar gerakan halus.", ""]
    md.append("| # | Mula | Tempoh | Adegan | Audio (sumber masuk-keluar) | Visual |")
    md.append("|---|------|--------|--------|------------------------------|--------|")
    for i, s in enumerate(sc, 1):
        au = "; ".join(f"{g.src[-4:]} {g.a:.2f}-{g.b:.2f} ({g.bus})" for g in s.audio) or "muzik sahaja"
        vs = []
        for h in s.shots:
            if h.kind == "photo":
                vs.append(f"FOTO {h.src[-4:]} {h.dur:.1f}s")
            elif h.sync:
                z = f" zum{h.kw['push'][0]:.2f}" if h.kw.get("push") else ""
                vs.append(f"SYNC {h.src[-4:]} {h.ss:.1f}+{h.dur:.1f}s{z}")
            else:
                vs.append(f"CU {h.src[-4:]} {h.ss:.1f}+{h.dur:.1f}s")
        md.append(f"| {i} | {mmss(s.t0)} | {s.alen:.1f}s | **{s.name}**: {DESC.get(s.name,'')} | {au} | {'; '.join(vs)} |")
        rows.append({"scene": s.name, "start": round(s.t0, 3), "dur": round(s.alen, 3), "music": s.music,
                     "audio": [{"src": g.src, "in": g.a, "out": g.b, "bus": g.bus, "gain_db": g.gain} for g in s.audio],
                     "shots": [{"kind": h.kind, "src": h.src, "in": round(h.ss, 3), "dur": round(h.dur, 3),
                                "sync": h.sync, "dissolve": h.dis, "opts": {k: v for k, v in h.kw.items()}} for h in s.shots]})
    open(f"{outdir}/EDL.md", "w").write("\n".join(md) + "\n")
    json.dump({"total_s": round(total, 3), "scenes": rows}, open(f"{outdir}/timeline.json", "w"), indent=1, ensure_ascii=False, default=str)
    print("EDL ditulis", outdir, "jumlah", mmss(total))


if __name__ == "__main__":
    main(sys.argv[1])
