# 🎬 Nusantara Cinema — Sistem Reservasi Tiket Bioskop Terdistribusi

Aplikasi web simulasi **sistem reservasi tiket bioskop terdistribusi** yang dibangun menggunakan **Python Flask**. Sistem ini mensimulasikan jaringan bioskop dengan **tiga server cabang** — Jakarta (pusat), Makassar, dan Surabaya — lengkap dengan mekanisme **replikasi data Master-Slave** dan **transaksi terdistribusi Two-Phase Commit (2PC)**.

## 📋 Deskripsi

Nusantara Cinema adalah proyek simulasi konsep **Sistem Terdistribusi** yang mencakup:

- **Replikasi Data (Master-Slave)** — Perubahan harga tiket dilakukan di server pusat (Jakarta), lalu disebarkan ke server cabang melalui _replication log_ dengan dua mode:
  - 🔄 **Sync (Serentak)** — pusat menunggu konfirmasi seluruh cabang, data langsung seragam.
  - ⏳ **Async (Bertahap)** — cabang diperbarui mengikuti latensi jaringan masing-masing (Makassar ±4 detik, Surabaya ±8 detik).
- **Transaksi Terdistribusi (Two-Phase Commit)** — Setiap pemesanan tiket diproses melalui protokol 2PC yang melibatkan tiga layanan:
  1. 💳 **Layanan Pembayaran** — memvalidasi & memotong saldo dompet digital.
  2. 💺 **Layanan Kursi** — memvalidasi & mengunci kursi studio.
  3. 🎟️ **Layanan Tiket** — menerbitkan e-tiket.
- **Mutual Exclusion (Lock)** — Transaksi dilindungi `threading.Lock` sehingga dua pemesanan bersamaan tidak dapat mengambil kursi yang sama (mencegah _race condition_).

## ✨ Fitur

| Fitur                     | Keterangan                                                          |
| ------------------------- | ------------------------------------------------------------------- |
| 🏢 Multi-cabang           | 3 node server: Jakarta (Master), Makassar (Slave), Surabaya (Slave) |
| 💺 Denah kursi interaktif | 24 kursi per studio (baris A–D, kolom 1–6)                          |
| 🛒 Pemesanan tiket        | Maksimal 6 kursi per transaksi dengan protokol 2PC                  |
| 📊 Panel admin            | Ubah harga tiket (sync/async), atur saldo dompet, reset sistem      |
| 📡 Monitor real-time      | Pantau log tiap node, replication log, dan riwayat transaksi        |
| 🔒 Anti race condition    | Lock transaksi menjamin konsistensi data kursi                      |

## 🛠️ Teknologi

- **Python 3.x**
- **Flask** — web framework
- **HTML / CSS / JavaScript** — antarmuka pengguna
- **Threading** — simulasi latensi replikasi & lock transaksi

## 📁 Struktur Proyek

```
Sistem_ReservasiTikketBioskop/
├── app.py                  # Entry point aplikasi Flask (routing & API)
├── requirements.txt        # Daftar dependensi
├── modules/
│   ├── __init__.py
│   ├── bioskop.py          # Data node server & denah kursi
│   ├── replikasi.py        # Replikasi harga Master-Slave (sync/async)
│   └── transaksi_2pc.py    # Transaksi pemesanan dengan Two-Phase Commit
├── static/
│   └── style.css           # Stylesheet
└── templates/
    ├── base.html           # Template dasar
    ├── index.html          # Halaman utama (daftar cabang)
    ├── pesan.html          # Halaman pemesanan kursi
    └── admin.html          # Panel admin & monitoring
```

## 🚀 Cara Menjalankan

### 1. Clone repository

```bash
git clone https://github.com/Emil-02/Sistem_ReservasiTiketBioskop.git
cd Sistem_ReservasiTiketBioskop
```

### 2. (Opsional) Buat virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Install dependensi

```bash
pip install -r requirements.txt
```

### 4. Jalankan aplikasi

```bash
python app.py
```

### 5. Buka di browser

```
http://127.0.0.1:5001
```

## 🖥️ Halaman Aplikasi

| URL               | Halaman                                              |
| ----------------- | ---------------------------------------------------- |
| `/`               | Halaman utama — daftar cabang & status server        |
| `/pesan/<cabang>` | Pemesanan kursi (jakarta / makassar / surabaya)      |
| `/admin`          | Panel admin — ubah harga, atur saldo, monitor sistem |

## 🔌 API Endpoint

| Method | Endpoint              | Keterangan                                     |
| ------ | --------------------- | ---------------------------------------------- |
| GET    | `/api/nodes`          | Status seluruh node server                     |
| GET    | `/api/denah/<cabang>` | Denah kursi & harga cabang                     |
| POST   | `/api/booking`        | Proses pemesanan tiket (2PC)                   |
| POST   | `/api/admin/harga`    | Ubah harga tiket (mode sync/async)             |
| POST   | `/api/admin/saldo`    | Atur saldo dompet digital                      |
| POST   | `/api/admin/reset`    | Reset seluruh data sistem                      |
| GET    | `/api/admin/monitor`  | Data monitoring (log node, replikasi, riwayat) |

## 👥 Tim Pengembang

| Nama             | NIM   | Peran   |
| ---------------- | ----- | ------- |
| [Nama Anggota 1] | [NIM] | [Peran] |
| [Nama Anggota 2] | [NIM] | [Peran] |
| [Nama Anggota 3] | [NIM] | [Peran] |
| [Nama Anggota 4] | [NIM] | [Peran] |

## 📄 Lisensi

Proyek ini dibuat untuk keperluan tugas mata kuliah **Sistem Terdistribusi**.

## Menjalankan pada 3 Laptop (Mode Terdistribusi Nyata)

Ketiga laptop harus berada pada Wi-Fi/hotspot yang sama dan masing-masing
menjalankan salinan folder proyek ini. Jakarta bertindak sebagai server pusat,
sedangkan Makassar dan Surabaya menjadi server cabang.

1. Cari IPv4 setiap laptop dengan `ipconfig`.
2. Salin `network_config.example.json` menjadi `network_config.json` pada
   ketiga laptop.
3. Isi alamat IP ketiga laptop dan gunakan nilai `secret` yang sama persis.
4. Izinkan Python/port 5001 pada Windows Firewall ketika diminta.
5. Jalankan perintah berikut pada laptop yang sesuai:

```powershell
# Laptop pusat
python app.py --node jakarta --port 5001

# Laptop cabang Makassar
python app.py --node makassar --port 5001

# Laptop cabang Surabaya
python app.py --node surabaya --port 5001
```

Pengguna membuka alamat laptop pusat, misalnya
`http://192.168.1.10:5001`. Pemesanan Makassar dan Surabaya akan diteruskan
melalui HTTP ke server cabang pemilik kursi. Panel admin hanya tersedia secara
lokal pada laptop pusat melalui `http://127.0.0.1:5001/admin`.

Untuk memeriksa koneksi dari laptop pusat:

```powershell
Test-NetConnection 192.168.1.11 -Port 5001
Test-NetConnection 192.168.1.12 -Port 5001
```

Tanpa argumen `--node`, aplikasi tetap berjalan dalam mode simulasi satu laptop
seperti versi sebelumnya.
