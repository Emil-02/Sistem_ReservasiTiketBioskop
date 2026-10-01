"""
NUSANTARA CINEMA - Aplikasi Reservasi Tiket Bioskop
====================================================
Jaringan bioskop dengan tiga server cabang: Jakarta (pusat),
Makassar, dan Surabaya. Data harga direplikasi dari server pusat
ke cabang, dan setiap pemesanan diproses sebagai transaksi
terdistribusi (Two-Phase Commit) yang melibatkan layanan
pembayaran, kursi, dan penerbitan tiket.

Jalankan: python app.py (browser server akan terbuka otomatis)
"""
import threading
import webbrowser

from flask import Flask, abort, jsonify, render_template, request

from modules import bioskop, replikasi, transaksi_2pc
app = Flask(__name__)
def akses_dari_server():
    """Admin hanya boleh diakses langsung dari komputer server."""
    return request.remote_addr in {"127.0.0.1", "::1"}


@app.context_processor
def status_akses():
    """Dipakai template untuk menyembunyikan navigasi admin dari client."""
    return {"boleh_admin": akses_dari_server()}


def snapshot_nodes(ambil_log=False):
    """Kondisi terkini seluruh server cabang."""
    hasil = []
    for kunci, node in bioskop.NODES.items():
        data = {
            "kunci": kunci,
            "nama": node.nama,
            "role": node.role,
            "film": node.film,
            "jadwal": node.jadwal,
            "harga": node.harga,
            "kursi_kosong": len(node.kursi_kosong()),
            "total_kursi": len(node.kursi),
        }
        if ambil_log:
            data["log"] = node.log[:8]
        hasil.append(data)
    return hasil

# ============================== HALAMAN ==============================

@app.route("/")
def index():
    return render_template("index.html", nodes=snapshot_nodes())


@app.route("/pesan/<cabang>")
def halaman_pesan(cabang):
    if cabang not in bioskop.NODES:
        return render_template("index.html", nodes=snapshot_nodes()), 404
    return render_template("pesan.html", kunci=cabang, node=bioskop.NODES[cabang])


@app.route("/admin")
def halaman_admin():
    if not akses_dari_server():
        abort(403)
    return render_template("admin.html", saldo=transaksi_2pc.DOMPET["saldo"])


# ============================== API =================================

@app.route("/api/nodes")
def api_nodes():
    return jsonify(snapshot_nodes())


@app.route("/api/denah/<cabang>")
def api_denah(cabang):
    if cabang not in bioskop.NODES:
        return jsonify({"error": "Cabang tidak dikenal"}), 404
    node = bioskop.NODES[cabang]
    return jsonify({"kursi": node.kursi, "harga": node.harga,
                    "saldo": transaksi_2pc.DOMPET["saldo"]})


@app.route("/api/booking", methods=["POST"])
def api_booking():
    data = request.json
    cabang = data.get("cabang")
    daftar_kursi = data.get("kursi", [])
    nama = (data.get("nama") or "").strip()[:30]

    if cabang not in bioskop.NODES:
        return jsonify({"error": "Cabang tidak dikenal"}), 404
    if not nama:
        return jsonify({"error": "Nama pemesan wajib diisi"}), 400
    if not daftar_kursi:
        return jsonify({"error": "Pilih minimal satu kursi terlebih dahulu"}), 400
    if len(daftar_kursi) > 6:
        return jsonify({"error": "Maksimal 6 kursi per transaksi"}), 400

    hasil = transaksi_2pc.jalankan_2pc(cabang, daftar_kursi, nama)
    hasil["denah"] = bioskop.NODES[cabang].kursi
    return jsonify(hasil)


# ---- Panel admin ----

@app.route("/api/admin/harga", methods=["POST"])
def api_admin_harga():
    if not akses_dari_server():
        abort(403)
    data = request.json
    try:
        harga = int(data.get("harga", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Harga harus berupa angka"}), 400
    if not 1000 <= harga <= 1000000:
        return jsonify({"error": "Harga harus antara Rp1.000 - Rp1.000.000"}), 400

    if data.get("mode") == "sync":
        langkah = replikasi.update_harga_sync(harga)
    else:
        langkah = replikasi.update_harga_async(harga)
    return jsonify({"langkah": langkah})


@app.route("/api/admin/saldo", methods=["POST"])
def api_admin_saldo():
    if not akses_dari_server():
        abort(403)
    transaksi_2pc.atur_saldo(request.json.get("saldo"))
    return jsonify({"saldo": transaksi_2pc.DOMPET["saldo"]})


@app.route("/api/admin/reset", methods=["POST"])
def api_admin_reset():
    if not akses_dari_server():
        abort(403)
    bioskop.reset_semua()
    replikasi.REPLICATION_LOG.clear()
    transaksi_2pc.DOMPET["saldo"] = 200000
    transaksi_2pc.RIWAYAT.clear()
    return jsonify({"ok": True})


@app.route("/api/admin/monitor")
def api_admin_monitor():
    if not akses_dari_server():
        abort(403)
    return jsonify({
        "nodes": snapshot_nodes(ambil_log=True),
        "replication_log": replikasi.REPLICATION_LOG,
        "riwayat": transaksi_2pc.RIWAYAT,
        "saldo": transaksi_2pc.DOMPET["saldo"],
    })


if __name__ == "__main__":
    server_url = "http://127.0.0.1:5001/admin"
    print("=" * 60)
    print("  NUSANTARA CINEMA - Reservasi Tiket Bioskop")
    print(f"  Membuka browser: {server_url}")
    print("=" * 60)

    # Beri Flask waktu untuk mulai sebelum halaman dibuka. Reloader dimatikan
    # agar browser tidak terbuka dua kali saat menjalankan mode debug.
    threading.Timer(1.0, lambda: webbrowser.open(server_url)).start()
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5001)
