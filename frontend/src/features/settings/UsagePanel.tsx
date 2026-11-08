import { Gauge, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api";
import { Spinner, formatCost, formatTokens } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import type { UsageSettings, UsageSummary, UsageTotals } from "../../types";

type Form = {
  brightdata_per_profile: string;
  gemini_input_per_million: string;
  gemini_output_per_million: string;
  monthly_usd: string;
  monthly_profiles: string;
  fact_check_enabled: boolean;
};

const toText = (v: number | null) => (v === null || v === undefined ? "" : String(v));
const toNum = (v: string) => (v.trim() === "" ? null : Number(v));

function formFrom(s: UsageSettings): Form {
  return {
    brightdata_per_profile: toText(s.pricing.brightdata_per_profile),
    gemini_input_per_million: toText(s.pricing.gemini_input_per_million),
    gemini_output_per_million: toText(s.pricing.gemini_output_per_million),
    monthly_usd: toText(s.budget.monthly_usd),
    monthly_profiles: toText(s.budget.monthly_profiles),
    fact_check_enabled: s.fact_check_enabled,
  };
}

function Totals({ title, t }: { title: string; t: UsageTotals }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-lg font-bold text-slate-100">{formatCost(t.estimated_cost)}</p>
      <p className="text-[11px] text-slate-400">
        {t.brightdata_profiles} profiles · {t.gemini_calls} Gemini calls · {formatTokens(t.input_tokens + t.output_tokens)} tokens
      </p>
    </div>
  );
}

export function UsagePanel() {
  const toast = useToast();
  const [data, setData] = useState<UsageSummary | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .usage()
      .then((d) => {
        setData(d);
        setForm(formFrom(d.settings));
      })
      .catch((e) => toast.error(errorMessage(e, "Could not load usage.")));
  }, [toast]);

  if (!data || !form) {
    return (
      <section className="card flex items-center gap-2 p-6 text-xs text-slate-400">
        <Spinner /> Loading usage…
      </section>
    );
  }

  const invalid = (["brightdata_per_profile", "gemini_input_per_million", "gemini_output_per_million", "monthly_usd", "monthly_profiles"] as const).some(
    (k) => form[k].trim() !== "" && (Number.isNaN(Number(form[k])) || Number(form[k]) < 0),
  );

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const next = await api.saveUsageSettings({
        pricing: {
          brightdata_per_profile: toNum(form.brightdata_per_profile),
          gemini_input_per_million: toNum(form.gemini_input_per_million),
          gemini_output_per_million: toNum(form.gemini_output_per_million),
        },
        budget: { monthly_usd: toNum(form.monthly_usd), monthly_profiles: toNum(form.monthly_profiles) },
        fact_check_enabled: form.fact_check_enabled,
      });
      setData(next);
      setForm(formFrom(next.settings));
      toast.success("Usage settings saved.");
    } catch (err) {
      toast.error(errorMessage(err, "Could not save settings."));
    } finally {
      setSaving(false);
    }
  };

  const field = (key: keyof Omit<Form, "fact_check_enabled">, label: string, hint: string) => (
    <label className="space-y-1">
      <span className="text-[11px] font-medium text-slate-300">{label}</span>
      <input
        type="number"
        min="0"
        step="any"
        inputMode="decimal"
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        placeholder={hint}
        className="input"
      />
    </label>
  );

  const usdUnenforced = form.monthly_usd.trim() !== "" && !data.pricing_configured;

  return (
    <section className="card space-y-5 p-6" aria-label="Usage and budget">
      <div>
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
          <Gauge className="h-4 w-4 text-indigo-400" aria-hidden /> Usage &amp; budget
        </h3>
        <p className="mt-1 text-xs text-slate-400">
          Every profile scrape and Gemini call is counted. Enter your prices to see costs; limits stop new work before you overspend.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Totals title={`This month (${data.month.period})`} t={data.month} />
        <Totals title="Today" t={data.today} />
      </div>

      <form onSubmit={save} className="space-y-4">
        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold text-slate-300">Your prices (USD) — check your BrightData and Google AI billing pages</legend>
          <div className="grid gap-3 sm:grid-cols-3">
            {field("brightdata_per_profile", "BrightData, per profile", "e.g. 0.0015")}
            {field("gemini_input_per_million", "Gemini input, per 1M tokens", "e.g. 0.30")}
            {field("gemini_output_per_million", "Gemini output, per 1M tokens", "e.g. 2.50")}
          </div>
        </fieldset>
        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold text-slate-300">Monthly limits (leave empty for none)</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {field("monthly_usd", "Budget (USD)", "e.g. 5")}
            {field("monthly_profiles", "Profiles scraped", "e.g. 200")}
          </div>
          {usdUnenforced && (
            <p className="text-[11px] text-amber-300">The USD budget needs all three prices before it can be enforced. The profile limit works without prices.</p>
          )}
        </fieldset>
        <label className="flex cursor-pointer items-start gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={form.fact_check_enabled}
            onChange={(e) => setForm({ ...form, fact_check_enabled: e.target.checked })}
            className="mt-0.5 h-3.5 w-3.5 accent-indigo-500"
          />
          <span>
            Fact-check every message <span className="text-slate-500">(one extra Gemini call per message; flags claims not in your resume or their profile)</span>
          </span>
        </label>
        <div className="flex justify-end">
          <button type="submit" className="btn btn-primary" disabled={saving || invalid}>
            {saving ? <Spinner /> : <Save className="h-4 w-4" aria-hidden />} Save
          </button>
        </div>
      </form>
    </section>
  );
}
