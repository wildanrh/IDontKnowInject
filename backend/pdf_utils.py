"""PDF helpers: page rendering, lossless splitting, ZIP packaging, sample generator."""
import io
import re
import zipfile

import pymupdf


def get_pdf_info(pdf_path):
    doc = pymupdf.open(pdf_path)
    n = len(doc)
    doc.close()
    return {"pages": n}


def render_page_png(pdf_path, page_num, dpi=110):
    """Render a single 1-based page to PNG bytes."""
    doc = pymupdf.open(pdf_path)
    idx = max(0, min(len(doc) - 1, page_num - 1))
    pix = doc[idx].get_pixmap(dpi=dpi)
    data = pix.tobytes("png")
    doc.close()
    return data


def split_document(pdf_path, start_page, end_page, out_path):
    """Copy pages [start_page, end_page] (1-based) losslessly into a new PDF."""
    src = pymupdf.open(pdf_path)
    out = pymupdf.open()
    s = max(0, start_page - 1)
    e = min(len(src) - 1, end_page - 1)
    out.insert_pdf(src, from_page=s, to_page=e)
    out.save(out_path)  # no downscaling / re-compression -> original quality kept
    out.close()
    src.close()


def safe_filename(index, title):
    clean = re.sub(r'[^A-Za-z0-9]+', '_', title).strip('_')
    clean = clean[:60] or "Dokumen"
    return f"{index:02d}_{clean}.pdf"


def build_zip_bytes(files):
    """files: list of (filename, bytes). Returns BytesIO zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            zf.writestr(name, data)
    buf.seek(0)
    return buf


def generate_sample_pdf(out_path):
    """Create a realistic multi-page LHPP PLTD sample so users can test instantly."""
    doc = pymupdf.open()
    pages_content = [
        ("LAPORAN HASIL PEMERIKSAAN DAN PENGUJIAN (LHPP)",
         "PT PEMBANGKIT LISTRIK NUSANTARA\n\nNomor Laporan: LHPP/2026/PLTD-047\nTanggal: 12 Februari 2026\n"
         "Nama Instalasi: PLTD Tanjung Priok Unit 3\nJenis Pembangkit: PLTD\nKapasitas: 25 MW\nUnit: 3\n"
         "Nomor Seri: SN-DX8842-2026\nPemeriksa: Ir. Bambang Sudrajat"),
        ("DAFTAR ISI",
         "1. Spesifikasi Teknik Mesin\n2. Spesifikasi Teknik Generator\n3. Spesifikasi Teknik Generator Set\n"
         "4. Spesifikasi Teknik Transformator\n5. Sertifikat Produk\n6. Buku Manual Operasi / SOP\n"
         "7. Dokumen Lingkungan Hidup\n8. Gambar Single Line Diagram"),
        ("PEMERIKSAAN DOKUMEN",
         "Berikut adalah hasil pemeriksaan kelengkapan dokumen teknik untuk instalasi pembangkit."),
        ("1. Spesifikasi Teknik Mesin",
         "DATA SPESIFIKASI ENGINE\n\nMerk: MAN Diesel\nTipe: 18V32/44CR\nDaya: 25.000 kW\n"
         "Putaran: 750 rpm\nBahan Bakar: HSD / MFO\nSistem Pendingin: Water cooled"),
        ("DATA SPESIFIKASI ENGINE (lanjutan)",
         "Jumlah Silinder: 18\nDiameter Silinder: 320 mm\nLangkah: 440 mm\n"
         "Tekanan Kompresi: 180 bar\nKonsumsi Pelumas: 0.5 g/kWh"),
        ("2. Spesifikasi Teknik Generator",
         "DATA SPESIFIKASI GENERATOR\n\nMerk: ABB\nTipe: AMG 0900\nDaya: 31.250 kVA\n"
         "Tegangan: 11 kV\nFrekuensi: 50 Hz\nFaktor Daya: 0.8"),
        ("3. Spesifikasi Teknik Generator Set",
         "DATA GENERATOR SET\n\nKonfigurasi: Engine + Generator terkopel\n"
         "Total Output: 25 MW\nEfisiensi: 42%\nEmisi: sesuai baku mutu"),
        ("4. Spesifikasi Teknik Transformator",
         "DATA TRANSFORMATOR DAYA\n\nMerk: Trafindo\nKapasitas: 30 MVA\n"
         "Rasio: 11/150 kV\nVector Group: YNd1\nPendingin: ONAN/ONAF"),
        ("5. Hasil Uji Pabrik Peralatan Utama atau Sertifikat Produk",
         "SERTIFIKAT PRODUK\n\nFactory Acceptance Test telah dilaksanakan.\n"
         "Nomor Sertifikat: FAT-2026-1180\nStatus: LULUS"),
        ("SERTIFIKAT PRODUK (lanjutan)",
         "Hasil pengujian tegangan tembus, rugi beban, dan efisiensi memenuhi standar IEC."),
        ("6. Buku Manual Operasi atau SOP",
         "STANDARD OPERATING PROCEDURE\n\nProsedur start-up, operasi normal, dan shutdown darurat "
         "engine dan generator dijelaskan pada bagian ini."),
        ("7. Dokumen Lingkungan Hidup dan/atau Persetujuan Lingkungan",
         "DOKUMEN LINGKUNGAN\n\nPersetujuan Lingkungan Nomor: DLH/2025/8842\n"
         "Jenis: UKL-UPL\nStatus: Disetujui"),
        ("8. Gambar Single Line Diagram (SLD)",
         "SINGLE LINE DIAGRAM\n\nDiagram satu garis sistem kelistrikan instalasi pembangkit "
         "dari generator, transformator, hingga titik sambung jaringan."),
    ]
    for title, body in pages_content:
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text((60, 90), title, fontsize=16, fontname="helv")
        page.insert_text((60, 140), body, fontsize=11, fontname="helv")
    doc.save(out_path)
    doc.close()
