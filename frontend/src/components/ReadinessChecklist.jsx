import { CheckCircle2, Circle, ShieldCheck, Download } from "lucide-react";
import { Button } from "@/components/ui/button";

export const ReadinessChecklist = ({ checks, ready, onDownloadZip, hasOutputs }) => {
  return (
    <div data-testid="readiness-checklist" className="rounded-2xl border border-border bg-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <ShieldCheck className={`h-4 w-4 ${ready ? "text-emerald-500" : "text-amber-500"}`} />
        <h3 className="font-heading font-semibold text-sm">Status SIUjang Ready</h3>
      </div>
      <div className="space-y-2.5">
        {checks.map((c) => (
          <div key={c.label} className="flex items-start gap-2.5" data-testid={`check-${c.key}`}>
            {c.done ? (
              <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500 shrink-0 mt-0.5" />
            ) : (
              <Circle className="h-4.5 w-4.5 text-muted-foreground/40 shrink-0 mt-0.5" />
            )}
            <span className={`text-sm ${c.done ? "" : "text-muted-foreground"}`}>{c.label}</span>
          </div>
        ))}
      </div>
      <Button
        data-testid="download-all-btn"
        disabled={!hasOutputs}
        onClick={onDownloadZip}
        className="w-full mt-5 gap-2 font-semibold"
      >
        <Download className="h-4 w-4" /> Download Semua Dokumen (ZIP)
      </Button>
    </div>
  );
};
