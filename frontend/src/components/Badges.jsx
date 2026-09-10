import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

const conf = (c) => {
  if (c >= 90) return { cls: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800", bar: "bg-emerald-500" };
  if (c >= 60) return { cls: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800", bar: "bg-amber-500" };
  return { cls: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800", bar: "bg-red-500" };
};

export const ConfidenceBadge = ({ value }) => {
  const s = conf(value);
  return (
    <div className="flex items-center gap-2" data-testid="confidence-badge">
      <div className="h-1.5 w-14 rounded-full bg-muted overflow-hidden hidden sm:block">
        <div className={`h-full ${s.bar}`} style={{ width: `${value}%` }} />
      </div>
      <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-mono font-semibold ${s.cls}`}>
        {value}%
      </span>
    </div>
  );
};

export const StatusBadge = ({ status }) => {
  const map = {
    ready: { icon: CheckCircle2, cls: "text-emerald-600 dark:text-emerald-400", label: "Siap" },
    review: { icon: AlertTriangle, cls: "text-amber-600 dark:text-amber-400", label: "Perlu Review" },
    low: { icon: XCircle, cls: "text-red-600 dark:text-red-400", label: "Rendah" },
  };
  const s = map[status] || map.review;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${s.cls}`} data-testid="status-badge">
      <Icon className="h-4 w-4" /> {s.label}
    </span>
  );
};
