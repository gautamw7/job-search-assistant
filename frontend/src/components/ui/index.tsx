import { Check, Copy, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import type { TargetStatus } from "../../types";

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} aria-hidden />;
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-xl font-bold text-slate-100">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon: ReactNode;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-14 text-center">
      <div className="rounded-2xl bg-slate-800/70 p-3 text-slate-400">{icon}</div>
      <p className="text-sm font-semibold text-slate-200">{title}</p>
      {body && <p className="max-w-sm text-xs text-slate-400">{body}</p>}
      {action}
    </div>
  );
}

export function CopyButton({
  text,
  id,
  copiedKey,
  onCopy,
  label = "Copy",
  className = "btn btn-secondary",
}: {
  text: string;
  id: string;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  label?: string;
  className?: string;
}) {
  const copied = copiedKey === id;
  return (
    <button type="button" onClick={() => onCopy(text, id)} className={className} disabled={!text}>
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 text-emerald-400" aria-hidden /> Copied
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" aria-hidden /> {label}
        </>
      )}
    </button>
  );
}

const STATUS: Record<TargetStatus, { label: string; cls: string; spin?: boolean }> = {
  queued: { label: "Queued", cls: "border-slate-700 bg-slate-800/60 text-slate-300" },
  enriching: {
    label: "Fetching profile",
    cls: "border-sky-500/30 bg-sky-500/10 text-sky-300",
    spin: true,
  },
  drafting: {
    label: "Writing message",
    cls: "border-indigo-500/30 bg-indigo-500/10 text-indigo-300",
    spin: true,
  },
  checking: {
    label: "Fact-checking",
    cls: "border-violet-500/30 bg-violet-500/10 text-violet-300",
    spin: true,
  },
  success: { label: "Ready", cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" },
  failed: { label: "Failed", cls: "border-rose-500/30 bg-rose-500/10 text-rose-300" },
  cancelled: { label: "Cancelled", cls: "border-slate-700 bg-slate-800/60 text-slate-400" },
};

export function StatusChip({ status }: { status: TargetStatus }) {
  const s = STATUS[status];
  return (
    <span className={`chip ${s.cls}`}>
      {s.spin && <Spinner className="h-3 w-3" />}
      {s.label}
    </span>
  );
}

export function Avatar({ text }: { text: string }) {
  return (
    <span
      aria-hidden
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600/15 text-xs font-bold text-indigo-300"
    >
      {text}
    </span>
  );
}

export function formatCost(cost: number | null | undefined, freeTierAssumed = false): string {
  if (cost === null || cost === undefined) return "cost unknown";
  const value = cost < 0.01 && cost > 0 ? "< $0.01" : `$${cost.toFixed(2)}`;
  return freeTierAssumed ? `${value} (free tier assumed)` : value;
}

export function formatTokens(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n);
}
