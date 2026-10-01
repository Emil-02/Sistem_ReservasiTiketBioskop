"""Komunikasi HTTP antarnode untuk mode tiga laptop."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


NODE_ID = os.environ.get("CINEMA_NODE", "").strip().lower()
CONFIG_PATH = Path(os.environ.get("CINEMA_CONFIG", "network_config.json"))


def _muat_config():
    if not CONFIG_PATH.exists():
        return {"secret": "", "nodes": {}}
    with CONFIG_PATH.open(encoding="utf-8") as berkas:
        return json.load(berkas)


CONFIG = _muat_config()
NODES = CONFIG.get("nodes", {})
SECRET = CONFIG.get("secret", "")


def aktif():
    return NODE_ID in NODES and bool(SECRET)


def lokal(cabang):
    return not aktif() or cabang == NODE_ID


def panggil(cabang, path, method="GET", data=None, timeout=4):
    """Memanggil API internal node dan mengembalikan JSON."""
    if cabang not in NODES:
        raise RuntimeError(f"Alamat node {cabang} belum dikonfigurasi")
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = Request(
        NODES[cabang].rstrip("/") + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "X-Cinema-Secret": SECRET},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            pesan = json.loads(exc.read().decode("utf-8")).get("error")
        except Exception:
            pesan = None
        raise RuntimeError(pesan or f"Node {cabang} mengembalikan HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Node {cabang} tidak dapat dihubungi: {exc}") from exc

