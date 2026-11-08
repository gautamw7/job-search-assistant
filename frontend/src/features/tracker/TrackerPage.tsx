import { BellRing, ExternalLink, KanbanSquare, MessageSquarePlus, RefreshCw, Send } from "lucide-react";
import { useMemo, useState } from "react";
import { api } from "../../api";
import type { GeneratedResult } from "../../api";
import { FactCheckNotice } from "../../components/messages";
import { Avatar, CopyButton, EmptyState, PageHeader, Spinner } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import { initials, profileHandle, timeAgo } from "../../lib/format";
import type { Contact, ContactStatus, ProfileCard } from "../../types";
import type { useTracker } from "./useTracker";

const STATUS_LABEL: Record<ContactStatus, string> = {
  drafted: "Drafted",
  sent: "Sent",
  replied: "Replied",
  interviewing: "Interviewing",
  closed: "Closed",
};
const STATUS_STYLE: Record<ContactStatus, string> = {
  drafted: "border-slate-700 bg-slate-800/60 text-slate-300",
  sent: "border-sky-500/30 bg-sky-500/10 text-sky-300",
  replied: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  interviewing: "border-violet-500/30 bg-violet-500/10 text-violet-300",
  closed: "border-slate-700 bg-slate-900 text-slate-500",
};
type Filter = ContactStatus | "all" | "due";

type Props = {
  tracker: ReturnType<typeof useTracker>;
  cards: Record<string, ProfileCard>;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  onHistoryChanged: () => void;
};

