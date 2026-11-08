import { AlertTriangle, Link2, ShieldCheck, ShieldQuestion } from "lucide-react";
import type { FactCheck } from "../types";

/** Result of the second-pass fact check, shown above a message. */
export function FactCheckNotice({ check }: { check?: FactCheck | null }) {
  if (!check || check.status === "skipped") return null;
  if (check.status === "pass") {
    return (
      <p className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-300">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden /> Fact-checked: every claim matches your resume or their profile
      </p>
    );
  }
  if (check.status === "error") {
    return (
      <p className="inline-flex items-center gap-1.5 text-[11px] text-slate-500" title={check.error ?? undefined}>
        <ShieldQuestion className="h-3.5 w-3.5" aria-hidden /> Fact check didn't run — review the facts yourself
      </p>
    );
  }
  return (
    <div role="alert" className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
      <p className="mb-1.5 flex items-center gap-1.5 font-semibold">
        <AlertTriangle className="h-4 w-4" aria-hidden />
        {check.issues.length} claim{check.issues.length === 1 ? "" : "s"} not found in your resume or their profile
      </p>
      <ul className="space-y-1">
        {check.issues.map((issue, i) => (
          <li key={i}>
            <span className="font-medium">“{issue.claim}”</span>
            {issue.reason && <span className="text-amber-200/70"> — {issue.reason}</span>}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[11px] text-amber-200/70">Edit it before sending, or use Refine to remove it.</p>
    </div>
  );
}

/** Verified overlaps between you and the recipient that were given to the writer. */
export function SharedBackground({ hooks }: { hooks?: string[] }) {
  if (!hooks?.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
        <Link2 className="h-3 w-3" aria-hidden /> Shared:
      </span>
      {hooks.map((h) => (
        <span key={h} className="chip border-sky-500/30 bg-sky-500/10 text-sky-200">
          {h.replace(/\.$/, "")}
        </span>
      ))}
    </div>
  );
}
