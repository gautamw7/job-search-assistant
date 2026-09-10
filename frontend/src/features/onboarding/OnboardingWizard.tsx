import { AlertCircle, ArrowRight, Check, Copy, RefreshCw, Sparkles, Upload } from "lucide-react";

type Props = {
  step: number;
  resumeFile: File | null;
  styleText: string;
  fullPrompt: string;
  isUploading: boolean;
  isSaving: boolean;
  error: string | null;
  copiedUrl: string | null;
  onFileChange: (f: File | null) => void;
  onUpload: (e: React.FormEvent) => void;
  onSaveStyle: (e: React.FormEvent) => void;
  onStyleChange: (v: string) => void;
  onCopy: (text: string, url: string) => void;
  onBack: () => void;
};

export function OnboardingWizard({
  step,
  resumeFile,
  styleText,
  fullPrompt,
  isUploading,
  isSaving,
  error,
  copiedUrl,
  onFileChange,
  onUpload,
  onSaveStyle,
  onStyleChange,
  onCopy,
  onBack,
}: Props) {
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-[#080b12] p-6">
      <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900/90 p-8 shadow-2xl backdrop-blur-xl">
        <div className="mb-6 flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-indigo-500/10 p-2.5 text-indigo-400">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100">Welcome to Job Search Assistant</h1>
              <p className="text-xs text-slate-400">Initial Setup & Profile Onboarding</p>
            </div>
          </div>
          <div className="flex gap-1.5">
            <span className={`h-2.5 w-8 rounded-full ${step === 1 ? "bg-indigo-500" : "bg-slate-700"}`} />
            <span className={`h-2.5 w-8 rounded-full ${step === 2 ? "bg-indigo-500" : "bg-slate-700"}`} />
          </div>
        </div>

        {step === 1 ? (
          <form onSubmit={onUpload} className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Step 1: Upload Your Resume (PDF)</h2>
              <p className="mt-1 text-xs text-slate-400">Your resume is parsed into Markdown and powers all tailored outreach generations.</p>
            </div>
            <label className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 bg-slate-950/50 p-8 cursor-pointer hover:border-indigo-500 transition-all">
              <Upload className="mb-3 h-10 w-10 text-indigo-400" />
              <span className="text-sm font-medium text-slate-300">{resumeFile ? resumeFile.name : "Click to select resume PDF"}</span>
              <span className="mt-1 text-xs text-slate-500">PDF format only</span>
              <input type="file" accept=".pdf" className="hidden" onChange={(e) => e.target.files && onFileChange(e.target.files[0])} />
            </label>
            {error && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 flex items-start gap-2.5">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <div><span className="font-semibold block mb-0.5">Resume Validation Failed</span><span>{error}</span></div>
              </div>
            )}
            <div className="flex justify-end">
              <button type="submit" disabled={!resumeFile || isUploading} className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-indigo-500 disabled:opacity-50 transition-all">
                {isUploading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <>Continue <ArrowRight className="h-4 w-4" /></>}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={onSaveStyle} className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Step 2: Communication Style & Tone</h2>
              <p className="mt-1 text-xs text-slate-400">Define how you want your outreach messages to sound.</p>
            </div>
            {fullPrompt && (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-3 flex items-center justify-between">
                <span className="text-xs text-slate-400">Need the full analyst prompt? </span>
                <button type="button" onClick={() => onCopy(fullPrompt, "onboarding-prompt")} className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 text-xs font-semibold shadow transition-all">
                  {copiedUrl === "onboarding-prompt" ? <><Check className="h-3.5 w-3.5 text-emerald-300" /> Copied Prompt!</> : <><Copy className="h-3.5 w-3.5" /> Copy Prompt</>}
                </button>
              </div>
            )}
            <div className="relative group">
              <textarea
                rows={6}
                value={styleText}
                onChange={(e) => onStyleChange(e.target.value)}
                placeholder="e.g. - Greeting: Hey [Name]&#10;- Tone: Professional yet conversational"
                className="w-full rounded-xl border border-slate-800 bg-slate-950 p-4 pr-12 text-sm text-slate-200 focus:border-indigo-500 focus:outline-none"
                required
              />
              <button type="button" onClick={() => onCopy(styleText, "onboarding-style")} className="absolute top-3 right-3 flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3 py-1.5 text-xs font-semibold shadow transition-all">
                {copiedUrl === "onboarding-style" ? <><Check className="h-3.5 w-3.5 text-emerald-400" /> Copied!</> : <><Copy className="h-3.5 w-3.5" /> Copy</>}
              </button>
            </div>
            <div className="flex justify-between">
              <button type="button" onClick={onBack} className="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-700">Back</button>
              <button type="submit" disabled={isSaving} className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-indigo-500 disabled:opacity-50 transition-all">
                {isSaving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <>Complete Setup <Sparkles className="h-4 w-4" /></>}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
