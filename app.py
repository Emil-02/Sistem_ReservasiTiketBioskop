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
import argparse
import threading
import webbrowser

from flask import Flask, abort, jsonify, redirect, render_template, request

from modules import bioskop, jaringan, replikasi, transaksi_2pc
app = Flask(__name__)
def akses_dari_server():
    """Admin hanya boleh diakses langsung dari komputer server."""
    return (request.remote_addr in {"127.0.0.1", "::1"}
            and (not jaringan.aktif() or jaringan.NODE_ID == "jakarta"))


def _snapshot_lokal(kunci, ambil_log=False):
    node = bioskop.NODES[kunci]
    data = {
        "kunci": kunci, "nama": node.nama, "role": node.role,
        "film": node.film, "jadwal": node.jadwal, "harga": node.harga,
        "kursi_kosong": len(node.kursi_kosong()),
        "total_kursi": len(node.kursi), "online": True,
    }
    if ambil_log:
        data["log"] = node.log[:8]
    return data


@app.context_processor
def status_akses():
    """Dipakai template untuk menyembunyikan navigasi admin dari client."""
    node_id = jaringan.NODE_ID if jaringan.aktif() else "jakarta"
    return {"boleh_admin": akses_dari_server(), "node_id": node_id,
            "nama_node": bioskop.NODES.get(node_id, bioskop.NODES["jakarta"]).nama,
            "mode_terdistribusi": jaringan.aktif()}


def snapshot_nodes(ambil_log=False):
    """Kondisi terkini seluruh server cabang."""
    if jaringan.aktif():
        hasil = []
        for kunci in bioskop.NODES:
            if jaringan.lokal(kunci):
                hasil.append(_snapshot_lokal(kunci, ambil_log))
                continue
            try:
                hasil.append(jaringan.panggil(
                    kunci, "/api/internal/status" + ("?log=1" if ambil_log else "")))
            except RuntimeError as exc:
                data = _snapshot_lokal(kunci, ambil_log)
                data.update({"online": False, "error": str(exc)})
                hasil.append(data)
        return hasil
    hasil = []
    for kunci, node in bioskop.NODES.items():
        hasil.append(_snapshot_lokal(kunci, ambil_log))
    return hasil


def _internal_diizinkan():
    return jaringan.aktif() and request.headers.get("X-Cinema-Secret") == jaringan.SECRET

# ============================== HALAMAN ==============================

@app.route("/")
def index():
    if jaringan.aktif() and jaringan.NODE_ID != "jakarta":
        # Cabang tidak perlu meminta status seluruh jaringan. Ini juga mencegah
        # kartu ganda bila ada laptop lain yang salah memakai NODE_ID serupa.
        node = _snapshot_lokal(jaringan.NODE_ID, ambil_log=True)
        return render_template("cabang.html", node=node)
    return render_template("index.html", nodes=snapshot_nodes())


@app.route("/pesan/<cabang>")
def halaman_pesan(cabang):
    if cabang not in bioskop.NODES:
        return render_template("index.html", nodes=snapshot_nodes()), 404
    if jaringan.aktif() and jaringan.NODE_ID != "jakarta" and cabang != jaringan.NODE_ID:
        return redirect(f"/pesan/{jaringan.NODE_ID}")
    return render_template("pesan.html", kunci=cabang, node=bioskop.NODES[cabang])


@app.route("/admin")
def halaman_admin():
    if not akses_dari_server():
        abort(403)
    return render_template("admin.html", saldo=transaksi_2pc.DOMPET["saldo"],
                           harga=bioskop.NODES["jakarta"].harga)


# ============================== API =================================

@app.route("/api/nodes")
def api_nodes():
    return jsonify(snapshot_nodes())


@app.route("/api/cabang/monitor")
def api_cabang_monitor():
    if not jaringan.aktif() or jaringan.NODE_ID == "jakarta":
        return jsonify({"error": "Endpoint ini khusus server cabang"}), 404
    return jsonify(_snapshot_lokal(jaringan.NODE_ID, ambil_log=True))


@app.route("/api/denah/<cabang>")
def api_denah(cabang):
    if cabang not in bioskop.NODES:
        return jsonify({"error": "Cabang tidak dikenal"}), 404
    if jaringan.aktif() and not jaringan.lokal(cabang):
        try:
            return jsonify(jaringan.panggil(cabang, "/api/internal/denah"))
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
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

    if jaringan.aktif() and not jaringan.lokal(cabang):
        try:
            hasil = jaringan.panggil(cabang, "/api/internal/booking", "POST", data)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        return jsonify(hasil)
    hasil = transaksi_2pc.jalankan_2pc(cabang, daftar_kursi, nama)
    hasil["denah"] = bioskop.NODES[cabang].kursi
    return jsonify(hasil)


# Endpoint antarnode. Jangan diekspos tanpa secret yang kuat.
@app.route("/api/internal/status")
def api_internal_status():
    if not _internal_diizinkan():
        abort(403)
    return jsonify(_snapshot_lokal(jaringan.NODE_ID, request.args.get("log") == "1"))


