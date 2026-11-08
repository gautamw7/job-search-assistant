import { Briefcase, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../../../api";
import { Spinner } from "../../../components/ui";
import { useToast } from "../../../context/ToastContext";
import { errorMessage } from "../../../lib/http";
import type { HiringContact } from "../../../types";

type Props = {
  url: string;
  onAddProfiles: (urls: string[]) => void;
};

/**
 * "People also viewed" for this profile. Bio hints are free; "Check for hiring posts"
 * scrapes the selected people in ONE BrightData request (each person costs one profile).
 */
export function HiringContacts({ url, onAddProfiles }: Props) {
  const toast = useToast();
  const [contacts, setContacts] = useState<HiringContact[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [checking, setChecking] = useState(false);

  const load = async () => {
    try {
      const list = await api.hiringContacts(url);
      setContacts(list);
      // Pre-select people with a free signal who haven't been checked yet.
      setSelected(new Set(list.filter((c) => c.signals.length && !c.checked).map((c) => c.linkedin_url)));
    } catch (e) {
      setError(errorMessage(e, "Could not load related people."));
    }
  };

  useEffect(() => {
    load();
  }, [url]); // eslint-disable-line react-hooks/exhaustive-deps

  const hiring = useMemo(() => (contacts ?? []).filter((c) => (c.hiring_posts ?? 0) > 0), [contacts]);
  const unchecked = useMemo(() => [...selected].filter((u) => !contacts?.find((c) => c.linkedin_url === u)?.checked), [selected, contacts]);

  const toggle = (u: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(u)) next.delete(u);
      else next.add(u);
      return next;
    });

  const check = async () => {
    if (!unchecked.length) return;
    setChecking(true);
    try {
      const results = await api.batchEnrich(unchecked);
      const found = Object.values(results).filter((r) => r.ok && (r.hiring_posts ?? 0) > 0).length;
      const failed = Object.values(results).filter((r) => !r.ok).length;
      toast[found ? "success" : "info"](
        `${found} of ${unchecked.length} ${found === 1 ? "is" : "are"} posting about hiring${failed ? ` (${failed} couldn't be scraped)` : ""}.`,
      );
      await load();
    } catch (e) {
      toast.error(errorMessage(e, "Hiring check failed."));
    } finally {
      setChecking(false);
    }
  };

  if (error) return <p className="text-xs text-rose-300">{error}</p>;
  if (!contacts) {
    return (
      <p className="flex items-center gap-2 text-xs text-slate-400">
        <Spinner /> Loading related people…
      </p>
    );
  }
  if (!contacts.length) return <p className="text-xs text-slate-500">LinkedIn didn't list any related people for this profile.</p>;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-slate-200">
          People also viewed ({contacts.length}){hiring.length > 0 && <span className="text-emerald-300"> · {hiring.length} hiring</span>}
        </p>
        <div className="flex gap-2">
          <button type="button" className="btn btn-secondary !py-1.5" onClick={check} disabled={checking || !unchecked.length}>
            {checking ? <Spinner /> : <Search className="h-3.5 w-3.5" aria-hidden />}
            Check {unchecked.length || ""} for hiring posts
          </button>
          <button
            type="button"
            className="btn btn-primary !py-1.5"
            disabled={!selected.size}
            onClick={() => onAddProfiles([...selected])}
          >
            <Plus className="h-3.5 w-3.5" aria-hidden /> Add {selected.size || ""} to generator
          </button>
        </div>
      </div>
      <p className="text-[11px] text-slate-500">
        Bio hints are free. Checking scrapes each selected person once (one BrightData profile each), in a single request.
      </p>
      <ul className="max-h-72 space-y-1.5 overflow-y-auto pr-1">
        {contacts.map((c) => (
          <li key={c.linkedin_url}>
            <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-2.5 hover:border-slate-700">
              <input
                type="checkbox"
                checked={selected.has(c.linkedin_url)}
                onChange={() => toggle(c.linkedin_url)}
                className="mt-0.5 h-3.5 w-3.5 accent-indigo-500"
                aria-label={`Select ${c.name}`}
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <a href={c.linkedin_url} target="_blank" rel="noreferrer" className="text-xs font-medium text-slate-100 hover:underline">
                    {c.name || c.linkedin_url}
                  </a>
                  {(c.hiring_posts ?? 0) > 0 && (
                    <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                      <Briefcase className="h-3 w-3" aria-hidden /> {c.hiring_posts} hiring post{c.hiring_posts === 1 ? "" : "s"}
                    </span>
                  )}
                  {c.checked && !c.hiring_posts && <span className="chip border-slate-700 text-slate-500">no hiring posts</span>}
                  {c.signals.map((s) => (
                    <span key={s} className="chip border-amber-500/30 bg-amber-500/10 text-amber-200">
                      {s}
                    </span>
                  ))}
                </div>
                {c.headline && <p className="truncate text-[11px] text-slate-400">{c.headline}</p>}
                {c.latest_hiring_post && <p className="mt-1 line-clamp-2 text-[11px] text-emerald-200/80">“{c.latest_hiring_post}”</p>}
              </div>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}
