import os
import uuid
import asyncio
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Annotated

from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict

import detection
import ai_detection
import pdf_utils
import storage_client as store

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="SIUjang Document Manager")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("siujang")

PyObjectId = Annotated[str, BeforeValidator(str)]
APP = store.APP_NAME


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def orig_key(pid): return f"{APP}/{pid}/original.pdf"
def output_key(pid, filename): return f"{APP}/{pid}/output/{filename}"


# ---------------- Models ----------------
class DocumentItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    section: str = ""
    start_page: int
    end_page: int
    confidence: int = 80
    status: str = "review"
    required: bool = True
    matched_by: List[str] = []
    scanned: bool = False


class ProjectMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")


async def get_project(pid):
    doc = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Project tidak ditemukan")
    return doc


# ---------------- Upload ----------------
@api.post("/projects/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "File harus berformat PDF")
    pid = str(uuid.uuid4())
    data = await file.read()

    tmp = Path(tempfile.gettempdir()) / f"up_{pid}.pdf"
    tmp.write_bytes(data)
    try:
        info = pdf_utils.get_pdf_info(str(tmp))
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise HTTPException(400, f"PDF tidak dapat dibaca: {e}")

    store.put_object(orig_key(pid), data, "application/pdf")
    tmp.unlink(missing_ok=True)

    project = {
        "id": pid, "filename": file.filename, "size_bytes": len(data),
        "pages": info["pages"], "status": "uploaded", "documents": [],
        "metadata": {}, "template_id": None, "created_at": now_iso(),
    }
    await db.projects.insert_one(dict(project))
    return project


# ---------------- Analyze ----------------
async def _run_analysis(pid, path, learned, use_ai, granularity, template_id):
    try:
        pages = await asyncio.to_thread(detection.extract_pages, path)
        pages = detection.strip_repeating_lines(pages)
        meta = detection.extract_metadata(pages)

        detected, mode, ai_error = None, "heuristic", None
        if use_ai:
            try:
                detected = await ai_detection.detect_documents_ai(pages, granularity)
                mode = "ai"
            except Exception as e:
                logger.exception("AI detection failed, falling back to heuristic")
                ai_error = str(e)[:300]
        if not detected:
            detected = detection.detect_documents(pages, learned_titles=list(learned))
            mode = "heuristic"

        documents = []
        for d in detected:
            item = DocumentItem(
                title=d["title"], section=d.get("section", ""),
                start_page=d["start_page"], end_page=d["end_page"],
                confidence=d["confidence"], status=d["status"],
                matched_by=d["matched_by"], scanned=d["scanned"],
                required=("cover" not in d["matched_by"] and d.get("section") != "Pembukaan"),
            )
            documents.append(item.model_dump())

        await db.projects.update_one(
            {"id": pid},
            {"$set": {"documents": documents, "metadata": meta, "status": "analyzed",
                      "template_id": template_id, "analysis_mode": mode,
                      "granularity": granularity, "ai_error": ai_error}})
    except Exception as e:
        logger.exception("Analysis failed")
        await db.projects.update_one(
            {"id": pid}, {"$set": {"status": "error", "ai_error": str(e)[:300]}})


@api.post("/projects/{pid}/analyze")
async def analyze(pid: str, template_id: Optional[str] = None,
                  use_ai: bool = True, granularity: str = "detail"):
    project = await get_project(pid)
    if project.get("status") == "analyzing":
        return project
    path = store.local_cache_path(orig_key(pid))

    learned = set()
    async for c in db.corrections.find({}, {"_id": 0, "title": 1}):
        if c.get("title"):
            learned.add(c["title"])
    if template_id:
        tpl = await db.templates.find_one({"id": template_id}, {"_id": 0})
        if tpl:
            learned.update(tpl.get("documents", []))

    await db.projects.update_one({"id": pid}, {"$set": {"status": "analyzing", "ai_error": None}})
    asyncio.create_task(_run_analysis(pid, path, learned, use_ai, granularity, template_id))
    return await get_project(pid)


# ---------------- List / get / delete ----------------
@api.get("/projects")
async def list_projects():
    return await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.get("/projects/{pid}")
async def read_project(pid: str):
    return await get_project(pid)


@api.delete("/projects/{pid}")
async def delete_project(pid: str):
    await db.projects.delete_one({"id": pid})
    return {"ok": True}


# ---------------- Update documents ----------------
class UpdateDocsBody(BaseModel):
    documents: List[DocumentItem]


@api.put("/projects/{pid}/documents")
async def update_documents(pid: str, body: UpdateDocsBody):
    project = await get_project(pid)
    old = {d["id"]: d for d in project.get("documents", [])}
    new_docs = [d.model_dump() for d in body.documents]

    for d in new_docs:
        prev = old.get(d["id"])
        if prev and (prev["start_page"] != d["start_page"] or prev["end_page"] != d["end_page"]
                     or prev["title"] != d["title"]):
            await db.corrections.insert_one({
                "id": str(uuid.uuid4()), "project_id": pid, "title": d["title"],
                "ai_start": prev["start_page"], "ai_end": prev["end_page"],
                "user_start": d["start_page"], "user_end": d["end_page"],
                "created_at": now_iso(),
            })

    await db.projects.update_one({"id": pid}, {"$set": {"documents": new_docs}})
    return await get_project(pid)


# ---------------- Page preview image ----------------
@api.get("/projects/{pid}/page/{page_num}")
async def page_image(pid: str, page_num: int):
    await get_project(pid)
    path = store.local_cache_path(orig_key(pid))
    png = pdf_utils.render_page_png(path, page_num)
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "max-age=3600"})


