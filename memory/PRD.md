# PRD — SIUjang Document Manager

## Problem Statement
Aplikasi web untuk menyiapkan dokumen LHPP/laporan sebelum diunggah ke SIUjang Gatrik.
User mengunggah satu PDF besar; sistem membaca isinya, mendeteksi batas tiap dokumen
secara **content-aware** (bukan nomor halaman tetap), memberi confidence score,
mengizinkan koreksi manual, memilih dokumen yang diperlukan, memisahkan (split) tanpa
menurunkan kualitas, lalu mengunduh per file atau ZIP.

## User Choices
- Tanpa autentikasi (single-user)
- OCR: Tesseract (`ind+eng`)
- Database: MongoDB
- Lingkup: MVP + fitur lanjutan (template, metadata, learning)
- Preview PDF di browser (thumbnail per halaman)

## Architecture
- **Frontend**: React (CRA/craco), Tailwind + shadcn/ui, next-themes, sonner. `src/App.js` orchestrator + `src/components/*`.
- **Backend**: FastAPI (`/api` prefix). PyMuPDF (baca/render/split lossless), pytesseract OCR fallback, pypdf.
- **Detection engine** (`detection.py`): ekstraksi teks per halaman + OCR fallback, deteksi numbered heading, keyword kategori, heading-like, deteksi TOC (skip false boundary), similaritas antar halaman (Jaccard), confidence scoring, metadata regex.
- **Storage**: Emergent Object Storage (source of truth) + temp cache lokal untuk pemrosesan. PDF asli & hasil split disimpan di object storage.
- **DB**: MongoDB — collections `projects`, `templates`, `corrections`.

## Implemented (2026-06)
- Upload PDF + endpoint sample generator (Contoh LHPP PLTD 13 halaman)
- Analisa content-aware dengan rentang halaman dinamis + confidence + status
- Tabel hasil deteksi: edit nama/halaman, tambah, hapus, preview, checkbox "Diperlukan", select-all
- Split hanya dokumen terpilih (kualitas asli), preview, download per file & ZIP
- Preview PDF (thumbnail filmstrip + gambar halaman render)
- Metadata extraction (nomor laporan, tanggal, perusahaan, instalasi, jenis pembangkit, kapasitas, unit, seri, pemeriksa)
- Template manager (seed: LHPP PLTD/PLTU/PLTS) — bantuan deteksi, tidak mengunci halaman
- Learning: koreksi user (halaman/judul) disimpan ke `corrections` & dipakai memperkaya deteksi berikutnya
- SIUjang Ready checklist + tombol Download Semua
- Riwayat proyek, hapus proyek, dark/light mode
- Verified: backend 11/11 tests pass; frontend E2E flow pass

## Implemented (2026-06, iterasi 2) — Fix "PDF asli hanya 1 dokumen"
- Penyebab: header form berulang di tiap halaman (126 hal) membuat heuristik gagal → hanya "Dokumen Lengkap".
- **Deteksi AI** (`ai_detection.py`): GPT-5.4 via Emergent Universal Key, batch 60 halaman, output JSON {title, section, start_page, end_page, confidence}; normalisasi rentang (tanpa tumpang tindih, seluruh halaman tercakup). Fallback otomatis ke heuristik bila AI gagal.
- Heuristik diperbaiki: `strip_repeating_lines` (hapus header/footer berulang), deteksi judul bagian ALL-CAPS + reset penomoran per bagian, halaman FOTO/HASIL dianggap lanjutan.
- Opsi analisa di UI: toggle "Deteksi AI" (default on) + granularitas "Per item / mata uji" vs "Per bagian besar".
- Analisa & split kini **background task** (status `analyzing`/`splitting`) + polling di frontend → tidak kena timeout proxy; split paralel (6 thread).
- Download ZIP dibangun langsung dari PDF asli (11 dtk untuk 92 file, sebelumnya 66 dtk/502).
- Tabel deteksi dikelompokkan per bagian (section) + badge AI. Field baru dokumen: `section`; proyek: `analysis_mode`, `granularity`, `ai_error`, `split_error`.
- Verified dengan PDF asli user (126 hal → 96 dokumen AI / 87 heuristik); testing agent iteration_2: backend 9/9 + frontend E2E pass.

## Backlog / Next
- P1: Preview PDF embed langsung (iframe) selain render gambar
- P1: Opsi hapus file/proyek otomatis setelah selesai (privasi)
- P1: Pemetaan otomatis ke daftar kebutuhan unggah SIUjang (pilih hanya dokumen yang diminta SIUjang)
- P2: Metadata extraction lebih kaya via LLM
- P2: Halaman-level exclude (buang halaman tertentu dalam satu dokumen)
- P2: Statistik akurasi deteksi dari data koreksi
- P2: Ukuran file hasil split masih besar (resource dibagi per halaman) — opsi kompresi lossless lanjutan
