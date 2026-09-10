"""Content-aware document boundary detection for SIUjang LHPP reports.

The engine never relies on fixed page numbers. It reads the text of every page
(with OCR fallback for scanned pages) and detects where a new document/section
begins based on numbered headings, keyword headings and heading-like lines,
while continuation pages stay attached to the current document.
"""
import re
import io
from collections import Counter

import pymupdf  # PyMuPDF
import pytesseract
from PIL import Image

# --- Known document categories (help detection, do NOT lock page numbers) ---
# Each: (canonical_title, [keywords], strong_flag)
CATEGORIES = [
    ("Spesifikasi Teknik Mesin", ["spesifikasi teknik mesin", "spesifikasi mesin",
                                   "data spesifikasi engine", "spesifikasi engine", "diesel engine"]),
    ("Spesifikasi Teknik Generator", ["spesifikasi teknik generator", "spesifikasi generator",
                                       "data spesifikasi generator"]),
    ("Spesifikasi Teknik Generator Set", ["spesifikasi teknik generator set", "generator set",
                                          "genset", "spesifikasi gen set"]),
    ("Spesifikasi Teknik Transformator", ["spesifikasi teknik transformator", "transformator",
                                          "spesifikasi trafo", "trafo daya"]),
    ("Hasil Uji Pabrik / Sertifikat Produk", ["hasil uji pabrik", "sertifikat produk",
                                              "factory test", "test certificate", "sertifikat"]),
    ("Buku Manual Operasi / SOP", ["buku manual operasi", "manual operasi", "sop",
                                   "standard operating procedure", "operation manual"]),
    ("Dokumen Lingkungan Hidup", ["dokumen lingkungan", "persetujuan lingkungan",
                                  "lingkungan hidup", "amdal", "ukl", "upl", "sppl"]),
    ("Gambar Single Line Diagram (SLD)", ["single line diagram", "gambar sld", "diagram satu garis"]),
    ("Gambar Layout", ["gambar layout", "layout instalasi", "tata letak", "site plan"]),
    ("Gambar Sistem Pembumian", ["sistem pembumian", "pembumian", "grounding", "gambar pentanahan"]),
    ("Sertifikat Kelaikan Operasi (SLO)", ["kelaikan operasi", "slo", "sertifikat laik operasi"]),
]

# Numbered heading near the top of a page, e.g. "1. Spesifikasi Teknik Mesin"
NUM_RE = re.compile(
    r'^\s*(?:item\s*)?(\d{1,2})\s*[\.\)]\s+([A-Za-z][^\n]{2,90})',
    re.IGNORECASE | re.MULTILINE,
)
BAB_RE = re.compile(
    r'^\s*(?:BAB|BAGIAN|LAMPIRAN)\s+([IVXLC0-9]{1,4})\s*[:\.\-]?\s*([A-Za-z][^\n]{2,90})',
    re.IGNORECASE | re.MULTILINE,
)

STOP_TITLE = re.compile(r'(halaman|tanggal|nomor|tabel|gambar\s+\d)$', re.IGNORECASE)


def _roman_to_int(s):
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    s = s.upper()
    if s.isdigit():
        return int(s)
    total, prev = 0, 0
    for ch in reversed(s):
        v = vals.get(ch, 0)
        total += -v if v < prev else v
        prev = max(prev, v)
    return total or None


def extract_pages(pdf_path, ocr_threshold=40):
    """Return list of dicts: {num(1-based), text, scanned}."""
    doc = pymupdf.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text("text") or ""
        scanned = False
        if len(text.strip()) < ocr_threshold:
            # Likely scanned image -> OCR fallback
            try:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img, lang="ind+eng")
                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
                    scanned = True
            except Exception:
                pass
        pages.append({"num": i + 1, "text": text, "scanned": scanned})
    doc.close()
    return pages


def _top_lines(text, n=12):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[:n]


def _tokens(text):
    return [w for w in re.findall(r'[a-zA-Z]{3,}', text.lower())]


