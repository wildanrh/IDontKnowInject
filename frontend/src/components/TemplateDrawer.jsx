import { useEffect, useState } from "react";
import { Plus, Trash2, X, Save, Layers } from "lucide-react";
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { api } from "@/lib/api";

export const TemplateDrawer = ({ open, onOpenChange, templates, onChanged }) => {
  const [editing, setEditing] = useState(null); // {id?, name, documents[]}
  const [docInput, setDocInput] = useState("");

  useEffect(() => { if (!open) { setEditing(null); setDocInput(""); } }, [open]);

  const startNew = () => setEditing({ name: "", documents: [] });
  const startEdit = (t) => setEditing({ ...t });

  const addDoc = () => {
    const v = docInput.trim();
    if (!v) return;
    setEditing((e) => ({ ...e, documents: [...e.documents, v] }));
    setDocInput("");
  };

  const save = async () => {
    if (!editing.name.trim()) { toast.error("Nama template wajib diisi"); return; }
    if (editing.id) await api.updateTemplate(editing.id, editing);
    else await api.createTemplate(editing);
    toast.success("Template disimpan");
    setEditing(null);
    onChanged();
  };

  const remove = async (id) => {
    await api.deleteTemplate(id);
    toast.success("Template dihapus");
    onChanged();
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent data-testid="template-drawer" className="w-full sm:max-w-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="font-heading flex items-center gap-2">
            <Layers className="h-5 w-5 text-primary" /> Manajemen Template
          </SheetTitle>
          <SheetDescription>Simpan daftar dokumen yang membantu deteksi laporan berikutnya.</SheetDescription>
        </SheetHeader>

        {!editing ? (
          <div className="mt-6 space-y-3">
            <Button data-testid="new-template-btn" onClick={startNew} className="w-full gap-1.5">
              <Plus className="h-4 w-4" /> Template Baru
            </Button>
            {templates.map((t) => (
              <div key={t.id} data-testid={`template-item-${t.id}`} className="rounded-xl border border-border p-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-sm">{t.name}</div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => startEdit(t)}>Edit</Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 hover:text-destructive" onClick={() => remove(t.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground mt-1">{t.documents.length} dokumen</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            <Input
              data-testid="template-name-input" placeholder="Nama template (mis. LHPP PLTD)"
              value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })}
            />
            <div className="flex gap-2">
              <Input
                data-testid="template-doc-input" placeholder="Nama dokumen…"
                value={docInput} onChange={(e) => setDocInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addDoc()}
              />
              <Button data-testid="add-template-doc-btn" onClick={addDoc} size="icon"><Plus className="h-4 w-4" /></Button>
            </div>
            <div className="space-y-1.5">
              {editing.documents.map((d, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
                  <span>{i + 1}. {d}</span>
                  <button onClick={() => setEditing((e) => ({ ...e, documents: e.documents.filter((_, j) => j !== i) }))}>
                    <X className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-2 pt-2">
              <Button variant="outline" onClick={() => setEditing(null)} className="flex-1">Batal</Button>
              <Button data-testid="save-template-btn" onClick={save} className="flex-1 gap-1.5"><Save className="h-4 w-4" /> Simpan</Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};
