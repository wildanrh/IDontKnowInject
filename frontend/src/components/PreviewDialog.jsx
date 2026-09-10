import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api, pageLabel } from "@/lib/api";

export const PreviewDialog = ({ pid, doc, open, onOpenChange }) => {
  const [activePage, setActivePage] = useState(null);

  useEffect(() => {
    if (doc) setActivePage(doc.start_page);
  }, [doc]);

  if (!doc) return null;
  const pages = [];
  for (let p = doc.start_page; p <= doc.end_page; p++) pages.push(p);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="preview-dialog" className="max-w-5xl w-[95vw] h-[85vh] flex flex-col p-0 gap-0">
        <DialogHeader className="p-4 border-b border-border">
          <DialogTitle className="font-heading text-base truncate">
            {doc.title} · Hal {pageLabel(doc.start_page, doc.end_page)}
          </DialogTitle>
          <DialogDescription className="sr-only">Pratinjau halaman dokumen</DialogDescription>
        </DialogHeader>
        <div className="flex flex-1 min-h-0">
          <ScrollArea className="w-32 sm:w-40 border-r border-border bg-muted/30 shrink-0">
            <div className="p-2 space-y-2">
              {pages.map((p) => (
                <button
                  key={p} data-testid={`thumb-${p}`}
                  onClick={() => setActivePage(p)}
                  className={`block w-full rounded-lg overflow-hidden border-2 transition-colors ${
                    activePage === p ? "border-primary" : "border-transparent hover:border-border"
                  }`}
                >
                  <img
                    src={api.pageImageUrl(pid, p)} alt={`Halaman ${p}`}
                    className="w-full bg-white" loading="lazy"
                  />
                  <div className="text-[11px] font-mono py-1 text-center bg-card">Hal {p}</div>
                </button>
              ))}
            </div>
          </ScrollArea>
          <div className="flex-1 bg-muted/20 overflow-auto flex items-start justify-center p-4">
            {activePage && (
              <img
                data-testid="preview-main-image"
                src={api.pageImageUrl(pid, activePage)} alt={`Halaman ${activePage}`}
                className="max-w-full shadow-lg rounded bg-white"
              />
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
