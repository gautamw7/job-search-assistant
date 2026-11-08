import { useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import type { KeyService } from "../../types";

/** Which API keys are saved (masked values only — the backend never returns the real key). */
export function useKeys(enabled: boolean) {
  const [masked, setMasked] = useState<Record<KeyService, string | null>>({
    brightdata: null,
    gemini: null,
    adzuna: null,
    apify: null,
  });
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    const [brightdata, gemini, adzuna, apify] = await Promise.all([
      api.getKey("brightdata"),
      api.getKey("gemini"),
      api.getKey("adzuna"),
      api.getKey("apify"),
    ]);
    setMasked({ brightdata, gemini, adzuna, apify });
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (enabled) refresh();
  }, [enabled, refresh]);

  const missing = loaded
    ? ([
        ["BrightData", masked.brightdata],
        ["Gemini", masked.gemini],
      ] as const)
        .filter(([, v]) => !v)
        .map(([n]) => n)
    : [];

  return { masked, loaded, missing, refresh };
}
