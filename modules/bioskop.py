"""
Data pusat simulasi bioskop terdistribusi "Nusantara Cinema".
Tiga node server: Jakarta (Master), Makassar (Slave), Surabaya (Slave).
Setiap node menyimpan replika data film (harga & jadwal) serta denah kursi studionya.
"""
import time

BARIS = ["A", "B", "C", "D"]
KOLOM = 6  # 24 kursi per studio


def buat_denah():
    """Denah kursi kosong. None = kosong, string = nama pemesan."""
    return {f"{baris}{nomor}": None for baris in BARIS for nomor in range(1, KOLOM + 1)}


class NodeServer:
    """Merepresentasikan satu server cabang bioskop (node)."""

    def __init__(self, nama, role="Slave"):
        self.nama = nama
        self.role = role
        self.reset()

    def reset(self):
        self.film = "GARUDA DI DADAKU: REBORN"
        self.jadwal = "19:30"
        self.harga = 45000
        self.update_terakhir = 0  # timestamp penulisan harga terakhir
        self.kursi = buat_denah()
        self.log = []

    def catat(self, pesan):
        self.log.insert(0, {"waktu": time.strftime("%H:%M:%S"), "pesan": pesan})
        del self.log[20:]

    def kursi_kosong(self):
        return [k for k, v in self.kursi.items() if v is None]


NODES = {
    "jakarta": NodeServer("Jakarta", role="Master"),
    "makassar": NodeServer("Makassar"),
    "surabaya": NodeServer("Surabaya"),
}


def reset_semua():
    for node in NODES.values():
        node.reset()