@app.route("/api/internal/denah")
def api_internal_denah():
    if not _internal_diizinkan():
        abort(403)
    node = bioskop.NODES[jaringan.NODE_ID]
    return jsonify({"kursi": node.kursi, "harga": node.harga,
                    "saldo": transaksi_2pc.DOMPET["saldo"]})


@app.route("/api/internal/booking", methods=["POST"])
def api_internal_booking():
    if not _internal_diizinkan():
        abort(403)
    data = request.get_json(silent=True) or {}
    if data.get("cabang") != jaringan.NODE_ID:
        return jsonify({"error": "Pemesanan dikirim ke node yang salah"}), 400
    hasil = transaksi_2pc.jalankan_2pc(
        jaringan.NODE_ID, data.get("kursi", []), (data.get("nama") or "")[:30])
    hasil["denah"] = bioskop.NODES[jaringan.NODE_ID].kursi
    return jsonify(hasil)


@app.route("/api/internal/harga", methods=["POST"])
def api_internal_harga():
    if not _internal_diizinkan():
        abort(403)
    harga = int((request.get_json(silent=True) or {}).get("harga", 0))
    node = bioskop.NODES[jaringan.NODE_ID]
    node.harga = harga
    node.catat(f"Menerima pembaruan harga Rp{harga:,} dari pusat")
    return jsonify({"ok": True})


@app.route("/api/internal/saldo", methods=["POST"])
def api_internal_saldo():
    if not _internal_diizinkan():
        abort(403)
    transaksi_2pc.atur_saldo((request.get_json(silent=True) or {}).get("saldo"))
    return jsonify({"saldo": transaksi_2pc.DOMPET["saldo"]})


@app.route("/api/internal/reset", methods=["POST"])
def api_internal_reset():
    if not _internal_diizinkan():
        abort(403)
    bioskop.NODES[jaringan.NODE_ID].reset()
    transaksi_2pc.DOMPET["saldo"] = 200000
    transaksi_2pc.RIWAYAT.clear()
    return jsonify({"ok": True})


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

    if jaringan.aktif():
        lokal = bioskop.NODES[jaringan.NODE_ID]
        lokal.harga = harga
        lokal.catat(f"Harga tiket diubah menjadi Rp{harga:,} (server pusat)")
        langkah = ["Server pusat Jakarta menyimpan harga baru"]
        for cabang in ("makassar", "surabaya"):
            try:
                jaringan.panggil(cabang, "/api/internal/harga", "POST", {"harga": harga})
                langkah.append(f"Cabang {cabang.title()} menerima pembaruan")
            except RuntimeError as exc:
                langkah.append(str(exc))
    elif data.get("mode") == "sync":
        langkah = replikasi.update_harga_sync(harga)
    else:
        langkah = replikasi.update_harga_async(harga)
    return jsonify({"langkah": langkah})


@app.route("/api/admin/saldo", methods=["POST"])
def api_admin_saldo():
    if not akses_dari_server():
        abort(403)
    transaksi_2pc.atur_saldo(request.json.get("saldo"))
    if jaringan.aktif():
        for cabang in ("makassar", "surabaya"):
            try:
                jaringan.panggil(cabang, "/api/internal/saldo", "POST",
                                  {"saldo": transaksi_2pc.DOMPET["saldo"]})
            except RuntimeError:
                pass
    return jsonify({"saldo": transaksi_2pc.DOMPET["saldo"]})


@app.route("/api/admin/reset", methods=["POST"])
def api_admin_reset():
    if not akses_dari_server():
        abort(403)
    bioskop.reset_semua()
    replikasi.REPLICATION_LOG.clear()
    transaksi_2pc.DOMPET["saldo"] = 200000
    transaksi_2pc.RIWAYAT.clear()
    if jaringan.aktif():
        for cabang in ("makassar", "surabaya"):
            try:
                jaringan.panggil(cabang, "/api/internal/reset", "POST", {})
            except RuntimeError:
                pass
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
    parser = argparse.ArgumentParser(description="Server node Nusantara Cinema")
    parser.add_argument("--node", choices=bioskop.NODES, help="jakarta/makassar/surabaya")
    parser.add_argument("--port", type=int, default=5001)
    args = parser.parse_args()
    if args.node:
        jaringan.NODE_ID = args.node
    if args.node and not jaringan.aktif():
        raise SystemExit("network_config.json belum ada/valid. Salin dari file contoh.")
    halaman_awal = "/admin" if (not jaringan.aktif() or jaringan.NODE_ID == "jakarta") else "/"
    server_url = f"http://127.0.0.1:{args.port}{halaman_awal}"
    print("=" * 60)
    print("  NUSANTARA CINEMA - Reservasi Tiket Bioskop")
    print(f"  Membuka browser: {server_url}")
    print("=" * 60)

    # Beri Flask waktu untuk mulai sebelum halaman dibuka. Reloader dimatikan
    # agar browser tidak terbuka dua kali saat menjalankan mode debug.
    threading.Timer(1.0, lambda: webbrowser.open(server_url)).start()
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=args.port, threaded=True)
