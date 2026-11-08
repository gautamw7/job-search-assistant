import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { configureBackend } from "../lib/http";

export type BackendState = "connecting" | "ready" | "failed";
const MAX_ATTEMPTS = 40;

/** Waits for the backend sidecar to come up, then keeps a light heartbeat. */
export function useBackend() {
  const [state, setState] = useState<BackendState>("connecting");
  const [attempt, setAttempt] = useState(0);
  const [online, setOnline] = useState(true);
  const generation = useRef(0);

  const connect = useCallback(async () => {
    const run = ++generation.current;
    setState("connecting");
    await configureBackend();
    for (let i = 1; i <= MAX_ATTEMPTS; i++) {
      if (run !== generation.current) return;
      setAttempt(i);
      try {
        if (await api.health()) {
          setOnline(true);
          setState("ready");
          return;
        }
      } catch {
        await new Promise((r) => setTimeout(r, Math.min(300 * i, 1500)));
      }
    }
    if (run === generation.current) setState("failed");
  }, []);

  useEffect(() => {
    connect();
    return () => {
      generation.current++;
    };
  }, [connect]);

  useEffect(() => {
    if (state !== "ready") return;
    const id = window.setInterval(() => {
      api.health().then(setOnline).catch(() => setOnline(false));
    }, 15000);
    return () => window.clearInterval(id);
  }, [state]);

  return { state, attempt, maxAttempts: MAX_ATTEMPTS, online, retry: connect };
}