# ---------------- Serve original PDF ----------------
@api.get("/projects/{pid}/original.pdf")
async def original_pdf(pid: str):
    await get_project(pid)
    data = store.get_object(orig_key(pid))
    return Response(content=data, media_type="application/pdf")


# ---------------- Split selected documents ----------------
def _split_one(pid, path, i, d):
    fname = pdf_utils.safe_filename(i, d["title"])
    tmp = Path(tempfile.gettempdir()) / f"{pid}_{fname}"
    pdf_utils.split_document(path, d["start_page"], d["end_page"], str(tmp))
    size = tmp.stat().st_size
    store.upload_from_path(output_key(pid, fname), str(tmp), "application/pdf")
    tmp.unlink(missing_ok=True)
    return {
        "id": d["id"], "index": i, "filename": fname, "title": d["title"],
        "section": d.get("section", ""),
        "start_page": d["start_page"], "end_page": d["end_page"], "size_bytes": size,
    }


async def _run_split(pid, path, selected):
    try:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=6) as pool:
            tasks = [loop.run_in_executor(pool, _split_one, pid, path, i, d)
                     for i, d in enumerate(selected, start=1)]
            results = await asyncio.gather(*tasks)
        await db.projects.update_one(
            {"id": pid}, {"$set": {"status": "split", "outputs": list(results), "split_at": now_iso()}})
    except Exception as e:
        logger.exception("Split failed")
        await db.projects.update_one(
            {"id": pid}, {"$set": {"status": "analyzed", "split_error": str(e)[:300]}})


@api.post("/projects/{pid}/split")
async def split(pid: str):
    project = await get_project(pid)
    if project.get("status") == "splitting":
        return project
    path = store.local_cache_path(orig_key(pid))
    selected = [d for d in project.get("documents", []) if d.get("required")]
    if not selected:
        raise HTTPException(400, "Tidak ada dokumen yang dipilih")

    await db.projects.update_one(
        {"id": pid}, {"$set": {"status": "splitting", "split_error": None, "outputs": []}})
    asyncio.create_task(_run_split(pid, path, selected))
    return await get_project(pid)


@api.get("/projects/{pid}/output/{filename}")
async def get_output(pid: str, filename: str, download: bool = False):
    if ".." in filename or "/" in filename:
        raise HTTPException(400, "Nama file tidak valid")
    data = store.get_object(output_key(pid, filename))
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(content=data, media_type="application/pdf", headers=headers)


