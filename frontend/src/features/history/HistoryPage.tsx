import { ChevronDown, ChevronUp, ExternalLink, History, RefreshCw, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Avatar, CopyButton, EmptyState, PageHeader, Spinner } from "../../components/ui";
import { initials, parseWhen, profileHandle, timeAgo } from "../../lib/format";
import type { HistoryEntry, ProfileCard } from "../../types";

type Props = {
  entries: Record<string, HistoryEntry>;
  cards: Record<string, ProfileCard>;
  loading: boolean;
  error: string | null;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  onRefresh: () => void;
};

export function HistoryPage({ entries, cards, loading, error, copiedKey, onCopy, onRefresh }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return Object.entries(entries)
      .map(([url, entry]) => {
        const generations = entry.generations ?? [];
        const latest = generations[generations.length - 1];
        return { url, generations, latest, card: cards[url] };
      })
      .filter(({ url, card, generations }) => {
        if (!generations.length) return false;
        if (!q) return true;
        return [url, card?.name, card?.current_company_name, card?.position]
          .filter(Boolean)
          .some((v) => String(v).toLowerCase().includes(q));
      })
      .sort(
        (a, b) =>
          (parseWhen(b.latest?.generated_at)?.getTime() ?? 0) - (parseWhen(a.latest?.generated_at)?.getTime() ?? 0),
      );
  }, [entries, cards, query]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="History"
        subtitle="Every message you've generated, newest first."
        actions={
          <button type="button" className="btn btn-secondary" onClick={onRefresh} disabled={loading}>
            {loading ? <Spinner /> : <RefreshCw className="h-4 w-4" aria-hidden />} Refresh
          </button>
        }
      />

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name, company or link…"
          aria-label="Search history"
          className="input !pl-10"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            aria-label="Clear search"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-200">
          {error}
        </div>
      )}

      {loading && rows.length === 0 ? (
        <div className="card flex items-center justify-center gap-3 p-12 text-sm text-slate-400">
          <Spinner className="h-5 w-5" /> Loading history…
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<History className="h-6 w-6" />}
          title={query ? "No matches" : "Nothing here yet"}
          body={query ? "Try a different name, company or link." : "Messages you generate will be saved here automatically."}
        />
      ) : (
        <ul className="space-y-3">
          {rows.map(({ url, generations, latest, card }) => {
            const name = card?.name || profileHandle(url);
            const headline = [card?.position, card?.current_company_name].filter(Boolean).join(" · ");
            const isOpen = open === url;
            return (
              <li key={url} className="card overflow-hidden">
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : url)}
                  aria-expanded={isOpen}
                  className="flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-slate-800/40"
                >
                  <Avatar text={initials(name)} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-semibold text-slate-100">{name}</span>
                      <span className="chip shrink-0 border-slate-700 bg-slate-800/60 text-slate-300">
                        {generations.length} version{generations.length > 1 ? "s" : ""}
                      </span>
                    </div>
                    {headline && <p className="truncate text-xs text-slate-400">{headline}</p>}
                    {!isOpen && latest && (
                      <p className="mt-1.5 line-clamp-2 text-xs text-slate-500">{latest.generated_message}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2 text-[11px] text-slate-500">
                    {timeAgo(latest?.generated_at)}
                    {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="space-y-3 border-t border-slate-800 bg-slate-900/30 p-4">
                    <a href={url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:underline">
                      Open profile <ExternalLink className="h-3 w-3" aria-hidden />
                    </a>
                    {[...generations].reverse().map((g, i) => (
                      <div key={g.generated_at + i} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                        <div className="mb-2 flex items-center justify-between text-[11px] text-slate-500">
                          <span className="font-semibold text-indigo-300">
                            {i === 0 ? "Latest" : `Version ${generations.length - i}`} · {timeAgo(g.generated_at)}
                          </span>
                          <CopyButton
                            text={g.generated_message}
                            id={`h-${url}-${i}`}
                            copiedKey={copiedKey}
                            onCopy={onCopy}
                            className="btn btn-ghost !px-2 !py-1"
                          />
                        </div>
                        {g.user_note && <p className="mb-2 text-[11px] italic text-slate-500">Note: “{g.user_note}”</p>}
                        <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-200">{g.generated_message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
