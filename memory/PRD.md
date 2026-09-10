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

## Backlog / Next
- P1: Preview PDF embed langsung (iframe) selain render gambar
- P1: Opsi hapus file/proyek otomatis setelah selesai (privasi)
- P2: Metadata extraction lebih kaya via LLM
- P2: Halaman-level exclude (buang halaman tertentu dalam satu dokumen)
- P2: Statistik akurasi deteksi dari data koreksi