def _jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _match_category(text, learned=None):
    """Return (canonical_title, score 0-1, matched_keyword) for best category.
    More specific (longer) keyword matches win ties."""
    low = text.lower()
    top = " ".join(_top_lines(text, 8)).lower()
    best = (None, 0.0, None, 0)
    cats = list(CATEGORIES)
    if learned:
        for title in learned:
            cats.append((title, [title.lower()]))
    for title, kws in cats:
        score = 0.0
        matched = None
        klen = 0
        for kw in kws:
            if kw in top:
                if 1.0 > score or (score == 1.0 and len(kw) > klen):
                    score, matched, klen = 1.0, kw, len(kw)
            elif kw in low and score < 0.55:
                score, matched, klen = 0.55, kw, len(kw)
        if score > best[1] or (score == best[1] and klen > best[3]):
            best = (title, score, matched, klen)
    return best[0], best[1], best[2]


def _analyze_page(page, learned=None):
    text = page["text"]
    top_block = "\n".join(_top_lines(text, 12))

    # Table-of-contents / daftar isi detection: many numbered items on one page
    all_nums = NUM_RE.findall(text)
    is_toc = len(all_nums) >= 3
    if not is_toc and re.search(r'daftar\s+isi', text[:400], re.IGNORECASE):
        is_toc = True

    numbered = None
    m = NUM_RE.search(top_block)
    if m:
        num = int(m.group(1))
        title = m.group(2).strip().rstrip('.:;- ')
        if 1 <= num <= 40 and not STOP_TITLE.search(title):
            numbered = {"number": num, "title": title}
    if not numbered:
        mb = BAB_RE.search(top_block)
        if mb:
            num = _roman_to_int(mb.group(1))
            title = mb.group(2).strip().rstrip('.:;- ')
            if num:
                numbered = {"number": num, "title": title}

    cat_title, cat_score, cat_kw = _match_category(text, learned)

    heading_like = False
    for l in _top_lines(text, 6):
        letters = re.sub(r'[^A-Za-z]', '', l)
        if len(letters) >= 4 and l.upper() == l and len(l) <= 70:
            heading_like = True
            break

    return {
        "numbered": numbered,
        "cat_title": cat_title,
        "cat_score": cat_score,
        "cat_kw": cat_kw,
        "heading_like": heading_like,
        "is_toc": is_toc,
        "len": len(text.strip()),
        "tokens": _tokens(text),
    }


