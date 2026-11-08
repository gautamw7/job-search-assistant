import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api";
import type { GeneratedResult, TargetPayload } from "../../api";
import { useToast } from "../../context/ToastContext";
import { canonicalLinkedin, extractLinkedinUrls } from "../../lib/format";
import { errorMessage } from "../../lib/http";
import type { Job, JobTarget, TargetRow } from "../../types";

const ROWS_KEY = "jsa.rows.v1";
const JOB_KEY = "jsa.job.v1";
const POLL_MS = 1200;
const FINISHED = new Set(["success", "failed", "cancelled"]);

let rowSeq = 0;
const newRow = (url = ""): TargetRow => ({
  id: `r${Date.now().toString(36)}${rowSeq++}`,
  url,
  note: "",
});

function loadRows(): TargetRow[] {
  try {
    const raw = localStorage.getItem(ROWS_KEY);
    const parsed = raw ? (JSON.parse(raw) as TargetRow[]) : [];
    if (Array.isArray(parsed) && parsed.length) return parsed;
  } catch {
    /* storage unavailable or corrupt: start fresh */
  }
  return [newRow()];
}

function toPayload(row: TargetRow, url: string): TargetPayload {
  const prefs = { length: row.length, tone: row.tone };
  const hasPrefs = Boolean(row.length || row.tone);
  return {
    linkedin_url: url,
    additional_note: row.note.trim() || undefined,
    additional_preferences: hasPrefs ? prefs : undefined,
    refresh_profile: row.refresh || undefined,
  };
}

type Override = Partial<JobTarget>;

