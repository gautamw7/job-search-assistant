import { XCircle } from "lucide-react";
import { StatusChip, Spinner, formatCost, formatTokens } from "../../../components/ui";
import { formatSeconds, profileHandle } from "../../../lib/format";
import type { JobTarget, UsageTotals } from "../../../types";

type Props = {
  cards: JobTarget[];
  done: number;
  total: number;
  elapsed: number;
  isRunning: boolean;
  usage?: UsageTotals;
  onCancel: () => void;
};

export function ProgressPanel({ cards, done, total, elapsed, isRunning, usage, onCancel }: Props) {
  if (!total) {
    return isRunning ? (
      <div className="card flex items-center gap-3 p-5 text-xs text-slate-300" role="status">
        <Spinner /> Starting…
      </div>
    ) : null;
  }
  const pct = Math.round((done / total) * 100);
  return (
    <section className="card space-y-4 p-5" aria-label="Generation progress">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-100" role="status" aria-live="polite">
          {isRunning ? `Generating — ${done} of ${total} done` : `Finished — ${done} of ${total}`}
          {isRunning && (
            <span className="ml-2 font-mono text-xs font-normal text-slate-400">{formatSeconds(elapsed)}</span>
          )}
        </p>
        {isRunning && (
          <button type="button" onClick={onCancel} className="btn btn-danger">
            <XCircle className="h-4 w-4" aria-hidden /> Cancel remaining
          </button>
        )}
      </div>

      <div
        className="h-1.5 overflow-hidden rounded-full bg-slate-800"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      {usage && (usage.brightdata_profiles > 0 || usage.gemini_calls > 0) && (
        <p className="text-[11px] text-slate-500">
          This run: {usage.brightdata_profiles} profile{usage.brightdata_profiles === 1 ? "" : "s"} scraped ·{" "}
          {usage.gemini_calls} Gemini call{usage.gemini_calls === 1 ? "" : "s"} ·{" "}
          {formatTokens(usage.input_tokens + usage.output_tokens)} tokens · {formatCost(usage.estimated_cost)}
        </p>
      )}

      <ul className="grid gap-2 sm:grid-cols-2">
        {cards.map((c) => (
          <li
            key={c.linkedin_url}
            className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2"
          >
            <span className="truncate text-xs text-slate-300" title={c.linkedin_url}>
              {profileHandle(c.linkedin_url)}
            </span>
            <StatusChip status={c.status} />
          </li>
        ))}
      </ul>
    </section>
  );
}
