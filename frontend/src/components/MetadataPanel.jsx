import { useState } from "react";
import { Copy, Check, FileSearch } from "lucide-react";
import { toast } from "sonner";

const FIELDS = [
  ["nomor_laporan", "Nomor Laporan"],
  ["tanggal", "Tanggal"],
  ["perusahaan", "Nama Perusahaan"],
  ["instalasi", "Nama Instalasi"],
  ["jenis_pembangkit", "Jenis Pembangkit"],
  ["kapasitas", "Kapasitas"],
  ["unit", "Unit"],
  ["nomor_seri", "Nomor Seri"],
  ["pemeriksa", "Pemeriksa / Penguji"],
];

export const MetadataPanel = ({ metadata }) => {
  const [copied, setCopied] = useState(null);
  const copy = (k, v) => {
    navigator.clipboard.writeText(v);
    setCopied(k);
    toast.success("Disalin ke clipboard");
    setTimeout(() => setCopied(null), 1200);
  };
  const has = FIELDS.some(([k]) => metadata?.[k]);

  return (
    <div data-testid="metadata-panel" className="rounded-2xl border border-border bg-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <FileSearch className="h-4 w-4 text-primary" />
        <h3 className="font-heading font-semibold text-sm">Metadata Laporan</h3>
      </div>
      {!has ? (
        <p className="text-sm text-muted-foreground">Metadata tidak terdeteksi otomatis.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3">
          {FIELDS.map(([k, label]) => {
            const v = metadata?.[k];
            if (!v) return null;
            return (
              <div key={k} className="group" data-testid={`meta-${k}`}>
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-medium truncate">{v}</span>
                  <button
                    onClick={() => copy(k, v)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-primary shrink-0"
                  >
                    {copied === k ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
