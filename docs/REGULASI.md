# Regulasi bawaan SIPAK

SIPAK menyertakan salinan PDF yang diberikan pengguna: Permendagri No. 8 Tahun 2026 tentang Pedoman Tata Kehidupan Praja Institut Pemerintahan Dalam Negeri. Tidak perlu mengunggah naskah melalui aplikasi.

## Sumber dan versi

- Naskah lengkap: `backend/assets/regulations/permendagri-8-2026.pdf` (25 halaman, 61 pasal).
- Manifest sumber: `backend/assets/regulations/permendagri-8-2026.json`.
- SHA-256: `2c3b9ea6b80c21ebbd1ebeff0382fc9e35a70d981e4120b02d6e6df288083f11`.
- Sesuai halaman 25, ditetapkan 18 Februari 2026 dan diundangkan 2 Maret 2026. Pasal 61 menyatakan berlaku pada tanggal diundangkan; aplikasi memakai `2026-03-02`.
- Asal dataset adalah PDF pengguna; kesesuaian sumber teknis terhadap PDF tidak menyatakan bahwa aplikasi melakukan autentikasi tanda tangan pemerintah atau verifikasi perubahan hukum terbaru.

Saat startup, aplikasi memeriksa checksum dan kelengkapan 61 pasal, kemudian memasang versi tetap dengan ID deterministik. Startup berikutnya tidak membuat duplikat atau menimpa penilaian/versi lama. Bila aset hilang, checksum berubah, atau indeks tidak lengkap, aplikasi gagal memulai dengan pesan penyebab, bukan memakai basis hukum parsial. Instalasi tercatat dalam audit sistem. Untuk memasang ke database tanpa menjalankan server: `python -m backend.manage seed-regulations`.

Semua halaman tetap tersedia pada PDF sumber. Teks pasal diindeks tanpa nomor halaman cetak, judul bab berikutnya, atau blok pengesahan penutup. Teks ketentuan dan referensi halaman asal tetap disimpan. Menu Regulasi menyediakan pencarian, kelompok pasal, naskah PDF, sumber per pasal, dan pemetaan sanksi. Tidak ada langkah unggah atau pembuatan aturan yang diperlukan untuk dataset bawaan.

## Pencocokan sanksi

486 aturan kondisional diturunkan dari referensi Pasal 36–39 ke ketentuan Pasal 7, 9, 11, 15, 17, 19, dan 21. Angka ini adalah jumlah cabang kondisi, bukan jumlah pasal atau pelanggaran. Kategori dan sanksi hanya tampil jika semua kondisi cabang didukung fakta bersumber yang diperiksa manusia.

- Sanksi ringan dan sedang bersifat kumulatif berdasarkan Pasal 39 ayat (1)–(2). Pasal 39 ayat (3) dicantumkan sebagai dasar pemeriksaan jika kedua kategori dikenakan bersamaan; aplikasi belum menggabungkan beberapa perbuatan menjadi satu keputusan sanksi otomatis.
- Cabang Pasal 38 membedakan Pratama dari Muda/Madya/Utama, akibat pada korban, kerusakan dan keributan, serta perdamaian pada ketentuan tertentu.
- Pengulangan Pasal 39 ayat (4)–(6) tidak diasumsikan dari ketiadaan data. Riwayat dan syarat pengulangan harus dinyatakan sebagai fakta bersumber.
- Kebutuhan berita acara ujian, ambang ketidakhadiran, pengulangan ringan dan bukti deteksi/laboratorium ditambahkan sebagai kondisi eksplisit pada ketentuan yang mensyaratkannya.
- Seluruh isi naskah tetap dapat dibaca. Ketentuan tentang kesehatan, kehamilan, status perkawinan, kehidupan seksual dan orientasi ditampilkan sebagai rujukan saja dan tidak dijadikan aturan pencocokan sanksi otomatis.

Setiap aturan menyimpan kutipan perbuatan, seluruh paragraf dasar sanksi terkait, versi sumber dan kondisi. Tidak ada klasifikasi berdasarkan satu kata kunci. Penilaian tetap pendahuluan; keputusan resmi tetap dicatat secara terpisah oleh pejabat berwenang. Aturan bawaan tidak dapat ditambah atau ditimpa melalui API editor; perubahan hukum memerlukan versi dataset baru, mempertahankan versi lama.

## Fakta untuk analisis

Pada tab Pemetaan Sanksi, buka detail ketentuan dan salin referensinya sebagai nilai `conduct`. Setiap fakta berikut harus menyertakan `sources` berupa halaman dan kutipan asli BAP; tidak cukup menyalin kutipan regulasi sebagai bukti perbuatan.

| Kunci | Arti nilai |
|---|---|
| `conduct` | Referensi ketentuan yang diduga dilanggar, misalnya `Pasal 11 ayat (2) huruf bo` |
| `praja_level` | `Pratama`, `Muda`, `Madya`, atau `Utama`, bila cabang aturan mensyaratkan tingkat |
| `severe_consequence` | Ada akibat korban memerlukan perawatan inap, luka berat, cacat atau meninggal dunia |
| `damage_and_disturbance` | Mengakibatkan kerusakan **dan** keributan pada ketentuan Pasal 11 ayat (2) huruf bp |
| `peace_with_victim` | Terjadi perdamaian dengan korban untuk huruf bq |
| `repeated_serious` | Pelanggaran berat sebagaimana cakupan Pasal 39 ayat (6) dilakukan lebih dari satu kali |
| `medium_escalation` | Pelanggaran sedang dilakukan saat menjalani sanksi sedang, dan/atau pelanggaran sedang yang sama lebih dari 3 kali dalam 2 bulan (Pasal 39 ayat (4)–(5)) |
| `exam_minutes_confirmed` | Perbuatan pada Pasal 7 ayat (2) huruf c / Pasal 9 ayat (2) huruf d dibuktikan berita acara |
| `absence_threshold_met` | Tanpa izin 7 hari kalender berturut-turut atau 14 hari kalender akumulatif dalam satu semester |
| `light_repeat_threshold_met` | Pelanggaran ringan yang sama 3 kali dalam satu bulan sejak pelanggaran pertama |
| `screening_or_lab_confirmed` | Bukti hasil pemeriksaan deteksi awal dan/atau laboratorium pada huruf br |

Tidak diketahui bukan `false`. Jangan mengisi fakta yang tidak didukung BAP dan pemeriksaan. Keabsahan pembuktian, pembelaan, serta penetapan akhir tidak ditentukan oleh pencocokan komputer.
