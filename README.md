# SIPAK

Panduan publish: [Railway + PostgreSQL + penyimpanan PDF](docs/DEPLOY_RAILWAY.md). Dockerfile membangun frontend dan backend menjadi satu service.

Sistem Informasi Pengolahan dan Analisis Kasus. React/TypeScript + FastAPI, dengan ekstraksi PDF PyMuPDF, inferensi API OpenRouter atau Ollama lokal, validasi Pydantic, database SQLAlchemy, dan laporan PDF ReportLab. Antarmuka berbahasa Indonesia memakai identitas navy, crimson, dan pink; logo SIPAK dibuat dari simbol dokumen/perisai, PDF rekomendasi memakai kop dan logo IPDN yang diberikan pengguna.

## Menjalankan di Windows

Gunakan **CPython Windows 3.11 atau lebih baru**, bukan Python MSYS/MinGW (wheel PyMuPDF tidak kompatibel). Node.js 22 atau lebih baru direkomendasikan.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd ci
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m backend.manage init --email admin@sipak.local
npm.cmd run build
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Buka [SIPAK lokal](http://127.0.0.1:8000). Masuk dengan akun dan kata sandi yang dipilih pada perintah `init`. Tidak ada akun/kata sandi bawaan dan tidak ada data perkara demonstrasi di database. Alternatif bootstrap noninteraktif tersedia melalui `BOOTSTRAP_EMAIL` dan `BOOTSTRAP_PASSWORD` (12+ karakter) di `.env`; hanya bekerja ketika belum ada pengguna. Hapus kata sandi bootstrap dari `.env` setelah inisialisasi.

Pada workspace ini runtime kompatibel dipasang dalam `.venv-win`; ganti `.venv` dengan `.venv-win` pada perintah di atas. `scripts/start.ps1` mendeteksi kedua folder tersebut.

Pengembangan: jalankan backend dengan `--reload`, lalu `npm.cmd run dev` pada terminal kedua. Vite meneruskan `/api` ke backend. Navigasi memakai hash sehingga dapat dibuka ulang tanpa aturan rewrite. Dokumentasi API: [OpenAPI lokal](http://127.0.0.1:8000/docs).

## AI melalui API

Default provider sekarang **OpenRouter**. Ollama dan GPU tidak diperlukan untuk mode API. Setelah login Komdis, buka **Pengaturan â†’ Provider AI**, pilih OpenRouter, isi Model ID yang mendukung structured outputs serta API key, simpan, lalu uji koneksi. Pengujian koneksi hanya mengakses metadata key/katalog model; tidak mengirim BAP atau menjalankan inferensi berbayar. Key disimpan pada `.env` backend dan tidak pernah dikembalikan ke frontend. Lihat [panduan API](docs/AI_API.md).

Setiap unggah atau proses ulang melalui OpenRouter memerlukan persetujuan pengiriman teks BAP ke OpenRouter dan penyedia model. Backend memeriksa persetujuan, provider dan model sebelum memproses. Snapshot konfigurasi melekat pada satu pekerjaan agar tujuan tidak berubah ketika pengaturan diganti. Key tidak dimasukkan ke audit; provider, model dan persetujuan tercatat. Tidak ada fallback otomatis. Harga/kredit mengikuti akun dan model pengguna.

PDF tetap disimpan privat di server SIPAK. Teks diekstrak per halaman, dipotong menjadi chunk dengan nomor halaman asli, lalu dikirim menggunakan JSON Schema. Pydantic memvalidasi struktur dan kutipan dicocokkan kembali dengan halaman asli. Hasil tanpa sumber valid ditahan untuk pemeriksaan. Kegagalan API, saldo, model, schema, PDF pindai atau timeout ditampilkan sebagai gagal, tanpa hasil AI palsu. Uji integrasi memakai API tiruan; panggilan provider asli belum diuji tanpa key pengguna.

Ollama tetap opsional: pilih Ollama di Pengaturan atau tetapkan `AI_PROVIDER=ollama`, unduh model yang sesuai dengan `ollama pull`, lalu jalankan `ollama serve`. Endpoint lokal tetap dibatasi ke loopback/host Docker `ollama`.

Restart server menandai pekerjaan terputus untuk dicoba ulang. Proses memakai background task lokal, belum durable queue lintas worker; jalankan satu worker. Memakai model cloud tidak otomatis mempublikasikan aplikasi ke internet.

## Draf evaluasi dan kop surat

Setelah fakta BAP diverifikasi, buka Evaluasi dan pilih **Buat draf AI**. AI mengisi ringkasan, rekomendasi dan pertimbangan bersumber, serta menyarankan pasal dari regulasi terverifikasi. Dropdown dapat mencari seluruh pasal dan menampilkan teks aslinya. Kategori/usulan sanksi diisi dari hasil pencocokan lengkap yang terkait pasal pilihan; tanpa kecukupan atau bila hasilnya ambigu, kategori tetap belum ditentukan dan tindak lanjut berupa pendalaman. Komdis dapat mengoreksi semua isian dan wajib mengonfirmasi telaah sebelum menyetujui PDF. Draf tersimpan tidak otomatis menyetujui atau menetapkan keputusan perkara.

Pengaturan **AI & Surat** menyediakan kop IPDN dengan logo dan alamat dari pengguna. Kop dapat dikoreksi, termasuk logo kiri/kanan PNG/JPEG, unit, alamat dan kontak. Detail nomor surat, tanggal, tempat dan tujuan tersedia pada evaluasi. PDF A4 menggunakan tata letak surat instansi, tanpa tanda tangan, dengan lampiran kutipan BAP dan teks pasal terpilih serta watermark SIPAK pada setiap halaman. Snapshot kop dan pasal melekat pada evaluasi yang disetujui, sehingga perubahan pengaturan berikutnya tidak mengubah versi dokumen tersebut.

Endpoint baru: GET/PUT `/api/settings/letterhead`, GET `/api/evaluation/articles`, POST `/api/cases/{id}/evaluation/draft`. Draf memerlukan revisi/penilaian terkini dan persetujuan provider yang sesuai untuk pengiriman cloud. Tidak ada panggilan AI otomatis ketika sekadar membuka halaman. Draf menyaring kandidat maksimal 12 pasal utuh; pilihan manual menampilkan semua pasal terverifikasi. Kutipan draf diperiksa terhadap sumber ekstraksi. Ini memvalidasi sumber, bukan membuktikan kebenaran penalaran model; substansi draf perlu ditelaah Komdis.

## PostgreSQL

SQLite adalah fallback pengembangan agar aplikasi dapat dijalankan tanpa layanan tambahan. Untuk PostgreSQL:

1. Tetapkan `POSTGRES_PASSWORD` pada `.env`.
2. Jalankan `docker compose up -d db`.
3. Tetapkan `DATABASE_URL=postgresql+psycopg://sipak:PASSWORD@localhost:5432/sipak` (URL-encode kata sandi bila perlu).
4. Inisialisasi akun Komdis pada database tersebut, lalu jalankan ulang backend.

Skema dibentuk saat startup untuk database baru. Data SQLite tidak dipindahkan otomatis. Sebelum perubahan skema produksi, buat backup dan migrasi terkontrol; Alembic belum disediakan. Relasi dokumen, halaman, perkara, entitas, kutipan sumber, versi regulasi, pasal, aturan, pemeriksaan, penilaian, keputusan, pengguna, sesi dan audit memakai foreign key. Detail ekstraksi dinamis disimpan sebagai entitas bertipe JSON; pemisahan lebih lanjut ke master person dan riwayat disiplin lintas perkara belum diimplementasikan.

## Regulasi dan sanksi

Regulasi sudah tersedia sebagai **bawaan aplikasi** dari PDF yang diberikan pengguna: `backend/assets/regulations/permendagri-8-2026.pdf`. Seluruh 25 halaman dan 61 pasal dipaketkan, dengan tanggal berlaku 2 Maret 2026 sesuai naskah. Saat startup SIPAK memeriksa checksum, lalu memasang indeks dan 486 cabang aturan kondisional tanpa unggah manual. Restart tidak membuat duplikat atau menimpa data perkara. Menu Regulasi menyediakan pencarian pasal, sumber PDF dan pemetaan sanksi; versi bawaan bersifat tetap.

Aturan merujuk ketentuan perilaku dan Pasal 35â€“39, termasuk sanksi kumulatif, tingkat Praja, akibat, dan pengulangan. Sanksi tidak tampil ketika syarat kurang. Beberapa ketentuan mengenai karakteristik sensitif disediakan sebagai rujukan saja, tanpa pencocokan sanksi otomatis. Penilaian tetap memerlukan fakta bersumber dan telaah manusia. Lihat [panduan regulasi](docs/REGULASI.md) untuk arti kondisi, sumber dan batas penerapan. API impor versi lain tetap tersedia untuk pengembangan versi mendatang; penggunaan normal tidak memerlukannya.

Contoh bentuk fakta (gunakan kutipan nyata, bukan teks contoh):

```json
{
  "conduct": {"value":"Pasal 11 ayat (2) huruf bo", "sources":[{"page":1,"quote":"kutipan asli"}]},
  "praja_level": {"value":"Pratama", "sources":[{"page":1,"quote":"kutipan asli identitas"}]},
  "repeated_serious": {"value":false, "sources":[{"page":2,"quote":"kutipan riwayat"}]}
}
```

Nilai kosong tidak berarti false atau tidak ada pengulangan; jangan mengisi fakta yang tidak didukung sumber. Penilaian menyimpan versi aturan, kutipan, sumber BAP dan revisi perkara. Koreksi ekstraksi membatalkan tampilan penilaian aktif sampai dinilai ulang; riwayat sebelumnya tetap tersedia. Sistem tidak memverifikasi kebenaran semantik otomatis di luar sumber kutipan dan kondisi yang disusun manusia.

## Alur Komdis dan rekomendasi

Satu ruang kerja Komdis: **unggah BAP → proses AI → periksa/verifikasi → evaluasi → rekomendasi PDF**. Fakta, sumber, bukti, saksi, kronologi, telaah ketentuan dan riwayat tersedia dalam detail perkara. Koreksi serta penilaian ketentuan memakai form tanpa masukan JSON.

Evaluasi `Perlu perbaikan` mengembalikan perkara ke verifikasi. Evaluasi `Lanjutkan` memerlukan hasil terverifikasi, ringkasan, rekomendasi dan dasar pertimbangan. Dokumen rekomendasi memuat watermark SIPAK pada setiap halaman. Perubahan revisi atau analisis membatalkan kesiapan PDF sampai dievaluasi ulang. Rekomendasi merupakan hasil telaah manusia Komdis, sedangkan hasil AI tetap menjadi bahan pemeriksaan.

## Hak akses dan privasi

Akun baru hanya memiliki peran `komdis`: baca, unggah, koreksi/verifikasi, analisis, evaluasi/rekomendasi, konfigurasi sistem dan anggota. Akun lama otomatis disatukan ke Komdis saat startup, tanpa mengubah email/password atau menghapus riwayat. Semua anggota adalah pengguna internal tepercaya dengan akses workspace bersama. Arsip keputusan resmi versi lama dipertahankan dan tetap terkunci; Komdis tidak diberikan izin menetapkan keputusan resmi. Lihat [panduan Komdis](docs/ROLES.md).

Reset kata sandi lokal tersedia melalui `python -m backend.manage reset-password --email ...`; seluruh sesi pengguna tersebut dicabut.

Cookie sesi HttpOnly/SameSite Strict, hashing kata sandi scrypt dengan salt, pemeriksaan origin pada mutasi browser, rate limiting login, UUID untuk file, validasi masukan, dan audit aktivitas diterapkan. File tidak berada di direktori publik. Perkara dapat dipindahkan ke tab Terhapus setelah konfirmasi, lalu dipulihkan kembali. BAP, lampiran, evaluasi, dan jejak keputusan tetap disimpan; akses PDF dan detail diblokir selama perkara terhapus. Dokumen gagal tanpa perkara dapat dihapus Komdis setelah konfirmasi. Isi koreksi dan keputusan disimpan untuk jejak historis.

Untuk penerapan institusi, aktifkan TLS pada reverse proxy, `COOKIE_SECURE=true`, enkripsi volume/disk dan backup, pembatasan akun OS, rotasi/retensi audit, backup database, pengujian beban serta evaluasi hukum/regulasi oleh institusi. Enkripsi at rest mengandalkan infrastruktur, bukan enkripsi aplikasi. Mode server lokal default hanya bind `127.0.0.1`. Antarmuka menggunakan font Google bila jaringan tersedia; fallback font sistem tetap berjalan. Jangan publikasikan direktori `data` atau `.env`.

## Verifikasi

```powershell
npm.cmd run build
.\.venv-win\Scripts\python.exe -m pytest backend/tests -q
```

Pengujian menggunakan database sementara dan stub Ollama **hanya di test**, dengan PDF sintetis berlabel pengujian. Tidak ada hasil hardcoded yang dipakai aplikasi. Cakupan meliputi akses anonim, peran, unggah PDF, ekstraksi teks/sumber, penolakan hasil tanpa sumber, chunking, kegagalan inferensi, koreksi/verifikasi, aturan berbasis kondisi, regulasi versi, workflow, keputusan, dan laporan PDF.

## Batas versi awal

Alur utama bekerja sebagai aplikasi lokal. Yang memerlukan pekerjaan lanjutan sebelum klaim sistem produksi lengkap: evaluasi penerapan aturan oleh institusi; pengujian model nyata pada data yang diizinkan; OCR; master identitas lintas perkara dan riwayat disiplin terintegrasi; kontrol per kasus/kampus; migrasi database; antrean pekerjaan tahan restart; manajemen pengguna lengkap (nonaktifkan/ubah peran/ganti sandi mandiri); tanda tangan dan mekanisme dokumen keputusan resmi; hardening operasional. Tidak ada deployment publik/cloud karena stack FastAPI/PostgreSQL/Ollama lokal ini tidak kompatibel langsung dengan runtime Sites Workers dan memerlukan lingkungan institusi.

Filter Ringan/Sedang/Berat berlaku pada tab Pasal dan Pemetaan Sanksi. Tab Pasal menampilkan pasal perilaku dan dasar sanksi yang terkait melalui aturan versi regulasi aktif; teks pasal tetap utuh. Pada pemetaan, kategori dan rincian hanya berasal dari cabang aturan yang cocok dengan filter. Kelompok ketentuan dan pencarian tetap dapat dikombinasikan.

Login desktop memenuhi layar dalam dua kolom; login mobile juga memenuhi layar dalam dua bagian atas-bawah: logo pada panel navy di atas, form masuk di bawah. Teks Ruang kerja Komdis hanya tampil di desktop. Tidak menambahkan pendaftaran atau login sosial dari contoh referensi.

## Mobile dan PWA

Tabel menggunakan satu struktur data: desktop berupa tabel, mobile menjadi kartu berlabel per baris. Pencarian, filter, pagination, serta tindakan baca/hapus/pulihkan tetap tersedia tanpa gulir horizontal. Tab navigasi dapat membungkus ke baris berikutnya.

Favicon SVG/ICO dan ikon Apple/PWA memakai mark dokumen-perisai SIPAK. Manifest ada di `public/manifest.webmanifest`, dengan ikon 192/512 dan maskable. Generator ikon: `python scripts/generate_app_icons.py`. Mode produksi mendaftarkan `public/sw.js`; hanya halaman publik `offline.html` yang disimpan pada Cache Storage. API, BAP, lampiran, rekomendasi dan respons login tidak dicache oleh service worker. Aplikasi tetap memerlukan koneksi untuk pekerjaan Komdis. Naikkan versi cache pada sw.js bila fallback offline diperbarui.

Hosting HTTPS atau localhost/127.0.0.1 diperlukan untuk pemasangan PWA; opsi pemasangan mengikuti browser perangkat. Lihat [syarat PWA MDN](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable). Tidak ada prompt pemasangan otomatis di UI.

Verifikasi PWA: `node --test scripts/tests/pwa.test.mjs` memeriksa manifest, ukuran ikon, cache offline, dan pengecualian API/PDF. HTTP pratinjau produksi memeriksa manifest, favicon, seluruh ikon, sw.js dan offline.html beserta MIME type. Pemasangan pada perangkat fisik belum diuji.

Desktop dan mobile memakai tema bersama: latar biru lembut, topbar navy membulat, kartu angka navy/biru/pink, dan panel identitas perkara navy. Sorotan rekomendasi menggunakan pink lembut/crimson; warna status tetap semantik. Desktop memakai sidebar navy dengan menu aktif terang dan panel membulat, sementara mobile tetap memakai navigasi bawah serta kartu tabel vertikal.

Login tidak memakai bingkai atau margin luar pada desktop/mobile. Navbar mobile mengambang dengan radius 20 px. Form tetap dapat digulir vertikal pada viewport pendek, tanpa memotong kontrol.

Judul tab browser dan nama PWA adalah SIPAK. Pada mobile, sidebar dan tombol burger diganti navigasi bawah membulat: Ringkasan, Perkara, Unggah, Rekomendasi, dan Lainnya. Menu aktif memakai ikon lingkaran terangkat; Arsip BAP, Regulasi, dan Pengaturan tersedia melalui panel Lainnya sesuai izin pengguna. Konten dan notifikasi diberi ruang agar tidak tertutup navigasi atau area aman perangkat. Desktop tetap memakai sidebar.

Pilihan filter, pasal, kategori, peran dan provider memakai dropdown SIPAK dengan panel navy/biru lembut, pencarian melalui keyboard, serta penanda pilihan aktif. Model AI tetap dapat diketik bebas dengan saran model dalam panel yang sama. Pemilih tanggal surat memakai kalender SIPAK; checkbox/radio mengikuti palet aplikasi. Sidebar desktop memiliki transisi lebar 320 ms, label memudar, dan ikon collapse berputar; preferensi reduced motion tetap dihormati.

Setelah memperbarui kode backend, mulai ulang server SIPAK; build frontend saja tidak memuat endpoint/prompt Python terbaru. Untuk pengembangan lokal, `scripts/start.ps1 -Dev` memuat ulang perubahan backend secara otomatis. Pesan fitur belum tersedia pada server berarti proses backend masih memakai versi lama. Kop surat menyediakan Coba lagi saat pemuatan gagal, dan daftar pasal tetap dimuat bila pemuatan kop gagal. Draf evaluasi menggunakan suara kelembagaan Komdis dengan usulan tindakan langsung; hasil lama berubah setelah Perbarui draf.

Logo kop surat dibatasi lagi setelah konversi PNG agar hasil normalisasi tetap di bawah 350 KB dan dapat disimpan/dibaca ulang. Logo lama yang sempat tersimpan terlalu besar diperkecil saat dibaca, dengan tetap mempertahankan logo dan isi kop; penyimpanan berikutnya memakai hasil yang sudah sesuai batas. Snapshot kop pada rekomendasi lama tetap dipertahankan.
