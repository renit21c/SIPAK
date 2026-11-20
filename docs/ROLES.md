# Ruang kerja per peran

Identitas, navigasi, statistik, antrean, tindakan utama, notifikasi dan panduan menyesuaikan peran dari sesi backend. Tidak ada pemilih peran pada frontend yang dapat mengubah hak akses pengguna.

| Peran | Fokus dashboard | Navigasi khusus | Tindakan |
|---|---|---|---|
| Administrator | Kondisi sistem, dokumen gagal, antrean dan konfigurasi | Kelola Pengguna, Jejak Audit, Pengaturan | Kelola akun/provider, pemrosesan dan verifikasi; tidak mencatat keputusan resmi |
| Pemeriksa | Pemrosesan BAP dan dokumen yang perlu diperbaiki | Ekstraksi BAP, Analisis, Riwayat | Unggah, telusuri sumber dan masukkan fakta analisis; tidak memverifikasi/menetapkan keputusan |
| Verifikator | Antrean hasil belum terverifikasi dan progres verifikasi | Antrean Verifikasi, Pemeriksaan & Sanksi | Koreksi/verifikasi hasil, telaah klasifikasi, lengkapi pemeriksaan |
| Pejabat berwenang | Perkara siap keputusan dan keputusan yang telah dicatat | Antrean Keputusan, Pemeriksaan, Laporan | Telaah lalu catat keputusan resmi setelah syarat proses lengkap; tidak mengunggah BAP atau mengubah provider |
| Pengamat | Ringkasan perkara, hasil verifikasi dan laporan | Perkara, Laporan, Arsip, Regulasi | Baca/pratinjau/unduh; tanpa kontrol unggah, verifikasi, analisis tulis atau keputusan |

Halaman akun untuk personel nonadmin menampilkan identitas dan hak akses. Editor provider, API key, pengelolaan pengguna dan audit hanya ditampilkan untuk administrator. Halaman yang tidak tersedia untuk suatu peran menampilkan penolakan akses meskipun hash URL diketik langsung. API tetap memeriksa izin setiap tindakan; menyembunyikan tombol bukan pengganti pemeriksaan backend.

Antrean verifikasi menyaring perkara yang belum diverifikasi. Antrean keputusan menampilkan perkara berstatus `Menunggu Keputusan Berwenang` serta daftar keputusan tercatat. Tombol pencatatan keputusan hanya tersedia bagi `decide`, dengan verifikasi dan sepuluh tahap awal pemeriksaan terpenuhi; backend tetap melakukan validasi ulang. Halaman Laporan menyediakan akses PDF untuk seluruh peran yang memiliki izin baca.

Perubahan ini membedakan ruang kerja dan tindakan, bukan menerapkan pembatasan baca per perkara/kampus. Izin baca workspace yang sudah ada tetap berlaku; seluruh data yang ditampilkan berasal dari database, tanpa statistik demonstrasi.

## API key dan Git/deployment

API key yang disimpan melalui Pengaturan berada pada `.env` backend dan dipakai bersama oleh proses SIPAK pada server tersebut. Pengguna/role operasional tidak perlu memasukkan key sendiri. Git push tidak menghapus atau memindahkan file `.env` lokal. `.env`, variasi `.env.*` selain contoh, dan berkas konfigurasi sementara diabaikan oleh Git serta konteks Docker.

Key tidak ikut berpindah melalui push/clone karena tidak berada di source. Server/hosting baru harus diberi `OPENROUTER_API_KEY`, `AI_PROVIDER` dan `AI_MODEL` melalui secret/environment hosting atau `.env` privat pada server. Secret yang dipasang permanen pada layanan hosting dapat digunakan oleh deployment berikutnya tanpa mengetik ulang. Jangan memaksa `.env` masuk commit. Jika suatu secret pernah telanjur masuk commit, mengabaikan file tidak menghapus secret dari riwayat; ganti key tersebut.
