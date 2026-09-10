"""Emergent object storage client + local temp cache for PDF processing.

Object storage is the source of truth. Because PyMuPDF needs a real file path,
we cache downloads under a temp dir; the cache is disposable.
"""
import os
import tempfile
from pathlib import Path

import requests

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "siujang-docmgr"

CACHE_DIR = Path(tempfile.gettempdir()) / "siujang_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    emergent_key = os.environ.get("EMERGENT_LLM_KEY")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": emergent_key}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str = "application/pdf") -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=180,
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=180,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> bytes:
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key}, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key}, timeout=120)
    resp.raise_for_status()
    return resp.content


def local_cache_path(path: str) -> str:
    """Ensure the object is present on local disk (temp cache) and return the path."""
    safe = path.replace("/", "__")
    local = CACHE_DIR / safe
    if not local.exists() or local.stat().st_size == 0:
        data = get_object(path)
        local.write_bytes(data)
    return str(local)


def upload_from_path(path: str, local_file: str, content_type: str = "application/pdf") -> dict:
    data = Path(local_file).read_bytes()
    return put_object(path, data, content_type)
