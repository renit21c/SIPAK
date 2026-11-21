# SIPAK

Sistem Informasi Pengolahan dan Analisis Kasus untuk membantu Komdis mengolah BAP hingga menghasilkan dokumen rekomendasi.

**[Buka SIPAK](https://sipak.up.railway.app/)**

## Fitur

- Unggah BAP PDF, termasuk hasil scan melalui FastOCR.
- Ekstraksi identitas, saksi, kronologi, bukti, dan kutipan sumber.
- Draf evaluasi AI, pencarian pasal, kategori, dan usulan tindakan untuk ditelaah Komdis.
- Rekomendasi PDF dengan kop instansi dan watermark SIPAK.
- Tampilan responsif, PWA, serta aplikasi Android.

**Alur:** Unggah BAP → Proses → Verifikasi → Evaluasi → Unduh rekomendasi.

## Menjalankan lokal

Persyaratan: Python Windows 3.11+ dan Node.js 22+.

Instalasi pertama:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd ci
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m backend.manage init --email admin@sipak.local
npm.cmd run build
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Buka [localhost:8000](http://127.0.0.1:8000) dan masuk dengan akun yang dibuat. Jika menggunakan environment `.venv-win`, sesuaikan path Python.

## Konfigurasi AI dan OCR

Isi `.env` untuk lokal, atau **Variables** di Railway:

```env
AI_PROVIDER=openrouter
AI_MODEL=provider/model-id
OPENROUTER_API_KEY=api_key_openrouter
OCR_PROVIDER=fastocr
FASTOCR_API_KEY=api_key_fastocr
```

Pilih model yang mendukung structured outputs. FastOCR opsional untuk PDF scan; PDF berteks tetap bisa diproses tanpa key FastOCR. Setelah mengubah konfigurasi, restart server atau redeploy.

Pengiriman dokumen ke layanan AI/OCR memerlukan konfirmasi pengguna. Draf AI tetap ditelaah Komdis sebelum menjadi rekomendasi. Simpan API key hanya di backend.

## Panduan

- [Deploy Railway](docs/DEPLOY_RAILWAY.md)
- [Pengaturan AI](docs/AI_API.md)
- [Alur Komdis](docs/ROLES.md)
- [Regulasi](docs/REGULASI.md)
- [Build APK Android](android/README.md)
- [Detail implementasi](docs/IMPLEMENTATION.md)

**Teknologi:** React, TypeScript, FastAPI, PostgreSQL/SQLite, OpenRouter, dan FastOCR.
