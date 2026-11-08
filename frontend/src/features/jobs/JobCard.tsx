import { Bookmark, CheckCircle2, ChevronDown, ChevronUp, ExternalLink, FileText, MessageSquarePlus, Users, X } from "lucide-react";
import { useState } from "react";
import { api } from "../../api";
import { Spinner } from "../../components/ui";
import { timeAgo } from "../../lib/format";
import type { JobListing, JobStatus } from "../../types";

const FACTORS: [string, string][] = [
  ["similarity", "Profile match"],
  ["title", "Title"],
  ["skills", "Skills"],
  ["seniority", "Seniority"],
  ["location", "Location"],
  ["startup", "Company type"],
  ["recency", "Recency"],
];

function Badge({ tone, children, title }: { tone: "good" | "bad" | "warn" | "info" | "muted"; children: React.ReactNode; title?: string }) {
  const cls = {
    good: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    bad: "border-rose-500/40 bg-rose-500/10 text-rose-300",
    warn: "border-amber-500/30 bg-amber-500/10 text-amber-200",
    info: "border-sky-500/30 bg-sky-500/10 text-sky-300",
    muted: "border-slate-700 bg-slate-800/60 text-slate-400",
  }[tone];
  return (
    <span className={`chip ${cls}`} title={title}>
      {children}
    </span>
  );
}

function scoreTone(score: number) {
  return score >= 70 ? "text-emerald-300 border-emerald-500/40" : score >= 50 ? "text-amber-200 border-amber-500/40" : "text-slate-300 border-slate-700";
}

type Props = {
  job: JobListing;
  onStatus: (id: string, status: JobStatus) => void;
  onOutreach: (job: JobListing) => void;
  onTailor: (job: JobListing) => void;
};