export function TrackerPage({ tracker, cards, copiedKey, onCopy, onHistoryChanged }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: tracker.contacts.length, due: tracker.dueCount };
    for (const contact of tracker.contacts) c[contact.status] = (c[contact.status] ?? 0) + 1;
    return c;
  }, [tracker.contacts, tracker.dueCount]);

  const visible = useMemo(() => {
    const list = tracker.contacts.filter((c) =>
      filter === "all" ? true : filter === "due" ? c.followup_due : c.status === filter,
    );
    // Due follow-ups first, then most recently touched.
    return list.sort(
      (a, b) =>
        Number(b.followup_due) - Number(a.followup_due) ||
        String(b.updated_at ?? b.latest_at ?? "").localeCompare(String(a.updated_at ?? a.latest_at ?? "")),
    );
  }, [tracker.contacts, filter]);

  const toast = useToast();
  const [markingSent, setMarkingSent] = useState(false);
  const drafted = counts.drafted ?? 0;
  const markAllSent = async () => {
    const urls = tracker.contacts.filter((c) => c.status === "drafted").map((c) => c.linkedin_url);
    if (!urls.length || !window.confirm(`Mark ${urls.length} drafted message${urls.length === 1 ? "" : "s"} as sent? Follow-up reminders start from today.`)) return;
    setMarkingSent(true);
    try {
      const r = await api.bulkUpdateContacts(urls, "sent");
      toast.success(`Marked ${r.updated} as sent.`);
      tracker.refresh();
    } catch (e) {
      toast.error(errorMessage(e, "Could not update those contacts."));
    } finally {
      setMarkingSent(false);
    }
  };

  const filters: { id: Filter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "due", label: "Follow-up due" },
    ...(Object.keys(STATUS_LABEL) as ContactStatus[]).map((s) => ({ id: s as Filter, label: STATUS_LABEL[s] })),
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="Outreach tracker"
        subtitle={`Mark messages as sent; a follow-up is suggested after ${tracker.followupDays} days without a reply.`}
        actions={
          <>
            {drafted > 0 && (
              <button type="button" className="btn btn-primary" onClick={markAllSent} disabled={markingSent}>
                {markingSent ? <Spinner /> : <Send className="h-4 w-4" aria-hidden />} Mark {drafted} drafted as sent
              </button>
            )}
            <button type="button" className="btn btn-secondary" onClick={tracker.refresh} disabled={tracker.loading}>
              {tracker.loading ? <Spinner /> : <RefreshCw className="h-4 w-4" aria-hidden />} Refresh
            </button>
          </>
        }
      />

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter contacts">
        {filters.map((f) => (
          <button
            key={f.id}
            role="tab"
            aria-selected={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`btn !py-1.5 ${filter === f.id ? "btn-primary" : "btn-ghost"} ${f.id === "due" && counts.due ? "!border-amber-500/50" : ""}`}
          >
            {f.id === "due" && <BellRing className="h-3.5 w-3.5" aria-hidden />}
            {f.label}
            <span className="rounded-full bg-black/25 px-1.5 text-[10px]">{counts[f.id] ?? 0}</span>
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <EmptyState
          icon={<KanbanSquare className="h-6 w-6" />}
          title={tracker.contacts.length ? "Nobody in this view" : "No contacts yet"}
          body={tracker.contacts.length ? "Try another filter." : "Generate a message, then mark it as sent to start tracking."}
        />
      ) : (
        <ul className="space-y-3">
          {visible.map((c) => (
            <ContactRow
              key={c.linkedin_url}
              contact={c}
              card={cards[c.linkedin_url]}
              copiedKey={copiedKey}
              onCopy={onCopy}
              onUpdate={tracker.update}
              onHistoryChanged={onHistoryChanged}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function ContactRow({
  contact: c,
  card,
  copiedKey,
  onCopy,
  onUpdate,
  onHistoryChanged,
}: {
  contact: Contact;
  card?: ProfileCard;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  onUpdate: ReturnType<typeof useTracker>["update"];
  onHistoryChanged: () => void;
}) {
  const toast = useToast();
  const [notes, setNotes] = useState(c.notes);
  const [showFollowup, setShowFollowup] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [draft, setDraft] = useState<GeneratedResult | null>(null);
  const name = card?.name || profileHandle(c.linkedin_url);
  const headline = [card?.position, card?.current_company_name].filter(Boolean).join(" · ");
  const canFollowUp = c.status === "sent";

  const writeFollowup = async () => {
    setDrafting(true);
    try {
      setDraft(await api.followup(c.linkedin_url, instruction.trim()));
      onHistoryChanged();
    } catch (e) {
      toast.error(errorMessage(e, "Could not write a follow-up."));
    } finally {
      setDrafting(false);
    }
  };

  const markFollowupSent = async () => {
    if (await onUpdate(c.linkedin_url, { followup_sent: true })) {
      toast.success("Follow-up marked as sent.");
      setDraft(null);
      setShowFollowup(false);
    }
  };

  const contactLine =
    c.status === "drafted"
      ? `Drafted ${timeAgo(c.latest_at)}`
      : c.days_since_contact !== null
        ? `Last contact ${c.days_since_contact === 0 ? "today" : `${c.days_since_contact} d ago`}${c.followup_count ? ` · ${c.followup_count} follow-up${c.followup_count > 1 ? "s" : ""}` : ""}`
        : "";

  return (
    <li className={`card overflow-hidden ${c.followup_due ? "!border-amber-500/40" : ""}`}>
      <div className="flex flex-wrap items-start gap-3 p-4">
        <Avatar text={initials(name)} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <a href={c.linkedin_url} target="_blank" rel="noreferrer" className="truncate text-sm font-semibold text-slate-100 hover:underline">
              {name}
            </a>
            <ExternalLink className="h-3 w-3 text-slate-500" aria-hidden />
            {c.followup_due && (
              <span className="chip border-amber-500/40 bg-amber-500/10 text-amber-200">
                <BellRing className="h-3 w-3" aria-hidden /> Follow-up due
              </span>
            )}
          </div>
          {headline && <p className="truncate text-xs text-slate-400">{headline}</p>}
          <p className="mt-1 text-[11px] text-slate-500">{contactLine}</p>
        </div>
        <label className="sr-only" htmlFor={`status-${c.linkedin_url}`}>
          Status for {name}
        </label>
        <select
          id={`status-${c.linkedin_url}`}
          value={c.status}
          onChange={(e) => onUpdate(c.linkedin_url, { status: e.target.value as ContactStatus })}
          className={`input !w-40 ${STATUS_STYLE[c.status]}`}
        >
          {(Object.keys(STATUS_LABEL) as ContactStatus[]).map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-3 border-t border-slate-800 bg-slate-900/30 p-4">
        <div>
          <div className="mb-1.5 flex items-center justify-between text-[11px] text-slate-500">
            <span>{c.latest_kind === "followup" ? "Latest follow-up" : "Message"}</span>
            <CopyButton text={c.latest_message} id={`t-${c.linkedin_url}`} copiedKey={copiedKey} onCopy={onCopy} className="btn btn-ghost !px-2 !py-1" />
          </div>
          <p className="line-clamp-3 whitespace-pre-wrap text-xs leading-relaxed text-slate-300">{c.latest_message}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {c.status === "drafted" && (
            <button type="button" className="btn btn-primary" onClick={() => onUpdate(c.linkedin_url, { status: "sent" })}>
              <Send className="h-3.5 w-3.5" aria-hidden /> Mark as sent
            </button>
          )}
          {canFollowUp && (
            <button type="button" className={`btn ${c.followup_due ? "btn-primary" : "btn-secondary"}`} onClick={() => setShowFollowup((v) => !v)} aria-expanded={showFollowup}>
              <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden /> Write follow-up
            </button>
          )}
        </div>

        {showFollowup && (
          <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Optional: mention I'm free next week, add my new project…"
                aria-label={`Follow-up instruction for ${name}`}
                className="input"
              />
              <button type="button" className="btn btn-primary shrink-0" onClick={writeFollowup} disabled={drafting}>
                {drafting ? <Spinner /> : <MessageSquarePlus className="h-4 w-4" aria-hidden />} {draft ? "Rewrite" : "Write"}
              </button>
            </div>
            {draft && (
              <>
                <FactCheckNotice check={draft.fact_check} />
                <p className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm leading-relaxed text-slate-100">
                  {draft.generated_message}
                </p>
                <div className="flex justify-end gap-2">
                  <CopyButton text={draft.generated_message} id={`fu-${c.linkedin_url}`} copiedKey={copiedKey} onCopy={onCopy} />
                  <button type="button" className="btn btn-primary" onClick={markFollowupSent}>
                    <Send className="h-3.5 w-3.5" aria-hidden /> Mark follow-up sent
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        <textarea
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={() => notes !== c.notes && onUpdate(c.linkedin_url, { notes })}
          placeholder="Notes (saved when you click away): referral offered, call booked for Tue…"
          aria-label={`Notes for ${name}`}
          className="input"
        />
      </div>
    </li>
  );
}
