import { ClipboardPaste, Plus, Send, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";
import { PageHeader, Spinner } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import type { HistoryEntry, ProfileCard } from "../../types";
import { ProgressPanel } from "./components/ProgressPanel";
import { ResultCard } from "./components/ResultCard";
import { TargetTable } from "./components/TargetTable";
import type { useGenerator } from "./useGenerator";

type Props = {
  gen: ReturnType<typeof useGenerator>;
  history: Record<string, HistoryEntry>;
  cards: Record<string, ProfileCard>;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  missingKeys: string[];
  onOpenSettings: () => void;
  onMarkSent: (url: string) => void;
};

export function GeneratorPage({ gen, history, cards, copiedKey, onCopy, missingKeys, onOpenSettings, onMarkSent }: Props) {
  const toast = useToast();
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const invalid = Object.keys(gen.issues).length;
  const canGenerate = gen.readyCount > 0 && invalid === 0 && !gen.isRunning && missingKeys.length === 0;

  const applyPaste = () => {
    const added = gen.addUrls(pasteText);
    if (added) toast.success(`Added ${added} profile${added === 1 ? "" : "s"}.`);
    else toast.info("No new LinkedIn profile links found in that text.");
    setPasteText("");
    setPasteOpen(false);
  };

  return (
    <div
      className="mx-auto max-w-5xl space-y-6"
      onKeyDown={(e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && canGenerate) {
          e.preventDefault();
          gen.generate();
        }
      }}
    >
      <PageHeader
        title="Outreach generator"
        subtitle="Add LinkedIn profiles and get a personalized message for each one."
        actions={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setPasteOpen((o) => !o)} aria-expanded={pasteOpen}>
              <ClipboardPaste className="h-4 w-4" aria-hidden /> Paste links
            </button>
            <button type="button" className="btn btn-ghost" onClick={gen.clearRows} disabled={gen.isRunning}>
              <Trash2 className="h-4 w-4" aria-hidden /> Clear
            </button>
          </>
        }
      />

      {missingKeys.length > 0 && (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-100">
          <span>
            Add your <strong>{missingKeys.join(" and ")}</strong> API key{missingKeys.length > 1 ? "s" : ""} before generating.
          </span>
          <button type="button" className="btn btn-secondary" onClick={onOpenSettings}>
            Open API keys
          </button>
        </div>
      )}

      <section className="card space-y-4 p-5" aria-label="Targets">
        {pasteOpen && (
          <div className="space-y-2 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <label htmlFor="paste-links" className="text-xs font-medium text-slate-300">
              Paste any text containing LinkedIn profile links (one per line, a spreadsheet column, etc.)
            </label>
            <textarea
              id="paste-links"
              rows={4}
              autoFocus
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              className="input font-mono"
              placeholder={"https://www.linkedin.com/in/jane-doe\nhttps://www.linkedin.com/in/john-smith"}
            />
            <div className="flex justify-end gap-2">
              <button type="button" className="btn btn-ghost" onClick={() => setPasteOpen(false)}>
                Cancel
              </button>
              <button type="button" className="btn btn-primary" onClick={applyPaste} disabled={!pasteText.trim()}>
                Add profiles
              </button>
            </div>
          </div>
        )}

        <TargetTable rows={gen.rows} issues={gen.issues} disabled={gen.isRunning} onRemove={gen.removeRow} onUpdate={gen.updateRow} />

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4">
          <button type="button" className="btn btn-ghost" onClick={gen.addRow} disabled={gen.isRunning}>
            <Plus className="h-4 w-4" aria-hidden /> Add profile
          </button>
          <div className="flex items-center gap-3">
            <span className="hidden text-[11px] text-slate-500 sm:inline">
              {invalid ? `${invalid} link${invalid > 1 ? "s" : ""} need fixing` : "Ctrl/⌘ + Enter to generate"}
            </span>
            <button type="button" onClick={gen.generate} disabled={!canGenerate} className="btn btn-primary !px-5 !py-2.5">
              {gen.isRunning ? (
                <>
                  <Spinner /> Generating…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" aria-hidden /> Generate {gen.readyCount || ""} message
                  {gen.readyCount === 1 ? "" : "s"}
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      <ProgressPanel
        cards={gen.cards}
        done={gen.progress.done}
        total={gen.progress.total}
        elapsed={gen.elapsed}
        isRunning={gen.isRunning}
        usage={gen.job?.usage}
        onCancel={gen.cancel}
      />

      {gen.cards.length > 0 ? (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-200">Results</h3>
          {gen.cards
            .filter((c) => c.status === "success" || c.status === "failed" || c.generated_message || c.error)
            .map((c) => (
              <ResultCard
                key={c.linkedin_url}
                target={c}
                card={cards[c.linkedin_url]}
                versions={history[c.linkedin_url]?.generations ?? []}
                busy={!!gen.busy[c.linkedin_url]}
                copiedKey={copiedKey}
                onCopy={onCopy}
                onRetry={gen.retry}
                onRegenerate={gen.regenerate}
                onAddProfiles={(urls) => {
                  const added = gen.addUrls(urls.join("\n"));
                  toast.success(added ? `Added ${added} profile${added === 1 ? "" : "s"} to the generator.` : "Those profiles are already in your list.");
                }}
                onMarkSent={onMarkSent}
                tracking={history[c.linkedin_url]?.tracking?.status}
              />
            ))}
        </div>
      ) : (
        !gen.isRunning && (
          <p className="flex items-center justify-center gap-2 py-8 text-xs text-slate-500">
            <Send className="h-4 w-4" aria-hidden /> Your generated messages will appear here.
          </p>
        )
      )}
    </div>
  );
}
