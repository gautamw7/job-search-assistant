import { AlertCircle, ArrowRight, FileText, Sparkles, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { CopyButton, Spinner } from "../../components/ui";
import { errorMessage } from "../../lib/http";

type Props = {
  needsResume: boolean;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  onRefresh: () => Promise<void> | void;
  onSkipStyle: () => void;
};

/** Step is derived from what is actually missing, so it can never get out of sync. */
export function OnboardingWizard({ needsResume, copiedKey, onCopy, onRefresh, onSkipStyle }: Props) {
  const step = needsResume ? 1 : 2;
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [style, setStyle] = useState("");
  const [prompt, setPrompt] = useState("");

  useEffect(() => {
    api.getStylePrompt().then((p) => setPrompt(p.prompt)).catch(() => undefined);
  }, []);

  const pick = (f: File | undefined) => {
    if (!f) return;
    setError(null);
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    setFile(f);
  };

  const uploadResume = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await api.uploadResume(file);
      await onRefresh();
    } catch (err) {
      setError(errorMessage(err, "Resume upload failed."));
    } finally {
      setBusy(false);
    }
  };

  const saveStyle = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.saveStyle(style.trim(), "response");
      await onRefresh();
    } catch (err) {
      setError(errorMessage(err, "Could not save your style."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full w-full overflow-y-auto bg-[#080b12] p-6">
      {/* m-auto centers when there is room and scrolls (instead of clipping) when there is not. */}
      <div className="card m-auto w-full max-w-xl space-y-6 !bg-slate-900/90 p-8 backdrop-blur-xl">
        <header className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-indigo-500/10 p-2.5 text-indigo-400">
              <Sparkles className="h-6 w-6" aria-hidden />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100">Welcome to Job Search Assistant</h1>
              <p className="text-xs text-slate-400">Two quick steps and you're ready to write.</p>
            </div>
          </div>
          <ol className="flex gap-1.5" aria-label={`Step ${step} of 2`}>
            {[1, 2].map((n) => (
              <li key={n} className={`h-2 w-8 rounded-full ${n <= step ? "bg-indigo-500" : "bg-slate-700"}`} />
            ))}
          </ol>
        </header>

        {step === 1 ? (
          <form onSubmit={uploadResume} className="space-y-5">
            <div>
              <h2 className="text-sm font-semibold text-slate-200">1. Upload your resume (PDF)</h2>
              <p className="mt-1 text-xs text-slate-400">It's converted to text and used to personalize every message.</p>
            </div>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                pick(e.dataTransfer.files[0]);
              }}
              className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors ${
                dragging ? "border-indigo-400 bg-indigo-500/10" : "border-slate-700 bg-slate-950/50"
              }`}
            >
              {file ? <FileText className="mb-3 h-9 w-9 text-emerald-400" aria-hidden /> : <Upload className="mb-3 h-9 w-9 text-indigo-400" aria-hidden />}
              <p className="text-sm font-medium text-slate-200">{file ? file.name : "Drag your PDF here"}</p>
              <button type="button" className="btn btn-secondary mt-3" onClick={() => fileRef.current?.click()}>
                {file ? "Choose a different file" : "Browse files"}
              </button>
              <input ref={fileRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
            </div>
            {error && <ErrorBox title="That didn't work" text={error} />}
            <div className="flex justify-end">
              <button type="submit" className="btn btn-primary !px-5 !py-2.5" disabled={!file || busy}>
                {busy ? <Spinner /> : <>Continue <ArrowRight className="h-4 w-4" aria-hidden /></>}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={saveStyle} className="space-y-5">
            <div>
              <h2 className="text-sm font-semibold text-slate-200">2. Describe how you write</h2>
              <p className="mt-1 text-xs text-slate-400">
                Greeting, tone, how direct you are, length. You can also skip this and use a sensible default.
              </p>
            </div>
            {prompt && (
              <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <span className="text-xs text-slate-400">Let an AI that knows you draft it:</span>
                <CopyButton text={prompt} id="onboarding-prompt" copiedKey={copiedKey} onCopy={onCopy} label="Copy prompt" className="btn btn-primary" />
              </div>
            )}
            <textarea
              rows={7}
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              aria-label="Your writing style"
              placeholder={"- Greeting: Hey [Name],\n- Tone: warm but direct\n- Under 100 words"}
              className="input"
            />
            {error && <ErrorBox title="Couldn't save" text={error} />}
            <div className="flex items-center justify-between">
              <button type="button" className="btn btn-ghost" onClick={onSkipStyle} disabled={busy}>
                Use the default for now
              </button>
              <button type="submit" className="btn btn-primary !px-5 !py-2.5" disabled={busy || !style.trim()}>
                {busy ? <Spinner /> : <>Finish setup <Sparkles className="h-4 w-4" aria-hidden /></>}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function ErrorBox({ title, text }: { title: string; text: string }) {
  return (
    <div role="alert" className="flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-200">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>
        <span className="mb-0.5 block font-semibold">{title}</span>
        {text}
      </div>
    </div>
  );
}
