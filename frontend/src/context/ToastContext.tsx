import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

type Kind = "success" | "error" | "info";
interface ToastItem {
  id: number;
  kind: Kind;
  message: string;
}

const Ctx = createContext<{ push: (kind: Kind, message: string) => void } | null>(null);

const STYLES: Record<Kind, string> = {
  success: "border-emerald-500/30 bg-emerald-950/90 text-emerald-100",
  error: "border-rose-500/40 bg-rose-950/90 text-rose-100",
  info: "border-indigo-500/30 bg-slate-900/95 text-slate-100",
};
const ICONS = { success: CheckCircle2, error: AlertCircle, info: Info };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setItems((p) => p.filter((t) => t.id !== id)), []);
  const push = useCallback(
    (kind: Kind, message: string) => {
      const id = nextId.current++;
      setItems((p) => [...p.slice(-3), { id, kind, message }]);
      window.setTimeout(() => dismiss(id), kind === "error" ? 8000 : 4000);
    },
    [dismiss],
  );

  return (
    <Ctx.Provider value={useMemo(() => ({ push }), [push])}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
        role="region"
        aria-live="polite"
        aria-label="Notifications"
      >
        {items.map((t) => {
          const Icon = ICONS[t.kind];
          return (
            <div
              key={t.id}
              role={t.kind === "error" ? "alert" : "status"}
              className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-2xl backdrop-blur ${STYLES[t.kind]}`}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <p className="flex-1 break-words">{t.message}</p>
              <button
                onClick={() => dismiss(t.id)}
                aria-label="Dismiss notification"
                className="rounded p-0.5 opacity-70 hover:opacity-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return useMemo(
    () => ({
      success: (m: string) => ctx.push("success", m),
      error: (m: string) => ctx.push("error", m),
      info: (m: string) => ctx.push("info", m),
    }),
    [ctx],
  );
}
