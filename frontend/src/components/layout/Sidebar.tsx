import { Briefcase, FileText, History, KanbanSquare, Key, PenLine, Send } from "lucide-react";
import type { ActiveTab } from "../../types";

const NAV = [
  { id: "generator" as ActiveTab, label: "Generator", icon: Send },
  { id: "jobs" as ActiveTab, label: "Jobs", icon: Briefcase },
  { id: "tracker" as ActiveTab, label: "Tracker", icon: KanbanSquare },
  { id: "history" as ActiveTab, label: "History", icon: History },
  { id: "resume" as ActiveTab, label: "Resume", icon: FileText },
  { id: "style" as ActiveTab, label: "Writing style", icon: PenLine },
  { id: "config" as ActiveTab, label: "Settings", icon: Key },
];

export function Sidebar({
  activeTab,
  onChange,
  online,
  attention,
  badges,
}: {
  activeTab: ActiveTab;
  onChange: (t: ActiveTab) => void;
  online: boolean;
  /** Tabs that need the user's attention (e.g. missing API keys). */
  attention?: ActiveTab[];
  /** Small counters next to a tab (e.g. follow-ups due). */
  badges?: Partial<Record<ActiveTab, number>>;
}) {
  return (
    <aside className="flex w-16 shrink-0 flex-col justify-between border-r border-slate-800 bg-slate-950/60 p-3 lg:w-60 lg:p-4">
      <div>
        <div className="mb-4 flex items-center gap-3 border-b border-slate-800/80 px-1 py-3 lg:px-3 lg:py-4">
          <div className="rounded-xl bg-indigo-600/10 p-2 text-indigo-400">
            <Send className="h-5 w-5" aria-hidden />
          </div>
          <div className="hidden lg:block">
            <h1 className="text-sm font-bold text-slate-100">Job Search Assistant</h1>
            <p className="text-[10px] text-slate-400">Outreach workspace</p>
          </div>
        </div>
        <nav className="space-y-1" aria-label="Main">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => onChange(id)}
              title={label}
              aria-current={activeTab === id ? "page" : undefined}
              className={`relative flex w-full items-center justify-center gap-3 rounded-xl px-3 py-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 lg:justify-start ${
                activeTab === id
                  ? "bg-indigo-600/10 font-semibold text-indigo-300"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              <span className="hidden lg:inline">{label}</span>
              {!!badges?.[id] && (
                <span
                  className="absolute right-1 top-1 min-w-[1.1rem] rounded-full bg-amber-500 px-1 text-center text-[10px] font-bold text-slate-950 lg:static lg:ml-auto"
                  aria-label={`${badges[id]} need attention`}
                >
                  {badges[id]}
                </span>
              )}
              {attention?.includes(id) && (
                <span
                  className="absolute right-2 top-2 h-2 w-2 rounded-full bg-amber-400 lg:static lg:ml-auto"
                  aria-label="Needs attention"
                />
              )}
            </button>
          ))}
        </nav>
      </div>
      <div
        className="flex items-center justify-center gap-2 border-t border-slate-800/80 pt-3 text-[11px] lg:justify-start lg:px-3"
        role="status"
      >
        <span
          className={`h-2 w-2 rounded-full ${online ? "bg-emerald-400" : "bg-rose-500 animate-pulse"}`}
          aria-hidden
        />
        <span className={`hidden lg:inline ${online ? "text-slate-500" : "text-rose-400"}`}>
          {online ? "Backend connected" : "Backend offline"}
        </span>
      </div>
    </aside>
  );
}
