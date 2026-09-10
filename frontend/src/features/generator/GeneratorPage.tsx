import { Plus, RefreshCw, Sparkles, XCircle } from "lucide-react";
import type { MessageCardData, TargetRow } from "../../types";
import { MessageCards } from "./components/MessageCards";
import { ProgressBanner } from "./components/ProgressBanner";
import { TargetTable } from "./components/TargetTable";

type Props = {
  rows: TargetRow[];
  generatedCards: MessageCardData[];
  isGenerating: boolean;
  genProgressStage: string;
  elapsedSeconds: number;
  enrichCache: Record<string, unknown>;
  expandedCards: Record<string, boolean>;
  openHistoryDrawers: Record<string, boolean>;
  tweakInputs: Record<string, string>;
  copiedUrl: string | null;
  historyData: Record<string, unknown>;
  onAddRow: () => void;
  onRemoveRow: (id: string) => void;
  onUpdateRow: (id: string, field: keyof TargetRow, val: string) => void;
  onGenerate: () => void;
  onStop: () => void;
  onToggleExpand: (url: string) => void;
  onCopy: (text: string, url: string) => void;
  onRetry: (card: MessageCardData, idx: number) => void;
  onRegenerate: (card: MessageCardData, idx: number) => void;
  onTweakChange: (url: string, val: string) => void;
  onToggleHistory: (url: string) => void;
};

export function GeneratorPage({
  rows,
  generatedCards,
  isGenerating,
  genProgressStage,
  elapsedSeconds,
  enrichCache,
  expandedCards,
  openHistoryDrawers,
  tweakInputs,
  copiedUrl,
  historyData,
  onAddRow,
  onRemoveRow,
  onUpdateRow,
  onGenerate,
  onStop,
  onToggleExpand,
  onCopy,
  onRetry,
  onRegenerate,
  onTweakChange,
  onToggleHistory,
}: Props) {
  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Batch Outreach Generator</h2>
          <p className="text-xs text-slate-400">Queue target LinkedIn profile URLs and notes to generate personalized AI outreach messages.</p>
        </div>
        <button
          onClick={onAddRow}
          className="flex items-center gap-2 rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-all"
        >
          <Plus className="h-4 w-4" /> Add Target Row
        </button>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur shadow-xl space-y-4">
        <TargetTable rows={rows} onAddRow={onAddRow} onRemoveRow={onRemoveRow} onUpdateRow={onUpdateRow} />
        <ProgressBanner isGenerating={isGenerating} stage={genProgressStage} elapsedSeconds={elapsedSeconds} />
        <div className="flex justify-end pt-2 gap-3">
          <button
            onClick={onStop}
            disabled={!isGenerating}
            className="flex items-center gap-2 rounded-xl bg-rose-600/80 hover:bg-rose-600 px-5 py-3 text-xs font-semibold text-white shadow-lg transition-all disabled:opacity-30"
          >
            <XCircle className="h-4 w-4" /> Stop Generation
          </button>
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-xs font-semibold text-white shadow-lg hover:bg-indigo-500 disabled:opacity-50 transition-all"
          >
            {isGenerating ? <><RefreshCw className="h-4 w-4 animate-spin" /> Generating Outreach...</> : <><Sparkles className="h-4 w-4" /> Generate All Outreach ({rows.length})</>}
          </button>
        </div>
      </div>

      <MessageCards
        generatedCards={generatedCards}
        rows={rows}
        enrichCache={enrichCache}
        expandedCards={expandedCards}
        openHistoryDrawers={openHistoryDrawers}
        tweakInputs={tweakInputs}
        copiedUrl={copiedUrl}
        historyData={historyData as Record<string, { generations?: Array<{ generated_message: string; generated_at: string }> }>}
        onToggleExpand={onToggleExpand}
        onCopy={onCopy}
        onRetry={onRetry}
        onRegenerate={onRegenerate}
        onTweakChange={onTweakChange}
        onToggleHistory={onToggleHistory}
      />
    </div>
  );
}
