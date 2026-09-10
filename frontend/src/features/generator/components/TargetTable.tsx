import { Trash2 } from "lucide-react";
import type { TargetRow } from "../../../types";

type Props = {
  rows: TargetRow[];
  onAddRow: () => void;
  onRemoveRow: (id: string) => void;
  onUpdateRow: (id: string, field: keyof TargetRow, val: string) => void;
};

export function TargetTable({ rows, onRemoveRow, onUpdateRow }: Props) {
  return (
    <div className="space-y-3">
      {rows.map((row, index) => (
        <div key={row.id} className="flex items-center gap-3">
          <span className="w-6 text-center text-xs font-bold text-slate-500">{index + 1}</span>
          <input
            type="url"
            value={row.linkedin_url}
            onChange={(e) => onUpdateRow(row.id, "linkedin_url", e.target.value)}
            placeholder="https://www.linkedin.com/in/recruiter-profile"
            className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          />
          <input
            type="text"
            value={row.additional_note}
            onChange={(e) => onUpdateRow(row.id, "additional_note", e.target.value)}
            placeholder="Optional note (e.g. met at AI hackathon)"
            className="w-72 rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          />
          <select
            value={row.length || ""}
            onChange={(e) => onUpdateRow(row.id, "length", e.target.value)}
            className="rounded-xl border border-indigo-500/40 bg-indigo-500/10 px-3.5 py-2.5 text-xs text-indigo-300 focus:border-indigo-500 focus:outline-none appearance-none cursor-pointer"
          >
            <option value="">Default Length</option>
            <option value="short">Short</option>
            <option value="medium">Medium</option>
            <option value="detailed">Detailed</option>
          </select>
          <button
            onClick={() => onRemoveRow(row.id)}
            disabled={rows.length === 1}
            className="rounded-xl p-2.5 text-slate-500 hover:bg-rose-500/10 hover:text-rose-400 disabled:opacity-30 transition-all"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