def detect_documents(pages, learned_titles=None):
    """Return list of detected documents with dynamic page boundaries.

    Each doc: {title, start_page, end_page, confidence, status, matched_by, scanned}
    """
    analyzed = [_analyze_page(p, learned_titles) for p in pages]
    docs = []
    last_number = 0

    for idx, (page, sig) in enumerate(zip(pages, analyzed)):
        start_new = False
        matched_by = []
        title = None

        # Skip table-of-contents pages: they list many items but are not boundaries
        if sig["is_toc"]:
            if docs:
                docs[-1]["end_page"] = page["num"]
            continue

        num_ok = (
            sig["numbered"] is not None
            and last_number < sig["numbered"]["number"] <= last_number + 4
        )
        if num_ok:
            start_new = True
            last_number = sig["numbered"]["number"]
            title = sig["numbered"]["title"]
            matched_by.append("numbered")
            if sig["cat_score"] >= 1.0:
                matched_by.append("keyword")
        elif sig["cat_score"] >= 1.0 and sig["heading_like"]:
            # keyword-only boundary for unnumbered sections (drawings, appendices)
            prev_cat = docs[-1]["_cat"] if docs else None
            if sig["cat_title"] != prev_cat:
                start_new = True
                title = sig["cat_title"]
                matched_by.append("keyword")
                matched_by.append("heading")

        if start_new:
            if docs:
                docs[-1]["end_page"] = page["num"] - 1
            docs.append({
                "title": title or f"Dokumen (Halaman {page['num']})",
                "start_page": page["num"],
                "end_page": page["num"],
                "matched_by": matched_by,
                "_cat": sig["cat_title"] if sig["cat_score"] >= 1.0 else None,
                "_start_idx": idx,
                "scanned": page["scanned"],
            })
        else:
            if docs:
                docs[-1]["end_page"] = page["num"]
                if page["scanned"]:
                    docs[-1]["scanned"] = True

    # Pages before the first detected document -> cover / table of contents
    if docs and docs[0]["start_page"] > 1:
        docs.insert(0, {
            "title": "Sampul / Daftar Isi",
            "start_page": 1,
            "end_page": docs[0]["start_page"] - 1,
            "matched_by": ["cover"],
            "_cat": None,
            "_start_idx": 0,
            "scanned": pages[0]["scanned"],
        })
    if not docs:
        docs.append({
            "title": "Dokumen Lengkap",
            "start_page": 1,
            "end_page": len(pages),
            "matched_by": [],
            "_cat": None,
            "_start_idx": 0,
            "scanned": any(p["scanned"] for p in pages),
        })

    # Confidence scoring
    for d in docs:
        conf = 55
        mb = d["matched_by"]
        if "numbered" in mb:
            conf += 25
        if "keyword" in mb:
            conf += 15
        if "heading" in mb:
            conf += 6
        if "cover" in mb:
            conf = 60
        span = d["end_page"] - d["start_page"] + 1
        if span >= 1:
            conf += 3
        # page continuity: continuation pages should resemble the start page
        s_idx = d["_start_idx"]
        sims = []
        base = analyzed[s_idx]["tokens"]
        for j in range(s_idx + 1, min(len(analyzed), s_idx + span)):
            sims.append(_jaccard(base, analyzed[j]["tokens"]))
        if sims:
            avg = sum(sims) / len(sims)
            if avg >= 0.15:
                conf += 5
            elif avg < 0.05 and span > 1:
                conf -= 6
        if d["scanned"]:
            conf -= 8  # OCR is less certain
        conf = max(35, min(99, conf))
        d["confidence"] = conf
        d["status"] = "ready" if conf >= 90 else ("review" if conf >= 60 else "low")
        d.pop("_cat", None)
        d.pop("_start_idx", None)

    return docs


def extract_metadata(pages):
    """Best-effort extraction of key report metadata from the first pages."""
    text = "\n".join(p["text"] for p in pages[:6])
    low = text.lower()

    def find(patterns):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip().rstrip('.,;:')
        return None

    jenis = None
    for kode in ["PLTD", "PLTU", "PLTG", "PLTGU", "PLTS", "PLTA", "PLTP", "PLTMG"]:
        if kode.lower() in low:
            jenis = kode
            break

    return {
        "nomor_laporan": find([r'No(?:mor)?\.?\s*(?:Laporan|LHPP)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\.\/\-]{3,40})']),
        "tanggal": find([r'Tanggal\s*[:\-]?\s*([0-9]{1,2}[ \-\/][A-Za-z0-9]+[ \-\/][0-9]{2,4})',
                         r'([0-9]{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+[0-9]{4})']),
        "perusahaan": find([r'((?:PT|CV)\.?\s+[A-Z][^\n]{2,45})']),
        "instalasi": find([r'(?:Nama\s+)?Instalasi\s*[:\-]?\s*([^\n]{3,45})']),
        "jenis_pembangkit": jenis,
        "kapasitas": find([r'Kapasitas\s*[:\-]?\s*([0-9\.,]+\s*(?:MW|kW|kVA|MVA|MWe))',
                           r'([0-9\.,]+\s*(?:MW|kVA|MVA))']),
        "unit": find([r'Unit\s*[:\-]?\s*([A-Za-z0-9\.\-]{1,20})']),
        "nomor_seri": find([r'(?:No(?:mor)?\.?\s*Seri|Serial\s*(?:No)?)\s*[:\-]?\s*([A-Za-z0-9\-\/]{3,30})']),
        "pemeriksa": find([r'\b(?:Pemeriksa|Penguji|Inspektor)\b\s*[:\-]\s*([A-Za-z][A-Za-z\.\, ]{3,45})']),
    }
