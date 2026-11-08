import { Briefcase, FileText, RefreshCw, Search, Settings2, Sparkles } from "lucide-react";
import { useState } from "react";
import { EmptyState, PageHeader, Spinner, formatCost } from "../../components/ui";
import type { JobListing, JobStatus } from "../../types";
import { JobCard } from "./JobCard";
import { SearchProfileForm } from "./SearchProfileForm";
import { TailorView } from "./TailorView";
import type { useJobs } from "./useJobs";

const STAGE_LABEL: Record<string, string> = {
  collecting: "Searching job sources",
  saving: "Saving listings",
  embedding: "Comparing jobs with your profile",
  scoring: "Scoring matches",
  details: "Reading full descriptions",
  reviewing: "AI review of the best matches",
  done: "Done",
};
const STATUS_TABS: { id: JobStatus; label: string }[] = [
  { id: "new", label: "New" },
  { id: "saved", label: "Saved" },
  { id: "applied", label: "Applied" },
  { id: "dismissed", label: "Not for me" },
];

type Props = {
  jobs: ReturnType<typeof useJobs>;
  onOpenTab: (tab: "resume" | "config") => void;
  onOutreach: (job: JobListing) => void;
};

export function JobsPage({ jobs: j, onOpenTab, onOutreach }: Props) {
  const [ambitions, setAmbitions] = useState("");
  const [editing, setEditing] = useState(false);
  const [tailoring, setTailoring] = useState<JobListing | null>(null);

  if (!j.meta || j.profile === undefined) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-slate-400">
        <Spinner /> Loading job search…
      </div>
    );
  }

  const header = <PageHeader title="Jobs" subtitle="Roles matched to your resume and goals, ranked by how well you fit." />;

  if (!j.meta.resume_confirmed) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        {header}
        <EmptyState
          icon={<FileText className="h-6 w-6" />}
          title="Confirm your structured resume first"
          body="Job matching works from the reviewed, structured copy of your resume."
          action={
            <button className="btn btn-primary" onClick={() => onOpenTab("resume")}>
              Go to Resume
            </button>
          }
        />
      </div>
    );
  }

  const noSources = !Object.values(j.meta.sources).some(Boolean);
  const needsProfile = !j.profile || !j.profile.confirmed || editing;

  if (needsProfile) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        {header}
        {!j.profile ? (
          <section className="card space-y-4 p-6">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
              <Sparkles className="h-4 w-4 text-indigo-400" aria-hidden /> Set up your job search
            </h3>
            <p className="text-xs text-slate-400">
              We'll read your resume and suggest titles, seniority, skills and countries. Tell us your ambitions first so the suggestion fits
              where you want to go, not only where you've been.
            </p>
            <label className="block space-y-1">
              <span className="text-[11px] font-medium text-slate-300">Your ambitions (optional)</span>
              <textarea
                rows={3}
                className="input"
                value={ambitions}
                onChange={(e) => setAmbitions(e.target.value)}
                placeholder="e.g. I want to move to Germany and join an early-stage startup in ML. I speak A2 German and will need a visa."
              />
            </label>
            <div className="flex justify-end">
              <button className="btn btn-primary" onClick={() => j.suggest(ambitions)} disabled={j.suggesting}>
                {j.suggesting ? <Spinner /> : <Sparkles className="h-4 w-4" aria-hidden />} Suggest my profile
              </button>
            </div>
          </section>
        ) : (
          <SearchProfileForm
            key={JSON.stringify(j.profile.profile)}
            initial={j.profile.profile}
            questions={j.questions}
            meta={j.meta}
            onSave={async (p) => {
              const ok = await j.saveProfile(p);
              if (ok) setEditing(false);
              return ok;
            }}
            onCancel={j.profile.confirmed ? () => setEditing(false) : undefined}
            onResuggest={() => j.suggest(ambitions)}
          />
        )}
      </div>
    );
  }

  if (tailoring) return <TailorView job={tailoring} onBack={() => setTailoring(null)} />;

  const profile = j.profile!.profile;
  const run = j.run;
  const running = run?.status === "running";
  const usage = run?.usage;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="Jobs"
        subtitle={`${profile.titles.slice(0, 3).join(" · ")} — ${profile.countries.map((c) => c.toUpperCase()).join(", ")}`}
        actions={
          <>
            <button className="btn btn-ghost" onClick={() => setEditing(true)} disabled={running}>
              <Settings2 className="h-4 w-4" aria-hidden /> Search profile
            </button>
            {run && run.status !== "running" && (
              <button className="btn btn-secondary" onClick={() => j.search(true)} disabled={noSources} title="Search again now (ignores the 24-hour cache)">
                <RefreshCw className="h-4 w-4" aria-hidden /> Refresh
              </button>
            )}
            <button className="btn btn-primary" onClick={() => j.search(false)} disabled={running || noSources}>
              {running ? <Spinner /> : <Search className="h-4 w-4" aria-hidden />} Find jobs
            </button>
          </>
        }
      />

      {j.profile?.stale && (
        <div role="alert" className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
          Your resume changed since this profile was made. Review the search profile so matches stay accurate.
        </div>
      )}

      {noSources && (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-100">
          <span>Add Adzuna (free) or Apify keys to search for jobs.</span>
          <button className="btn btn-secondary" onClick={() => onOpenTab("config")}>
            Open Settings
          </button>
        </div>
      )}

      {run && (running || run.notices.length > 0 || run.status === "failed") && (
        <section className="card space-y-2 p-4 text-xs" aria-live="polite">
          {running && (
            <p className="flex items-center gap-2 font-medium text-slate-200">
              <Spinner /> {STAGE_LABEL[run.stage] ?? run.stage}… <span className="font-normal text-slate-500">{run.message}</span>
            </p>
          )}
          {run.status === "failed" && <p className="text-rose-300">Search failed: {run.error}</p>}
          {run.notices.map((n) => (
            <p key={n} className="text-amber-200">
              • {n}
            </p>
          ))}
          {usage && !running && (
            <p className="text-slate-500">
              Last search: {usage.adzuna_calls ?? 0} Adzuna searches · {usage.apify_results ?? 0} LinkedIn jobs · {usage.gemini_calls} AI calls ·{" "}
              {formatCost(usage.estimated_cost, usage.free_tier_assumed)}
            </p>
          )}
        </section>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex gap-1.5" role="tablist" aria-label="Job status">
          {STATUS_TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={j.filters.status === t.id} onClick={() => j.setFilters((f) => ({ ...f, status: t.id }))} className={`btn !py-1.5 ${j.filters.status === t.id ? "btn-primary" : "btn-ghost"}`}>
              {t.label}
            </button>
          ))}
        </div>
        <select className="input !w-44 !py-1.5" value={j.filters.country} onChange={(e) => j.setFilters((f) => ({ ...f, country: e.target.value }))} aria-label="Filter by country">
          <option value="">All countries</option>
          {profile.countries.map((c) => (
            <option key={c} value={c}>
              {j.meta!.countries.find((x) => x.code === c)?.name ?? c.toUpperCase()}
            </option>
          ))}
        </select>
        <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-300">
          <input type="checkbox" className="h-3.5 w-3.5 accent-indigo-500" checked={j.filters.startupOnly} onChange={(e) => j.setFilters((f) => ({ ...f, startupOnly: e.target.checked }))} />
          Startups only
        </label>
        <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-300">
          <input type="checkbox" className="h-3.5 w-3.5 accent-indigo-500" checked={j.filters.hideGerman} onChange={(e) => j.setFilters((f) => ({ ...f, hideGerman: e.target.checked }))} />
          Hide German-required
        </label>
        <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-300">
          <input type="checkbox" className="h-3.5 w-3.5 accent-indigo-500" checked={j.filters.hideAbove} onChange={(e) => j.setFilters((f) => ({ ...f, hideAbove: e.target.checked }))} />
          Hide jobs above my level
        </label>
        {j.loadingJobs && <Spinner />}
      </div>

      {j.jobs.length === 0 && !j.loadingJobs ? (
        <EmptyState
          icon={<Briefcase className="h-6 w-6" />}
          title={run ? "No jobs in this view" : "No searches yet"}
          body={run ? "Try another filter, or run a fresh search." : "Click “Find jobs” to search Adzuna and LinkedIn for roles that match your profile."}
        />
      ) : (
        <div className="space-y-3">
          {j.jobs.map((job) => (
            <JobCard key={job.id} job={job} onStatus={j.setStatus} onOutreach={onOutreach} onTailor={setTailoring} />
          ))}
        </div>
      )}
    </div>
  );
}
