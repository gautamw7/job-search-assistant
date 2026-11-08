import {
  AlertCircle,
  Briefcase,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  History,
  RefreshCw,
  Send,
  Sparkles,
  Users,
} from "lucide-react";
import { useState } from "react";
import { api } from "../../../api";
import { FactCheckNotice, SharedBackground } from "../../../components/messages";
import { Avatar, CopyButton, Spinner } from "../../../components/ui";
import { initials, profileHandle, timeAgo, wordCount } from "../../../lib/format";
import type { ContactStatus, Generation, JobTarget, ProfileCard, ProfileDetails } from "../../../types";
import { HiringContacts } from "./HiringContacts";

type Props = {
  target: JobTarget;
  card?: ProfileCard;
  versions: Generation[];
  busy: boolean;
  copiedKey: string | null;
  tracking?: ContactStatus;
  onCopy: (text: string, key: string) => void;
  onRetry: (url: string) => void;
  onRegenerate: (url: string, note: string) => void;
  onAddProfiles: (urls: string[]) => void;
  onMarkSent: (url: string) => void;
};

type Panel = "signals" | "people" | "versions" | null;

export function ResultCard({
  target,
  card,
  versions,
  busy,
  copiedKey,
  tracking,
  onCopy,
  onRetry,
  onRegenerate,
  onAddProfiles,
  onMarkSent,
}: Props) {
  const url = target.linkedin_url;
  const [tweak, setTweak] = useState("");
  const [panel, setPanel] = useState<Panel>(null);
  const [details, setDetails] = useState<ProfileDetails | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const name = card?.name || profileHandle(url);
  const headline = [card?.position, card?.current_company_name].filter(Boolean).join(" · ");
  const ok = target.status === "success" && !!target.generated_message;
  const sent = tracking && tracking !== "drafted";

  const toggle = async (next: Exclude<Panel, null>) => {
    const opening = panel !== next;
    setPanel(opening ? next : null);
    if (opening && next === "signals" && !details) {
      setLoadingDetails(true);
      setDetails(await api.profile(url));
      setLoadingDetails(false);
    }
  };

  const submitTweak = () => {
    if (busy) return;
    onRegenerate(url, tweak.trim());
    setTweak("");
  };

  const PanelButton = ({ id, icon, label }: { id: Exclude<Panel, null>; icon: React.ReactNode; label: string }) => (
    <button
      type="button"
      onClick={() => toggle(id)}
      aria-expanded={panel === id}
      className={`inline-flex items-center gap-1.5 font-medium ${panel === id ? "text-slate-100" : "text-slate-400 hover:text-slate-100"}`}
    >
      {icon} {label}
      {panel === id ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
    </button>
  );

  return (
    <article className="card overflow-hidden" aria-label={`Result for ${name}`}>
      <header className="flex items-center gap-3 border-b border-slate-800 p-4">
        <Avatar text={initials(name)} />
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-slate-100">{name}</h3>
          <p className="truncate text-xs text-slate-400">{headline || url}</p>
        </div>
        {sent && <span className="chip border-emerald-500/30 bg-emerald-500/10 capitalize text-emerald-300">{tracking}</span>}
        <a href={url} target="_blank" rel="noreferrer" className="btn btn-ghost !px-2.5" aria-label={`Open ${name} on LinkedIn`}>
          <ExternalLink className="h-4 w-4" aria-hidden />
        </a>
      </header>

      <div className="space-y-4 p-4">
        {ok ? (
          <>
            <SharedBackground hooks={target.shared_background} />
            <FactCheckNotice check={target.fact_check} />
            <div className="relative">
              <p className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm leading-relaxed text-slate-100">
                {target.generated_message}
              </p>
              {busy && (
                <div className="absolute inset-0 flex items-center justify-center gap-2 rounded-xl bg-slate-950/80 text-xs text-slate-300">
                  <Spinner /> Rewriting…
                </div>
              )}
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
              <span>
                {wordCount(target.generated_message!)} words · {target.generated_message!.length} characters ·{" "}
                {timeAgo(target.generated_at) || "just now"}
              </span>
              <div className="flex gap-2">
                <button type="button" className="btn btn-secondary" onClick={() => onMarkSent(url)} disabled={!!sent}>
                  <Send className="h-3.5 w-3.5" aria-hidden /> {sent ? "Marked as sent" : "Mark as sent"}
                </button>
                <CopyButton
                  text={target.generated_message!}
                  id={`msg-${url}`}
                  copiedKey={copiedKey}
                  onCopy={onCopy}
                  label="Copy message"
                  className="btn btn-primary"
                />
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                submitTweak();
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={tweak}
                onChange={(e) => setTweak(e.target.value)}
                disabled={busy}
                placeholder="Refine it: shorter, mention my ML project, less formal…"
                aria-label={`Refine message for ${name}`}
                className="input"
              />
              <button type="submit" disabled={busy} className="btn btn-secondary shrink-0">
                {busy ? <Spinner /> : <Sparkles className="h-4 w-4" aria-hidden />} Refine
              </button>
            </form>
          </>
        ) : target.status === "failed" || target.error ? (
          <div role="alert" className="space-y-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-rose-200">
              <AlertCircle className="h-4 w-4" aria-hidden /> Couldn't generate this message
            </div>
            <p className="break-words rounded-lg bg-rose-950/50 p-3 font-mono text-xs text-rose-200/90">
              {target.error || "Unknown error."}
            </p>
            <button type="button" onClick={() => onRetry(url)} disabled={busy} className="btn btn-danger">
              {busy ? <Spinner /> : <RefreshCw className="h-4 w-4" aria-hidden />} Try again
            </button>
          </div>
        ) : (
          <p className="text-xs text-slate-500">Cancelled before this profile started.</p>
        )}

        <div className="flex flex-wrap gap-4 border-t border-slate-800 pt-3 text-xs">
          <PanelButton id="signals" icon={<Briefcase className="h-3.5 w-3.5" aria-hidden />} label="Profile & hiring posts" />
          <PanelButton id="people" icon={<Users className="h-3.5 w-3.5" aria-hidden />} label="Find hiring contacts" />
          {versions.length > 1 && (
            <PanelButton id="versions" icon={<History className="h-3.5 w-3.5" aria-hidden />} label={`${versions.length} versions`} />
          )}
        </div>

        {panel === "signals" && (
          <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-xs">
            {loadingDetails ? (
              <p className="flex items-center gap-2 text-slate-400">
                <Spinner /> Loading profile…
              </p>
            ) : !details?.card && !details?.activity ? (
              <p className="text-slate-500">No profile data is saved for this URL yet.</p>
            ) : (
              <>
                <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    ["Location", details.card?.location],
                    ["Followers", details.card?.followers],
                    ["Connections", details.card?.connections],
                    ["Company", details.card?.current_company_name],
                  ].map(([k, v]) => (
                    <div key={String(k)}>
                      <dt className="text-slate-500">{k}</dt>
                      <dd className="text-slate-200">{v ?? "—"}</dd>
                    </div>
                  ))}
                </dl>
                <div>
                  <p className="mb-1.5 font-semibold text-emerald-300">
                    Hiring posts used for personalization ({details.activity?.hiring.length ?? 0})
                  </p>
                  {details.activity?.hiring.length ? (
                    <ul className="space-y-2">
                      {details.activity.hiring.slice(0, 5).map((p, i) => (
                        <li key={i} className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-2.5">
                          <p className="whitespace-pre-wrap text-slate-200">{p.title}</p>
                          {p.link && (
                            <a href={p.link} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
                              View post →
                            </a>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-slate-500">No recent hiring posts detected.</p>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {panel === "people" && (
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <HiringContacts url={url} onAddProfiles={onAddProfiles} />
          </div>
        )}

        {panel === "versions" && (
          <ol className="space-y-2">
            {[...versions].reverse().map((v, i) => (
              <li key={v.generated_at + i} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <div className="mb-1.5 flex items-center justify-between text-[11px] text-slate-500">
                  <span>
                    {i === 0 ? "Latest" : `Version ${versions.length - i}`}
                    {v.kind === "followup" ? " · follow-up" : ""} · {timeAgo(v.generated_at)}
                  </span>
                  <CopyButton text={v.generated_message} id={`ver-${url}-${i}`} copiedKey={copiedKey} onCopy={onCopy} className="btn btn-ghost !px-2 !py-1" />
                </div>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-300">{v.generated_message}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </article>
  );
}
