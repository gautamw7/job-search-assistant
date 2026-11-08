import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { errorMessage } from "../lib/http";
import type { HistoryEntry, ProfileCard } from "../types";

export function useHistory(enabled: boolean) {
  const [entries, setEntries] = useState<Record<string, HistoryEntry>>({});
  const [cards, setCards] = useState<Record<string, ProfileCard>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [history, allCards] = await Promise.all([
        api.history(),
        api.allCards().catch(() => ({}) as Record<string, ProfileCard>),
      ]);
      setEntries(history);
      setCards(allCards);
    } catch (e) {
      setError(errorMessage(e, "Could not load history."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (enabled) refresh();
  }, [enabled, refresh]);

  return { entries, cards, loading, error, refresh };
}
