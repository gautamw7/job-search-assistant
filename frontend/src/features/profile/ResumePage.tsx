import { AlertCircle, Check, Copy, RefreshCw, Upload } from "lucide-react";

type Props = {
  resumeMarkdown: string;
  copiedUrl: string | null;
  onCopy: (text: string, url: string) => void;
  onUpload?: (file: File) => void;
};

export function ResumePage({ resumeMarkdown, copiedUrl, onCopy }: Props) {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Resume & Profile</h2>
        <p className="text-xs text-slate-400">Your parsed resume in Markdown - powers all tailored outreach.</p>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">Parsed Resume</h3>
          <button
            onClick={() => onCopy(resumeMarkdown, "resume-md")}
            className="flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3 py-1.5 text-xs font-semibold"
          >
            {copiedUrl === "resume-md" ? <><Check className="h-3.5 w-3.5 text-emerald-400" /> Copied!</> : <><Copy className="h-3.5 w-3.5" /> Copy Markdown</>}
          </button>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 max-h-[60vh] overflow-y-auto">
          <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">{resumeMarkdown || "No resume uploaded yet."}</pre>
        </div>
      </div>
    </div>
  );
}
