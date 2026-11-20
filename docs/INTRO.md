# Intro SIPAK

Intro menggunakan aset lokal `public/intro/sipak-intro.mp4` (720p, H.264/AAC, 5,2 detik) dan `poster.jpg`. Tidak ada layanan video eksternal atau pengiriman data pengguna. Versi ekspor 1080p tersedia di folder artifacts lokal, tidak ikut commit.

Palu dan alas dibuat sebagai bentuk putih flat 2D di atas warna navy SIPAK. Tidak ada garis dekoratif di bawah judul. Dua ketukan memakai suara sintetis dengan resonansi rendah dan gema pendek, dengan puncak audio di bawah clipping. Akhir video memudar ke navy; overlay web memudar selama 800 ms sambil halaman aplikasi muncul.

Pengguna memilih Mulai untuk pemutaran bersuara, atau Lewati untuk langsung membuka aplikasi. Saat diputar, suara dapat dibisukan. Browser membatasi autoplay bersuara; playback dipanggil langsung dari klik pengguna sesuai [kebijakan Chrome](https://developer.chrome.com/blog/autoplay/).

Intro berjalan sekali per sesi tab melalui sessionStorage. Navigasi internal dan refresh tidak mengulanginya. Tab baru dapat menampilkan intro lagi. Preferensi reduced motion melewati intro. Kegagalan media dan timeout pemutaran membuka aplikasi; konten aplikasi tidak dapat difokuskan selama intro aktif. Escape melewati intro. Setelah transisi, fokus berpindah ke kontrol awal halaman.

## Membuat ulang video

Generator asli ada di `scripts/render_intro.py`; tidak dibutuhkan saat menjalankan backend atau build frontend. Di Windows, gunakan Python yang kompatibel dan font Arial/Segoe UI bawaan:

```powershell
.\.venv-win\Scripts\python.exe -m pip install --target tmp/intro-tools Pillow imageio-ffmpeg
.\.venv-win\Scripts\python.exe scripts/render_intro.py
npm.cmd run build
```

Generator menghasilkan ekspor 1080p/720p, WAV, dan poster di `artifacts/sipak-intro-white`, lalu menyalin video web dan poster ke `public/intro`. Aset ini harus ikut commit ketika diperbarui. Folder artifacts dan tmp tetap diabaikan Git. Tidak mengubah .env atau konfigurasi AI.
