import { AlertTriangle, CheckCircle2, ExternalLink, KeyRound, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
import { api } from "../../api";
import { PageHeader, Spinner } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import type { KeyService } from "../../types";
import { UsagePanel } from "./UsagePanel";

type CardProps = {
  service: KeyService;
  title: string;
  purpose: string;
  help: { label: string; href: string };
  icon: ReactNode;
  masked: string | null;
  onChanged: () => void;
};

function KeyCard({ service, title, purpose, help, icon, masked, onChanged }: CardProps) {
  const toast = useToast();
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    setSaving(true);
    setNote(null);
    try {
      const r = await api.saveKey(service, value.trim());
      setValue("");
      onChanged();
      if (r.verified === false) setNote({ ok: false, text: r.message });
      else {
        setNote({ ok: true, text: "Key saved and verified." });
        toast.success(`${title} key saved.`);
      }
    } catch (err) {
      setNote({ ok: false, text: errorMessage(err, "Could not save the key.") });
    } finally {
      setSaving(false);
    }
  };

  const check = async () => {
    setChecking(true);
    setNote(null);
    try {
      await api.testKey(service);
      setNote({ ok: true, text: "The stored key works." });
    } catch (err) {
      setNote({ ok: false, text: errorMessage(err, "The stored key failed validation.") });
    } finally {
      setChecking(false);
    }
  };

  return (
    <section className="card space-y-4 p-6" aria-label={`${title} API key`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            {icon} {title}
          </h3>
          <p className="mt-1 text-xs text-slate-400">{purpose}</p>
        </div>
        <span
          className={`chip shrink-0 ${masked ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-amber-500/30 bg-amber-500/10 text-amber-300"}`}
        >
          {masked ? "Saved" : "Not set"}
        </span>
      </div>

      {masked && (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5">
          <code className="text-xs text-slate-300">{masked}</code>
          <button type="button" className="btn btn-secondary !py-1.5" onClick={check} disabled={checking}>
            {checking ? <Spinner /> : <KeyRound className="h-3.5 w-3.5" aria-hidden />} Check
          </button>
        </div>
      )}

      <form onSubmit={save} className="space-y-3">
        <label htmlFor={`key-${service}`} className="sr-only">
          {title} API key
        </label>
        <input
          id={`key-${service}`}
          type="password"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={masked ? "Paste a new key to replace it" : `Paste your ${title} API key`}
          className="input"
        />
        <div className="flex items-center justify-between gap-3">
          <a href={help.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:underline">
            {help.label} <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
          <button type="submit" className="btn btn-primary" disabled={!value.trim() || saving}>
            {saving ? <Spinner /> : <ShieldCheck className="h-4 w-4" aria-hidden />} Save &amp; verify
          </button>
        </div>
      </form>

      {note && (
        <p
          role={note.ok ? "status" : "alert"}
          className={`flex items-start gap-2 rounded-xl border p-3 text-xs ${
            note.ok ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-amber-500/30 bg-amber-500/10 text-amber-100"
          }`}
        >
          {note.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />}
          {note.text}
        </p>
      )}
    </section>
  );
}

export function SettingsPage({
  masked,
  onChanged,
}: {
  masked: Record<KeyService, string | null>;
  onChanged: () => void;
}) {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Settings"
        subtitle="API keys are stored in your operating system's secure keyring and never shown again."
      />
      <KeyCard
        service="brightdata"
        title="BrightData"
        purpose="Fetches LinkedIn profile details (name, experience, recent posts)."
        help={{ label: "Get a BrightData key", href: "https://brightdata.com/cp/setting/users" }}
        icon={<ShieldCheck className="h-4 w-4 text-indigo-400" aria-hidden />}
        masked={masked.brightdata}
        onChanged={onChanged}
      />
      <KeyCard
        service="gemini"
        title="Gemini"
        purpose="Writes the outreach messages."
        help={{ label: "Get a Gemini key", href: "https://aistudio.google.com/apikey" }}
        icon={<Sparkles className="h-4 w-4 text-indigo-400" aria-hidden />}
        masked={masked.gemini}
        onChanged={onChanged}
      />
      <UsagePanel />
    </div>
  );
}
