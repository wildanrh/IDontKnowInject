"""SIUjang Document Manager - backend integration tests."""
import io
import os
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
    open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip().rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def sample_project():
    r = requests.post(f"{API}/projects/sample", timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "id" in data and "filename" in data and "pages" in data and "size_bytes" in data
    assert data["pages"] >= 10
    return data


@pytest.fixture(scope="module")
def analyzed_project(sample_project):
    pid = sample_project["id"]
    r = requests.post(f"{API}/projects/{pid}/analyze", timeout=180)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "analyzed"
    assert isinstance(data["documents"], list) and len(data["documents"]) >= 3
    assert isinstance(data["metadata"], dict)
    return data


# ---------- sample ----------
def test_sample_endpoint(sample_project):
    assert sample_project["status"] == "uploaded"


# ---------- analyze / content-aware ----------
def test_analyze_dynamic_ranges(analyzed_project):
    docs = analyzed_project["documents"]
    # Not one-doc-per-page
    assert len(docs) < analyzed_project["pages"]
    # At least one multi-page doc
    multi = [d for d in docs if d["end_page"] > d["start_page"]]
    assert multi, "Expected at least one multi-page document"
    # All confidences numeric
    for d in docs:
        assert 0 <= d["confidence"] <= 100
        assert d["status"] in ("ready", "review", "low")
        assert isinstance(d["required"], bool)


def test_analyze_spesifikasi_mesin_multi_page(analyzed_project):
    docs = analyzed_project["documents"]
    mesin = [d for d in docs if "Mesin" in d["title"]]
    assert mesin, f"Spesifikasi Teknik Mesin not detected. Titles: {[d['title'] for d in docs]}"
    assert mesin[0]["end_page"] > mesin[0]["start_page"], "Mesin should span multiple pages"


def test_metadata_pltd(analyzed_project):
    meta = analyzed_project["metadata"]
    assert meta.get("jenis_pembangkit") == "PLTD"


# ---------- update docs + corrections ----------
def test_update_documents_records_correction(analyzed_project):
    pid = analyzed_project["id"]
    docs = [dict(d) for d in analyzed_project["documents"]]
    original_title = docs[1]["title"]
    docs[1]["title"] = "TEST_" + original_title
    docs[1]["end_page"] = min(analyzed_project["pages"], docs[1]["end_page"] + 0)  # no bounds change
    docs[1]["start_page"] = docs[1]["start_page"]
    # Actually change end_page to force correction if possible
    if docs[1]["end_page"] + 1 <= analyzed_project["pages"] and (len(docs) <= 2 or docs[1]["end_page"] + 1 < docs[2]["start_page"]):
        docs[1]["end_page"] += 1

    r = requests.put(f"{API}/projects/{pid}/documents", json={"documents": docs}, timeout=30)
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["documents"][1]["title"].startswith("TEST_")

    c = requests.get(f"{API}/corrections", timeout=30)
    assert c.status_code == 200
    corrections = c.json()
    assert any(x["project_id"] == pid for x in corrections)


# ---------- split + outputs + zip ----------
def test_split_and_outputs(analyzed_project):
    pid = analyzed_project["id"]
    r = requests.post(f"{API}/projects/{pid}/split", timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "split"
    outputs = data.get("outputs", [])
    assert outputs, "No outputs generated"

    # Get first output pdf
    first = outputs[0]
    resp = requests.get(f"{API}/projects/{pid}/output/{first['filename']}", timeout=30)
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    assert resp.content[:4] == b"%PDF"


def test_download_zip(analyzed_project):
    pid = analyzed_project["id"]
    r = requests.get(f"{API}/projects/{pid}/download-zip", timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/zip")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert names, "ZIP is empty"


# ---------- page image + original pdf ----------
def test_page_image(sample_project):
    pid = sample_project["id"]
    r = requests.get(f"{API}/projects/{pid}/page/1", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/png")
    assert r.content[:8].startswith(b"\x89PNG")


def test_original_pdf(sample_project):
    pid = sample_project["id"]
    r = requests.get(f"{API}/projects/{pid}/original.pdf", timeout=30)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


# ---------- templates CRUD ----------
def test_templates_seeded():
    r = requests.get(f"{API}/templates", timeout=30)
    assert r.status_code == 200
    tpls = r.json()
    names = {t["name"] for t in tpls}
    for expected in ["LHPP PLTD", "LHPP PLTU", "LHPP PLTS"]:
        assert expected in names, f"Missing seeded template {expected}. Got {names}"


def test_templates_crud():
    payload = {"id": "", "name": "TEST_Template", "documents": ["Doc A", "Doc B"], "created_at": ""}
    # Let backend create id
    r = requests.post(f"{API}/templates", json={"name": "TEST_Template", "documents": ["Doc A", "Doc B"]}, timeout=30)
    assert r.status_code == 200, r.text
    tpl = r.json()
    tid = tpl["id"]
    # Update
    r = requests.put(f"{API}/templates/{tid}", json={"id": tid, "name": "TEST_Template2", "documents": ["X"]}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Template2"
    # Delete
    r = requests.delete(f"{API}/templates/{tid}", timeout=30)
    assert r.status_code == 200
    # Confirm gone
    r = requests.get(f"{API}/templates", timeout=30)
    assert not any(t["id"] == tid for t in r.json())