export function useGenerator(onFinished: () => void) {
  const toast = useToast();
  const [rows, setRows] = useState<TargetRow[]>(loadRows);
  const [jobId, setJobId] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem(JOB_KEY);
    } catch {
      return null;
    }
  });
  const [job, setJob] = useState<Job | null>(null);
  const [overrides, setOverrides] = useState<Record<string, Override>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [starting, setStarting] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const finishedRef = useRef(onFinished);
  finishedRef.current = onFinished;
  const rowsRef = useRef(rows);
  rowsRef.current = rows;

  useEffect(() => {
    try {
      localStorage.setItem(ROWS_KEY, JSON.stringify(rows));
    } catch {
      /* ignore */
    }
  }, [rows]);

  const isRunning = job?.status === "running" || starting;

  // Poll the running job. Real per-target stages come from the backend.
  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    const tick = async () => {
      try {
        const state = await api.getJob(jobId);
        if (stopped) return;
        setJob(state);
        if (state.status !== "running") {
          stopped = true;
          window.clearInterval(timer);
          try {
            sessionStorage.removeItem(JOB_KEY);
          } catch {
            /* ignore */
          }
          const ok = state.targets.filter((t) => t.status === "success").length;
          const failed = state.targets.filter((t) => t.status === "failed").length;
          if (state.status === "cancelled") toast.info(`Cancelled. ${ok} message(s) finished before stopping.`);
          else if (failed) toast.error(`${ok} generated, ${failed} failed. See the cards for details.`);
          else toast.success(`${ok} message${ok === 1 ? "" : "s"} ready.`);
          finishedRef.current();
        }
      } catch (err) {
        if (stopped) return;
        stopped = true;
        window.clearInterval(timer);
        setJobId(null);
        setJob(null);
        toast.error(errorMessage(err, "Lost track of the generation job."));
      }
    };
    const timer = window.setInterval(tick, POLL_MS);
    tick();
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [jobId, toast]);

  // Elapsed-time display only; progress itself is real.
  useEffect(() => {
    if (!isRunning) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isRunning]);

  const issues = useMemo(() => {
    const seen = new Map<string, number>();
    const out: Record<string, string> = {};
    rows.forEach((row, i) => {
      if (!row.url.trim()) return;
      const canon = canonicalLinkedin(row.url);
      if (!canon) {
        out[row.id] = "Use a profile link like linkedin.com/in/jane-doe";
        return;
      }
      const key = canon.toLowerCase();
      if (seen.has(key)) out[row.id] = `Same profile as row ${seen.get(key)! + 1}`;
      else seen.set(key, i);
    });
    return out;
  }, [rows]);

  const readyRows = useMemo(
    () => rows.filter((r) => r.url.trim() && canonicalLinkedin(r.url) && !issues[r.id]),
    [rows, issues],
  );

  const updateRow = useCallback(
    (id: string, patch: Partial<TargetRow>) =>
      setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r))),
    [],
  );
  const addRow = useCallback(() => setRows((prev) => [...prev, newRow()]), []);
  const removeRow = useCallback(
    (id: string) =>
      setRows((prev) => {
        const next = prev.filter((r) => r.id !== id);
        return next.length ? next : [newRow()];
      }),
    [],
  );
  const clearRows = useCallback(() => setRows([newRow()]), []);

  /** Paste any text containing profile links; returns how many new rows were added. */
  const addUrls = useCallback((text: string): number => {
    const current = rowsRef.current;
    const existing = new Set(
      current.map((r) => canonicalLinkedin(r.url)?.toLowerCase()).filter(Boolean) as string[],
    );
    const fresh: string[] = [];
    for (const url of extractLinkedinUrls(text)) {
      const key = url.toLowerCase();
      if (!existing.has(key)) {
        existing.add(key);
        fresh.push(url);
      }
    }
    if (fresh.length) {
      // Drop untouched empty rows so pasted links replace the blank starter row.
      const kept = current.filter((r) => r.url.trim() || r.note.trim());
      setRows([...kept, ...fresh.map((u) => newRow(u))]);
    }
    return fresh.length;
  }, []);

  const generate = useCallback(async () => {
    if (isRunning || readyRows.length === 0) return;
    setStarting(true);
    setOverrides({});
    setJob(null);
    try {
      const payload = readyRows.map((r) => toPayload(r, canonicalLinkedin(r.url)!));
      const id = await api.startJob(payload);
      setStartedAt(Date.now());
      setNow(Date.now());
      try {
        sessionStorage.setItem(JOB_KEY, id);
      } catch {
        /* ignore */
      }
      setJobId(id);
    } catch (err) {
      toast.error(errorMessage(err, "Could not start generation."));
    } finally {
      setStarting(false);
    }
  }, [isRunning, readyRows, toast]);

  const cancel = useCallback(async () => {
    if (!jobId) return;
    try {
      setJob(await api.cancelJob(jobId));
    } catch (err) {
      toast.error(errorMessage(err, "Could not cancel."));
    }
  }, [jobId, toast]);

  const runOne = useCallback(
    async (url: string, work: () => Promise<GeneratedResult>, failure: string) => {
      setBusy((b) => ({ ...b, [url]: true }));
      try {
        const r = await work();
        setOverrides((o) => ({
          ...o,
          [url]: {
            status: "success",
            generated_message: r.generated_message,
            generated_at: r.generated_at,
            error: null,
            fact_check: r.fact_check ?? null,
            shared_background: r.shared_background ?? [],
          },
        }));
        finishedRef.current();
      } catch (err) {
        const message = errorMessage(err, failure);
        setOverrides((o) => ({ ...o, [url]: { ...o[url], error: message } }));
        toast.error(message);
      } finally {
        setBusy((b) => ({ ...b, [url]: false }));
      }
    },
    [toast],
  );

  const retry = useCallback(
    (url: string) => {
      const row = rows.find((r) => canonicalLinkedin(r.url) === url);
      const payload = row ? toPayload(row, url) : { linkedin_url: url };
      return runOne(url, () => api.generateOne(payload), "Retry failed.");
    },
    [rows, runOne],
  );

  const regenerate = useCallback(
    (url: string, note: string) => runOne(url, () => api.regenerate(url, note), "Regeneration failed."),
    [runOne],
  );

  const cards = useMemo(
    () => (job?.targets ?? []).map((t) => ({ ...t, ...(overrides[t.linkedin_url] ?? {}) }) as JobTarget),
    [job, overrides],
  );
  const done = cards.filter((c) => FINISHED.has(c.status)).length;
  const elapsed = startedAt && isRunning ? Math.max(0, Math.round((now - startedAt) / 1000)) : 0;

  return {
    rows,
    issues,
    readyCount: readyRows.length,
    updateRow,
    addRow,
    removeRow,
    clearRows,
    addUrls,
    job,
    cards,
    busy,
    isRunning,
    progress: { done, total: cards.length },
    elapsed,
    generate,
    cancel,
    retry,
    regenerate,
  };
}
