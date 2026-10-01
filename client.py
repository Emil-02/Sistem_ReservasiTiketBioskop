"""Client launcher untuk Sistem Reservasi Tiket Bioskop.

Jalankan di laptop client dengan:
    python client.py

Ubah SERVER_IP jika alamat IP laptop server berubah.
"""

import socket
import sys
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen


# Isi dengan alamat IPv4 laptop yang menjalankan app.py.
SERVER_IP = "192.168.10.125"
SERVER_PORT = 5001
SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}"


def main():
    print(f"Menghubungkan ke server: {SERVER_URL}")
    try:
        with urlopen(SERVER_URL, timeout=5) as response:
            if response.status >= 400:
                raise RuntimeError(f"Server mengembalikan HTTP {response.status}")
    except (URLError, TimeoutError, socket.timeout, OSError, RuntimeError) as exc:
        print("Gagal terhubung ke server.")
        print("Pastikan server sudah menjalankan 'python app.py', berada di Wi-Fi yang sama,")
        print("dan Windows Firewall mengizinkan port 5001.")
        print(f"Detail: {exc}")
        sys.exit(1)

    print("Terhubung. Membuka aplikasi di browser...")
    webbrowser.open(SERVER_URL)


if __name__ == "__main__":
    main()
