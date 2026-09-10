import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const EditDocDialog = ({ doc, maxPages, open, onOpenChange, onSave }) => {
  const [title, setTitle] = useState("");
  const [start, setStart] = useState(1);
  const [end, setEnd] = useState(1);

  useEffect(() => {
    if (doc) {
      setTitle(doc.title || "");
      setStart(doc.start_page || 1);
      setEnd(doc.end_page || 1);
    }
  }, [doc]);

  const save = () => {
    const s = Math.max(1, Math.min(maxPages, Number(start) || 1));
    const e = Math.max(s, Math.min(maxPages, Number(end) || s));
    onSave({ ...doc, title: title.trim() || "Dokumen", start_page: s, end_page: e });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="edit-doc-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Edit Dokumen</DialogTitle>
          <DialogDescription>Sesuaikan nama dan rentang halaman dokumen.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>Nama Dokumen</Label>
            <Input data-testid="edit-title-input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Halaman Awal</Label>
              <Input data-testid="edit-start-input" type="number" min={1} max={maxPages} value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Halaman Akhir</Label>
              <Input data-testid="edit-end-input" type="number" min={1} max={maxPages} value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">Total halaman PDF: {maxPages}. Perubahan halaman disimpan sebagai pola pembelajaran.</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Batal</Button>
          <Button data-testid="save-doc-btn" onClick={save}>Simpan</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
