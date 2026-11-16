# Projek suntingan: Majlis Pertunangan Melayu

Video sinematik 25:14 (1920x1080, 29.97 fps, H.264 + AAC 320 kbps, -16 LUFS) daripada 43 video dan 20 gambar
iPhone (`IMG_2102` hingga `IMG_2168`). Media asal dan MP4 akhir **tidak** disimpan dalam repositori ini
(terlalu besar dan peribadi); hanya skrip, garis masa dan dokumen suntingan.

## Kandungan

| Fail | Fungsi |
|------|--------|
| `docs/EDL.md` | Senarai keputusan suntingan: masa mula, audio (sumber, masuk-keluar), bidikan visual |
| `docs/timeline.json` | Garis masa yang sama dalam bentuk mesin |
| `tools/timeline.py` | **Garis masa suntingan** (ubah di sini untuk menyunting semula) |
| `tools/engine.py` | Enjin audio (landasan pemudahcara, titik potong pada celah perkataan), susun atur |
| `tools/vrender.py` | Pemaparan bidikan, dissolve, atom per bingkai, pengekodan akhir |
| `tools/cine.py`, `tools/photos.py` | Penggredan warna per klip, Ken Burns untuk foto (profil warna HEIC ditukar ke sRGB) |
| `tools/music.py` | Gubahan muzik instrumental asli (skala Hijaz: pad, petikan gaya gambus, rebana) |
| `tools/titles.py` | Grafik teks (tajuk, nama pemudahcara, terima kasih) |
| `tools/asr.py`, `tools/show.py` | Transkripsi Whisper (faster-whisper) dan paparan transkrip |
| `tools/make.py`, `tools/rebuild.py`, `tools/encode.py` | Peringkat audio, video dan eksport |

Skrip menganggap folder kerja ditetapkan oleh pemboleh ubah `S` dalam `tools/cine.py`
(`S/src` = media asal, `S/aud` = audio 16 kHz untuk ASR). Laraskan `S` sebelum menjalankan.

## Alur kerja

1. Muat turun media ke `S/src`; ekstrak audio 16 kHz ke `S/aud` dan jalankan `asr.py` (model `medium` untuk klip panjang).
2. `stats.py` mengukur pendedahan/warna setiap klip (digunakan untuk penggredan per klip).
3. Ubah `timeline.py` (adegan, titik masuk-keluar audio, bidikan).
4. `make.py audio` menghasilkan campuran audio dan stem (`stem_dialog/ambien/muzik.wav`); `rebuild.py` memaparkan bidikan dan atom;
   `encode.py` mengeksport MP4.

## Keputusan suntingan utama

- **Landasan suara pemudahcara (Tuan Haji Alfadhilah):** audio dikekalkan berterusan; visual bertukar kepada tetamu, hantaran,
  cincin dan reaksi tanpa suara asal. Titik potong dipilih pada celah antara perkataan (bukan di tengah perkataan) dengan sambungan 35 ms.
  Ucapan tidak dipercepat dan susunan ayat tidak diubah.
- **Doa dan dialog:** audio asal adegan, muzik dimatikan (doa) atau direndahkan automatik (~20 dB di bawah suara).
- **Muzik:** instrumental asli yang dijana dalam kod (bebas hak cipta, selamat untuk YouTube). Boleh diganti dengan muzik pilihan:
  gantikan `stem_muzik.wav`.
- **Warna:** gamma per klip ke aras seragam, imbangan putih halus, hitam sedikit diangkat dan sorotan dihadkan (pakaian putih tidak terbakar).
  Tiada penajaman; stabilisasi hanya pada klip berjalan tangan (ketibaan).
- **Foto:** gerakan zum/anjakan perlahan; foto menegak dibingkai dengan latar kabur lembut, tidak diregangkan.

## Perkara yang disengajakan (boleh dibalikkan)

- **Nama pasangan dan tarikh tidak dipaparkan** dalam teks. Nama masih terdengar dalam audio pengisytiharan dan soal jawab pinangan
  (memotongnya akan mengubah maksud ucapan).
- **Tarikh dan tempat hajat** (IMG_2133, 173.6-229.5 s) **tidak dimasukkan**; ia maklumat peribadi yang tidak diminta untuk dipaparkan.
  Untuk memasukkannya semula, tambah `speech("syarat_2", "IMG_2133", 173.6, 229.5, ...)` dalam `timeline.py`.
- **Jumlah hantaran** (IMG_2139, ~0-145 s) tidak dimasukkan. Mas kahwin dan wang saksi dikekalkan sebagai adat.
- Klip tersalah rakam dibuang: IMG_2105, IMG_2127 (<0.2 s), IMG_2121-2124 (swafoto/sembang juru kamera), IMG_2115 dan IMG_2160-2168 hanya sebahagian sebagai suasana.
- Tiada narasi atau suara tiruan ditambah.

## Penyemakan

Dikesan automatik pada MP4 akhir: tiada skrin hitam, tiada bingkai beku >1.5 s, tiada kesenyapan >=1 s, bilangan bingkai tepat
(45,379) dengan beza audio/video 6 ms, puncak audio -1.0 dBFS, kelantangan bersepadu -16 LUFS. Kesegerakan disahkan dengan
membandingkan bingkai asal dan bingkai akhir pada titik masa sebenar.
