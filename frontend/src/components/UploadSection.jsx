import { useRef, useState } from "react";
import { UploadCloud, FileText, Sparkles, Clock, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { fmtBytes } from "@/lib/api";

export const UploadSection = ({
  templates, selectedTemplate, setSelectedTemplate,
  onUpload, onSample, loading, history, onOpenHistory, onDeleteHistory,
}) => {
  const inputRef = useRef();
  const [drag, setDrag] = useState(false);

  const handleFiles = (files) => {
    const f = files?.[0];
    if (f) onUpload(f);
  };

  return (
    <div className="max-w-3xl mx-auto fade-up">
      <div className="text-center mb-8">
        <h1 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight">
          Siapkan Dokumen LHPP dalam Hitungan Menit
        </h1>
        <p className="text-muted-foreground mt-3 text-sm sm:text-base max-w-xl mx-auto">
          Unggah satu PDF laporan besar. Sistem membaca isinya, mendeteksi batas
          setiap dokumen secara otomatis, lalu memisahkannya menjadi file siap unggah ke SIUjang Gatrik.
        </p>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground whitespace-nowrap">
          Template Deteksi
        </span>
        <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
          <SelectTrigger data-testid="template-select" className="bg-card">
            <SelectValue placeholder="Tanpa template (deteksi otomatis)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Tanpa template (deteksi otomatis)</SelectItem>
            {templates.map((t) => (
              <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div
        data-testid="dropzone"
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-10 sm:p-14 text-center transition-colors bg-card ${
          drag ? "border-primary bg-primary/5 drop-active" : "border-border hover:border-primary/60"
        }`}
      >
        <input
          ref={inputRef} type="file" accept="application/pdf" className="hidden"
          data-testid="file-input"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="mx-auto h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
          <UploadCloud className="h-8 w-8 text-primary" />
        </div>
        <p className="font-heading font-semibold text-lg">Tarik PDF ke sini atau pilih file</p>
        <p className="text-sm text-muted-foreground mt-1">Format PDF • laporan/LHPP multi-halaman</p>
      </div>

      <div className="flex items-center gap-3 my-5">
        <div className="h-px flex-1 bg-border" />
        <span className="text-xs text-muted-foreground">atau</span>
        <div className="h-px flex-1 bg-border" />
      </div>

      <Button
        data-testid="sample-btn" onClick={onSample} disabled={loading}
        variant="secondary" className="w-full h-12 gap-2 font-semibold"
      >
        <Sparkles className="h-4 w-4 text-accent" /> Coba File Contoh LHPP PLTD
      </Button>

      {history?.length > 0 && (
        <div className="mt-10">
          <div className="flex items-center gap-2 mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Clock className="h-3.5 w-3.5" /> Proyek Terakhir
          </div>
          <div className="space-y-2">
            {history.slice(0, 5).map((p) => (
              <div
                key={p.id} data-testid={`history-item-${p.id}`}
                className="flex items-center gap-3 rounded-xl border border-border bg-card p-3 hover:border-primary/50 transition-colors"
              >
                <FileText className="h-5 w-5 text-primary shrink-0" />
                <button className="flex-1 text-left min-w-0" onClick={() => onOpenHistory(p.id)}>
                  <div className="font-medium text-sm truncate">{p.filename}</div>
                  <div className="text-xs text-muted-foreground">
                    {p.pages} halaman • {fmtBytes(p.size_bytes)} • {p.status}
                  </div>
                </button>
                <Button
                  data-testid={`delete-history-${p.id}`} variant="ghost" size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => onDeleteHistory(p.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
