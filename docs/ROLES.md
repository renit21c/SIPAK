# Ruang kerja Komdis

SIPAK memakai satu peran operasional: `komdis`. Semua anggota menjalankan alur yang sama: unggah BAP, periksa sumber dan koreksi hasil, verifikasi, telaah ketentuan bila diperlukan, evaluasi, lalu unduh rekomendasi PDF.

Saat startup pertama setelah pembaruan ini, akun dengan peran lama otomatis dipindahkan ke Komdis. Email, hash password, identitas pengguna, sesi, perkara dan riwayat tetap dipertahankan. Perubahan tercatat pada audit. Peran lama tetap tersimpan sebagai referensi historis database, tetapi akun baru hanya dapat memakai Komdis. Tidak ada pemilih peran di form anggota. Seluruh anggota adalah pengguna internal tepercaya dan dapat mengelola konfigurasi AI serta menambah anggota; pembatasan antaranggota/perkara/kampus tidak diterapkan.

## Alur perkara

1. Unggah PDF BAP berteks. OpenRouter tetap meminta persetujuan pengiriman isi dokumen per pekerjaan.
2. AI mengekstrak informasi beserta halaman dan kutipan sumber. Keluaran tanpa sumber valid ditahan.
3. Komdis mengoreksi data melalui form dan memverifikasinya. Koreksi menambah revisi; catatan dan snapshot lama tetap ada.
4. Telaah ketentuan opsional memakai pilihan pasal, kondisi dan kutipan sumber melalui form. Kondisi belum diketahui tidak diasumsikan sebagai tidak/false.
5. Evaluasi menentukan `Perlu perbaikan` atau `Lanjutkan`. Perbaikan mengembalikan perkara ke verifikasi. Lanjutkan memerlukan BAP terverifikasi, ringkasan evaluasi, rekomendasi dan dasar pertimbangan.
6. Endpoint rekomendasi PDF hanya melayani evaluasi Lanjutkan untuk revisi dan hasil analisis terbaru. PDF memuat watermark SIPAK pada setiap halaman, evaluator, dasar pertimbangan, usulan tindak lanjut, fakta BAP, bukti, saksi, kronologi dan sumbernya.

Hasil ini merupakan rekomendasi Komdis. Pencatatan keputusan resmi tidak menjadi fitur operasional akun Komdis. Arsip keputusan dari versi sebelumnya tetap dibaca dan mengunci perubahan perkara tersebut.

Perubahan BAP, analisis baru, atau evaluasi Perlu perbaikan membuat PDF rekomendasi belum dapat diunduh sampai evaluasi diperbarui. PDF yang sudah diunduh tetap memuat identitas evaluasi dan revisi asal; berkas lama di luar aplikasi tidak dapat ditarik kembali.

## API key dan deployment

API key tersimpan pada `.env` backend dan digunakan oleh proses server bersama. `.env`, database, unggahan dan screenshot pengujian tidak masuk Git. Push tidak menghapus key lokal. Server/hosting baru memerlukan secret/environment tersendiri; secret hosting yang persisten dapat dipakai kembali pada deployment selanjutnya. Jangan memasukkan `.env` ke commit.

## Antarmuka

Login hanya menampilkan identitas SIPAK, judul Komdis dan form masuk, tanpa ilustrasi justice atau animasi. Tombol mata menampilkan/menyembunyikan password tanpa mengubah nilainya. Menu utama terdiri dari Ringkasan, Unggah BAP, Perkara, Rekomendasi, Arsip BAP, Regulasi dan Pengaturan. Pengelolaan anggota dan audit berada dalam Pengaturan.
