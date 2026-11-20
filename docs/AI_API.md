# AI melalui API OpenRouter

Model dapat dijalankan di layanan OpenRouter, tanpa instalasi Ollama atau GPU pada komputer SIPAK. Backend aplikasi dan penyimpanan dokumen tetap berjalan pada server SIPAK; pemilihan model cloud tidak otomatis mempublikasikan website.

## Pengaturan lewat aplikasi

1. Restart backend setelah pembaruan kode, lalu refresh browser.
2. Masuk sebagai anggota Komdis dan buka **Pengaturan → Provider AI**.
3. Pilih **OpenRouter · API Cloud**.
4. Isi Model ID dari katalog OpenRouter yang mendukung `structured_outputs`, serta API key dari akun pengguna sendiri.
5. Simpan, lalu pilih **Uji Koneksi**. Uji ini hanya memeriksa metadata key dan katalog model, tanpa mengirim isi BAP atau menjalankan inferensi berbayar. Daftar model mendukung schema kemudian tersedia pada saran input Model ID. Dukungan endpoint dan aturan privasi akun masih dapat memengaruhi ketersediaan model.

Field key selalu kosong setelah disimpan. Placeholder hanya menunjukkan apakah key telah tersedia. Kosongkan saat menyimpan untuk mempertahankan key, atau centang penghapusan untuk menghapus key. Tidak perlu mengirim API key melalui chat.

Alternatif konfigurasi pada `.env` server:

```dotenv
AI_PROVIDER=openrouter
AI_MODEL=provider/model-id
OPENROUTER_API_KEY=isi_key_di_server
AI_TIMEOUT_SECONDS=180
```

Gunakan ID model nyata dari katalog, bukan teks placeholder. Bila konfigurasi ditentukan oleh environment layanan/container, environment tersebut memiliki prioritas saat restart; sinkronkan nilainya dengan `.env`. UI mengubah konfigurasi proses yang sedang berjalan dan menyimpan `.env`. Jalankan satu worker, sesuai model pemrosesan dokumen versi ini. Perubahan UI tidak menyinkronkan konfigurasi lintas beberapa proses/replica.

## Pemrosesan dan persetujuan dokumen

- PDF asli disimpan di penyimpanan privat SIPAK. PyMuPDF mengambil teks per halaman; hanya teks chunk yang dikirim ke endpoint `https://openrouter.ai/api/v1/chat/completions`.
- Dialog menyebutkan nama dokumen, model, tujuan dan ruang lingkup data (termasuk identitas, keterangan dan bukti). Persetujuan wajib untuk tiap unggah/pemrosesan ulang menggunakan API eksternal. Memilih provider atau menyimpan key bukan persetujuan menyeluruh untuk isi BAP.
- Backend menolak permintaan cloud tanpa persetujuan dan memeriksa kecocokan provider/model yang dikonfirmasi. Setiap pekerjaan menyimpan snapshot konfigurasi dalam memori agar pergantian provider saat pekerjaan berjalan tidak mengubah tujuan tanpa persetujuan baru. Kunci tidak disimpan pada catatan pekerjaan/audit.
- Permintaan memakai JSON Schema strict; Pydantic dan pencocokan kutipan tetap memvalidasi hasil. Data dokumen diperlakukan sebagai masukan tidak tepercaya. Analisis regulasi dan keputusan resmi tetap terpisah dari model.
- Tidak ada fallback otomatis ke provider/model lain dan tidak ada pengulangan request berbayar secara diam-diam. Kesalahan autentikasi, saldo, rate limit, timeout, output terpotong atau JSON invalid menghasilkan status gagal dengan pesan yang tidak memuat isi respons sensitif.

Routing OpenRouter menyertakan `require_parameters: true`, `data_collection: deny`, `zdr: true`, dan `allow_fallbacks: false`. Opsi ZDR mengikuti kebijakan serta pilihan akun/guardrail OpenRouter dan dapat memiliki pengecualian; ini bukan jaminan mutlak bahwa data tidak pernah disimpan. Periksa kebijakan akun/provider sesuai kewenangan institusi. Tidak ada plugin web/PDF atau penyedia tambahan yang diaktifkan aplikasi.

Key disimpan pada `.env` backend, tidak pada frontend bundle/localStorage dan tidak dikembalikan melalui API. `.env` tidak terenkripsi oleh aplikasi; lindungi akses OS/volume, gunakan HTTPS saat aplikasi diakses melalui jaringan, dan jangan memasukkan `.env` ke Git. Penggunaan API mengikuti harga dan kredit akun/model pengguna. Pengujian implementasi menggunakan transport tiruan; panggilan API asli memerlukan key pengguna dan belum diuji pada sesi pengembangan.

## Mode Ollama opsional

Pilih Ollama pada Pengaturan, isi model yang telah diunduh lalu simpan. Atau tetapkan `AI_PROVIDER=ollama` dan `OLLAMA_MODEL=...` pada server. Endpoint Ollama tetap dibatasi ke loopback/host Docker `ollama`. Mode ini tidak memerlukan persetujuan pengiriman ke pihak ketiga.

## Referensi implementasi

- [Structured outputs OpenRouter](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Provider routing dan kebijakan data](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Kebijakan ZDR](https://openrouter.ai/docs/guides/features/zdr)
- [Pemeriksaan metadata API key](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key)
