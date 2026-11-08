import { AlertTriangle, Briefcase, CheckCircle2, ExternalLink, KeyRound, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
import { api } from "../../api";
import { PageHeader, Spinner } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import type { KeyService } from "../../types";
import { UsagePanel } from "./UsagePanel";

type Field = { name: string; label: string; placeholder: string };

type CardProps = {
  service: KeyService;
  title: string;
  purpose: string;
  help: { label: string; href: string };
  icon: ReactNode;
  masked: string | null;
  /** Inputs sent to the backend; most keys have one ("api_key"). */
  fields?: Field[];
  onChanged: () => void;
};

function KeyCard({ service, title, purpose, help, icon, masked, fields, onChanged }: CardProps) {
  const toast = useToast();
  const inputs: Field[] = fields ?? [
    { name: "api_key", label: `${title} API key`, placeholder: masked ? "Paste a new key to replace it" : `Paste your ${title} API key` },
  ];
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);
  const complete = inputs.every((f) => (values[f.name] ?? "").trim());

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!complete) return;
    setSaving(true);
    setNote(null);
    try {
      const payload = Object.fromEntries(inputs.map((f) => [f.name, values[f.name].trim()]));
      const r = await api.saveKey(service, payload);
      setValues({});
      onChanged();
      if (r.verified === false) setNote({ ok: false, text: r.message });
      else {
        setNote({ ok: true, text: "Saved and verified." });
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
          <code className="truncate text-xs text-slate-300">{masked}</code>
          <button type="button" className="btn btn-secondary !py-1.5" onClick={check} disabled={checking}>
            {checking ? <Spinner /> : <KeyRound className="h-3.5 w-3.5" aria-hidden />} Check
          </button>
        </div>
      )}

      <form onSubmit={save} className="space-y-3">
        <div className={inputs.length > 1 ? "grid gap-3 sm:grid-cols-2" : ""}>
          {inputs.map((f) => (
            <div key={f.name}>
              <label htmlFor={`key-${service}-${f.name}`} className={inputs.length > 1 ? "mb-1 block text-[11px] font-medium text-slate-300" : "sr-only"}>
                {f.label}
              </label>
              <input
                id={`key-${service}-${f.name}`}
                type="password"
                autoComplete="off"
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                placeholder={f.placeholder}
                className="input"
              />
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between gap-3">
          <a href={help.href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:underline">
            {help.label} <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
          <button type="submit" className="btn btn-primary" disabled={!complete || saving}>
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
      <PageHeader title="Settings" subtitle="API keys are stored in your operating system's secure keyring and never shown again." />

      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Outreach</h3>
      <KeyCard
        service="brightdata"
        title="BrightData"
        purpose="Fetches LinkedIn profile details (name, education, recent posts)."
        help={{ label: "Get a BrightData key", href: "https://brightdata.com/cp/setting/users" }}
        icon={<ShieldCheck className="h-4 w-4 text-indigo-400" aria-hidden />}
        masked={masked.brightdata}
        onChanged={onChanged}
      />
      <KeyCard
        service="gemini"
        title="Gemini"
        purpose="Writes messages, checks facts and ranks jobs."
        help={{ label: "Get a Gemini key", href: "https://aistudio.google.com/apikey" }}
        icon={<Sparkles className="h-4 w-4 text-indigo-400" aria-hidden />}
        masked={masked.gemini}
        onChanged={onChanged}
      />

      <h3 className="pt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Job search</h3>
      <KeyCard
        service="adzuna"
        title="Adzuna"
        purpose="Free job listings for India. Needs both the App ID and the App key. Other countries are searched via LinkedIn (Apify)."
        help={{ label: "Get free Adzuna keys", href: "https://developer.adzuna.com/signup" }}
        icon={<Search className="h-4 w-4 text-indigo-400" aria-hidden />}
        masked={masked.adzuna}
        fields={[
          { name: "app_id", label: "App ID", placeholder: "e.g. 1a2b3c4d" },
          { name: "app_key", label: "App key", placeholder: "32-character key" },
        ]}
        onChanged={onChanged}
      />
      <KeyCard
        service="apify"
        title="Apify"
        purpose="LinkedIn job listings with full descriptions and company size. About $1 per 1,000 jobs; the free plan includes $5 a month."
        help={{ label: "Get an Apify token", href: "https://console.apify.com/settings/integrations" }}
        icon={<Briefcase className="h-4 w-4 text-indigo-400" aria-hidden />}
        masked={masked.apify}
        onChanged={onChanged}
      />

      <UsagePanel />
    </div>
  );
}
