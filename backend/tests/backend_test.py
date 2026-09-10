"""SIUjang Document Manager - backend integration tests (async analyze/split)."""
import io
import os
import time
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
    open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip().rstrip("/")
API = f"{BASE_URL}/api"
LHPP_PATH = "/root/lhpp.pdf"


def _poll(pid, target_statuses, timeout=200, interval=5):
    """Poll GET /api/projects/{pid} until status in target_statuses. Return final project."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = requests.get(f"{API}/projects/{pid}", timeout=30)
        assert r.status_code == 200, r.text
        last = r.json()
        if last.get("status") in target_statuses:
            return last
        if last.get("status") == "error":
            raise AssertionError(f"Project error: {last.get('ai_error')}")
        time.sleep(interval)
    raise AssertionError(f"Timed out waiting for {target_statuses}, last status={last.get('status') if last else None}")


# ---------------- Upload LHPP ----------------
@pytest.fixture(scope="module")
def lhpp_project():
    assert os.path.exists(LHPP_PATH), "lhpp.pdf missing"
    with open(LHPP_PATH, "rb") as f:
        r = requests.post(f"{API}/projects/upload",
                          files={"file": ("lhpp.pdf", f, "application/pdf")}, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["pages"] == 126, f"expected 126 pages, got {data['pages']}"
    assert data["status"] == "uploaded"
    return data


def test_upload_lhpp(lhpp_project):
    assert lhpp_project["filename"] == "lhpp.pdf"
    assert lhpp_project["size_bytes"] > 1_000_000


# ---------------- Analyze AI detail ----------------
@pytest.fixture(scope="module")
def lhpp_ai_detail(lhpp_project):
    pid = lhpp_project["id"]
    r = requests.post(f"{API}/projects/{pid}/analyze",
                      params={"use_ai": "true", "granularity": "detail"}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("status") in ("analyzing", "analyzed")
    return _poll(pid, {"analyzed"}, timeout=240)


def test_analyze_ai_detail_ranges(lhpp_ai_detail):
    p = lhpp_ai_detail
    assert p.get("analysis_mode") == "ai", f"expected mode ai, got {p.get('analysis_mode')}, err={p.get('ai_error')}"
    docs = p["documents"]
    assert len(docs) > 40, f"expected >40 docs in detail mode, got {len(docs)}"
    # section field exists
    for d in docs:
        assert "section" in d
        assert d["start_page"] <= d["end_page"]
        assert 1 <= d["start_page"] <= 126
        assert 1 <= d["end_page"] <= 126
        assert "ai" in d.get("matched_by", []), f"doc missing 'ai' in matched_by: {d}"
    # ordered, non-overlapping, covers 1..126
    sorted_docs = sorted(docs, key=lambda d: d["start_page"])
    for i, d in enumerate(sorted_docs):
        if i + 1 < len(sorted_docs):
            nxt = sorted_docs[i + 1]
            assert d["end_page"] < nxt["start_page"] or d["end_page"] == nxt["start_page"] - 1, \
                f"overlap: {d['title']}({d['start_page']}-{d['end_page']}) vs {nxt['title']}({nxt['start_page']}-{nxt['end_page']})"
    assert sorted_docs[0]["start_page"] == 1
    assert sorted_docs[-1]["end_page"] == 126


def test_analyze_ai_spesifikasi_mesin_page5(lhpp_ai_detail):
    docs = lhpp_ai_detail["documents"]
    mesin = [d for d in docs if "Spesifikasi Teknik Mesin" in d["title"]]
    assert mesin, f"'Spesifikasi Teknik Mesin' not found. Titles sample: {[d['title'] for d in docs[:10]]}"
    m = mesin[0]
    assert m["start_page"] <= 5 <= m["end_page"], f"Mesin should include page 5, got {m['start_page']}-{m['end_page']}"


# ---------------- Analyze heuristic ----------------
def test_analyze_heuristic(lhpp_project):
    pid = lhpp_project["id"]
    r = requests.post(f"{API}/projects/{pid}/analyze",
                      params={"use_ai": "false"}, timeout=30)
    assert r.status_code == 200, r.text
    p = _poll(pid, {"analyzed"}, timeout=120)
    assert p.get("analysis_mode") == "heuristic"
    docs = p["documents"]
    assert len(docs) > 20, f"expected >20 heuristic docs (not just 'Dokumen Lengkap'), got {len(docs)}: {[d['title'] for d in docs[:5]]}"


# ---------------- Analyze AI section (fewer) ----------------
def test_analyze_ai_section_fewer(lhpp_project):
    pid = lhpp_project["id"]
    r = requests.post(f"{API}/projects/{pid}/analyze",
                      params={"use_ai": "true", "granularity": "section"}, timeout=30)
    assert r.status_code == 200, r.text
    p = _poll(pid, {"analyzed"}, timeout=240)
    assert p.get("analysis_mode") == "ai"
    docs = p["documents"]
    assert len(docs) < 40, f"section mode should have fewer docs, got {len(docs)}"


# ---------------- Update docs records correction ----------------
def test_update_documents_records_correction(lhpp_project):
    pid = lhpp_project["id"]
    # Re-analyze in detail AI to have consistent docs list
    r = requests.post(f"{API}/projects/{pid}/analyze",
                      params={"use_ai": "true", "granularity": "detail"}, timeout=30)
    assert r.status_code == 200
    p = _poll(pid, {"analyzed"}, timeout=240)
    docs = [dict(d) for d in p["documents"]]
    original_title = docs[1]["title"]
    docs[1]["title"] = "TEST_" + original_title
    r = requests.put(f"{API}/projects/{pid}/documents", json={"documents": docs}, timeout=30)
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["documents"][1]["title"].startswith("TEST_")
    assert "section" in updated["documents"][1]
    c = requests.get(f"{API}/corrections", timeout=30)
    assert c.status_code == 200
    assert any(x["project_id"] == pid for x in c.json())


# ---------------- Split + outputs + zip ----------------
def test_split_and_zip(lhpp_project):
    pid = lhpp_project["id"]
    # ensure documents present (analyzed in detail from previous test)
    proj = requests.get(f"{API}/projects/{pid}").json()
    assert proj["documents"], "no docs to split"
    n_required = sum(1 for d in proj["documents"] if d.get("required"))
    assert n_required > 0

    t0 = time.time()
    r = requests.post(f"{API}/projects/{pid}/split", timeout=30)
    assert r.status_code == 200
    p = _poll(pid, {"split"}, timeout=90, interval=3)
    elapsed = time.time() - t0
    assert elapsed < 90, f"split took too long: {elapsed:.1f}s"
    outputs = p.get("outputs", [])
    assert len(outputs) == n_required
    for o in outputs:
        assert o.get("filename") and o.get("size_bytes", 0) > 0

    # fetch first PDF
    first = outputs[0]
    resp = requests.get(f"{API}/projects/{pid}/output/{first['filename']}", timeout=30)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"

    # zip
    t1 = time.time()
    z = requests.get(f"{API}/projects/{pid}/download-zip", timeout=90)
    zip_elapsed = time.time() - t1
    assert z.status_code == 200
    assert z.headers.get("content-type", "").startswith("application/zip")
    zf = zipfile.ZipFile(io.BytesIO(z.content))
    assert len(zf.namelist()) == n_required
    assert zip_elapsed < 60, f"zip too slow {zip_elapsed:.1f}s"


# ---------------- Regression: sample project AI ----------------
def test_sample_ai_regression():
    r = requests.post(f"{API}/projects/sample", timeout=60)
    assert r.status_code == 200
    pid = r.json()["id"]
    r2 = requests.post(f"{API}/projects/{pid}/analyze",
                       params={"use_ai": "true", "granularity": "detail"}, timeout=30)
    assert r2.status_code == 200
    p = _poll(pid, {"analyzed"}, timeout=180)
    docs = p["documents"]
    assert docs
    assert any("Spesifikasi Teknik Mesin" in d["title"] for d in docs), \
        f"Mesin not detected in sample. Titles: {[d['title'] for d in docs]}"
    # split
    r3 = requests.post(f"{API}/projects/{pid}/split", timeout=30)
    assert r3.status_code == 200
    p2 = _poll(pid, {"split"}, timeout=60, interval=2)
    assert p2["outputs"]
    z = requests.get(f"{API}/projects/{pid}/download-zip", timeout=30)
    assert z.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(z.content))
    assert zf.namelist()


# ---------------- Templates seeded (regression) ----------------
def test_templates_seeded():
    r = requests.get(f"{API}/templates", timeout=30)
    assert r.status_code == 200
    names = {t["name"] for t in r.json()}
    for expected in ["LHPP PLTD", "LHPP PLTU", "LHPP PLTS"]:
        assert expected in names
