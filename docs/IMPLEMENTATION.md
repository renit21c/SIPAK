# Status implementasi dan validasi

Implementasi awal ini dimulai dari direktori kosong. Tidak ada gambar referensi yang menyertai lampiran teks, sehingga identitas visual mengikuti palet, tipografi, simbol dokumen/perisai, dan arahan dashboard institusional dalam spesifikasi.

## Tersedia

- React/TypeScript: login, dashboard, ekstraksi, data perkara, detail hasil, analisis ketentuan, manajemen sanksi, pemeriksaan, riwayat, regulasi, pengguna dan konfigurasi.
- Ruang kerja berbeda untuk admin, pemeriksa, verifikator, pejabat dan pengamat; antrean verifikasi/keputusan, laporan, pengguna serta audit terpisah. Guard halaman dan tombol menyesuaikan izin sesi.
- Sidebar desktop yang dapat diciutkan dan menu mobile; pencarian, filter status, urutan waktu, dan paginasi tabel; notifikasi dokumen yang perlu ditelaah.
- FastAPI dengan sesi database, scrypt, role-based permissions, pemeriksaan origin, rate limiting login, validasi request dan audit.
- Unggah PDF privat dengan signature/ukuran/password/page limit; teks PyMuPDF per halaman, chunk overlap dan sumber.
- Adapter API OpenRouter (default) dan Ollama opsional; pengaturan provider/model/key melalui UI admin, key backend saja, persetujuan per dokumen, snapshot pekerjaan, JSON Schema/Pydantic, withholding sumber tidak valid dan penanganan galat tanpa membocorkan respons sensitif.
- Penyimpanan database SQLAlchemy dengan dukungan PostgreSQL dan fallback SQLite untuk pengembangan. Source quotations tersimpan terpisah dari nilai entitas.
- Koreksi dan verifikasi manusia, pemeriksaan revisi, rekaman snapshot, alasan menerima/menolak klasifikasi, catatan rekomendasi komisi, lampiran PDF.
- Regulasi bawaan dari PDF pengguna: 25 halaman, 61 pasal, checksum, pemuatan otomatis, indeks/sumber PDF serta 486 cabang aturan kondisional; versi historis tetap dipertahankan.
- Mesin deterministik mengecek seluruh kondisi aturan; syarat kurang menghasilkan status informasi tidak cukup, bukan kategori/sanksi pasti.
- Template 12 tahap pemeriksaan dengan tanggal, penanggung jawab, dokumen dan catatan; pencatatan keputusan khusus peran pejabat; penguncian perkara; PDF laporan pendahuluan dengan catatan keputusan terpisah.

## Belum diverifikasi atau belum lengkap

- **Provider nyata**: integrasi OpenRouter diuji dengan transport HTTP tiruan, tanpa key, biaya atau pengiriman BAP nyata. Kualitas keluaran API/model nyata tetap perlu dievaluasi setelah konfigurasi pengguna.
- **Regulasi** sudah dipaketkan dari PDF pengguna dan tidak perlu diunggah. Kesesuaian penerapan dan kewenangan institusi tetap memerlukan evaluasi; naskah sumber tidak diautentikasi secara independen terhadap pemerintah. Lihat REGULASI.md.
- **PostgreSQL** didukung driver dan Compose; uji integrasi sesi ini memakai SQLite. Server PostgreSQL/Docker belum dijalankan.
- Penyimpanan entitas menggunakan JSON per tipe dan foreign key untuk sumber. Normalisasi master identitas lintas perkara, tabel riwayat disiplin, dan semua 24 entitas rekomendasi belum lengkap.
- Aturan bawaan telah tersedia. Penilaian tetap memerlukan masukan fakta manusia bersumber; pencocokan awal dari fakta AI belum diotomatisasi.
- Role-based workspace access tersedia; case-level/kampus ACL, nonaktifkan pengguna, pergantian peran dan sandi mandiri belum tersedia. Reset sandi administrator dilakukan via CLI lokal.
- Queue tahan restart, migrations/Alembic, OCR, SSO, antivirus scanning, enkripsi aplikasi at rest, retensi otomatis, serta integrasi tanda tangan/keputusan resmi belum tersedia. OCR dan GPU memang tidak diwajibkan untuk MVP.
- Aplikasi dijalankan lokal; belum dipublikasikan atau diterapkan untuk produksi institusi.

## Pemeriksaan yang dijalankan

- `npm.cmd run build`: pemeriksaan TypeScript dan build Vite.
- `python -m pytest backend/tests -q`: 42 pengujian integrasi/unit meliputi keamanan sesi/peran, PDF, sumber, chunking, kegagalan model, verifikasi/revisi, versi regulasi, matching berbasis kondisi, workflow/keputusan, dan isi laporan PDF.
- Browser lokal: login, delapan menu utama, status kosong dan konfigurasi belum terhubung; tata letak desktop 1440 px dan mobile 390 px serta interaksi menu mobile.

Lihat README untuk penyiapan akun, konfigurasi, perintah pengujian dan batas penerapan.