def _build_zip(path, outputs):
    files = []
    for o in outputs:
        data = pdf_utils.split_document_bytes(path, o["start_page"], o["end_page"])
        files.append((o["filename"], data))
    return pdf_utils.build_zip_bytes(files)


@api.get("/projects/{pid}/download-zip")
async def download_zip(pid: str):
    project = await get_project(pid)
    outputs = project.get("outputs", [])
    if not outputs:
        raise HTTPException(400, "Belum ada dokumen hasil split")
    path = store.local_cache_path(orig_key(pid))
    buf = await asyncio.to_thread(_build_zip, path, outputs)
    base = os.path.splitext(project["filename"])[0]
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{base}_SIUjang.zip"'})


# ---------------- Sample PDF ----------------
@api.post("/projects/sample")
async def create_sample():
    pid = str(uuid.uuid4())
    tmp = Path(tempfile.gettempdir()) / f"sample_{pid}.pdf"
    pdf_utils.generate_sample_pdf(str(tmp))
    info = pdf_utils.get_pdf_info(str(tmp))
    data = tmp.read_bytes()
    store.put_object(orig_key(pid), data, "application/pdf")
    tmp.unlink(missing_ok=True)
    project = {
        "id": pid, "filename": "Contoh_LHPP_PLTD.pdf", "size_bytes": len(data),
        "pages": info["pages"], "status": "uploaded", "documents": [],
        "metadata": {}, "template_id": None, "created_at": now_iso(),
    }
    await db.projects.insert_one(dict(project))
    return project


# ---------------- Templates ----------------
class Template(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    documents: List[str] = []
    created_at: str = Field(default_factory=now_iso)


@api.get("/templates")
async def list_templates():
    return await db.templates.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)


@api.post("/templates")
async def create_template(tpl: Template):
    doc = tpl.model_dump()
    await db.templates.insert_one(dict(doc))
    return doc


@api.put("/templates/{tid}")
async def update_template(tid: str, tpl: Template):
    data = tpl.model_dump()
    data["id"] = tid
    await db.templates.update_one({"id": tid}, {"$set": data}, upsert=True)
    return data


@api.delete("/templates/{tid}")
async def delete_template(tid: str):
    await db.templates.delete_one({"id": tid})
    return {"ok": True}


@api.get("/corrections")
async def list_corrections():
    return await db.corrections.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.get("/")
async def root():
    return {"app": "SIUjang Document Manager", "status": "ok"}


app.include_router(api)
app.add_middleware(
    CORSMiddleware, allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    try:
        store.init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    if await db.templates.count_documents({}) == 0:
        defaults = [
            ("LHPP PLTD", ["Spesifikasi Teknik Mesin", "Spesifikasi Teknik Generator",
                           "Spesifikasi Teknik Generator Set", "Spesifikasi Teknik Transformator",
                           "Sertifikat Produk", "Buku Manual Operasi / SOP", "Dokumen Lingkungan Hidup",
                           "Gambar Single Line Diagram (SLD)", "Gambar Layout", "Gambar Sistem Pembumian"]),
            ("LHPP PLTU", ["Spesifikasi Teknik Boiler", "Spesifikasi Teknik Turbin",
                           "Spesifikasi Teknik Generator", "Spesifikasi Teknik Transformator",
                           "Sertifikat Produk", "Dokumen Lingkungan Hidup",
                           "Gambar Single Line Diagram (SLD)"]),
            ("LHPP PLTS", ["Spesifikasi Modul Surya", "Spesifikasi Inverter",
                           "Spesifikasi Teknik Transformator", "Sertifikat Produk",
                           "Dokumen Lingkungan Hidup", "Gambar Layout"]),
        ]
        for name, docs in defaults:
            await db.templates.insert_one(Template(name=name, documents=docs).model_dump())


@app.on_event("shutdown")
async def shutdown():
    client.close()
