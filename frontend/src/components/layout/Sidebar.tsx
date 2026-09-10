import { FileText, History, Key, Send, Settings } from "lucide-react";
import type { ActiveTab } from "../../types";

const NAV = [
  { id: "generator" as ActiveTab, label: "Batch Generator", icon: Send },
  { id: "history" as ActiveTab, label: "Generation History", icon: History },
  { id: "resume" as ActiveTab, label: "Resume & Profile", icon: FileText },
  { id: "style" as ActiveTab, label: "Communication Style", icon: Settings },
  { id: "config" as ActiveTab, label: "API Keys", icon: Key },
];

export function Sidebar({ activeTab, onChange }: { activeTab: ActiveTab; onChange: (t: ActiveTab) => void }) {
  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950/60 p-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center gap-3 px-3 py-4 mb-4 border-b border-slate-800/80">
          <div className="rounded-xl bg-indigo-600/10 p-2 text-indigo-400">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
              <rect x="2" y="9" width="4" height="12" />
              <circle cx="4" cy="4" r="2" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100">Job Search Assistant</h1>
            <p className="text-[10px] text-slate-400">Outreach Workspace</p>
          </div>
        </div>
        <nav className="space-y-1.5">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => onChange(id)}
              className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-medium transition-all ${
                activeTab === id ? "bg-indigo-600/10 text-indigo-400 font-semibold" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`}
            >
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </nav>
      </div>
      <div className="border-t border-slate-800/80 pt-4 px-3 flex items-center justify-between text-[11px] text-slate-500">
        <span>v0.1.0 Tauri App</span>
        <span className="flex items-center gap-1 text-emerald-400 font-medium">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> API Connected
        </span>
      </div>
    </aside>
  );
}
