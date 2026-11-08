import { Plus, Trash2 } from "lucide-react";
import type { StructuredResume } from "../../types";

/** How a field is edited: one line, one item per line, or comma-separated. */
type Kind = "text" | "lines" | "csv";
type FieldSpec<T> = { key: keyof T & string; label: string; kind?: Kind; wide?: boolean };

const toInput = (v: unknown, kind: Kind) =>
  kind === "lines" ? ((v as string[]) ?? []).join("\n") : kind === "csv" ? ((v as string[]) ?? []).join(", ") : String(v ?? "");

const fromInput = (raw: string, kind: Kind): string | string[] =>
  kind === "lines" ? raw.split("\n") : kind === "csv" ? raw.split(",").map((s) => s.trimStart()) : raw;

/** Lists are stored raw while typing; blanks are removed by the backend on save. */
function FieldInput<T>({ spec, item, onChange, idPrefix }: { spec: FieldSpec<T>; item: T; onChange: (v: string | string[]) => void; idPrefix: string }) {
  const kind = spec.kind ?? "text";
  const id = `${idPrefix}-${spec.key}`;
  return (
    <label htmlFor={id} className={`space-y-1 ${spec.wide || kind === "lines" ? "sm:col-span-2" : ""}`}>
      <span className="text-[11px] font-medium text-slate-400">
        {spec.label}
        {kind === "lines" && <span className="text-slate-600"> (one per line)</span>}
        {kind === "csv" && <span className="text-slate-600"> (comma-separated)</span>}
      </span>
      {kind === "lines" ? (
        <textarea id={id} rows={4} value={toInput(item[spec.key], kind)} onChange={(e) => onChange(fromInput(e.target.value, kind))} className="input leading-relaxed" />
      ) : (
        <input id={id} type="text" value={toInput(item[spec.key], kind)} onChange={(e) => onChange(fromInput(e.target.value, kind))} className="input" />
      )}
    </label>
  );
}

function ListSection<T extends object>({
  title,
  items,
  fields,
  blank,
  itemLabel,
  onChange,
}: {
  title: string;
  items: T[];
  fields: FieldSpec<T>[];
  blank: T;
  itemLabel: (item: T, i: number) => string;
  onChange: (items: T[]) => void;
}) {
  const update = (i: number, key: string, value: unknown) => onChange(items.map((it, j) => (j === i ? { ...it, [key]: value } : it)));
  return (
    <fieldset className="space-y-3">
      <legend className="mb-2 flex w-full items-center justify-between text-xs font-semibold uppercase tracking-wide text-slate-400">
        {title}
        <button type="button" className="btn btn-ghost !py-1 normal-case tracking-normal" onClick={() => onChange([...items, { ...blank }])}>
          <Plus className="h-3.5 w-3.5" aria-hidden /> Add
        </button>
      </legend>
      {items.length === 0 && <p className="text-xs text-slate-600">None.</p>}
      {items.map((item, i) => (
        <div key={i} className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/50 p-3">
          <div className="flex items-center justify-between">
            <span className="truncate text-xs font-medium text-slate-300">{itemLabel(item, i)}</span>
            <button type="button" className="btn btn-ghost !px-2 !py-1 hover:!text-rose-400" onClick={() => onChange(items.filter((_, j) => j !== i))} aria-label={`Remove ${itemLabel(item, i)}`}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {fields.map((f) => (
              <FieldInput key={f.key} spec={f} item={item} idPrefix={`${title}-${i}`} onChange={(v) => update(i, f.key, v)} />
            ))}
          </div>
        </div>
      ))}
    </fieldset>
  );
}

export function StructuredResumeEditor({ value, onChange }: { value: StructuredResume; onChange: (v: StructuredResume) => void }) {
  const set = <K extends keyof StructuredResume>(key: K, v: StructuredResume[K]) => onChange({ ...value, [key]: v });
  const contactFields: FieldSpec<StructuredResume["contact"]>[] = [
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "phone", label: "Phone" },
    { key: "location", label: "Location" },
    { key: "links", label: "Links", kind: "lines" },
  ];

  return (
    <div className="space-y-6">
      <fieldset className="space-y-3">
        <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Contact</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {contactFields.map((f) => (
            <FieldInput key={f.key} spec={f} item={value.contact} idPrefix="contact" onChange={(v) => set("contact", { ...value.contact, [f.key]: v })} />
          ))}
        </div>
      </fieldset>

      <label htmlFor="summary" className="block space-y-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Summary</span>
        <textarea id="summary" rows={3} value={value.summary} onChange={(e) => set("summary", e.target.value)} className="input leading-relaxed" />
      </label>

      <ListSection
        title="Experience"
        items={value.experience}
        blank={{ title: "", company: "", location: "", start: "", end: "", bullets: [] }}
        itemLabel={(x, i) => [x.title, x.company].filter(Boolean).join(" · ") || `Role ${i + 1}`}
        fields={[
          { key: "title", label: "Title" },
          { key: "company", label: "Company" },
          { key: "location", label: "Location" },
          { key: "start", label: "Start" },
          { key: "end", label: "End" },
          { key: "bullets", label: "Bullet points", kind: "lines" },
        ]}
        onChange={(v) => set("experience", v)}
      />

      <ListSection
        title="Projects"
        items={value.projects}
        blank={{ name: "", tech: [], link: "", bullets: [] }}
        itemLabel={(p, i) => p.name || `Project ${i + 1}`}
        fields={[
          { key: "name", label: "Name" },
          { key: "link", label: "Link" },
          { key: "tech", label: "Technologies", kind: "csv", wide: true },
          { key: "bullets", label: "Bullet points", kind: "lines" },
        ]}
        onChange={(v) => set("projects", v)}
      />

      <ListSection
        title="Education"
        items={value.education}
        blank={{ institution: "", degree: "", field: "", location: "", start: "", end: "", grade: "", highlights: [] }}
        itemLabel={(e, i) => e.institution || `School ${i + 1}`}
        fields={[
          { key: "institution", label: "Institution", wide: true },
          { key: "degree", label: "Degree" },
          { key: "field", label: "Field" },
          { key: "start", label: "Start" },
          { key: "end", label: "End" },
          { key: "grade", label: "Grade" },
          { key: "location", label: "Location" },
          { key: "highlights", label: "Highlights", kind: "lines" },
        ]}
        onChange={(v) => set("education", v)}
      />

      <ListSection
        title="Skills"
        items={value.skills}
        blank={{ category: "", items: [] }}
        itemLabel={(s, i) => s.category || `Skill group ${i + 1}`}
        fields={[
          { key: "category", label: "Category", wide: true },
          { key: "items", label: "Skills", kind: "csv", wide: true },
        ]}
        onChange={(v) => set("skills", v)}
      />

      <ListSection
        title="Languages"
        items={value.languages}
        blank={{ name: "", level: "" }}
        itemLabel={(l, i) => l.name || `Language ${i + 1}`}
        fields={[
          { key: "name", label: "Language" },
          { key: "level", label: "Level (e.g. Native, C1, A2)" },
        ]}
        onChange={(v) => set("languages", v)}
      />

      <label htmlFor="certs" className="block space-y-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Certifications <span className="normal-case tracking-normal text-slate-600">(one per line)</span>
        </span>
        <textarea id="certs" rows={3} value={value.certifications.join("\n")} onChange={(e) => set("certifications", e.target.value.split("\n"))} className="input" />
      </label>
    </div>
  );
}
