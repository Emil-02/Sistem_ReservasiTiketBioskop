import unittest
from unittest.mock import patch

import app as aplikasi
from modules import jaringan


class DistributedModeTest(unittest.TestCase):
    def setUp(self):
        self.node_lama = jaringan.NODE_ID
        self.nodes_lama = jaringan.NODES
        self.secret_lama = jaringan.SECRET
        jaringan.NODE_ID = "jakarta"
        jaringan.NODES = {
            "jakarta": "http://127.0.0.1:5001",
            "makassar": "http://127.0.0.1:5002",
            "surabaya": "http://127.0.0.1:5003",
        }
        jaringan.SECRET = "test-secret"
        aplikasi.app.config["TESTING"] = True
        self.client = aplikasi.app.test_client()

    def tearDown(self):
        jaringan.NODE_ID = self.node_lama
        jaringan.NODES = self.nodes_lama
        jaringan.SECRET = self.secret_lama

    def test_endpoint_internal_ditolak_tanpa_secret(self):
        self.assertEqual(self.client.get("/api/internal/status").status_code, 403)

    def test_endpoint_internal_mengembalikan_node_lokal(self):
        response = self.client.get(
            "/api/internal/status", headers={"X-Cinema-Secret": "test-secret"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["kunci"], "jakarta")

    @patch("app.jaringan.panggil")
    def test_booking_cabang_diteruskan_ke_laptop_cabang(self, panggil):
        panggil.return_value = {"sukses": True, "tiket": "TIX-TEST"}
        response = self.client.post("/api/booking", json={
            "cabang": "makassar", "kursi": ["A1"], "nama": "Budi"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["sukses"])
        panggil.assert_called_once()
        self.assertEqual(panggil.call_args.args[:3],
                         ("makassar", "/api/internal/booking", "POST"))


if __name__ == "__main__":
    unittest.main()
