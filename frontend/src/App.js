import { useEffect, useMemo, useRef, useState } from "react";
import { ThemeProvider } from "next-themes";
import { Toaster, toast } from "sonner";
import { FileText, Scissors, RotateCcw, Loader2, ScanSearch } from "lucide-react";
import "@/App.css";

import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/Navbar";
import { UploadSection } from "@/components/UploadSection";
import { AnalysisProgress } from "@/components/AnalysisProgress";
import { MetadataPanel } from "@/components/MetadataPanel";
import { ReadinessChecklist } from "@/components/ReadinessChecklist";
import { DetectionTable } from "@/components/DetectionTable";
import { EditDocDialog } from "@/components/EditDocDialog";
import { PreviewDialog } from "@/components/PreviewDialog";
import { SplitResults } from "@/components/SplitResults";
import { TemplateDrawer } from "@/components/TemplateDrawer";
import { api, fmtBytes } from "@/lib/api";

const uid = () => Math.random().toString(36).slice(2, 10);

function Dashboard() {
  const [project, setProject] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [history, setHistory] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState("none");
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeStep, setAnalyzeStep] = useState(0);
  const [editDoc, setEditDoc] = useState(null);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [splitting, setSplitting] = useState(false);
  const stepTimer = useRef(null);

  const refreshTemplates = async () => setTemplates(await api.listTemplates());
  const refreshHistory = async () => setHistory(await api.listProjects());

  useEffect(() => { refreshTemplates(); refreshHistory(); }, []);

  const docs = project?.documents || [];
  const outputs = project?.outputs || [];
  const analyzed = project?.status === "analyzed" || project?.status === "split";

  // ---------- Upload / sample ----------
  const handleUpload = async (file) => {
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("File harus berformat PDF"); return;
    }
    setLoading(true);
    try {
      const p = await api.uploadPdf(file);
      setProject(p);
      toast.success(`PDF diunggah: ${p.pages} halaman`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal mengunggah PDF");
    } finally { setLoading(false); refreshHistory(); }
  };

  const handleSample = async () => {
    setLoading(true);
    try {
      const p = await api.createSample();
      setProject(p);
      toast.success("File contoh LHPP PLTD dibuat");
    } catch { toast.error("Gagal membuat file contoh"); }
    finally { setLoading(false); refreshHistory(); }
  };

  const openHistory = async (pid) => {
    setLoading(true);
    try { setProject(await api.getProject(pid)); }
    finally { setLoading(false); }
  };

  const deleteHistory = async (pid) => {
    await api.deleteProject(pid);
    if (project?.id === pid) setProject(null);
    refreshHistory();
    toast.success("Proyek dihapus");
  };

  // ---------- Analyze ----------
  const runAnalyze = async () => {
    if (!project) return;
    setAnalyzing(true);
    setAnalyzeStep(0);
    stepTimer.current = setInterval(() => {
      setAnalyzeStep((s) => (s < 3 ? s + 1 : s));
    }, 800);
    try {
      const tpl = selectedTemplate !== "none" ? selectedTemplate : undefined;
      const p = await api.analyze(project.id, tpl);
      clearInterval(stepTimer.current);
      setAnalyzeStep(4);
      setProject(p);
      setTimeout(() => setAnalyzing(false), 500);
      toast.success(`${p.documents.length} dokumen terdeteksi`);
    } catch (e) {
      clearInterval(stepTimer.current);
      setAnalyzing(false);
      toast.error(e?.response?.data?.detail || "Analisa gagal");
    }
    refreshHistory();
  };

  // ---------- Document mutations ----------
  const persist = async (newDocs) => {
    const optimistic = { ...project, documents: newDocs };
    setProject(optimistic);
    try {
      const p = await api.updateDocuments(project.id, newDocs);
      setProject(p);
    } catch { toast.error("Gagal menyimpan perubahan"); }
  };

  const toggleReq = (id) =>
    persist(docs.map((d) => (d.id === id ? { ...d, required: !d.required } : d)));
  const toggleAll = (val) => persist(docs.map((d) => ({ ...d, required: val })));
  const deleteDoc = (id) => persist(docs.filter((d) => d.id !== id));
  const addDoc = () => {
    const nd = {
      id: uid(), title: "Dokumen Baru", start_page: 1, end_page: 1,
      confidence: 70, status: "review", required: true, matched_by: ["manual"], scanned: false,
    };
    persist([...docs, nd]);
    setEditDoc(nd);
  };
  const saveEdit = (updated) => {
    persist(docs.map((d) => (d.id === updated.id ? updated : d)));
    setEditDoc(null);
    toast.success("Dokumen diperbarui");
  };

  // ---------- Split ----------
  const runSplit = async () => {
    const selected = docs.filter((d) => d.required);
    if (selected.length === 0) { toast.error("Pilih minimal satu dokumen"); return; }
    setSplitting(true);
    try {
      const p = await api.split(project.id);
      setProject(p);
      toast.success(`${p.outputs.length} dokumen berhasil dipisahkan`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Split gagal");
    } finally { setSplitting(false); refreshHistory(); }
  };

  const downloadZip = () => { window.location.href = api.zipUrl(project.id); };

  // ---------- Readiness ----------
  const selectedCount = docs.filter((d) => d.required).length;
  const readiness = useMemo(() => {
    if (!analyzed) return null;
    const allVerified = docs.filter((d) => d.required).every((d) => d.confidence >= 60);
    const checks = [
      { key: "detected", label: "Struktur dokumen sudah dianalisa", done: analyzed },
      { key: "selected", label: `Dokumen diperlukan sudah dipilih (${selectedCount})`, done: selectedCount > 0 },
      { key: "verified", label: "Semua dokumen terpilih terverifikasi", done: selectedCount > 0 && allVerified },
      { key: "split", label: "Dokumen sudah dipisahkan menjadi PDF", done: outputs.length > 0 },
    ];
    const done = checks.filter((c) => c.done).length;
    return { checks, done, total: checks.length, ready: done === checks.length };
  }, [analyzed, docs, outputs, selectedCount]);

  const reset = () => { setProject(null); refreshHistory(); };

  return (
    <div className="App min-h-screen grain">
      <Navbar readiness={readiness} onOpenTemplates={() => setTemplatesOpen(true)} />
      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!project ? (
          <UploadSection
            templates={templates} selectedTemplate={selectedTemplate}
            setSelectedTemplate={setSelectedTemplate}
            onUpload={handleUpload} onSample={handleSample} loading={loading}
            history={history} onOpenHistory={openHistory} onDeleteHistory={deleteHistory}
          />
        ) : (
          <div className="space-y-6">
            {/* File header */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-4 rounded-2xl border border-border bg-card p-5 fade-up">
              <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-heading font-semibold truncate" data-testid="project-filename">{project.filename}</div>
                <div className="text-sm text-muted-foreground">
                  {project.pages} halaman • {fmtBytes(project.size_bytes)} •{" "}
                  <span className="capitalize">{project.status === "uploaded" ? "belum dianalisa" : project.status === "analyzed" ? "sudah dianalisa" : "sudah dipisah"}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={reset} className="gap-1.5" data-testid="reset-btn">
                  <RotateCcw className="h-4 w-4" /> PDF Lain
                </Button>
                {!analyzed && (
                  <Button data-testid="analyze-btn" onClick={runAnalyze} disabled={analyzing} className="gap-1.5">
                    {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
                    Analisa PDF
                  </Button>
                )}
              </div>
            </div>

            {analyzing && <AnalysisProgress step={analyzeStep} />}

            {analyzed && !analyzing && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                  <DetectionTable
                    documents={docs}
                    onToggle={toggleReq} onToggleAll={toggleAll}
                    onEdit={setEditDoc} onPreview={setPreviewDoc}
                    onDelete={deleteDoc} onAdd={addDoc}
                  />

                  {/* Split action bar */}
                  <div className="sticky bottom-4 z-20 flex flex-col sm:flex-row items-center gap-3 rounded-2xl border border-border bg-card/95 backdrop-blur p-4 shadow-lg">
                    <div className="flex-1 text-sm">
                      <span className="font-semibold" data-testid="selected-count">{selectedCount}</span> dari {docs.length} dokumen dipilih
                    </div>
                    <Button
                      data-testid="split-btn" onClick={runSplit} disabled={splitting || selectedCount === 0}
                      className="w-full sm:w-auto gap-2 font-semibold"
                    >
                      {splitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Scissors className="h-4 w-4" />}
                      SPLIT DOKUMEN TERPILIH
                    </Button>
                  </div>

                  {outputs.length > 0 && (
                    <SplitResults pid={project.id} outputs={outputs} onPreview={setPreviewDoc} />
                  )}
                </div>

                <div className="space-y-6">
                  <MetadataPanel metadata={project.metadata} />
                  <ReadinessChecklist
                    checks={readiness.checks} ready={readiness.ready}
                    onDownloadZip={downloadZip} hasOutputs={outputs.length > 0}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <EditDocDialog
        doc={editDoc} maxPages={project?.pages || 1} open={!!editDoc}
        onOpenChange={(o) => !o && setEditDoc(null)} onSave={saveEdit}
      />
      <PreviewDialog
        pid={project?.id} doc={previewDoc} open={!!previewDoc}
        onOpenChange={(o) => !o && setPreviewDoc(null)}
      />
      <TemplateDrawer
        open={templatesOpen} onOpenChange={setTemplatesOpen}
        templates={templates} onChanged={refreshTemplates}
      />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <Dashboard />
      <Toaster position="top-right" richColors closeButton />
    </ThemeProvider>
  );
}
