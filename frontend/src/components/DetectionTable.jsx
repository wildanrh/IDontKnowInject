import React from "react";
import { Eye, Pencil, Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfidenceBadge, StatusBadge } from "@/components/Badges";
import { pageLabel } from "@/lib/api";

export const DetectionTable = ({
  documents, onToggle, onToggleAll, onEdit, onPreview, onDelete, onAdd,
}) => {
  const allReq = documents.length > 0 && documents.every((d) => d.required);

  return (
    <div data-testid="detection-table" className="rounded-2xl border border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between p-4 sm:p-5 border-b border-border">
        <div>
          <h3 className="font-heading font-semibold">Hasil Deteksi Dokumen</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {documents.length} dokumen terdeteksi • centang yang diperlukan
          </p>
        </div>
        <Button data-testid="add-doc-btn" variant="outline" size="sm" onClick={onAdd} className="gap-1.5">
          <Plus className="h-4 w-4" /> Tambah
        </Button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-muted-foreground border-b border-border">
              <th className="p-3 pl-4 w-10">
                <Checkbox
                  data-testid="select-all-checkbox" checked={allReq}
                  onCheckedChange={(v) => onToggleAll(!!v)}
                />
              </th>
              <th className="p-3 w-10">No</th>
              <th className="p-3">Nama Dokumen</th>
              <th className="p-3 w-24">Halaman</th>
              <th className="p-3 w-40">Confidence</th>
              <th className="p-3 w-32">Status</th>
              <th className="p-3 pr-4 w-28 text-right">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d, i) => {
              const showSection = d.section && d.section !== documents[i - 1]?.section;
              return (
              <React.Fragment key={d.id}>
              {showSection && (
                <tr className="bg-muted/50" data-testid={`section-row-${i}`}>
                  <td colSpan={7} className="px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {d.section}
                  </td>
                </tr>
              )}
              <tr
                data-testid={`doc-row-${i}`}
                className={`border-b border-border last:border-0 transition-colors hover:bg-muted/40 ${
                  d.required ? "" : "opacity-55"
                }`}
              >
                <td className="p-3 pl-4">
                  <Checkbox
                    data-testid={`doc-check-${i}`} checked={d.required}
                    onCheckedChange={() => onToggle(d.id)}
                  />
                </td>
                <td className="p-3 font-mono text-muted-foreground">{i + 1}</td>
                <td className="p-3 font-medium max-w-xs">
                  <span className="line-clamp-2">{d.title}</span>
                  {d.matched_by?.includes("ai") && (
                    <span className="ml-1 text-[10px] uppercase tracking-wide text-primary bg-primary/10 rounded px-1 py-0.5">AI</span>
                  )}
                  {d.scanned && (
                    <span className="ml-1 text-[10px] uppercase tracking-wide text-accent-foreground bg-accent/20 rounded px-1 py-0.5">OCR</span>
                  )}
                </td>
                <td className="p-3 font-mono whitespace-nowrap">Hal {pageLabel(d.start_page, d.end_page)}</td>
                <td className="p-3"><ConfidenceBadge value={d.confidence} /></td>
                <td className="p-3"><StatusBadge status={d.status} /></td>
                <td className="p-3 pr-4">
                  <div className="flex items-center justify-end gap-0.5">
                    <Button data-testid={`preview-btn-${i}`} variant="ghost" size="icon" className="h-8 w-8" onClick={() => onPreview(d)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button data-testid={`edit-btn-${i}`} variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(d)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button data-testid={`delete-btn-${i}`} variant="ghost" size="icon" className="h-8 w-8 hover:text-destructive" onClick={() => onDelete(d.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </td>
              </tr>
              </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
