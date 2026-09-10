import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { RefreshCw } from "lucide-react";
import { api } from "../lib/api-client";
import { Sidebar } from "../components/layout/Sidebar";
import type { TargetRow, MessageCardData } from "../types";
import { GeneratorPage } from "../features/generator/GeneratorPage";
import { HistoryPage } from "../features/history/HistoryPage";
import { OnboardingWizard } from "../features/onboarding/OnboardingWizard";
import { ResumePage } from "../features/profile/ResumePage";
import { StylePage } from "../features/profile/StylePage";
import { SettingsPage } from "../features/settings/SettingsPage";

export default function App() {
  const [activeTab, setActiveTab] = useState<"generator" | "history" | "resume" | "style" | "config">("generator");

  // Onboarding
  const [isCheckingSetup, setIsCheckingSetup] = useState(true);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [onboardingStep, setOnboardingStep] = useState(1);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeMarkdown, setResumeMarkdown] = useState<string>("");
  const [styleText, setStyleText] = useState<string>("");
  const [styleConfig, setStyleConfig] = useState<unknown>(null);
  const [fullPrompt, setFullPrompt] = useState<string>("");
  const [isUploadingResume, setIsUploadingResume] = useState(false);
  const [resumeUploadError, setResumeUploadError] = useState<string | null>(null);
  const [isSavingStyle, setIsSavingStyle] = useState(false);

  // API Keys
  const [brightdataKey, setBrightdataKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [brightdataStatus, setBrightdataStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [geminiStatus, setGeminiStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [brightdataTestStatus, setBrightdataTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [geminiTestStatus, setGeminiTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [brightdataError, setBrightdataError] = useState<string | null>(null);
  const [geminiError, setGeminiError] = useState<string | null>(null);
  const [brightdataTestError, setBrightdataTestError] = useState<string | null>(null);
  const [geminiTestError, setGeminiTestError] = useState<string | null>(null);
  const [savedBrightdataKey, setSavedBrightdataKey] = useState<string | null>(null);
  const [savedGeminiKey, setSavedGeminiKey] = useState<string | null>(null);

  // Generator
  const [rows, setRows] = useState<TargetRow[]>([{ id: "1", linkedin_url: "https://www.linkedin.com/in/", additional_note: "" }]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedCards, setGeneratedCards] = useState<MessageCardData[]>([]);
  const [backendStatus, setBackendStatus] = useState("Connecting to backend...");
  const [genProgressStage, setGenProgressStage] = useState("");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const [tweakInputs, setTweakInputs] = useState<Record<string, string>>({});
  const [historyData, setHistoryData] = useState<Record<string, unknown>>({});
  const [openHistoryDrawers, setOpenHistoryDrawers] = useState<Record<string, boolean>>({});
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);
  const [enrichCache, setEnrichCache] = useState<Record<string, unknown>>({});
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [historySearch, setHistorySearch] = useState("");
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const generationCancelToken = useRef<AbortController | null>(null);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isGenerating) {
      setElapsedSeconds(0);
      setGenProgressStage("Stage 1/3: Scraping & Enriching Recruiter Profile via BrightData...");
      interval = setInterval(() => {
        setElapsedSeconds((s) => {
          const next = s + 1;
          if (next === 6) setGenProgressStage("Stage 2/3: Analyzing Resume Context & Communication Style...");
          else if (next === 14) setGenProgressStage("Stage 3/3: Drafting Personalized Outreach Message with Gemini AI...");
          return next;
        });
      }, 1000);
    } else {
      setElapsedSeconds(0);
      setGenProgressStage("");
    }
    return () => clearInterval(interval);
  }, [isGenerating]);

  useEffect(() => {
    checkSystemSetup();
  }, []);

  const checkSystemSetup = async () => {
    setIsCheckingSetup(true);
    let connected = false;
    let attempts = 0;
    const maxAttempts = 30;
    while (!connected && attempts < maxAttempts) {
      attempts++;
      try {
        setBackendStatus(`Waiting for backend server (attempt ${attempts}/${maxAttempts})...`);
        const healthRes = await api.get("/health", { timeout: 2000 });
        if (healthRes.status === 200) connected = true;
      } catch {
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
    }
    if (!connected) {
      setIsCheckingSetup(false);
      setBackendStatus("Backend server failed to start or respond.");
      alert("Error: Backend server failed to start or respond at http://127.0.0.1:8000. Please ensure python environment and dependencies are installed.");
      return;
    }
    try {
      setBackendStatus("Loading workspace data...");
      const [resumeRes, styleRes] = await Promise.all([
        api.get("/resume/").catch(() => ({ status: 404, data: null })),
        api.get("/user-communication/").catch(() => ({ status: 404, data: null })),
      ]);
      const hasResume = resumeRes.status === 200 && resumeRes.data;
      const hasStyle = styleRes.status === 200 && (styleRes.data as Record<string, unknown>)?.style;
      if (hasResume) setResumeMarkdown(typeof resumeRes.data === "string" ? resumeRes.data : JSON.stringify(resumeRes.data));
      if (hasStyle) {
        setStyleText((styleRes.data as Record<string, string>).style);
        setStyleConfig(styleRes.data);
      }
      if (!hasResume || !hasStyle) setNeedsOnboarding(true);
      else setNeedsOnboarding(false);
    } catch (err) {
      console.error("Setup check error:", err);
      setNeedsOnboarding(true);
    } finally {
      setIsCheckingSetup(false);
    }
  };

  const handleUploadResume = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resumeFile) return;
    setIsUploadingResume(true);
    setResumeUploadError(null);
    const formData = new FormData();
    formData.append("file", resumeFile);
    try {
      const uploadRes = await api.post("/resume/", formData, { headers: { "Content-Type": "multipart/form-data" } });
      if (uploadRes.data?.error) {
        setResumeUploadError(uploadRes.data.error);
        return;
      }
      const res = await api.get("/resume/");
      setResumeMarkdown(res.data);
      setOnboardingStep(2);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setResumeUploadError(e.response?.data?.detail || e.message || "Resume upload failed.");
    } finally {
      setIsUploadingResume(false);
    }
  };

  const handleSaveStyle = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingStyle(true);
    try {
      await api.post("/user-communication/update", { style: styleText });
      setNeedsOnboarding(false);
      fetchHistory();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(`Style update failed: ${e.response?.data?.detail || e.message}`);
    } finally {
      setIsSavingStyle(false);
    }
  };

  const fetchHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const res = await api.get("/messages/");
      setHistoryData(res.data);
    } catch (err) {
      console.error("Failed to fetch history", err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const fetchEnrichForUrl = async (linkedinUrl: string) => {
    try {
      const [cardRes, activityRes, discoveryRes] = await Promise.all([
        api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/card`).catch(() => ({ data: null })),
        api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/activity`).catch(() => ({ data: null })),
        api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/discovery`).catch(() => ({ data: null })),
      ]);
      setEnrichCache((prev) => ({
        ...prev,
        [linkedinUrl]: { card: cardRes.data, activity: activityRes.data, discovery: discoveryRes.data },
      }));
    } catch (err) {
      console.error("Failed to fetch enrich for", linkedinUrl, err);
    }
  };

  const toggleCardExpand = (linkedinUrl: string) => {
    const isExpanded = expandedCards[linkedinUrl];
    if (!isExpanded && !enrichCache[linkedinUrl]) fetchEnrichForUrl(linkedinUrl);
    setExpandedCards((prev) => ({ ...prev, [linkedinUrl]: !isExpanded }));
  };

  const maskKey = (key: string) => {
    if (key.length <= 8) return "********";
    return key.slice(0, 4) + "********" + key.slice(-4);
  };

  const handleSaveBrightdataKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brightdataKey.trim()) return;
    setBrightdataStatus("testing");
    setBrightdataError(null);
    try {
      await api.post("/config/brightdata", { api_key: brightdataKey.trim() });
      setSavedBrightdataKey(brightdataKey);
      setBrightdataStatus("success");
      setBrightdataKey("");
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setBrightdataStatus("error");
      setBrightdataError(e.response?.data?.detail || e.message || "");
    }
  };

  const handleSaveGeminiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!geminiKey.trim()) return;
    setGeminiStatus("testing");
    setGeminiError(null);
    try {
      await api.post("/config/gemini", { api_key: geminiKey.trim() });
      setSavedGeminiKey(geminiKey);
      setGeminiStatus("success");
      setGeminiKey("");
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setGeminiStatus("error");
      setGeminiError(e.response?.data?.detail || e.message || "");
    }
  };

  const handleLoadKeys = async () => {
    try {
      const [bdRes, gmRes] = await Promise.all([
        api.get("/config/brightdata").catch(() => ({ data: null })),
        api.get("/config/gemini").catch(() => ({ data: null })),
      ]);
      if (bdRes.data?.api_key) setSavedBrightdataKey(bdRes.data.api_key);
      if (gmRes.data?.api_key) setSavedGeminiKey(gmRes.data.api_key);
    } catch (err) {
      console.error("Failed to load keys:", err);
    }
  };

  const handleTestStoredBrightdata = async () => {
    setBrightdataTestStatus("testing");
    setBrightdataTestError(null);
    try {
      await api.post("/config/brightdata/test");
      setBrightdataTestStatus("success");
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setBrightdataTestStatus("error");
      setBrightdataTestError(e.response?.data?.detail || e.message || "Stored key validation failed.");
    }
  };

  const handleTestStoredGemini = async () => {
    setGeminiTestStatus("testing");
    setGeminiTestError(null);
    try {
      await api.post("/config/gemini/test");
      setGeminiTestStatus("success");
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setGeminiTestStatus("error");
      setGeminiTestError(e.response?.data?.detail || e.message || "Stored key validation failed.");
    }
  };

  const addRow = () => {
    setRows([...rows, { id: Math.random().toString(36).substring(2, 9), linkedin_url: "https://www.linkedin.com/in/", additional_note: "" }]);
  };
  const removeRow = (id: string) => {
    if (rows.length === 1) return;
    setRows(rows.filter((r) => r.id !== id));
  };
  const updateRow = (id: string, field: keyof TargetRow, val: string) => {
    setRows(rows.map((r) => (r.id === id ? { ...r, [field]: val } : r)));
  };

  const handleGenerateBatch = async () => {
    setIsGenerating(true);
    const controller = new AbortController();
    generationCancelToken.current = controller;
    try {
      const payload = rows.map((r) => ({
        linkedin_url: r.linkedin_url.trim(),
        additional_note: r.additional_note.trim() || undefined,
        additional_preferences: { length: r.length || undefined, tone: r.tone || undefined },
      }));
      const res = await api.post("/messages/batch", payload, { signal: controller.signal });
      setGeneratedCards(res.data);
      fetchHistory();
      res.data.forEach((card: { linkedin_url: string }) => {
        if (card.linkedin_url) fetchEnrichForUrl(card.linkedin_url);
      });
    } catch (err: unknown) {
      if (axios.isCancel(err) || (err as { name?: string }).name === "AbortError") {
        console.log("Generation cancelled");
      } else {
        const e = err as { response?: { data?: { detail?: string } }; message?: string };
        console.error(e.response?.data?.detail || e.message);
      }
    } finally {
      generationCancelToken.current = null;
      setIsGenerating(false);
    }
  };

  const handleStopGeneration = () => {
    if (generationCancelToken.current) generationCancelToken.current.abort();
  };

  const handleRetryCard = async (card: MessageCardData, index: number) => {
    const originalRow: TargetRow = rows.find((r) => r.linkedin_url === card.linkedin_url) || {
      id: "",
      linkedin_url: card.linkedin_url,
      additional_note: "",
    };
    setGeneratedCards((prev) => prev.map((c, i) => (i === index ? { ...c, isRegenerating: true } : c)));
    try {
      const res = await api.post("/messages/", {
        linkedin_url: originalRow.linkedin_url,
        additional_note: originalRow.additional_note || undefined,
        additional_preferences: { length: originalRow.length || undefined, tone: originalRow.tone || undefined },
      });
      setGeneratedCards((prev) => prev.map((c, i) => (i === index ? { ...res.data, isRegenerating: false } : c)));
      fetchHistory();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setGeneratedCards((prev) => prev.map((c, i) => (i === index ? { ...c, isRegenerating: false, error: e.response?.data?.detail || e.message || "Retry failed" } : c)));
    }
  };

  const handleRegenerateCard = async (card: MessageCardData, index: number) => {
    const tweak = tweakInputs[card.linkedin_url] || "";
    setGeneratedCards((prev) => prev.map((c, i) => (i === index ? { ...c, isRegenerating: true } : c)));
    try {
      const res = await api.post("/messages/regenerate", { linkedin_url: card.linkedin_url, additional_note: tweak || undefined });
      setGeneratedCards((prev) => prev.map((c, i) => (i === index ? { ...res.data, isRegenerating: false, error: null } : c)));
      setTweakInputs((prev) => ({ ...prev, [card.linkedin_url]: "" }));
      fetchHistory();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setGeneratedCards((prev) => prev.map((c, i) => (i === index ? { ...c, isRegenerating: false, error: e.response?.data?.detail || e.message || "Regeneration failed" } : c)));
    }
  };

  const copyToClipboard = (text: string, url: string) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(url);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  useEffect(() => {
    if (!isCheckingSetup && !needsOnboarding) {
      fetchHistory();
      handleLoadKeys();
    }
  }, [isCheckingSetup, needsOnboarding]);

  useEffect(() => {
    const shouldFetch = activeTab === "style" || needsOnboarding;
    if (shouldFetch && !fullPrompt) {
      api
        .get("/user-communication/prompt")
        .then((res) => {
          if (res.data?.prompt) setFullPrompt(res.data.prompt);
          if (res.data) setStyleConfig(res.data);
        })
        .catch(() => {});
    }
  }, [activeTab, needsOnboarding, fullPrompt]);

  useEffect(() => {
    if (activeTab === "history" && !isCheckingSetup && !needsOnboarding && !isLoadingHistory && Object.keys(historyData).length === 0) {
      fetchHistory();
    }
  }, [activeTab]);

  if (isCheckingSetup) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#080b12] text-slate-300">
        <div className="flex flex-col items-center gap-4 text-center px-4">
          <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
          <p className="text-sm font-medium">Loading Job Search Assistant workspace...</p>
          <p className="text-xs text-slate-500 font-mono">{backendStatus}</p>
        </div>
      </div>
    );
  }

  if (needsOnboarding) {
    return (
      <OnboardingWizard
        step={onboardingStep}
        resumeFile={resumeFile}
        styleText={styleText}
        fullPrompt={fullPrompt}
        isUploading={isUploadingResume}
        isSaving={isSavingStyle}
        error={resumeUploadError}
        copiedUrl={copiedUrl}
        onFileChange={setResumeFile}
        onUpload={handleUploadResume}
        onSaveStyle={handleSaveStyle}
        onStyleChange={setStyleText}
        onCopy={copyToClipboard}
        onBack={() => setOnboardingStep(1)}
      />
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#080b12]">
      <Sidebar activeTab={activeTab} onChange={setActiveTab} />
      <main className="flex-1 overflow-y-auto p-8">
        {activeTab === "generator" && (
          <GeneratorPage
            rows={rows}
            generatedCards={generatedCards}
            isGenerating={isGenerating}
            genProgressStage={genProgressStage}
            elapsedSeconds={elapsedSeconds}
            enrichCache={enrichCache}
            expandedCards={expandedCards}
            openHistoryDrawers={openHistoryDrawers}
            tweakInputs={tweakInputs}
            copiedUrl={copiedUrl}
            historyData={historyData}
            onAddRow={addRow}
            onRemoveRow={removeRow}
            onUpdateRow={updateRow}
            onGenerate={handleGenerateBatch}
            onStop={handleStopGeneration}
            onToggleExpand={toggleCardExpand}
            onCopy={copyToClipboard}
            onRetry={handleRetryCard}
            onRegenerate={handleRegenerateCard}
            onTweakChange={(url, val) => setTweakInputs({ ...tweakInputs, [url]: val })}
            onToggleHistory={(url) => setOpenHistoryDrawers({ ...openHistoryDrawers, [url]: !openHistoryDrawers[url] })}
          />
        )}
        {activeTab === "history" && (
          <HistoryPage
            historyData={historyData as Record<string, { generations?: Array<{ generated_message: string; generated_at: string }> }>}
            enrichCache={enrichCache as Record<string, { card?: Record<string, unknown> }>}
            expandedCards={expandedCards}
            historySearch={historySearch}
            isLoading={isLoadingHistory}
            onSearchChange={setHistorySearch}
            onToggleExpand={toggleCardExpand}
            onRefresh={fetchHistory}
          />
        )}
        {activeTab === "resume" && <ResumePage resumeMarkdown={resumeMarkdown} copiedUrl={copiedUrl} onCopy={copyToClipboard} />}
        {activeTab === "style" && (
          <StylePage
            styleText={styleText}
            fullPrompt={fullPrompt}
            copiedUrl={copiedUrl}
            styleConfig={styleConfig}
            onStyleChange={setStyleText}
            onSave={handleSaveStyle}
            onCopy={copyToClipboard}
            isSaving={isSavingStyle}
          />
        )}
        {activeTab === "config" && (
          <SettingsPage
            brightdataKey={brightdataKey}
            geminiKey={geminiKey}
            brightdataStatus={brightdataStatus}
            geminiStatus={geminiStatus}
            brightdataTestStatus={brightdataTestStatus}
            geminiTestStatus={geminiTestStatus}
            brightdataError={brightdataError}
            geminiError={geminiError}
            brightdataTestError={brightdataTestError}
            geminiTestError={geminiTestError}
            savedBrightdataKey={savedBrightdataKey}
            savedGeminiKey={savedGeminiKey}
            onBrightdataChange={setBrightdataKey}
            onGeminiChange={setGeminiKey}
            onSaveBrightdata={handleSaveBrightdataKey}
            onSaveGemini={handleSaveGeminiKey}
            onTestBrightdata={handleTestStoredBrightdata}
            onTestGemini={handleTestStoredGemini}
            maskKey={maskKey}
          />
        )}
      </main>
    </div>
  );
}
