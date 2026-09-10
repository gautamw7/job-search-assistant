import { AlertCircle, CheckCircle, Key, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";

type Props = {
  brightdataKey: string;
  geminiKey: string;
  brightdataStatus: string;
  geminiStatus: string;
  brightdataTestStatus: string;
  geminiTestStatus: string;
  brightdataError: string | null;
  geminiError: string | null;
  brightdataTestError: string | null;
  geminiTestError: string | null;
  savedBrightdataKey: string | null;
  savedGeminiKey: string | null;
  onBrightdataChange: (v: string) => void;
  onGeminiChange: (v: string) => void;
  onSaveBrightdata: (e: React.FormEvent) => void;
  onSaveGemini: (e: React.FormEvent) => void;
  onTestBrightdata: () => void;
  onTestGemini: () => void;
  maskKey: (k: string) => string;
};

export function SettingsPage({
  brightdataKey,
  geminiKey,
  brightdataStatus,
  geminiStatus,
  brightdataTestStatus,
  geminiTestStatus,
  brightdataError,
  geminiError,
  brightdataTestError,
  geminiTestError,
  savedBrightdataKey,
  savedGeminiKey,
  onBrightdataChange,
  onGeminiChange,
  onSaveBrightdata,
  onSaveGemini,
  onTestBrightdata,
  onTestGemini,
  maskKey,
}: Props) {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">API Keys</h2>
        <p className="text-xs text-slate-400">Store and test your API credentials. Keys are saved securely in your system keyring.</p>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-indigo-400" /> BrightData API Key</h3>
        <p className="text-xs text-slate-400">Used for LinkedIn profile enrichment.</p>
        {savedBrightdataKey && (
          <div className="space-y-3 mb-4">
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 flex items-center justify-between">
              <span className="text-xs font-mono text-emerald-300">{maskKey(savedBrightdataKey)}</span>
              <span className="rounded-full bg-emerald-500/20 text-emerald-400 px-2 py-0.5 text-[10px] font-medium">Saved</span>
            </div>
            <button type="button" onClick={onTestBrightdata} disabled={brightdataTestStatus === "testing"} className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 disabled:opacity-50">
              {brightdataTestStatus === "testing" ? <><RefreshCw className="h-4 w-4 animate-spin" /> Checking...</> : <><Key className="h-4 w-4" /> Check Stored Key</>}
            </button>
            {brightdataTestStatus === "success" && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2"><CheckCircle className="h-4 w-4" /> Stored key valid!</div>}
            {brightdataTestStatus === "error" && brightdataTestError && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2"><AlertCircle className="h-4 w-4" /> {brightdataTestError}</div>}
          </div>
        )}
        <form onSubmit={onSaveBrightdata} className="space-y-3">
          <input type="password" value={brightdataKey} onChange={(e) => onBrightdataChange(e.target.value)} placeholder="Enter BrightData API key" className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none" />
          {brightdataStatus === "error" && brightdataError && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2"><AlertCircle className="h-4 w-4" /> {brightdataError}</div>}
          {brightdataStatus === "success" && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2"><CheckCircle className="h-4 w-4" /> Key saved!</div>}
          <button type="submit" disabled={!brightdataKey.trim() || brightdataStatus === "testing"} className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
            {brightdataStatus === "testing" ? <><RefreshCw className="h-4 w-4 animate-spin" /> Testing...</> : <><ShieldCheck className="h-4 w-4" /> Save & Test</>}
          </button>
        </form>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2"><Sparkles className="h-4 w-4 text-indigo-400" /> Gemini API Key</h3>
        <p className="text-xs text-slate-400">Used for generating outreach messages.</p>
        {savedGeminiKey && (
          <div className="space-y-3 mb-4">
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 flex items-center justify-between">
              <span className="text-xs font-mono text-emerald-300">{maskKey(savedGeminiKey)}</span>
              <span className="rounded-full bg-emerald-500/20 text-emerald-400 px-2 py-0.5 text-[10px] font-medium">Saved</span>
            </div>
            <button type="button" onClick={onTestGemini} disabled={geminiTestStatus === "testing"} className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 disabled:opacity-50">
              {geminiTestStatus === "testing" ? <><RefreshCw className="h-4 w-4 animate-spin" /> Checking...</> : <><Key className="h-4 w-4" /> Check Stored Key</>}
            </button>
            {geminiTestStatus === "success" && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2"><CheckCircle className="h-4 w-4" /> Stored key valid!</div>}
            {geminiTestStatus === "error" && geminiTestError && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2"><AlertCircle className="h-4 w-4" /> {geminiTestError}</div>}
          </div>
        )}
        <form onSubmit={onSaveGemini} className="space-y-3">
          <input type="password" value={geminiKey} onChange={(e) => onGeminiChange(e.target.value)} placeholder="Enter Gemini API key" className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none" />
          {geminiStatus === "error" && geminiError && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2"><AlertCircle className="h-4 w-4" /> {geminiError}</div>}
          {geminiStatus === "success" && <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2"><CheckCircle className="h-4 w-4" /> Key saved!</div>}
          <button type="submit" disabled={!geminiKey.trim() || geminiStatus === "testing"} className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
            {geminiStatus === "testing" ? <><RefreshCw className="h-4 w-4 animate-spin" /> Testing...</> : <><Sparkles className="h-4 w-4" /> Save & Test</>}
          </button>
        </form>
      </div>
    </div>
  );
}
