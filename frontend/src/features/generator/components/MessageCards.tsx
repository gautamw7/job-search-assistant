import {
  AlertCircle,
  ArrowRight,
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  History,
  Layers,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserCheck,
} from "lucide-react";
import type { MessageCardData, TargetRow } from "../../../types";

type Props = {
  generatedCards: MessageCardData[];
  rows: TargetRow[];
  enrichCache: Record<string, unknown>;
  expandedCards: Record<string, boolean>;
  openHistoryDrawers: Record<string, boolean>;
  tweakInputs: Record<string, string>;
  copiedUrl: string | null;
  historyData: Record<string, { generations?: Array<{ generated_message: string; generated_at: string }> }>;
  onToggleExpand: (url: string) => void;
  onCopy: (text: string, url: string) => void;
  onRetry: (card: MessageCardData, idx: number) => void;
  onRegenerate: (card: MessageCardData, idx: number) => void;
  onTweakChange: (url: string, val: string) => void;
  onToggleHistory: (url: string) => void;
};

export function MessageCards({
  generatedCards,
  rows,
  enrichCache,
  expandedCards,
  openHistoryDrawers,
  tweakInputs,
  copiedUrl,
  historyData,
  onToggleExpand,
  onCopy,
  onRetry,
  onRegenerate,
  onTweakChange,
  onToggleHistory,
}: Props) {
  if (generatedCards.length === 0) return null;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Enriched Results ({generatedCards.length})</h3>
        <span className="text-xs text-slate-400">Click card to expand — shows card info, activity, posts, message, history</span>
      </div>
      {generatedCards.map((card, idx) => {
        const enrich = (enrichCache[card.linkedin_url] as { card?: Record<string, unknown>; activity?: { hiring: unknown[]; dropped: unknown[] }; discovery?: { people_also_viewed: Array<Record<string, string>> } }) || {};
        const cardInfo = (enrich.card as Record<string, string | number>) || null;
        const activity = enrich.activity || null;
        const discovery = enrich.discovery || null;
        const isExpanded = !!expandedCards[card.linkedin_url];
        const cardLetter = String.fromCharCode(65 + idx);
        const urlHistory = (historyData[card.linkedin_url] as { generations?: unknown[] })?.generations || [];
        const originalRow = rows.find((r) => r.linkedin_url === card.linkedin_url);
        const isHistoryOpen = openHistoryDrawers[card.linkedin_url] || false;
        return (
          <div key={idx} className="rounded-2xl border border-slate-800 bg-slate-900/80 overflow-hidden shadow-xl">
            <button
              onClick={() => onToggleExpand(card.linkedin_url)}
              className="w-full flex items-center justify-between p-4 hover:bg-slate-800/50 transition-all text-left"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-xs font-bold bg-indigo-600 text-white px-2.5 py-1 rounded-lg shrink-0">Card {cardLetter}</span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-100 truncate">
                      {(cardInfo?.name as string) || card.linkedin_url.split("/in/")[1]?.replace(/\/$/, "") || "LinkedIn Profile"}
                    </span>
                    <span className={`h-2 w-2 rounded-full shrink-0 ${card.status === "success" ? "bg-emerald-400" : "bg-rose-400"}`} />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400 truncate">
                    {cardInfo ? (
                      <>
                        <span className="flex items-center gap-1"><UserCheck className="h-3 w-3" /> {(cardInfo.current_company_name as string) || "—"}</span>
                        <span>•</span>
                        <span className="flex items-center gap-1"><Layers className="h-3 w-3" /> {(cardInfo.location as string) || "—"}</span>
                        <span>•</span>
                        <span>{(cardInfo.followers as number) ?? "—"} followers • {(cardInfo.connections as number) ?? "—"} conn.</span>
                      </>
                    ) : (
                      <span className="font-mono text-indigo-300 truncate">{card.linkedin_url}</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`hidden sm:inline rounded-full px-3 py-1 text-xs font-medium ${card.status === "success" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border border-rose-500/20"}`}>{card.status === "success" ? "Ready" : "Failed"}</span>
                {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
              </div>
            </button>
            {isExpanded && (
              <div className="border-t border-slate-800 p-6 space-y-6 bg-slate-900/40">
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-indigo-400" /> Card Details</h4>
                  {cardInfo ? (
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div><span className="text-slate-500">Name</span><p className="text-slate-200 font-medium">{(cardInfo.name as string) || "—"}</p></div>
                      <div><span className="text-slate-500">Position</span><p className="text-slate-200">{(cardInfo.position as string) || "—"}</p></div>
                      <div><span className="text-slate-500">Company</span><p className="text-slate-200">{(cardInfo.current_company_name as string) || "—"}</p></div>
                      <div><span className="text-slate-500">Location</span><p className="text-slate-200">{(cardInfo.location as string) || "—"}</p></div>
                      <div><span className="text-slate-500">Followers</span><p className="text-slate-200">{(cardInfo.followers as number) ?? "—"}</p></div>
                      <div><span className="text-slate-500">Connections</span><p className="text-slate-200">{(cardInfo.connections as number) ?? "—"}</p></div>
                      <div className="col-span-2"><span className="text-slate-500">URL</span><p className="text-indigo-400 font-mono truncate">{(cardInfo.url as string) || card.linkedin_url}</p></div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">Enrich data not yet available • <span className="font-mono">{card.linkedin_url}</span></p>
                  )}
                  <a href={card.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 mt-3 text-xs font-mono text-indigo-400 hover:underline">Open LinkedIn <ArrowRight className="h-3 w-3" /></a>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3">
                  <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-2"><MessageSquare className="h-4 w-4 text-emerald-400" /> Activity {activity ? `(${(activity.hiring?.length || 0)} hiring, ${(activity.dropped?.length || 0)} other)` : ""}</h4>
                  {activity ? (
                    <>
                      {(activity.hiring?.length || 0) > 0 ? (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-emerald-300">Hiring ({(activity.hiring as unknown[]).length})</p>
                          {(activity.hiring as Array<Record<string, string>>).map((post: Record<string, string>, i: number) => (
                            <div key={i} className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                              <p className="text-xs text-slate-200 whitespace-pre-wrap">{post.title || JSON.stringify(post)}</p>
                              {post.link && <a href={post.link} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline mt-1 inline-block">View post →</a>}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No hiring posts detected</p>
                      )}
                      {(activity.dropped?.length || 0) > 0 && (
                        <details className="group">
                          <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-300">Show other posts ({activity.dropped.length})</summary>
                          <div className="mt-2 space-y-2 max-h-40 overflow-y-auto">
                            {(activity.dropped.slice(0, 5) as Array<Record<string, string>>).map((post: Record<string, string>, i: number) => (
                              <div key={i} className="rounded-lg border border-slate-800 bg-slate-900 p-2">
                                <p className="text-xs text-slate-400 whitespace-pre-wrap line-clamp-3">{post.title || "—"}</p>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </>
                  ) : (
                    <p className="text-xs text-slate-500">Loading activity...</p>
                  )}
                </div>

                {discovery && discovery.people_also_viewed?.length > 0 && (
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                    <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2"><UserCheck className="h-4 w-4 text-indigo-400" /> People Also Viewed ({discovery.people_also_viewed.length})</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                      {discovery.people_also_viewed.map((p: Record<string, string>, i: number) => (
                        <div key={i} className="rounded-lg border border-slate-800 bg-slate-900 p-2">
                          <p className="text-xs font-medium text-slate-200">{p.name}</p>
                          <p className="text-xs text-slate-400 truncate">{p.about || "—"}</p>
                          <p className="text-xs text-slate-500">{p.location || ""}</p>
                          {p.profile_link && <a href={p.profile_link} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline">Profile →</a>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {card.status === "success" && card.generated_message ? (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center text-xs text-slate-400">
                      <span className="font-semibold text-slate-300">Generated Outreach Message</span>
                      <span>{card.generated_at || "Just now"}</span>
                    </div>
                    <div className="relative group">
                      <div className="rounded-xl bg-slate-950 p-5 text-sm text-slate-100 leading-relaxed font-sans whitespace-pre-wrap border border-slate-800/80 shadow-inner">
                        {card.generated_message}
                      </div>
                      <button
                        onClick={() => onCopy(card.generated_message!, card.linkedin_url)}
                        className="absolute top-3 right-3 flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 text-xs font-semibold shadow-lg transition-all"
                      >
                        {copiedUrl === card.linkedin_url ? (<><Check className="h-4 w-4 text-emerald-300" /> Copied!</>) : (<><Copy className="h-4 w-4" /> Copy Message</>)}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 text-xs text-rose-300 space-y-3">
                    <div className="flex items-center gap-2 font-semibold text-sm">
                      <AlertCircle className="h-5 w-5 shrink-0" />
                      <span>Generation Error Encountered</span>
                    </div>
                    <p className="text-xs text-rose-200/90 font-mono bg-rose-950/50 p-3 rounded-lg border border-rose-500/20">
                      {card.error || "BrightData profile collection or Gemini token limit error."}
                    </p>
                    <button
                      onClick={() => onRetry(card, idx)}
                      disabled={card.isRegenerating}
                      className="flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500 transition-all shadow"
                    >
                      {card.isRegenerating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Retry Generation
                    </button>
                  </div>
                )}

                {originalRow?.additional_note && (
                  <div className="rounded-xl bg-slate-950/60 p-3.5 border border-slate-800/80 text-xs flex items-center gap-2">
                    <span className="font-semibold text-slate-400 shrink-0">User Note:</span>
                    <span className="text-slate-300 italic">"{originalRow.additional_note}"</span>
                  </div>
                )}

                {card.status === "success" && (
                  <div className="space-y-4 pt-2 border-t border-slate-800">
                    <div className="space-y-2">
                      <label className="text-xs font-semibold text-slate-300">Tweak / Refine Message</label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={tweakInputs[card.linkedin_url] || ""}
                          onChange={(e) => onTweakChange(card.linkedin_url, e.target.value)}
                          placeholder="E.g., make it more punchy, mention our mutual connection..."
                          className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                        />
                        <button
                          onClick={() => onRegenerate(card, idx)}
                          disabled={card.isRegenerating}
                          className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-all shadow"
                        >
                          {card.isRegenerating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                          Regenerate
                        </button>
                      </div>
                    </div>
                    {(urlHistory.length as number) > 0 && (
                      <div className="pt-2">
                        <button
                          onClick={() => onToggleHistory(card.linkedin_url)}
                          className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                        >
                          <History className="h-4 w-4" />
                          <span>Version History Timeline ({urlHistory.length} Iteration{(urlHistory.length as number) > 1 ? "s" : ""})</span>
                          {isHistoryOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </button>
                        {isHistoryOpen && (
                          <div className="mt-3 space-y-3 max-h-64 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-4">
                            {(urlHistory as Array<{ generated_message: string; generated_at: string }>).map((hist, hIdx: number) => (
                              <div key={hIdx} className="rounded-lg border border-slate-800 bg-slate-900/60 p-3.5 space-y-2">
                                <div className="flex justify-between items-center text-[11px] text-slate-400">
                                  <span className="font-bold text-indigo-400">Version {hIdx + 1}</span>
                                  <span>{hist.generated_at}</span>
                                </div>
                                <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">{hist.generated_message}</p>
                                <div className="flex justify-end pt-1">
                                  <button
                                    onClick={() => onCopy(hist.generated_message, card.linkedin_url + hIdx)}
                                    className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition-all"
                                  >
                                    {copiedUrl === card.linkedin_url + hIdx ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                                    Copy Version {hIdx + 1}
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
