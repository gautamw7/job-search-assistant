import { AlertTriangle, CheckCircle2, ListChecks, Pencil, RefreshCw, Save, Wand2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api";
import { Spinner } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import { timeAgo } from "../../lib/format";
import type { StructuredResume, StructuredResumeState } from "../../types";
import { StructuredResumeEditor } from "./StructuredResumeEditor";

/**
 * The reviewed, structured copy of the resume. Job search and tailored resumes use
 * this instead of the raw PDF text, so it must be confirmed once.
 */
export function StructuredResumePanel({ hasResume }: { hasResume: boolean }) {
  const toast = useToast();
  const [state, setState] = useState<StructuredResumeState | null | undefined>(undefined);
  const [draft, setDraft] = useState<StructuredResume | null>(null);
  const [busy, setBusy] = useState<"convert" | "save" | null>(null);

  useEffect(() => {
    api
      .getStructuredResume()
      .then((s) => {
        setState(s);
        if (s && !s.confirmed) setDraft(s.resume); // unreviewed: open for review
      })
      .catch((e) => toast.error(errorMessage(e, "Could not load the structured resume.")));
  }, [toast]);

  const convert = async () => {
    setBusy("convert");
    try {
      const s = await api.convertStructuredResume();
      setState(s);
      setDraft(s.resume);
      toast.info("Review each section, fix anything the conversion got wrong, then confirm.");
    } catch (e) {
      toast.error(errorMessage(e, "Conversion failed."));
    } finally {
      setBusy(null);
    }
  };

  const save = async () => {
    if (!draft) return;
    setBusy("save");
    try {
      const s = await api.saveStructuredResume(draft);
      setState(s);
      setDraft(null);
      toast.success("Structured resume confirmed.");
    } catch (e) {
      toast.error(errorMessage(e, "Could not save."));
    } finally {
      setBusy(null);
    }
  };

  if (state === undefined) {
    return (
      <section className="card flex items-center gap-2 p-5 text-xs text-slate-400">
        <Spinner /> Loading structured resume…
      </section>
    );
  }

  return (
    <section className="card space-y-4 p-5" aria-label="Structured resume">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <ListChecks className="h-4 w-4 text-indigo-400" aria-hidden /> Structured resume
            {state?.confirmed && !draft && (
              <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                <CheckCircle2 className="h-3 w-3" aria-hidden /> Confirmed
              </span>
            )}
            {state && !state.confirmed && <span className="chip border-amber-500/30 bg-amber-500/10 text-amber-300">Needs review</span>}
          </h3>
          <p className="mt-1 max-w-xl text-xs text-slate-400">
            A clean, sectioned copy of your resume. Job matching and tailored resumes use this, so check it once. Tailoring can only
            reorder and reword what's here, never add to it.
          </p>
        </div>
        <div className="flex gap-2">
          {draft ? (
            <>
              {state?.confirmed && (
                <button type="button" className="btn btn-ghost" onClick={() => setDraft(null)} disabled={!!busy}>
                  <X className="h-4 w-4" aria-hidden /> Cancel
                </button>
              )}
              <button type="button" className="btn btn-primary" onClick={save} disabled={!!busy}>
                {busy === "save" ? <Spinner /> : <Save className="h-4 w-4" aria-hidden />} Save &amp; confirm
              </button>
            </>
          ) : state ? (
            <button type="button" className="btn btn-secondary" onClick={() => setDraft(state.resume)}>
              <Pencil className="h-4 w-4" aria-hidden /> Edit
            </button>
          ) : (
            <button type="button" className="btn btn-primary" onClick={convert} disabled={!hasResume || !!busy}>
              {busy === "convert" ? <Spinner /> : <Wand2 className="h-4 w-4" aria-hidden />} Create from my resume
            </button>
          )}
        </div>
      </div>

      {state?.stale && (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
          <span className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" aria-hidden /> Your resume changed since this was built.
          </span>
          <button type="button" className="btn btn-secondary !py-1.5" onClick={convert} disabled={!!busy}>
            {busy === "convert" ? <Spinner /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden />} Rebuild from new resume
          </button>
        </div>
      )}

      {busy === "convert" && (
        <p className="flex items-center gap-2 text-xs text-slate-400" role="status">
          <Spinner /> Reading your resume… this takes 10–30 seconds.
        </p>
      )}

      {draft ? (
        <StructuredResumeEditor value={draft} onChange={setDraft} />
      ) : state ? (
        <dl className="grid gap-3 text-xs sm:grid-cols-4">
          {[
            ["Experience", state.resume.experience.length],
            ["Projects", state.resume.projects.length],
            ["Education", state.resume.education.length],
            ["Skills", state.resume.skills.reduce((n, s) => n + s.items.length, 0)],
          ].map(([k, v]) => (
            <div key={String(k)} className="rounded-xl border border-slate-800 bg-slate-950 p-3">
              <dt className="text-slate-500">{k}</dt>
              <dd className="text-lg font-bold text-slate-100">{v}</dd>
            </div>
          ))}
          <p className="text-[11px] text-slate-500 sm:col-span-4">Updated {timeAgo(state.updated_at.replace("T", " "))}</p>
        </dl>
      ) : (
        !hasResume && <p className="text-xs text-slate-500">Upload a resume PDF first.</p>
      )}
    </section>
  );
}
