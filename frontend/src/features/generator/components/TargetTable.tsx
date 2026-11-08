import { Trash2 } from "lucide-react";
import type { Length, TargetRow, Tone } from "../../../types";

type Props = {
  rows: TargetRow[];
  issues: Record<string, string>;
  disabled: boolean;
  onRemove: (id: string) => void;
  onUpdate: (id: string, patch: Partial<TargetRow>) => void;
};

export function TargetTable({ rows, issues, disabled, onRemove, onUpdate }: Props) {
  return (
    <ul className="space-y-3">
      {rows.map((row, i) => {
        const issue = issues[row.id];
        const n = i + 1;
        return (
          <li
            key={row.id}
            className="grid grid-cols-[1.5rem_1fr_auto] items-start gap-x-3 gap-y-2 md:grid-cols-[1.5rem_minmax(0,1.3fr)_minmax(0,1fr)_7.5rem_8.5rem_auto]"
          >
            <span className="pt-2.5 text-center text-xs font-bold text-slate-600">{n}</span>

            <div className="col-start-2 min-w-0">
              <input
                type="text"
                inputMode="url"
                value={row.url}
                disabled={disabled}
                onChange={(e) => onUpdate(row.id, { url: e.target.value })}
                placeholder="linkedin.com/in/jane-doe"
                aria-label={`LinkedIn profile ${n}`}
                aria-invalid={!!issue}
                aria-describedby={issue ? `issue-${row.id}` : undefined}
                className={`input ${issue ? "input-error" : ""}`}
              />
              {issue && (
                <p id={`issue-${row.id}`} role="alert" className="mt-1 text-[11px] text-rose-400">
                  {issue}
                </p>
              )}
              <label className="mt-1.5 inline-flex cursor-pointer items-center gap-1.5 text-[11px] text-slate-500 hover:text-slate-300">
                <input
                  type="checkbox"
                  checked={!!row.refresh}
                  disabled={disabled}
                  onChange={(e) => onUpdate(row.id, { refresh: e.target.checked })}
                  className="h-3 w-3 accent-indigo-500"
                />
                Re-scrape profile (skip cache)
              </label>
            </div>

            <input
              type="text"
              value={row.note}
              disabled={disabled}
              onChange={(e) => onUpdate(row.id, { note: e.target.value })}
              placeholder="Optional note, e.g. met at AI meetup"
              aria-label={`Note for profile ${n}`}
              className="input col-span-2 col-start-2 md:col-span-1 md:col-start-auto"
            />

            <select
              value={row.length ?? ""}
              disabled={disabled}
              onChange={(e) => onUpdate(row.id, { length: (e.target.value || undefined) as Length | undefined })}
              aria-label={`Message length for profile ${n}`}
              className="input col-start-2 cursor-pointer md:col-start-auto"
            >
              <option value="">Any length</option>
              <option value="short">Short</option>
              <option value="medium">Medium</option>
              <option value="detailed">Detailed</option>
            </select>

            <select
              value={row.tone ?? ""}
              disabled={disabled}
              onChange={(e) => onUpdate(row.id, { tone: (e.target.value || undefined) as Tone | undefined })}
              aria-label={`Tone for profile ${n}`}
              className="input cursor-pointer"
            >
              <option value="">Any tone</option>
              <option value="professional">Professional</option>
              <option value="friendly">Friendly</option>
              <option value="casual">Casual</option>
              <option value="confident">Confident</option>
              <option value="neutral">Neutral</option>
            </select>

            <button
              type="button"
              onClick={() => onRemove(row.id)}
              disabled={disabled}
              aria-label={`Remove profile ${n}`}
              className="btn btn-ghost !px-2.5 hover:!text-rose-400"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          </li>
        );
      })}
    </ul>
  );
}
