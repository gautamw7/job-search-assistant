import { useMemo, useState } from "react";

export function useHistorySearch(
  historyData: Record<string, unknown>,
  enrichCache: Record<string, { card?: { name?: string; current_company_name?: string } }>,
) {
  const [query, setQuery] = useState("");

  const filteredEntries = useMemo(() => {
    const q = query.trim().toLowerCase();
    const entries = Object.entries(historyData) as [string, { generations?: unknown[] }][];
    if (!q) return entries;
    return entries.filter(([url]) => {
      const card = enrichCache[url]?.card as { name?: string; current_company_name?: string } | undefined;
      const name = (card?.name ?? "").toLowerCase();
      const company = (card?.current_company_name ?? "").toLowerCase();
      return url.toLowerCase().includes(q) || name.includes(q) || company.includes(q);
    });
  }, [historyData, enrichCache, query]);

  return { query, setQuery, filteredEntries };
}
