"""
Layanan sinkronisasi data antar cabang (replikasi Master-Slave).
Perubahan harga dilakukan di server pusat (Jakarta) lalu
disebarkan ke server cabang melalui replication log.
Dua mode penyebaran:
  - sync : pusat menunggu konfirmasi seluruh cabang, data langsung seragam
  - async: cabang diperbarui bertahap mengikuti latensi jaringan masing-masing
"""
import threading
import time

from .bioskop import NODES

REPLICATION_LOG = []  # catatan perubahan data di server pusat
LAG_MAKASSAR = 4      # detik
LAG_SURABAYA = 8      # detik


def _tulis_log(operasi):
    REPLICATION_LOG.insert(0, {"waktu": time.strftime("%H:%M:%S"), "operasi": operasi})
    del REPLICATION_LOG[15:]


def update_harga_sync(harga_baru):
    """Mode serentak: pusat menunggu konfirmasi seluruh cabang."""
    master = NODES["jakarta"]
    master.harga = harga_baru
    master.update_terakhir = time.time()
    master.catat(f"Harga tiket diubah menjadi Rp{harga_baru:,} (server pusat)")
    _tulis_log(f"UPDATE harga = Rp{harga_baru:,} · mode serentak")

    for kunci in ("makassar", "surabaya"):
        node = NODES[kunci]
        node.harga = harga_baru
        node.update_terakhir = time.time()
        node.catat(f"Menerima pembaruan harga Rp{harga_baru:,} dari pusat")

    return [
        "Server pusat Jakarta menyimpan harga baru",
        "Seluruh cabang menerima pembaruan dan mengirim konfirmasi",
        "Harga kini seragam di semua cabang",
    ]


def update_harga_async(harga_baru):
    """Mode bertahap: pusat selesai duluan, cabang menyusul sesuai latensi."""
    master = NODES["jakarta"]
    master.harga = harga_baru
    master.update_terakhir = time.time()
    master.catat(f"Harga tiket diubah menjadi Rp{harga_baru:,} (server pusat)")
    _tulis_log(f"UPDATE harga = Rp{harga_baru:,} · mode bertahap")

    def terapkan_nanti(kunci, delay):
        time.sleep(delay)
        node = NODES[kunci]
        node.harga = harga_baru
        node.update_terakhir = time.time()
        node.catat(f"Pembaruan harga Rp{harga_baru:,} tiba setelah {delay} detik")

    threading.Thread(target=terapkan_nanti, args=("makassar", LAG_MAKASSAR), daemon=True).start()
    threading.Thread(target=terapkan_nanti, args=("surabaya", LAG_SURABAYA), daemon=True).start()

    return [
        "Server pusat Jakarta menyimpan harga baru",
        f"Cabang Makassar akan menerima pembaruan ±{LAG_MAKASSAR} detik lagi",
        f"Cabang Surabaya akan menerima pembaruan ±{LAG_SURABAYA} detik lagi",
    ]
