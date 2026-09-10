import { FileCheck2, Download, Eye, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, fmtBytes, pageLabel } from "@/lib/api";

export const SplitResults = ({ pid, outputs, onPreview }) => {
  return (
    <div data-testid="split-results" className="rounded-2xl border border-emerald-200 dark:border-emerald-900 bg-emerald-50/40 dark:bg-emerald-950/20 p-5 fade-up">
      <div className="flex items-center gap-2 mb-4">
        <Package className="h-5 w-5 text-emerald-600" />
        <h3 className="font-heading font-semibold">Hasil Split — {outputs.length} Dokumen</h3>
      </div>
      <div className="space-y-2">
        {outputs.map((o, i) => (
          <div
            key={o.filename} data-testid={`output-row-${i}`}
            className="flex items-center gap-3 rounded-xl border border-border bg-card p-3"
          >
            <FileCheck2 className="h-5 w-5 text-emerald-500 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="font-mono text-xs sm:text-sm truncate">{o.filename}</div>
              <div className="text-xs text-muted-foreground">
                Hal {pageLabel(o.start_page, o.end_page)} • {fmtBytes(o.size_bytes)}
              </div>
            </div>
            <Button
              data-testid={`output-preview-${i}`} variant="ghost" size="icon" className="h-8 w-8"
              onClick={() => onPreview(o)}
            >
              <Eye className="h-4 w-4" />
            </Button>
            <a href={api.outputUrl(pid, o.filename, true)} data-testid={`output-download-${i}`}>
              <Button variant="outline" size="sm" className="gap-1.5">
                <Download className="h-4 w-4" /> <span className="hidden sm:inline">Unduh</span>
              </Button>
            </a>
          </div>
        ))}
      </div>
    </div>
  );
};
