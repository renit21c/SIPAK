# Publish SIPAK ke Railway

Satu project berisi dua service: aplikasi SIPAK dan PostgreSQL. Service SIPAK memakai Dockerfile di root repo; React dibuild lalu dilayani oleh FastAPI pada domain yang sama. PostgreSQL menyimpan akun dan hasil pemeriksaan; volume SIPAK menyimpan PDF BAP dan lampiran.

Biaya Railway mengikuti paket dan penggunaan aplikasi, database, volume serta jaringan. Kredit OpenRouter terpisah. Periksa [pricing](https://docs.railway.com/pricing) sebelum membuat service. Panduan ini menyiapkan database cloud baru; akun dan PDF lokal tidak otomatis dipindahkan.

## 1. Buat project dan PostgreSQL

1. Login ke https://railway.com dengan akun GitHub yang bisa mengakses `renit21c/SIPAK`.
2. Buat **New Project / Empty Project**.
3. Tambahkan **Database / PostgreSQL**. Tunggu hingga berjalan.
4. Pertahankan nama service `Postgres` untuk reference di bawah; bila namanya berbeda, pilih nama sebenarnya.
5. Database cukup memakai private network dalam project ini. Tidak perlu Generate Domain atau mengaktifkan akses database publik.

Referensi: [PostgreSQL Railway](https://docs.railway.com/databases/postgresql).

## 2. Tambahkan aplikasi dari GitHub

1. Pada project yang sama, tambahkan service dari **GitHub Repo**.
2. Hubungkan repository `renit21c/SIPAK`, branch `main`.
3. Root directory tetap root repo. Railway mendeteksi `Dockerfile` secara otomatis.
4. Tidak perlu build command atau start command kustom. Dockerfile menjalankan Uvicorn pada `0.0.0.0:$PORT`, satu worker.

Referensi: [Dockerfile Railway](https://docs.railway.com/builds/dockerfiles).

## 3. Pasang volume PDF pada aplikasi

Tambahkan volume ke service **SIPAK**, dengan mount path:

```text
/app/data
```

Volume ini untuk file PDF; volume PostgreSQL yang dibuat oleh template adalah penyimpanan berbeda. Path PDF di environment harus `/app/data/documents`. Volume baru tersedia saat container berjalan, bukan pada tahap build atau pre-deploy. Tidak perlu menjalankan migrasi yang menulis PDF di pre-deploy.

Referensi: [Volumes Railway](https://docs.railway.com/volumes).

## 4. Isi Variables di service SIPAK

| Variable | Nilai |
|---|---|
| `DATABASE_URL` | Reference ke `Postgres.DATABASE_URL` dari service database yang sama |
| `STORAGE_PATH` | `/app/data/documents` |
| `PORT` | `8000` |
| `COOKIE_SECURE` | `true` |
| `AI_PROVIDER` | `openrouter` |
| `AI_MODEL` | Model ID OpenRouter, misalnya `nvidia/nemotron-3.5-super-vl` |
| `OPENROUTER_API_KEY` | API key OpenRouter milikmu |
| `AI_TIMEOUT_SECONDS` | `180` |
| `MAX_UPLOAD_MB` | `20` |
| `BOOTSTRAP_EMAIL` | Email login pertama, misalnya `admin@sipak.local` |
| `BOOTSTRAP_PASSWORD` | Password unik pilihanmu, minimal 12 karakter |
| `BOOTSTRAP_NAME` | `Komdis` |

Untuk DATABASE_URL, gunakan **Add Reference** lalu pilih Postgres dan DATABASE_URL, atau masukkan reference berikut sebagai nilai (jangan ganti dengan URL contoh):

```text
${{Postgres.DATABASE_URL}}
```

SIPAK otomatis memilih driver `psycopg` untuk URL `postgres://` atau `postgresql://` yang diberikan hosting. Gunakan URL private dari database, bukan `DATABASE_PUBLIC_URL`.

Masukkan key dan password hanya pada Variables hosting. `.env` lokal tidak ikut Git atau Docker image. Untuk konfigurasi cloud yang bertahan pada restart/redeploy, ubah provider, model dan API key melalui Variables Railway. Perubahan lewat editor Pengaturan SIPAK saat ini menulis `.env` dalam container dan mengubah proses berjalan; file tersebut tidak persisten, dan Variables hosting kembali memiliki prioritas pada restart.

## 5. Deploy

1. Simpan/apply Variables, lalu Deploy atau Redeploy service SIPAK.
2. Biarkan jumlah replica **1**; aplikasi masih memakai background task dalam proses yang sama.
3. Healthcheck path boleh `/` dan target port `8000`.
4. Pantau log build dan runtime. Startup membuat tabel, memasang regulasi bawaan, dan membuat akun bootstrap hanya jika database belum memiliki pengguna.
5. Tunggu status deployment berhasil sebelum membuka login.

Jangan isi command startup dengan `127.0.0.1` atau `--reload`. Command Dockerfile sudah siap untuk hosting. Inisialisasi akun tidak dilakukan pada image build atau lewat backend.manage pada laptop, karena database yang digunakan adalah database cloud.

## 6. Buat alamat publik

Buka service SIPAK **Settings / Networking / Generate Domain**. Pilih target port `8000` jika diminta. Buka URL HTTPS yang diberikan Railway. Hanya service aplikasi yang perlu alamat publik.

Referensi: [Domains Railway](https://docs.railway.com/networking/domains/working-with-domains).

## 7. Login dan periksa

1. Masuk dengan BOOTSTRAP_EMAIL dan BOOTSTRAP_PASSWORD dari langkah 4. Ini akun Komdis baru pada database cloud.
2. Setelah login pertama berhasil, hapus BOOTSTRAP_PASSWORD dari Variables dan apply/redeploy. Akun tetap tersimpan di PostgreSQL.
3. Buka Pengaturan lalu Uji Koneksi. Pemeriksaan hanya membaca metadata key dan model.
4. Unggah contoh BAP sintetis. Pemrosesan dokumen menggunakan API sesuai model dan biaya akun OpenRouter.
5. Coba verifikasi, evaluasi, dan unduh rekomendasi PDF.
6. Sesudah restart/redeploy, pastikan akun serta PDF sumber masih bisa dibuka. Aktifkan backup untuk PostgreSQL dan volume PDF.

## 8. Pembaruan berikutnya

Dengan GitHub source terhubung dan auto-deploy aktif, push ke branch main akan memicu deployment baru. Variables hosting dan volume tetap terpisah dari source code. Jangan menghapus service database atau volume saat memperbarui aplikasi.

## Troubleshooting

- **Build gagal**: buka build log; pastikan Dockerfile ada di root, root directory benar dan npm ci/pip install tidak gagal.
- **Database tidak terhubung**: periksa reference DATABASE_URL, nama service Postgres, status database, dan bahwa kedua service berada pada project/environment yang sama.
- **502 / tidak bisa dibuka**: pastikan aplikasi sudah Running, domain menarget port 8000, dan PORT=8000 di Variables.
- **Tidak bisa login**: akun lokal tidak ikut pindah. Periksa bootstrap di database cloud baru, password minimal 12 karakter, dan akses melalui HTTPS karena COOKIE_SECURE=true.
- **PDF hilang setelah redeploy**: volume harus terpasang pada service SIPAK di /app/data dan STORAGE_PATH=/app/data/documents. Database dan PDF sama-sama perlu penyimpanan persisten.
- **API key/model kembali ke nilai lama**: ubah Variables hosting dan redeploy, bukan hanya isian Pengaturan dalam container.
- **Pemrosesan terhenti saat redeploy**: startup menandai pekerjaan yang terputus sebagai gagal agar bisa dicoba ulang; queue durable belum tersedia.

Validasi lokal: build frontend dan tes konfigurasi/backend. Build Docker penuh memerlukan Docker Desktop/Linux engine aktif; bila engine tidak tersedia, hasil build image harus diperiksa pada deployment Railway.
