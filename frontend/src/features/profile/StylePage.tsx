import { Check, Copy } from "lucide-react";

type Props = {
  styleText: string;
  fullPrompt: string;
  copiedUrl: string | null;
  styleConfig: unknown;
  onStyleChange: (v: string) => void;
  onSave: (e: React.FormEvent) => void;
  onCopy: (text: string, url: string) => void;
  isSaving: boolean;
};

export function StylePage({ styleText, fullPrompt, copiedUrl, onStyleChange, onSave, onCopy, isSaving }: Props) {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Communication Style</h2>
        <p className="text-xs text-slate-400">Define how your outreach messages should sound - tone, directness, formatting.</p>
      </div>

      {fullPrompt && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-3 flex items-center justify-between">
          <span className="text-xs text-slate-400">Full analyst prompt</span>
          <button type="button" onClick={() => onCopy(fullPrompt, "style-prompt")} className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 text-xs font-semibold">
            {copiedUrl === "style-prompt" ? <><Check className="h-3.5 w-3.5" /> Copied!</> : <><Copy className="h-3.5 w-3.5" /> Copy Prompt</>}
          </button>
        </div>
      )}

      <form onSubmit={onSave} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="relative group">
          <textarea
            rows={10}
            value={styleText}
            onChange={(e) => onStyleChange(e.target.value)}
            placeholder="e.g. - Greeting: Hey [Name]&#10;- Tone: Professional yet conversational"
            className="w-full rounded-xl border border-slate-800 bg-slate-950 p-4 pr-12 text-sm text-slate-200 focus:border-indigo-500 focus:outline-none"
          />
          <button type="button" onClick={() => onCopy(styleText, "style-text")} className="absolute top-3 right-3 flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3 py-1.5 text-xs font-semibold">
            {copiedUrl === "style-text" ? <><Check className="h-3.5 w-3.5 text-emerald-400" /> Copied!</> : <><Copy className="h-3.5 w-3.5" /> Copy</>}
          </button>
        </div>
        <div className="flex justify-end">
          <button type="submit" disabled={isSaving} className="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
            {isSaving ? "Saving..." : "Save Style"}
          </button>
        </div>
      </form>
    </div>
  );
}
