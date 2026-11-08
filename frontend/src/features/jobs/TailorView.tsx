import { ArrowLeft, Download, FileCode, FileText, Hammer, Plus, Save, ShieldAlert, Sparkles, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { FactCheckNotice } from "../../components/messages";
import { PageHeader, Spinner } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import { timeAgo } from "../../lib/format";
import type { JobListing, StructuredResume, TailoredResume } from "../../types";
import { StructuredResumeEditor } from "../profile/StructuredResumeEditor";

type Busy = "create" | "save" | "pdf" | "export" | null;

/** One job's tailored resume: what changed, rule-check notes, fact check, editor, PDF. */
export function TailorView({ job, onBack }: { job: JobListing; onBack: () => void }) {
  const toast = useToast();
  const [versions, setVersions] = useState<TailoredResume[] | null>(null);
  const [current, setCurrent] = useState<TailoredResume | null>(null);
  const [draft, setDraft] = useState<StructuredResume | null>(null);
  const [busy, setBusy] = useState<Busy>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [compiler, setCompiler] = useState<{ available: boolean; compiler: string | null } | null>(null);

  const show = useCallback((t: TailoredResume | null) => {
    setCurrent(t);
    setDraft(t ? t.resume : null);
  }, []);

  useEffect(() => {
    Promise.all([api.listTailored(job.id), api.compilerStatus()])
      .then(([list, comp]) => {
        setVersions(list);
        setCompiler(comp);
        show(list[0] ?? null);
      })
      .catch((e) => toast.error(errorMessage(e, "Could not load tailored resumes.")));
  }, [job.id, show, toast]);

  // Load / refresh the PDF preview whenever the current version has a built PDF.
  useEffect(() => {
    let url: string | null = null;
    setPdfUrl(null);
    if (current?.has_pdf) {
      api
        .tailoredPdfBlob(current.id)
        .then((blob) => {
          url = URL.createObjectURL(blob);
          setPdfUrl(url);
        })
        .catch(() => undefined);
    }
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [current?.id, current?.has_pdf, current?.pdf_compiled_at]);

  const run = async <T,>(kind: Busy, work: () => Promise<T>, fail: string): Promise<T | null> => {
    setBusy(kind);
    try {
      return await work();
    } catch (e) {
      toast.error(errorMessage(e, fail));
      return null;
    } finally {
      setBusy(null);
    }
  };

  const create = async () => {
    const t = await run("create", () => api.createTailored(job.id), "Tailoring failed.");
    if (t) {
      setVersions((v) => [t, ...(v ?? [])]);
      show(t);
      toast.success("Tailored resume ready. Review it, then build the PDF.");
    }
  };

  const save = async (recheck: boolean) => {
    if (!current || !draft) return;
    const t = await run("save", () => api.updateTailored(current.id, draft, recheck), "Could not save.");
    if (t) {
      setVersions((v) => (v ?? []).map((x) => (x.id === t.id ? t : x)));
      show(t);
      toast.success(recheck ? "Saved and re-checked." : "Saved.");
    }
  };

  const buildPdf = async () => {
    if (!current) return;
    const t = await run("pdf", () => api.buildTailoredPdf(current.id), "Could not build the PDF.");
    if (t) {
      setVersions((v) => (v ?? []).map((x) => (x.id === t.id ? t : x)));
      show(t);
      toast.success(`PDF built with ${t.compiler ?? "LaTeX"}.`);
    }
  };

  const exportFile = async (kind: "pdf" | "tex") => {
    if (!current) return;
    const r = await run("export", () => api.exportTailored(current.id, kind), "Could not save the file.");
    if (r) toast.success(`Saved to ${r.path}`);
  };

  const remove = async () => {
    if (!current || !window.confirm("Delete this tailored version?")) return;
    await run("save", () => api.deleteTailored(current.id), "Could not delete.");
    const rest = (versions ?? []).filter((v) => v.id !== current.id);
    setVersions(rest);
    show(rest[0] ?? null);
  };

  const dirty = !!current && JSON.stringify(draft) !== JSON.stringify(current.resume);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <button type="button" className="btn btn-ghost mb-3" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" aria-hidden /> Back to jobs
        </button>
        <PageHeader
          title="Tailored resume"
          subtitle={`${job.title} · ${job.company}`}
          actions={
            current && (
              <>
                <button type="button" className="btn btn-ghost" onClick={create} disabled={!!busy} title="Make another tailored version">
                  <Plus className="h-4 w-4" aria-hidden /> New version
                </button>
                <button type="button" className="btn btn-ghost hover:!text-rose-400" onClick={remove} disabled={!!busy} aria-label="Delete this version">
                  <Trash2 className="h-4 w-4" aria-hidden />
                </button>
              </>
            )
          }
        />
      </div>

      {versions === null ? (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Spinner /> Loading…
        </div>
      ) : !current ? (
        <section className="card space-y-4 p-6">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Sparkles className="h-4 w-4 text-indigo-400" aria-hidden /> Tailor your resume for this role
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-xs text-slate-300">
            <li>Reorders and picks your most relevant experience, projects, bullets and skills for this job.</li>
            <li>Rewords bullets in the job's language, only where the fact is already in your resume.</li>
            <li>Never adds skills, numbers, roles or schools. A rule check removes anything new, and a fact check flags rewording that goes too far.</li>
          </ul>
          <div className="flex justify-end">
            <button type="button" className="btn btn-primary !px-5 !py-2.5" onClick={create} disabled={!!busy}>
              {busy === "create" ? <Spinner /> : <Sparkles className="h-4 w-4" aria-hidden />} Create tailored resume
            </button>
          </div>
          {busy === "create" && <p className="text-xs text-slate-400">Tailoring and fact-checking… this takes 20–60 seconds.</p>}
        </section>
      ) : (
        <>
          {versions.length > 1 && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-500">Versions:</span>
              {versions.map((v, i) => (
                <button key={v.id} type="button" onClick={() => show(v)} className={`btn !py-1 ${v.id === current.id ? "btn-primary" : "btn-ghost"}`}>
                  {versions.length - i} · {timeAgo(v.created_at.replace("T", " "))}
                </button>
              ))}
            </div>
          )}

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="card space-y-3 p-5 text-xs">
              <h3 className="text-sm font-semibold text-slate-100">What changed</h3>
              {current.changes.length ? (
                <ul className="list-disc space-y-1 pl-5 text-slate-300">
                  {current.changes.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-slate-500">No summary of changes.</p>
              )}
              {current.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {current.keywords.map((k) => (
                    <span key={k} className="chip border-sky-500/30 bg-sky-500/10 text-sky-200">
                      {k}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="card space-y-3 p-5 text-xs">
              <h3 className="text-sm font-semibold text-slate-100">Checks</h3>
              <FactCheckNotice check={current.fact_check} source="your base resume" />
              {current.guard_notes.length > 0 ? (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-amber-100">
                  <p className="mb-1 flex items-center gap-1.5 font-semibold">
                    <ShieldAlert className="h-4 w-4" aria-hidden /> Removed or flagged by the rule check
                  </p>
                  <ul className="list-disc space-y-0.5 pl-5">
                    {current.guard_notes.map((n) => (
                      <li key={n}>{n}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-emerald-300">Rule check: no new roles, skills, schools or numbers.</p>
              )}
            </div>
          </section>

          <section className="card space-y-4 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
                <FileText className="h-4 w-4 text-indigo-400" aria-hidden /> PDF
                {current.has_pdf && <span className="text-[11px] font-normal text-slate-500">built {timeAgo(current.pdf_compiled_at?.replace("T", " "))}</span>}
              </h3>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="btn btn-primary" onClick={buildPdf} disabled={!!busy || dirty || !compiler?.available} title={dirty ? "Save your edits first" : undefined}>
                  {busy === "pdf" ? <Spinner /> : <Hammer className="h-4 w-4" aria-hidden />} {current.has_pdf ? "Rebuild PDF" : "Build PDF"}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => exportFile("pdf")} disabled={!!busy || !current.has_pdf}>
                  <Download className="h-4 w-4" aria-hidden /> Save PDF to Downloads
                </button>
                <button type="button" className="btn btn-ghost" onClick={() => exportFile("tex")} disabled={!!busy}>
                  <FileCode className="h-4 w-4" aria-hidden /> Save .tex
                </button>
              </div>
            </div>
            {!compiler?.available && (
              <p className="text-xs text-amber-200">No LaTeX compiler found. Install TeX Live or run "make fetch-tectonic"; you can still save the .tex file.</p>
            )}
            {busy === "pdf" && <p className="text-xs text-slate-400">Building… the very first build downloads LaTeX packages and can take a few minutes.</p>}
            {pdfUrl ? (
              <object data={pdfUrl} type="application/pdf" className="h-[75vh] w-full rounded-xl border border-slate-800 bg-white" aria-label="PDF preview">
                <p className="p-4 text-xs text-slate-600">This window can't preview PDFs. Use "Save PDF to Downloads" to open it.</p>
              </object>
            ) : (
              current.has_pdf || <p className="text-xs text-slate-500">Build the PDF to preview it here.</p>
            )}
          </section>

          {draft && (
            <section className="card space-y-4 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">Edit tailored content</h3>
                  <p className="text-[11px] text-slate-500">The rule check runs again when you save, so edits can't add new facts either.</p>
                </div>
                <div className="flex gap-2">
                  <button type="button" className="btn btn-secondary" onClick={() => save(true)} disabled={!!busy || !dirty}>
                    {busy === "save" ? <Spinner /> : <ShieldAlert className="h-4 w-4" aria-hidden />} Save &amp; re-check
                  </button>
                  <button type="button" className="btn btn-primary" onClick={() => save(false)} disabled={!!busy || !dirty}>
                    <Save className="h-4 w-4" aria-hidden /> Save
                  </button>
                </div>
              </div>
              <StructuredResumeEditor value={draft} onChange={setDraft} />
            </section>
          )}
        </>
      )}
    </div>
  );
}
