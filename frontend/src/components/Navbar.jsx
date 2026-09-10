import { useTheme } from "next-themes";
import { Zap, Moon, Sun, Layers, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Navbar = ({ readiness, onOpenTemplates }) => {
  const { theme, setTheme } = useTheme();
  const ready = readiness?.ready;
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-card/95 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-primary flex items-center justify-center shadow-sm">
            <Zap className="h-5 w-5 text-primary-foreground" fill="currentColor" />
          </div>
          <div className="leading-tight">
            <div className="font-heading font-extrabold text-base sm:text-lg tracking-tight">
              SIUjang <span className="text-primary">Document Manager</span>
            </div>
            <div className="text-[11px] text-muted-foreground -mt-0.5 hidden sm:block">
              Penyiap Dokumen LHPP untuk SIUjang Gatrik
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {readiness && (
            <div
              data-testid="readiness-pill"
              className={`hidden md:flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold ${
                ready
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800"
                  : "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800"
              }`}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              {ready ? "SIUjang Ready" : `${readiness.done}/${readiness.total} langkah`}
            </div>
          )}
          <Button
            data-testid="open-templates-btn"
            variant="outline" size="sm" onClick={onOpenTemplates} className="gap-1.5"
          >
            <Layers className="h-4 w-4" /> <span className="hidden sm:inline">Template</span>
          </Button>
          <Button
            data-testid="theme-toggle-btn" variant="ghost" size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            title="Ganti tema"
          >
            <Sun className="h-5 w-5 dark:hidden" />
            <Moon className="h-5 w-5 hidden dark:block" />
          </Button>
        </div>
      </div>
    </header>
  );
};
