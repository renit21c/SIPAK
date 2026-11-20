# Status implementasi dan validasi

Implementasi awal ini dimulai dari direktori kosong. Tidak ada gambar referensi yang menyertai lampiran teks, sehingga identitas visual mengikuti palet, tipografi, simbol dokumen/perisai, dan arahan dashboard institusional dalam spesifikasi.

## Tersedia

- React/TypeScript: login, dashboard, ekstraksi, data perkara, detail hasil, analisis ketentuan, manajemen sanksi, pemeriksaan, riwayat, regulasi, pengguna dan konfigurasi.
- Satu ruang kerja Komdis: unggah, periksa/verifikasi, telaah ketentuan, evaluasi, rekomendasi PDF. Akun lama dimigrasi otomatis tanpa perubahan email/password. Form tidak memerlukan masukan JSON.
- Sidebar desktop yang dapat diciutkan dan menu mobile; pencarian, filter status, urutan waktu, dan paginasi tabel; notifikasi dokumen yang perlu ditelaah.
- FastAPI dengan sesi database, scrypt, role-based permissions, pemeriksaan origin, rate limiting login, validasi request dan audit.
- Unggah PDF privat dengan signature/ukuran/password/page limit; teks PyMuPDF per halaman, chunk overlap dan sumber.
- Adapter API OpenRouter (default) dan Ollama opsional; pengaturan provider/model/key melalui Pengaturan Komdis, key backend saja, persetujuan per dokumen, snapshot pekerjaan, JSON Schema/Pydantic, withholding sumber tidak valid dan penanganan galat tanpa membocorkan respons sensitif.
- Penyimpanan database SQLAlchemy dengan dukungan PostgreSQL dan fallback SQLite untuk pengembangan. Source quotations tersimpan terpisah dari nilai entitas.
- Koreksi dan verifikasi manusia, pemeriksaan revisi, rekaman snapshot, alasan menerima/menolak klasifikasi, catatan rekomendasi komisi, lampiran PDF.
- Regulasi bawaan dari PDF pengguna: 25 halaman, 61 pasal, checksum, pemuatan otomatis, indeks/sumber PDF serta 486 cabang aturan kondisional; versi historis tetap dipertahankan.
- Mesin deterministik mengecek seluruh kondisi aturan; syarat kurang menghasilkan status informasi tidak cukup, bukan kategori/sanksi pasti.
- Evaluasi Lanjutkan/Perlu perbaikan dengan revisi dan identitas penilaian. PDF rekomendasi ber-watermark SIPAK pada setiap halaman, lengkap dengan sumber, evaluator dan jejak evaluasi. Arsip keputusan lama tetap terkunci.

## Belum diverifikasi atau belum lengkap

- **Provider nyata**: integrasi OpenRouter diuji dengan transport HTTP tiruan, tanpa key, biaya atau pengiriman BAP nyata. Kualitas keluaran API/model nyata tetap perlu dievaluasi setelah konfigurasi pengguna.
- **Regulasi** sudah dipaketkan dari PDF pengguna dan tidak perlu diunggah. Kesesuaian penerapan dan kewenangan institusi tetap memerlukan evaluasi; naskah sumber tidak diautentikasi secara independen terhadap pemerintah. Lihat REGULASI.md.
- **PostgreSQL** didukung driver dan Compose; uji integrasi sesi ini memakai SQLite. Server PostgreSQL/Docker belum dijalankan.
- Penyimpanan entitas menggunakan JSON per tipe dan foreign key untuk sumber. Normalisasi master identitas lintas perkara, tabel riwayat disiplin, dan semua 24 entitas rekomendasi belum lengkap.
- Aturan bawaan telah tersedia. Penilaian tetap memerlukan masukan fakta manusia bersumber; pencocokan awal dari fakta AI belum diotomatisasi.
- Seluruh anggota Komdis berbagi hak operasional dan konfigurasi workspace. Pembatasan antaranggota/perkara/kampus, nonaktifkan pengguna dan sandi mandiri belum tersedia. Reset sandi melalui CLI lokal.
- Queue tahan restart, migrations/Alembic, OCR, SSO, antivirus scanning, enkripsi aplikasi at rest, retensi otomatis, serta integrasi tanda tangan/keputusan resmi belum tersedia. OCR dan GPU memang tidak diwajibkan untuk MVP.
- Aplikasi dijalankan lokal; belum dipublikasikan atau diterapkan untuk produksi institusi.

## Pemeriksaan yang dijalankan

- `npm.cmd run build`: pemeriksaan TypeScript dan build Vite.
- `python -m pytest backend/tests -q`: 42 pengujian integrasi/unit meliputi keamanan sesi/peran, PDF, sumber, chunking, kegagalan model, verifikasi/revisi, versi regulasi, matching berbasis kondisi, migrasi akun, arsip keputusan, evaluasi/revisi, dan watermark PDF rekomendasi.
- Browser lokal: login, delapan menu utama, status kosong dan konfigurasi belum terhubung; tata letak desktop 1440 px dan mobile 390 px serta interaksi menu mobile.

Lihat README untuk penyiapan akun, konfigurasi, perintah pengujian dan batas penerapan.
