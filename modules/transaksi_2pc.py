"""
Layanan transaksi pemesanan tiket.
Setiap pemesanan diproses sebagai transaksi terdistribusi dengan
protokol Two-Phase Commit yang melibatkan tiga layanan:
  1. Layanan Pembayaran : memvalidasi & memotong saldo dompet
  2. Layanan Kursi      : memvalidasi & mengunci kursi studio
  3. Layanan Tiket      : menerbitkan e-tiket
Seluruh transaksi dilindungi Lock (mutual exclusion) sehingga dua
pemesanan yang datang bersamaan tidak bisa mengambil kursi yang sama.
"""
import random
import string
import threading
import time
from .bioskop import NODES
DOMPET = {"saldo": 200000}          # dompet digital pelanggan
RIWAYAT = []                        # log transaksi coordinator
KUNCI_TRANSAKSI = threading.Lock()  # mencegah race condition antar pemesanan
def atur_saldo(nilai):
    try:
        DOMPET["saldo"] = max(0, int(nilai))
    except (TypeError, ValueError):
        pass
def jalankan_2pc(cabang, daftar_kursi, nama):
    node = NODES[cabang]
    total = node.harga * len(daftar_kursi)
    log = []
    alasan_gagal = None
    def catat(fase, pesan, status="info"):
        log.append({"fase": fase, "pesan": pesan, "status": status})
    with KUNCI_TRANSAKSI:  # hanya satu transaksi berjalan pada satu waktu
        catat("MULAI", f"Pemesanan {len(daftar_kursi)} kursi ({', '.join(daftar_kursi)}) "
                       f"cabang {node.nama} a.n. {nama} - total Rp{total:,}")
        # ---------------- FASE 1: PREPARE (VOTING) ----------------
        catat("PREPARE", "Coordinator meminta kesiapan seluruh layanan")
        votes = {}
        # Layanan Pembayaran
        if DOMPET["saldo"] >= total:
            votes["Layanan Pembayaran"] = "YES"
            catat("PREPARE", f"Layanan Pembayaran: saldo Rp{DOMPET['saldo']:,} mencukupi -> SIAP", "yes")
        else:
            votes["Layanan Pembayaran"] = "NO"
            alasan_gagal = (f"Saldo dompet tidak mencukupi "
                            f"(butuh Rp{total:,}, saldo Rp{DOMPET['saldo']:,})")
            catat("PREPARE", f"Layanan Pembayaran: {alasan_gagal} -> TOLAK", "no")
        # Layanan Kursi
        tidak_dikenal = [k for k in daftar_kursi if k not in node.kursi]
        terisi = [k for k in daftar_kursi if node.kursi.get(k) is not None]
        if tidak_dikenal:
            votes["Layanan Kursi"] = "NO"
            alasan_gagal = alasan_gagal or f"Kursi {', '.join(tidak_dikenal)} tidak dikenal"
            catat("PREPARE", f"Layanan Kursi: kursi {', '.join(tidak_dikenal)} tidak dikenal -> TOLAK", "no")
        elif terisi:
            votes["Layanan Kursi"] = "NO"
            alasan_gagal = alasan_gagal or (f"Kursi {', '.join(terisi)} sudah dipesan orang lain, "
                                            f"silakan pilih kursi lain")
            catat("PREPARE", f"Layanan Kursi: kursi {', '.join(terisi)} sudah terisi -> TOLAK", "no")
        else:
            votes["Layanan Kursi"] = "YES"
            catat("PREPARE", "Layanan Kursi: kursi tersedia dan dikunci sementara -> SIAP", "yes")
        # Layanan Tiket
        votes["Layanan Tiket"] = "YES"
        catat("PREPARE", "Layanan Tiket: siap menerbitkan e-tiket -> SIAP", "yes")
        # ---------------- FASE 2: COMMIT / ABORT ----------------
        semua_yes = all(v == "YES" for v in votes.values())
        tiket = None
        if semua_yes:
            keputusan = "COMMIT"
            catat("COMMIT", "Seluruh layanan siap -> coordinator mengirim COMMIT", "yes")
            DOMPET["saldo"] -= total
            catat("COMMIT", f"Layanan Pembayaran: saldo dipotong Rp{total:,}, "
                            f"sisa Rp{DOMPET['saldo']:,}", "yes")
            for k in daftar_kursi:
                node.kursi[k] = nama
            catat("COMMIT", f"Layanan Kursi: kursi {', '.join(daftar_kursi)} resmi atas nama {nama}", "yes")
            tiket = "TIX-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            catat("COMMIT", f"Layanan Tiket: e-tiket {tiket} diterbitkan", "yes")
            node.catat(f"Pemesanan {', '.join(daftar_kursi)} a.n. {nama} berhasil (COMMIT)")
        else:
            keputusan = "ABORT"
            catat("ABORT", "Ada layanan yang menolak -> coordinator membatalkan seluruh transaksi", "no")
            catat("ABORT", "Semua perubahan dibatalkan: saldo utuh, kursi tetap kosong, "
                           "tiket tidak diterbitkan", "no")
            node.catat(f"Pemesanan a.n. {nama} dibatalkan (ABORT)")
    RIWAYAT.insert(0, {
        "waktu": time.strftime("%H:%M:%S"),
        "keputusan": keputusan,
        "ringkas": f"{nama} · {node.nama} · kursi {', '.join(daftar_kursi)} · Rp{total:,}",
    })
    del RIWAYAT[10:]
    return {
        "sukses": semua_yes,
        "keputusan": keputusan,
        "alasan": alasan_gagal,
        "votes": votes,
        "log": log,
        "tiket": tiket,
        "total": total,
        "kursi": daftar_kursi,
        "cabang": node.nama,
        "nama": nama,
        "saldo_akhir": DOMPET["saldo"],
    }
