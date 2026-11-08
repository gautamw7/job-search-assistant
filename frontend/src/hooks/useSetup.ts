import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { errorMessage } from "../lib/http";

const SKIP_KEY = "jsa.styleSkipped";
type Source = "response" | "questions" | "default";

function readSkipped(): boolean {
  try {
    return localStorage.getItem(SKIP_KEY) === "1";
  } catch {
    return false;
  }
}

/** What the user has configured: resume text and writing style. */
export function useSetup(enabled: boolean) {
  const [resume, setResume] = useState<string | null>(null);
  const [style, setStyle] = useState<{ content: string; source: Source }>({ content: "", source: "default" });
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [styleSkipped, setStyleSkipped] = useState(readSkipped);

  const refresh = useCallback(async () => {
    try {
      const [r, s] = await Promise.all([api.getResume(), api.getStyle()]);
      setResume(r);
      setStyle({ content: s.content, source: s.source });
      setError(null);
    } catch (e) {
      setError(errorMessage(e, "Could not load your profile."));
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (enabled) refresh();
  }, [enabled, refresh]);

  const skipStyle = useCallback(() => {
    try {
      localStorage.setItem(SKIP_KEY, "1");
    } catch {
      /* ignore */
    }
    setStyleSkipped(true);
  }, []);

  return {
    resume,
    style,
    loaded,
    error,
    refresh,
    // The default style always "exists", so "needs a style" means the user never chose one.
    needsResume: loaded && !error && !resume,
    needsStyle: loaded && !error && style.source === "default" && !styleSkipped,
    skipStyle,
  };
}
