import { ArrowDown, ArrowUp, HelpCircle, Plus, Save, Trash2, Wand2, X } from "lucide-react";
import { useState } from "react";
import { Spinner } from "../../components/ui";
import type { CompanyType, JobsMeta, ProfileQuestion, SearchProfile, Seniority } from "../../types";

type Props = {
  initial: SearchProfile;
  questions: ProfileQuestion[];
  meta: JobsMeta;
  onSave: (p: SearchProfile) => Promise<boolean>;
  onCancel?: () => void;
};

const csv = (v: string[]) => v.join(", ");
const fromCsv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const COMPANY_TYPES: { id: CompanyType; label: string }[] = [
  { id: "startup", label: "Startup" },
  { id: "scaleup", label: "Scale-up" },
  { id: "enterprise", label: "Large company" },
  { id: "any", label: "Any" },
];

/** The confirmed profile drives every search. Pre-filled by the LLM; the user decides. */
export function SearchProfileForm({ initial, questions, meta, onSave, onCancel }: Props) {
  const [p, setP] = useState<SearchProfile>(initial);
  const [titles, setTitles] = useState(csv(initial.titles));
  const [skills, setSkills] = useState(csv(initial.skills));
  const [answers, setAnswers] = useState<Record<string, string>>(() =>
    Object.fromEntries(initial.clarifications.map((c) => [c.question, c.answer])),
  );
  const [addCountry, setAddCountry] = useState("");
  const [saving, setSaving] = useState(false);
  const set = <K extends keyof SearchProfile>(k: K, v: SearchProfile[K]) => setP((prev) => ({ ...prev, [k]: v }));
  const countryName = (code: string) => meta.countries.find((c) => c.code === code)?.name ?? code.toUpperCase();
  const allQuestions = [
    ...questions.map((q) => q.question),
    ...initial.clarifications.map((c) => c.question).filter((q) => !questions.some((x) => x.question === q)),
  ];

  const moveCountry = (i: number, d: -1 | 1) => {
    const next = [...p.countries];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    set("countries", next);
  };

  const toggleType = (t: CompanyType) => {
    if (t === "any") return set("company_types", ["any"]);
    const current = p.company_types.filter((x) => x !== "any");
    const next = current.includes(t) ? current.filter((x) => x !== t) : [...current, t];
    set("company_types", next.length ? next : ["any"]);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    await onSave({
      ...p,
      titles: fromCsv(titles).slice(0, 5),
      skills: fromCsv(skills),
      languages: p.languages.filter((l) => l.name.trim()),
      clarifications: allQuestions.map((q) => ({ question: q, answer: answers[q] ?? "" })).filter((c) => c.answer.trim()),
    });
    setSaving(false);
  };

  const label = "text-[11px] font-medium text-slate-300";
  return (
    <form onSubmit={submit} className="card space-y-6 p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Wand2 className="h-4 w-4 text-indigo-400" aria-hidden /> Search profile
          </h3>
          <p className="mt-1 text-xs text-slate-400">Suggested from your resume. Check it, answer the questions, then save. Every search uses this.</p>
        </div>
        {onCancel && (
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            <X className="h-4 w-4" aria-hidden /> Cancel
          </button>
        )}
      </div>

      {allQuestions.length > 0 && (
        <fieldset className="space-y-3 rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4">
          <legend className="flex items-center gap-1.5 px-1 text-xs font-semibold text-indigo-200">
            <HelpCircle className="h-4 w-4" aria-hidden /> A few questions your resume can't answer
          </legend>
          {allQuestions.map((q) => {
            const options = questions.find((x) => x.question === q)?.options ?? [];
            return (
              <div key={q} className="space-y-1.5">
                <p className="text-xs text-slate-200">{q}</p>
                <div className="flex flex-wrap gap-2">
                  {options.map((o) => (
                    <button
                      key={o}
                      type="button"
                      onClick={() => setAnswers((a) => ({ ...a, [q]: o }))}
                      className={`btn !py-1 ${answers[q] === o ? "btn-primary" : "btn-ghost"}`}
                      aria-pressed={answers[q] === o}
                    >
                      {o}
                    </button>
                  ))}
                  <input
                    type="text"
                    value={options.includes(answers[q] ?? "") ? "" : (answers[q] ?? "")}
                    onChange={(e) => setAnswers((a) => ({ ...a, [q]: e.target.value }))}
                    placeholder={options.length ? "Or type your own answer" : "Your answer"}
                    aria-label={`Answer: ${q}`}
                    className="input !w-auto min-w-[14rem] flex-1"
                  />
                </div>
              </div>
            );
          })}
        </fieldset>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-1 sm:col-span-2">
          <span className={label}>Job titles to search (comma-separated, up to 5; the first 3 are searched)</span>
          <input className="input" value={titles} onChange={(e) => setTitles(e.target.value)} />
        </label>
        <label className="space-y-1">
          <span className={label}>Seniority</span>
          <select className="input" value={p.seniority} onChange={(e) => set("seniority", e.target.value as Seniority)}>
            {["intern", "entry", "junior", "mid", "senior"].map((s) => (
              <option key={s} value={s}>
                {s[0].toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className={label}>Work style</span>
          <select className="input" value={p.remote} onChange={(e) => set("remote", e.target.value as SearchProfile["remote"])}>
            <option value="any">Any</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">On-site</option>
          </select>
        </label>
        <label className="space-y-1 sm:col-span-2">
          <span className={label}>Key skills (comma-separated)</span>
          <input className="input" value={skills} onChange={(e) => setSkills(e.target.value)} />
        </label>
      </div>

      <fieldset className="space-y-2">
        <legend className={label}>Countries, most preferred first</legend>
        <ul className="space-y-1.5">
          {p.countries.map((c, i) => (
            <li key={c} className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-1.5 text-xs">
              <span className="w-5 text-slate-500">{i + 1}.</span>
              <span className="flex-1 text-slate-200">{countryName(c)}</span>
              {!meta.countries.find((x) => x.code === c)?.adzuna && <span className="text-[10px] text-slate-500">LinkedIn only</span>}
              <button type="button" className="btn btn-ghost !px-1.5 !py-1" onClick={() => moveCountry(i, -1)} disabled={i === 0} aria-label={`Move ${countryName(c)} up`}>
                <ArrowUp className="h-3 w-3" />
              </button>
              <button type="button" className="btn btn-ghost !px-1.5 !py-1" onClick={() => moveCountry(i, 1)} disabled={i === p.countries.length - 1} aria-label={`Move ${countryName(c)} down`}>
                <ArrowDown className="h-3 w-3" />
              </button>
              <button type="button" className="btn btn-ghost !px-1.5 !py-1 hover:!text-rose-400" onClick={() => set("countries", p.countries.filter((x) => x !== c))} aria-label={`Remove ${countryName(c)}`}>
                <Trash2 className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
        <div className="flex gap-2">
          <select className="input" value={addCountry} onChange={(e) => setAddCountry(e.target.value)} aria-label="Add a country">
            <option value="">Add a country…</option>
            {meta.countries
              .filter((c) => !p.countries.includes(c.code))
              .map((c) => (
                <option key={c.code} value={c.code}>
                  {c.name}
                  {c.adzuna ? "" : " (LinkedIn only)"}
                </option>
              ))}
          </select>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!addCountry}
            onClick={() => {
              set("countries", [...p.countries, addCountry]);
              setAddCountry("");
            }}
          >
            <Plus className="h-4 w-4" aria-hidden /> Add
          </button>
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className={label}>Company type</legend>
        <div className="flex flex-wrap gap-2">
          {COMPANY_TYPES.map((t) => (
            <button key={t.id} type="button" onClick={() => toggleType(t.id)} aria-pressed={p.company_types.includes(t.id)} className={`btn !py-1.5 ${p.company_types.includes(t.id) ? "btn-primary" : "btn-ghost"}`}>
              {t.label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className={label}>Languages (German level matters for jobs in Germany)</legend>
        {p.languages.map((lang, i) => (
          <div key={i} className="flex gap-2">
            <input className="input" value={lang.name} placeholder="Language" aria-label={`Language ${i + 1}`} onChange={(e) => set("languages", p.languages.map((l, j) => (j === i ? { ...l, name: e.target.value } : l)))} />
            <select className="input !w-36" value={lang.level} aria-label={`Level for language ${i + 1}`} onChange={(e) => set("languages", p.languages.map((l, j) => (j === i ? { ...l, level: e.target.value } : l)))}>
              <option value="">Level…</option>
              {meta.language_levels.map((lv) => (
                <option key={lv} value={lv}>
                  {lv === "native" ? "Native" : lv}
                </option>
              ))}
            </select>
            <button type="button" className="btn btn-ghost !px-2 hover:!text-rose-400" onClick={() => set("languages", p.languages.filter((_, j) => j !== i))} aria-label={`Remove language ${i + 1}`}>
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        <button type="button" className="btn btn-ghost" onClick={() => set("languages", [...p.languages, { name: "", level: "" }])}>
          <Plus className="h-4 w-4" aria-hidden /> Add language
        </button>
      </fieldset>

      <div className="grid gap-3 sm:grid-cols-2">
        {[
          ["needs_sponsorship", "I need visa sponsorship"],
          ["willing_to_relocate", "I'm willing to relocate"],
          ["hide_german_required", "Hide jobs that require German"],
        ].map(([key, text]) => (
          <label key={key} className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
            <input type="checkbox" className="h-3.5 w-3.5 accent-indigo-500" checked={Boolean(p[key as keyof SearchProfile])} onChange={(e) => set(key as "needs_sponsorship", e.target.checked)} />
            {text}
          </label>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <label className="space-y-1 sm:col-span-2">
          <span className={label}>Career direction (one line, used when ranking)</span>
          <input className="input" value={p.career_direction} onChange={(e) => set("career_direction", e.target.value)} placeholder="e.g. Move into ML engineering at a product startup in Germany" />
        </label>
        <label className="space-y-1">
          <span className={label}>Minimum salary (optional)</span>
          <div className="flex gap-2">
            <input
              type="number"
              min="0"
              className="input"
              value={p.min_salary?.amount ?? ""}
              onChange={(e) => set("min_salary", e.target.value ? { amount: Number(e.target.value), currency: p.min_salary?.currency ?? "EUR" } : null)}
              aria-label="Minimum salary amount"
            />
            <input className="input !w-20" value={p.min_salary?.currency ?? ""} placeholder="EUR" disabled={!p.min_salary} onChange={(e) => p.min_salary && set("min_salary", { ...p.min_salary, currency: e.target.value.toUpperCase() })} aria-label="Currency" />
          </div>
        </label>
      </div>

      <div className="flex justify-end">
        <button type="submit" className="btn btn-primary !px-5 !py-2.5" disabled={saving || !titles.trim() || !p.countries.length}>
          {saving ? <Spinner /> : <Save className="h-4 w-4" aria-hidden />} Save profile
        </button>
      </div>
    </form>
  );
}
