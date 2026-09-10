import { Sparkles } from "lucide-react";

type Props = {
  isGenerating: boolean;
  stage: string;
  elapsedSeconds: number;
};

export function ProgressBanner({ isGenerating, stage, elapsedSeconds }: Props) {
  if (!isGenerating) return null;
  return (
    <div className="rounded-2xl border border-indigo-500/30 bg-indigo-500/10 p-6 space-y-3 backdrop-blur animate-pulse">
      <div className="flex items-center justify-between text-xs font-semibold text-indigo-300">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-400 animate-spin" />
          <span>{stage || "Processing Outreach Generation..."}</span>
        </div>
        <span className="font-mono bg-indigo-950/80 px-2.5 py-1 rounded-lg border border-indigo-500/30 text-indigo-200">
          ⏱️ {elapsedSeconds}s elapsed
        </span>
      </div>
      <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
        <div className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-full w-2/3 animate-pulse transition-all duration-500" />
      </div>
    </div>
  );
}