export function JobCard({ job, onStatus, onOutreach, onTailor }: Props) {
  const [open, setOpen] = useState(false);
  const [people, setPeople] = useState<Awaited<ReturnType<typeof api.peopleAtCompany>> | null>(null);
  const [loadingPeople, setLoadingPeople] = useState(false);
  const review = job.review;
  const breakdown = (job.score_breakdown ?? {}) as Record<string, number | null>;
  const score = Math.round(job.score ?? 0);
  const salary =
    job.salary_min || job.salary_max
      ? `${job.salary_currency ?? ""} ${[job.salary_min, job.salary_max].filter(Boolean).map((n) => Math.round(Number(n) / 1000) + "k").join("–")}`
      : null;
  const linkedin = job.sources.find((s) => s.source === "apify");
  const adzuna = job.sources.find((s) => s.source === "adzuna");

  const loadPeople = async () => {
    setLoadingPeople(true);
    try {
      setPeople(await api.peopleAtCompany(job.id));
    } finally {
      setLoadingPeople(false);
    }
  };

  return (
    <article className="card overflow-hidden" aria-label={`${job.title} at ${job.company}`}>
      <div className="flex items-start gap-4 p-4">
        <div className={`flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-xl border bg-slate-950 ${scoreTone(score)}`} title="Match score (0–100)">
          <span className="text-lg font-bold leading-none">{score}</span>
          <span className="text-[9px] uppercase tracking-wide text-slate-500">match</span>
        </div>
        <div className="min-w-0 flex-1 space-y-1.5">
          <h3 className="text-sm font-semibold text-slate-100">{job.title}</h3>
          <p className="text-xs text-slate-400">
            {job.company || "Unknown company"} · {job.location || job.country.toUpperCase()}
            {job.posted_at && ` · ${timeAgo(job.posted_at.replace("T", " ").slice(0, 19))}`}
            {salary && ` · ${salary}`}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {job.above_level && (
              <Badge tone="bad" title={job.above_level_reason ?? undefined}>
                Above your level
              </Badge>
            )}
            {job.company_kind === "startup" && (
              <Badge tone="good" title={job.company_kind_verified ? `${job.company_size} employees` : "Guessed from the description"}>
                {job.company_kind_verified ? "Startup" : "Likely startup (unverified)"}
              </Badge>
            )}
            {job.company_kind === "scaleup" && <Badge tone="info">Scale-up{job.company_kind_verified ? "" : " (unverified)"}</Badge>}
            {job.german_required === "yes" && (
              <Badge tone={job.german_gap ? "bad" : "warn"}>German {review?.german_level || ""} required{job.german_gap ? " (above your level)" : ""}</Badge>
            )}
            {job.german_required === "no" && <Badge tone="good">English OK</Badge>}
            {job.sponsorship === "yes" && <Badge tone="good">Visa sponsorship mentioned</Badge>}
            {job.sponsorship === "no" && <Badge tone="bad">No sponsorship</Badge>}
            {job.remote && <Badge tone="muted">{job.remote}</Badge>}
            {job.applicants != null && <Badge tone="muted">{job.applicants} applicants</Badge>}
          </div>
          {review?.reasons?.length ? <p className="text-xs text-slate-300">{review.reasons.join(" · ")}</p> : null}
          {review?.missing_skills?.length ? <p className="text-[11px] text-amber-200/80">Missing: {review.missing_skills.join(", ")}</p> : null}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-slate-800 px-4 py-3">
        <button type="button" className="btn btn-primary !py-1.5" onClick={() => onTailor(job)}>
          <FileText className="h-3.5 w-3.5" aria-hidden /> Tailor resume
        </button>
        {job.status !== "saved" && (
          <button type="button" className="btn btn-secondary !py-1.5" onClick={() => onStatus(job.id, "saved")}>
            <Bookmark className="h-3.5 w-3.5" aria-hidden /> Save
          </button>
        )}
        {job.status !== "applied" && (
          <button type="button" className="btn btn-secondary !py-1.5" onClick={() => onStatus(job.id, "applied")}>
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> Applied
          </button>
        )}
        {job.status !== "dismissed" && (
          <button type="button" className="btn btn-ghost !py-1.5" onClick={() => onStatus(job.id, "dismissed")} title="Hide this job; it won't come back in later searches">
            <X className="h-3.5 w-3.5" aria-hidden /> Not for me
          </button>
        )}
        <button type="button" className="btn btn-ghost !py-1.5" onClick={() => onOutreach(job)}>
          <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden /> Write outreach about this role
        </button>
        <span className="ml-auto flex items-center gap-3 text-[11px]">
          {linkedin && (
            <a href={linkedin.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-indigo-400 hover:underline">
              LinkedIn <ExternalLink className="h-3 w-3" aria-hidden />
            </a>
          )}
          {adzuna && (
            // Adzuna's terms require this attribution link on each displayed job.
            <a href={adzuna.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-indigo-400 hover:underline">
              Jobs by Adzuna <ExternalLink className="h-3 w-3" aria-hidden />
            </a>
          )}
          <button type="button" className="inline-flex items-center gap-1 text-slate-400 hover:text-slate-100" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
            Details {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </span>
      </div>

      {open && (
        <div className="space-y-4 border-t border-slate-800 bg-slate-900/30 p-4 text-xs">
          <div>
            <p className="mb-2 font-semibold text-slate-300">Why this score</p>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 sm:grid-cols-4">
              {FACTORS.map(([key, name]) => {
                const v = typeof breakdown[key] === "number" ? (breakdown[key] as number) : null;
                return (
                  <div key={key}>
                    <dt className="flex justify-between text-slate-500">
                      {name} <span>{v === null ? "—" : Math.round(v * 100)}</span>
                    </dt>
                    <dd className="mt-0.5 h-1 overflow-hidden rounded-full bg-slate-800">
                      <div className="h-full bg-indigo-500" style={{ width: `${(v ?? 0) * 100}%` }} />
                    </dd>
                  </div>
                );
              })}
            </dl>
            {review?.fit != null && <p className="mt-2 text-slate-400">AI review fit: {review.fit}/100 (blended with the factors above)</p>}
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <p className="font-semibold text-slate-300">People at {job.company || "this company"}</p>
              {people === null && (
                <button type="button" className="btn btn-ghost !py-1" onClick={loadPeople} disabled={loadingPeople}>
                  {loadingPeople ? <Spinner /> : <Users className="h-3.5 w-3.5" aria-hidden />} Find in my tracker
                </button>
              )}
            </div>
            {people && people.length === 0 && <p className="text-slate-500">Nobody from your tracker works here yet.</p>}
            {people?.map((p) => (
              <a key={p.linkedin_url} href={p.linkedin_url} target="_blank" rel="noreferrer" className="block text-indigo-300 hover:underline">
                {p.name || p.linkedin_url} <span className="text-slate-500">· {p.position} · {p.status}</span>
              </a>
            ))}
          </div>

          <div>
            <p className="mb-1 font-semibold text-slate-300">
              Description {job.description_is_snippet && <span className="font-normal text-slate-500">(short preview from the source)</span>}
            </p>
            <p className="max-h-72 overflow-y-auto whitespace-pre-wrap leading-relaxed text-slate-300">{job.description || "No description."}</p>
          </div>
        </div>
      )}
    </article>
  );
}
