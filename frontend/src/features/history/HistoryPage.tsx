import { ChevronDown, ChevronUp, Layers, RefreshCw, Search, ShieldCheck, XCircle } from "lucide-react";
import { SearchBar } from "../../components/history/SearchBar";

type Props = {
  historyData: Record<string, { generations?: Array<{ generated_message: string; generated_at: string }> }>;
  enrichCache: Record<string, { card?: Record<string, unknown> }>;
  expandedCards: Record<string, boolean>;
  historySearch: string;
  isLoading: boolean;
  onSearchChange: (v: string) => void;
  onToggleExpand: (url: string) => void;
  onRefresh: () => void;
};

export function HistoryPage({
  historyData,
  enrichCache,
  expandedCards,
  historySearch,
  isLoading,
  onSearchChange,
  onToggleExpand,
  onRefresh,
}: Props) {
  const entries = Object.entries(historyData).filter(([url]) => {
    if (!historySearch.trim()) return true;
    const q = historySearch.toLowerCase();
    const card = enrichCache[url]?.card as Record<string, string> | undefined;
    const name = (card?.name || "").toLowerCase();
    const company = (card?.current_company_name || "").toLowerCase();
    return url.toLowerCase().includes(q) || name.includes(q) || company.includes(q);
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Generation History Log</h2>
        <p className="text-xs text-slate-400">Append-only history of all outreach messages generated across profiles.</p>
      </div>

      <SearchBar value={historySearch} onChange={onSearchChange} />

      <div className="space-y-4">
        {isLoading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-12 text-center">
            <RefreshCw className="h-6 w-6 animate-spin text-indigo-400 mx-auto mb-3" />
            <p className="text-sm text-slate-400">Loading generation history...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-12 text-center">
            <p className="text-sm text-slate-500 mb-3">No generation history found yet.</p>
            <button onClick={onRefresh} className="inline-flex items-center gap-1.5 rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700">
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
          </div>
        ) : (
          entries.map(([url, data], idx) => {
            const generations = data.generations || [];
            const card = enrichCache[url]?.card as Record<string, string | number> | undefined;
            const isExpanded = !!expandedCards[url];
            return (
              <div key={idx} className="rounded-2xl border border-slate-800 bg-slate-900/80 overflow-hidden shadow-xl">
                <button
                  onClick={() => onToggleExpand(url)}
                  className="w-full flex items-center justify-between p-5 hover:bg-slate-800/40 transition-all text-left"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-slate-100 truncate">{(card?.name as string) || url.split("/in/")[1]?.replace(/\/$/, "") || "LinkedIn Profile"}</span>
                      <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-[10px] text-slate-300 shrink-0">{generations.length} Version{generations.length > 1 ? "s" : ""}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-400 truncate">
                      {card ? (
                        <>
                          <span className="flex items-center gap-1"><ShieldCheck className="h-3 w-3 text-indigo-400" /> {(card.current_company_name as string) || "—"}</span>
                          <span>•</span>
                          <span className="flex items-center gap-1"><Layers className="h-3 w-3" /> {(card.location as string) || "—"}</span>
                          <span>•</span>
                          <span>{(card.followers as number) ?? "—"} followers</span>
                        </>
                      ) : (
                        <span className="font-mono text-indigo-300 truncate">{url}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                  </div>
                </button>
                {isExpanded && (
                  <div className="border-t border-slate-800 p-5 space-y-4 bg-slate-900/30">
                    {generations.map((gen, gIdx) => (
                      <div key={gIdx} className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                        <div className="flex justify-between text-[11px] text-slate-400">
                          <span className="font-bold text-indigo-400">Version {gIdx + 1}{gIdx === generations.length - 1 ? " (Latest)" : ""}</span>
                          <span>{gen.generated_at}</span>
                        </div>
                        <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">{gen.generated_message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
