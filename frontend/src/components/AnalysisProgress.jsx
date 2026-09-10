import { CheckCircle2, Loader2, Circle } from "lucide-react";

const STEPS = [
  "Membaca PDF",
  "Mendeteksi struktur",
  "Mendeteksi dokumen",
  "Menentukan batas halaman",
  "Selesai",
];

export const AnalysisProgress = ({ step }) => {
  return (
    <div data-testid="analysis-progress" className="rounded-2xl border border-border bg-card p-6 fade-up">
      <div className="flex items-center gap-2 mb-5">
        <Loader2 className="h-5 w-5 text-primary animate-spin" />
        <span className="font-heading font-semibold">Menganalisa dokumen…</span>
      </div>
      <div className="space-y-3">
        {STEPS.map((label, i) => {
          const done = i < step;
          const active = i === step;
          return (
            <div key={label} className="flex items-center gap-3">
              {done ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              ) : active ? (
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              ) : (
                <Circle className="h-5 w-5 text-muted-foreground/40" />
              )}
              <span className={`text-sm ${done ? "text-muted-foreground" : active ? "font-medium" : "text-muted-foreground/60"}`}>
                {label}{active ? "…" : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export { STEPS };
