"""LLM-powered document boundary detection (Emergent Universal Key, GPT-5.4)."""
import os
import re
import json
import uuid
import logging

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger("siujang.ai")

BATCH_PAGES = 60
CHARS_PER_PAGE = 700

SYSTEM_PROMPT = """Anda adalah asisten yang memecah PDF Laporan Hasil Pemeriksaan dan Pengujian (LHPP) instalasi pembangkit listrik menjadi dokumen-dokumen terpisah untuk diunggah ke SIUjang Gatrik.

Anda menerima ringkasan teks tiap halaman (header berulang sudah dihapus). Tentukan batas dokumen berdasarkan ISI halaman, bukan nomor halaman tetap.

Aturan:
- Halaman lanjutan (tabel bersambung, foto/hasil pengujian dari item sebelumnya, halaman tanpa judul baru) HARUS digabung ke dokumen sebelumnya.
- Setiap halaman harus masuk tepat ke satu dokumen; rentang halaman berurutan dan tidak tumpang tindih.
- "section" = nama bagian besar (mis. "Pemeriksaan Dokumen", "Pemeriksaan Kesesuaian Desain", "Pemeriksaan Visual", "Evaluasi Hasil Uji Peralatan dan Sistem", "Pengujian Unit", "Pemeriksaan Dampak Lingkungan", "Kesimpulan", "Dokumen Pendukung"). Sampul, daftar isi, ringkasan eksekutif, riwayat/detail instalasi masuk section "Pembukaan".
- "title" = judul dokumen yang ringkas dan rapi (Title Case), tanpa nomor urut di depan, mis. "Spesifikasi Teknik Mesin", "Gambar Diagram Satu Garis (SLD)".
- "confidence" 0-100 = keyakinan Anda terhadap batas dokumen tersebut.
- Jika halaman pertama batch melanjutkan dokumen dari batch sebelumnya (diberikan sebagai konteks), set "continues_previous": true pada dokumen pertama.

GRANULARITAS
Balas HANYA JSON valid: {"documents":[{"title":"...","section":"...","start_page":n,"end_page":n,"confidence":n,"continues_previous":false}]}"""

GRANULARITY = {
    "detail": ("Pisahkan pada tingkat ITEM/MATA UJI: setiap item bernomor (mis. '1. Spesifikasi Teknik Mesin', "
               "'2. Spesifikasi Teknik Generator', '8. Gambar Diagram Satu Garis') menjadi satu dokumen tersendiri, "
               "termasuk halaman foto/hasil uji lanjutannya."),
    "section": ("Pisahkan pada tingkat BAGIAN/SUB-BAGIAN: gabungkan semua item dalam satu sub-bagian "
                "(mis. seluruh 'Pemeriksaan Dokumen' menjadi satu dokumen; 'Evaluasi Hasil Uji - Generator' satu dokumen)."),
}


def _summarize_page(p):
    lines = [l.strip() for l in p["clean_text"].splitlines() if l.strip()]
    body = " | ".join(lines)
    body = re.sub(r'\s+', ' ', body)
    if len(body) > CHARS_PER_PAGE:
        body = body[:CHARS_PER_PAGE] + " …"
    return f"[Hal {p['num']}] {body or '(halaman kosong / gambar)'}"


def _parse_json(text):
    text = text.strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if not m:
        raise ValueError("Tidak ada JSON dalam respons AI")
    return json.loads(m.group(0))


async def _ask(prompt, granularity):
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"detect-{uuid.uuid4()}",
        system_message=SYSTEM_PROMPT.replace("GRANULARITAS", GRANULARITY.get(granularity, GRANULARITY["detail"])),
    ).with_model("openai", "gpt-5.4").with_params(response_format={"type": "json_object"})
    raw = await chat.send_message(UserMessage(text=prompt))
    return _parse_json(raw).get("documents", [])


def _normalize(docs, lo, hi):
    """Sort, clip to [lo, hi], remove overlaps and fill gaps so every page in range belongs to one document."""
    clean = []
    for d in docs:
        try:
            s, e = int(d["start_page"]), int(d["end_page"])
        except (KeyError, TypeError, ValueError):
            continue
        s, e = max(lo, min(hi, s)), max(lo, min(hi, e))
        if e < s:
            s, e = e, s
        clean.append({
            "title": str(d.get("title") or f"Dokumen (Halaman {s})").strip(),
            "section": str(d.get("section") or "").strip(),
            "start_page": s, "end_page": e,
            "confidence": int(d.get("confidence") or 75),
            "continues_previous": bool(d.get("continues_previous")),
        })
    clean.sort(key=lambda d: d["start_page"])

    out = []
    for d in clean:
        if out and d["start_page"] <= out[-1]["end_page"]:
            d["start_page"] = out[-1]["end_page"] + 1
            if d["start_page"] > d["end_page"]:
                continue
        if out and d["start_page"] > out[-1]["end_page"] + 1:
            out[-1]["end_page"] = d["start_page"] - 1  # attach gap pages to previous doc
        if not out and d["start_page"] > lo:
            if lo == 1:
                out.append({"title": "Sampul / Pembukaan", "section": "Pembukaan", "start_page": 1,
                            "end_page": d["start_page"] - 1, "confidence": 60, "continues_previous": False})
            else:
                d["start_page"] = lo
        out.append(d)
    if out and out[-1]["end_page"] < hi:
        out[-1]["end_page"] = hi
    return out


async def detect_documents_ai(pages, granularity="detail"):
    """pages: list of {num, clean_text, scanned}. Returns list of docs (see server DocumentItem)."""
    total = len(pages)
    docs = []
    for start in range(0, total, BATCH_PAGES):
        batch = pages[start:start + BATCH_PAGES]
        lo, hi = batch[0]["num"], batch[-1]["num"]
        ctx = ""
        if docs:
            last = docs[-1]
            ctx = (f"Konteks: dokumen terakhir dari batch sebelumnya adalah \"{last['title']}\" "
                   f"(section \"{last['section']}\", hal {last['start_page']}-{last['end_page']}).\n\n")
        prompt = (f"{ctx}Total halaman PDF: {total}. Berikut halaman {lo}–{hi}:\n\n"
                  + "\n".join(_summarize_page(p) for p in batch))
        result = _normalize(await _ask(prompt, granularity), lo, hi)
        if docs and result and result[0]["continues_previous"]:
            docs[-1]["end_page"] = result[0]["end_page"]
            result = result[1:]
        docs.extend(result)

    docs = _normalize(docs, 1, total)
    scanned_pages = {p["num"] for p in pages if p.get("scanned")}
    final = []
    for d in docs:
        conf = max(35, min(99, d["confidence"]))
        final.append({
            "title": d["title"], "section": d["section"],
            "start_page": d["start_page"], "end_page": d["end_page"],
            "confidence": conf,
            "status": "ready" if conf >= 90 else ("review" if conf >= 60 else "low"),
            "matched_by": ["ai"],
            "scanned": any(n in scanned_pages for n in range(d["start_page"], d["end_page"] + 1)),
        })
    return final
