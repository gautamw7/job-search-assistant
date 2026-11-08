import { RotateCcw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api";
import { CopyButton, PageHeader, Spinner } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";

const MAX_CHARS = 8000;

type Props = {
  saved: string;
  source: "response" | "questions" | "default";
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  onSaved: () => void;
};

export function StylePage({ saved, source, copiedKey, onCopy, onSaved }: Props) {
  const toast = useToast();
  const [text, setText] = useState(saved);
  const [prompt, setPrompt] = useState({ prompt: "", default: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => setText(saved), [saved]);
  useEffect(() => {
    api.getStylePrompt().then(setPrompt).catch(() => undefined);
  }, []);

  const dirty = text.trim() !== saved.trim();
  const tooLong = text.length > MAX_CHARS;

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.saveStyle(text.trim(), "response");
      toast.success("Writing style saved.");
      onSaved();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save your style."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Writing style"
        subtitle="How your messages should sound — greeting, directness, length. Used for every generation."
        actions={
          <span
            className={`chip ${
              source === "default" ? "border-amber-500/30 bg-amber-500/10 text-amber-300" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
            }`}
          >
            {source === "default" ? "Using default style" : "Custom style"}
          </span>
        }
      />

      {prompt.prompt && (
        <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
          <p className="max-w-lg text-xs text-slate-400">
            Not sure how to describe your style? Paste this prompt into an AI assistant that knows you, then paste its answer below.
          </p>
          <CopyButton text={prompt.prompt} id="style-prompt" copiedKey={copiedKey} onCopy={onCopy} label="Copy analyst prompt" className="btn btn-primary" />
        </div>
      )}

      <form onSubmit={save} className="card space-y-3 p-5">
        <label htmlFor="style-text" className="text-xs font-medium text-slate-300">
          Your style guide
        </label>
        <textarea
          id="style-text"
          rows={12}
          value={text}
          onChange={(e) => setText(e.target.value)}
          className={`input leading-relaxed ${tooLong ? "input-error" : ""}`}
          placeholder={"- Greeting: Hey [Name],\n- Tone: warm but direct\n- Keep it under 100 words"}
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className={`text-[11px] ${tooLong ? "text-rose-400" : "text-slate-500"}`}>
            {text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
          </span>
          <div className="flex items-center gap-2">
            {prompt.default && (
              <button type="button" className="btn btn-ghost" onClick={() => setText(prompt.default)}>
                <RotateCcw className="h-4 w-4" aria-hidden /> Load default
              </button>
            )}
            <button type="submit" className="btn btn-primary" disabled={saving || !text.trim() || tooLong || !dirty}>
              {saving ? <Spinner /> : <Save className="h-4 w-4" aria-hidden />} Save style
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
