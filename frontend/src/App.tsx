import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  FileText, MessageSquare, Send, History, Settings, Plus, Trash2,
  Copy, Check, RefreshCw, AlertCircle, Sparkles, Upload, ArrowRight, ShieldCheck, UserCheck, Layers, ChevronDown, ChevronUp, Key, CheckCircle, Eye, EyeOff
} from 'lucide-react';

// API Client
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' }
});

interface TargetRow {
  id: string;
  linkedin_url: string;
  additional_note: string;
  length?: 'short' | 'medium' | 'detailed';
  tone?: 'professional' | 'friendly' | 'casual' | 'confident' | 'neutral';
}

interface MessageCardData {
  linkedin_url: string;
  generated_message: string | null;
  generated_at: string | null;
  status: 'success' | 'failed';
  error: string | null;
  isRegenerating?: boolean;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'generator' | 'history' | 'resume' | 'style' | 'config'>('generator');

  // Onboarding / Setup State
  const [isCheckingSetup, setIsCheckingSetup] = useState(true);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [onboardingStep, setOnboardingStep] = useState(1);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeMarkdown, setResumeMarkdown] = useState<string>('');
  const [styleText, setStyleText] = useState<string>('');
  const [styleConfig, setStyleConfig] = useState<any>(null);
  const [fullPrompt, setFullPrompt] = useState<string>('');
  const [isUploadingResume, setIsUploadingResume] = useState(false);
  const [resumeUploadError, setResumeUploadError] = useState<string | null>(null);
  const [isSavingStyle, setIsSavingStyle] = useState(false);

  // API Keys State
  const [brightdataKey, setBrightdataKey] = useState<string>('');
  const [geminiKey, setGeminiKey] = useState<string>('');
  const [brightdataStatus, setBrightdataStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [geminiStatus, setGeminiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [brightdataTestStatus, setBrightdataTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [geminiTestStatus, setGeminiTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [brightdataError, setBrightdataError] = useState<string | null>(null);
  const [geminiError, setGeminiError] = useState<string | null>(null);
  const [brightdataTestError, setBrightdataTestError] = useState<string | null>(null);
  const [geminiTestError, setGeminiTestError] = useState<string | null>(null);
  const [savedBrightdataKey, setSavedBrightdataKey] = useState<string | null>(null);
  const [savedGeminiKey, setSavedGeminiKey] = useState<string | null>(null);

  // Generator State
  const [rows, setRows] = useState<TargetRow[]>([
    { id: '1', linkedin_url: 'https://www.linkedin.com/in/', additional_note: '' }
  ]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedCards, setGeneratedCards] = useState<MessageCardData[]>([]);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<string>('Connecting to backend...');
  const [selectedCardIndex, setSelectedCardIndex] = useState<number>(0);
  const [genProgressStage, setGenProgressStage] = useState<string>('');
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [selectedHistoryRegenIdx, setSelectedHistoryRegenIdx] = useState<string | null>(null);
  const [historyTweaks, setHistoryTweaks] = useState<{ [key: string]: string }>({});

  // Live generation timer & anxiety-free stage progress
  useEffect(() => {
    let interval: any;
    if (isGenerating) {
      setElapsedSeconds(0);
      setGenProgressStage('Stage 1/3: Scraping & Enriching Recruiter Profile via BrightData...');
      interval = setInterval(() => {
        setElapsedSeconds(s => {
          const next = s + 1;
          if (next === 6) {
            setGenProgressStage('Stage 2/3: Analyzing Resume Context & Communication Style...');
          } else if (next === 14) {
            setGenProgressStage('Stage 3/3: Drafting Personalized Outreach Message with Gemini AI...');
          }
          return next;
        });
      }, 1000);
    } else {
      setElapsedSeconds(0);
      setGenProgressStage('');
    }
    return () => clearInterval(interval);
  }, [isGenerating]);

  // Tweak & History State per URL
  const [tweakInputs, setTweakInputs] = useState<{ [url: string]: string }>({});
  const [historyData, setHistoryData] = useState<{ [url: string]: any[] }>({});
  const [openHistoryDrawers, setOpenHistoryDrawers] = useState<{ [url: string]: boolean }>({});
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);
  const [enrichCache, setEnrichCache] = useState<{ [url: string]: any }>({});
  const [expandedCards, setExpandedCards] = useState<{ [url: string]: boolean }>({});

  // Check setup on mount
  useEffect(() => {
    checkSystemSetup();
  }, []);

  const checkSystemSetup = async () => {
    setIsCheckingSetup(true);
    let connected = false;
    let attempts = 0;
    const maxAttempts = 30; // 45 seconds timeout

    while (!connected && attempts < maxAttempts) {
      attempts++;
      try {
        setBackendStatus(`Waiting for backend server (attempt ${attempts}/${maxAttempts})...`);
        const healthRes = await api.get('/health', { timeout: 2000 });
        if (healthRes.status === 200) {
          connected = true;
        }
      } catch (err) {
        await new Promise(resolve => setTimeout(resolve, 1500));
      }
    }

    if (!connected) {
      setIsCheckingSetup(false);
      setBackendStatus('Backend server failed to start or respond.');
      alert("Error: Backend server failed to start or respond at http://127.0.0.1:8000. Please ensure python environment and dependencies are installed.");
      return;
    }

    try {
      setBackendStatus('Loading workspace data...');
      const [resumeRes, styleRes] = await Promise.all([
        api.get('/resume/').catch(() => ({ status: 404, data: null })),
        api.get('/user-communication/').catch(() => ({ status: 404, data: null }))
      ]);

      const hasResume = resumeRes.status === 200 && resumeRes.data;
      const hasStyle = styleRes.status === 200 && (styleRes.data as any)?.style;

      if (hasResume) setResumeMarkdown(typeof resumeRes.data === 'string' ? resumeRes.data : JSON.stringify(resumeRes.data));
      if (hasStyle) {
        setStyleText((styleRes.data as any).style);
        setStyleConfig((styleRes.data as any).config);
      }

      if (!hasResume || !hasStyle) {
        setNeedsOnboarding(true);
      } else {
        setNeedsOnboarding(false);
      }
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
    formData.append('file', resumeFile);
    try {
      const uploadRes = await api.post('/resume/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (uploadRes.data?.error) {
        setResumeUploadError(uploadRes.data.error);
        return;
      }
      const res = await api.get('/resume/');
      setResumeMarkdown(res.data);
      setOnboardingStep(2);
    } catch (err: any) {
      setResumeUploadError(err.response?.data?.detail || err.message || "Resume upload failed.");
    } finally {
      setIsUploadingResume(false);
    }
  };

  const handleSaveStyle = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingStyle(true);
    try {
      await api.post('/user-communication/update', { style: styleText });
      setNeedsOnboarding(false);
      fetchHistory();
    } catch (err: any) {
      alert(`Style update failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSavingStyle(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await api.get('/messages/');
      setHistoryData(res.data);
    } catch (err) {
      console.error("Failed to fetch history", err);
    }
  };

  const fetchEnrichForUrl = async (linkedinUrl: string) => {
    try {
      const [cardRes, activityRes, discoveryRes] = await Promise.all([
        api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/card`).catch(() => ({ data: null })),
        api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/activity`).catch(() => ({ data: null })),
        api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/discovery`).catch(() => ({ data: null })),
      ]);
      setEnrichCache(prev => ({
        ...prev,
        [linkedinUrl]: {
          card: cardRes.data,
          activity: activityRes.data,
          discovery: discoveryRes.data,
        }
      }));
    } catch (err) {
      console.error("Failed to fetch enrich for", linkedinUrl, err);
    }
  };

  const toggleCardExpand = (linkedinUrl: string) => {
    const isExpanded = expandedCards[linkedinUrl];
    if (!isExpanded && !enrichCache[linkedinUrl]) {
      fetchEnrichForUrl(linkedinUrl);
    }
    setExpandedCards(prev => ({ ...prev, [linkedinUrl]: !isExpanded }));
  };

  // API Keys Handlers
  const maskKey = (key: string) => {
    if (key.length <= 8) return '********';
    return key.slice(0, 4) + '********' + key.slice(-4);
  };

  const handleSaveBrightdataKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brightdataKey.trim()) return;
    setBrightdataStatus('testing');
    setBrightdataError(null);
    try {
      await api.post('/config/brightdata', { api_key: brightdataKey.trim() });
      setSavedBrightdataKey(brightdataKey);
      setBrightdataStatus('success');
      setBrightdataKey('');
    } catch (err: any) {
      setBrightdataStatus('error');
      setBrightdataError(err.response?.data?.detail || err.message);
    }
  };

  const handleSaveGeminiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!geminiKey.trim()) return;
    setGeminiStatus('testing');
    setGeminiError(null);
    try {
      await api.post('/config/gemini', { api_key: geminiKey.trim() });
      setSavedGeminiKey(geminiKey);
      setGeminiStatus('success');
      setGeminiKey('');
    } catch (err: any) {
      setGeminiStatus('error');
      setGeminiError(err.response?.data?.detail || err.message);
    }
  };

  const handleLoadKeys = async () => {
    try {
      const [bdRes, gmRes] = await Promise.all([
        api.get('/config/brightdata').catch(() => ({ data: null })),
        api.get('/config/gemini').catch(() => ({ data: null }))
      ]);
      if (bdRes.data?.api_key) setSavedBrightdataKey(bdRes.data.api_key);
      if (gmRes.data?.api_key) setSavedGeminiKey(gmRes.data.api_key);
    } catch (err) {
      console.error('Failed to load keys:', err);
    }
  };

  const handleTestStoredBrightdata = async () => {
    setBrightdataTestStatus('testing');
    setBrightdataTestError(null);
    try {
      await api.post('/config/brightdata/test');
      setBrightdataTestStatus('success');
    } catch (err: any) {
      setBrightdataTestStatus('error');
      setBrightdataTestError(err.response?.data?.detail || err.message || 'Stored key validation failed.');
    }
  };

  const handleTestStoredGemini = async () => {
    setGeminiTestStatus('testing');
    setGeminiTestError(null);
    try {
      await api.post('/config/gemini/test');
      setGeminiTestStatus('success');
    } catch (err: any) {
      setGeminiTestStatus('error');
      setGeminiTestError(err.response?.data?.detail || err.message || 'Stored key validation failed.');
    }
  };

  const handleRegenerateFromHistory = async (linkedinUrl: string, generationIndex: number) => {
    const tweakKey = `${historyDataIndexCache.current}-${generationIndex}`;
    const tweak = historyTweaks[tweakKey] || '';
    if (!tweak.trim()) return;

    setSelectedHistoryRegenIdx(tweakKey);
    try {
      const res = await api.post('/messages/regenerate', {
        linkedin_url: linkedinUrl,
        additional_note: tweak
      });
      await fetchHistory();
    } catch (err: any) {
      alert(`Regeneration failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setSelectedHistoryRegenIdx(null);
    }
  };

  // Track which history entry we're regenerating
  const historyDataIndexCache = React.useRef<number>(0);

  useEffect(() => {
    if (!needsOnboarding) {
      fetchHistory();
      handleLoadKeys();
    }
  }, [needsOnboarding]);

  // Fetch full prompt for copy feature when style tab is active or onboarding
  useEffect(() => {
    const shouldFetch = activeTab === 'style' || needsOnboarding;
    if (shouldFetch && !fullPrompt) {
      api.get('/user-communication/prompt')
        .then(res => {
          if (res.data?.prompt) setFullPrompt(res.data.prompt);
          if (res.data) setStyleConfig(res.data);
        })
        .catch(() => {});
    }
  }, [activeTab, needsOnboarding, fullPrompt]);

  // Fetch enrich card info for history URLs
  useEffect(() => {
    const urls = Object.keys(historyData);
    if (urls.length === 0) return;
    urls.forEach(url => {
      if (!enrichCache[url]) fetchEnrichForUrl(url);
    });
  }, [historyData]);

  // Add row in generator
  const addRow = () => {
    setRows([...rows, { id: Math.random().toString(36).substring(2, 9), linkedin_url: 'https://www.linkedin.com/in/', additional_note: '' }]);
  };

  const removeRow = (id: string) => {
    if (rows.length === 1) return;
    setRows(rows.filter(r => r.id !== id));
  };

  const updateRow = (id: string, field: keyof TargetRow, val: any) => {
    setRows(rows.map(r => r.id === id ? { ...r, [field]: val } : r));
  };

  // Generate Batch
  const handleGenerateBatch = async () => {
    setIsGenerating(true);
    setBatchError(null);
    try {
      const payload = rows.map(r => ({
        linkedin_url: r.linkedin_url.trim(),
        additional_note: r.additional_note.trim() || undefined,
        additional_preferences: {
          length: r.length || undefined,
          tone: r.tone || undefined
        }
      }));

      const res = await api.post('/messages/batch', payload);
      setGeneratedCards(res.data);
      setSelectedCardIndex(0);
      fetchHistory();
      // Fetch enrich card info for each generated linkedin_url
      res.data.forEach((card: any) => {
        if (card.linkedin_url) fetchEnrichForUrl(card.linkedin_url);
      });
    } catch (err: any) {
      setBatchError(err.response?.data?.detail || err.message || "Batch generation failed.");
    } finally {
      setIsGenerating(false);
    }
  };

  // Retry single card
  const handleRetryCard = async (card: MessageCardData, index: number) => {
    const originalRow: TargetRow = rows.find(r => r.linkedin_url === card.linkedin_url) || {
      id: '',
      linkedin_url: card.linkedin_url,
      additional_note: '',
      length: undefined,
      tone: undefined
    };

    setGeneratedCards(prev => prev.map((c, i) => i === index ? { ...c, isRegenerating: true, error: null } : c));

    try {
      const res = await api.post('/messages/', {
        linkedin_url: originalRow.linkedin_url,
        additional_note: originalRow.additional_note || undefined,
        additional_preferences: {
          length: originalRow.length || undefined,
          tone: originalRow.tone || undefined
        }
      });
      setGeneratedCards(prev => prev.map((c, i) => i === index ? {
        ...res.data,
        isRegenerating: false
      } : c));
      fetchHistory();
    } catch (err: any) {
      setGeneratedCards(prev => prev.map((c, i) => i === index ? {
        ...c,
        isRegenerating: false,
        error: err.response?.data?.detail || err.message || "Retry failed"
      } : c));
    }
  };

  // Regenerate / Tweak Card
  const handleRegenerateCard = async (card: MessageCardData, index: number) => {
    const tweak = tweakInputs[card.linkedin_url] || '';
    setGeneratedCards(prev => prev.map((c, i) => i === index ? { ...c, isRegenerating: true } : c));

    try {
      const res = await api.post('/messages/regenerate', {
        linkedin_url: card.linkedin_url,
        additional_note: tweak || undefined
      });
      setGeneratedCards(prev => prev.map((c, i) => i === index ? {
        ...res.data,
        isRegenerating: false,
        error: null
      } : c));
      setTweakInputs(prev => ({ ...prev, [card.linkedin_url]: '' }));
      fetchHistory();
    } catch (err: any) {
      setGeneratedCards(prev => prev.map((c, i) => i === index ? {
        ...c,
        isRegenerating: false,
        error: err.response?.data?.detail || err.message || "Regeneration failed"
      } : c));
    }
  };

  const copyToClipboard = (text: string, url: string) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(url);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

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

  // Startup Wizard / Modal Barrier
  if (needsOnboarding) {
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
              <span className={`h-2.5 w-8 rounded-full ${onboardingStep === 1 ? 'bg-indigo-500' : 'bg-slate-700'}`} />
              <span className={`h-2.5 w-8 rounded-full ${onboardingStep === 2 ? 'bg-indigo-500' : 'bg-slate-700'}`} />
            </div>
          </div>

          {onboardingStep === 1 ? (
            <form onSubmit={handleUploadResume} className="space-y-6">
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Step 1: Upload Your Resume (PDF)</h2>
                <p className="mt-1 text-xs text-slate-400">Your resume is parsed into Markdown and powers all tailored outreach generations.</p>
              </div>

              <label className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 bg-slate-950/50 p-8 cursor-pointer hover:border-indigo-500 transition-all">
                <Upload className="mb-3 h-10 w-10 text-indigo-400" />
                <span className="text-sm font-medium text-slate-300">
                  {resumeFile ? resumeFile.name : 'Click to select resume PDF'}
                </span>
                <span className="mt-1 text-xs text-slate-500">PDF format only</span>
                <input
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => e.target.files && setResumeFile(e.target.files[0])}
                />
              </label>

              {resumeUploadError && (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 flex items-start gap-2.5">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block mb-0.5">Resume Validation Failed</span>
                    <span>{resumeUploadError}</span>
                  </div>
                </div>
              )}

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={!resumeFile || isUploadingResume}
                  className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-indigo-500 disabled:opacity-50 transition-all"
                >
                  {isUploadingResume ? <RefreshCw className="h-4 w-4 animate-spin" /> : <>Continue <ArrowRight className="h-4 w-4" /></>}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleSaveStyle} className="space-y-6">
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Step 2: Communication Style & Tone</h2>
                <p className="mt-1 text-xs text-slate-400">Define how you want your outreach messages to sound (greeting style, directness, formatting rules).</p>
              </div>

              {fullPrompt && (
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-3 flex items-center justify-between">
                  <span className="text-xs text-slate-400">Need the full analyst prompt? </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(fullPrompt, 'onboarding-prompt')}
                    className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 text-xs font-semibold shadow transition-all"
                  >
                    {copiedUrl === 'onboarding-prompt' ? <><Check className="h-3.5 w-3.5 text-emerald-300" /> Copied Prompt!</> : <><Copy className="h-3.5 w-3.5" /> Copy Prompt</>}
                  </button>
                </div>
              )}

              <div className="relative group">
                <textarea
                  rows={6}
                  value={styleText}
                  onChange={(e) => setStyleText(e.target.value)}
                  placeholder="e.g. - Greeting: Hey [Name]&#10;- Tone: Professional yet conversational&#10;- Directness: High, get straight to the point&#10;- Length: Under 90 words"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-4 pr-12 text-sm text-slate-200 focus:border-indigo-500 focus:outline-none"
                  required
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(styleText, 'onboarding-style')}
                  className="absolute top-3 right-3 flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3 py-1.5 text-xs font-semibold shadow transition-all"
                >
                  {copiedUrl === 'onboarding-style' ? <><Check className="h-3.5 w-3.5 text-emerald-400" /> Copied!</> : <><Copy className="h-3.5 w-3.5" /> Copy</>}
                </button>
              </div>

              <div className="flex justify-between">
                <button
                  type="button"
                  onClick={() => setOnboardingStep(1)}
                  className="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-700"
                >
                  Back
                </button>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => copyToClipboard(styleText, 'onboarding-style-footer')}
                    className="hidden sm:flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 px-4 py-2.5 text-xs font-semibold text-slate-200 transition-all"
                  >
                    {copiedUrl === 'onboarding-style-footer' ? <><Check className="h-4 w-4 text-emerald-400" /> Copied!</> : <><Copy className="h-4 w-4" /> Copy Style</>}
                  </button>
                  <button
                    type="submit"
                    disabled={isSavingStyle}
                    className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-indigo-500 disabled:opacity-50 transition-all"
                  >
                    {isSavingStyle ? <RefreshCw className="h-4 w-4 animate-spin" /> : <>Complete Setup <Sparkles className="h-4 w-4" /></>}
                  </button>
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#080b12]">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-950/60 p-4 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 px-3 py-4 mb-4 border-b border-slate-800/80">
            <div className="rounded-xl bg-indigo-600/10 p-2 text-indigo-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-100">Job Search Assistant</h1>
              <p className="text-[10px] text-slate-400">Outreach Workspace</p>
            </div>
          </div>

          <nav className="space-y-1.5">
            <button
              onClick={() => setActiveTab('generator')}
              className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-medium transition-all ${
                activeTab === 'generator' ? 'bg-indigo-600/10 text-indigo-400 font-semibold' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}
            >
              <Send className="h-4 w-4" /> Batch Generator
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-medium transition-all ${
                activeTab === 'history' ? 'bg-indigo-600/10 text-indigo-400 font-semibold' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}
            >
              <History className="h-4 w-4" /> Generation History
            </button>
            <button
              onClick={() => setActiveTab('resume')}
              className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-medium transition-all ${
                activeTab === 'resume' ? 'bg-indigo-600/10 text-indigo-400 font-semibold' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}
            >
              <FileText className="h-4 w-4" /> Resume & Profile
            </button>
            <button
              onClick={() => setActiveTab('style')}
              className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-medium transition-all ${
                activeTab === 'style' ? 'bg-indigo-600/10 text-indigo-400 font-semibold' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}
            >
              <Settings className="h-4 w-4" /> Communication Style
            </button>
            <button
              onClick={() => setActiveTab('config')}
              className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-medium transition-all ${
                activeTab === 'config' ? 'bg-indigo-600/10 text-indigo-400 font-semibold' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}
            >
              <Key className="h-4 w-4" /> API Keys
            </button>
          </nav>
        </div>

        <div className="border-t border-slate-800/80 pt-4 px-3 flex items-center justify-between text-[11px] text-slate-500">
          <span>v0.1.0 Tauri App</span>
          <span className="flex items-center gap-1 text-emerald-400 font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> API Connected
          </span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8">
        {activeTab === 'generator' && (
          <div className="max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">Batch Outreach Generator</h2>
                <p className="text-xs text-slate-400">Queue target LinkedIn profile URLs and notes to generate personalized AI outreach messages.</p>
              </div>
              <button
                onClick={addRow}
                className="flex items-center gap-2 rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-all"
              >
                <Plus className="h-4 w-4" /> Add Target Row
              </button>
            </div>

            {/* Target Queue Table */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur shadow-xl space-y-4">
              <div className="space-y-3">
                {rows.map((row, index) => (
                  <div key={row.id} className="flex items-center gap-3">
                    <span className="w-6 text-center text-xs font-bold text-slate-500">{index + 1}</span>
                    <input
                      type="url"
                      value={row.linkedin_url}
                      onChange={(e) => updateRow(row.id, 'linkedin_url', e.target.value)}
                      placeholder="https://www.linkedin.com/in/recruiter-profile"
                      className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      value={row.additional_note}
                      onChange={(e) => updateRow(row.id, 'additional_note', e.target.value)}
                      placeholder="Optional note (e.g. met at AI hackathon)"
                      className="w-72 rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    />
                    <select
                      value={row.length || ''}
                      onChange={(e) => updateRow(row.id, 'length', e.target.value)}
                      className="rounded-xl border border-indigo-500/40 bg-indigo-500/10 px-3.5 py-2.5 text-xs text-indigo-300 focus:border-indigo-500 focus:outline-none appearance-none cursor-pointer"
                    >
                      <option value="">Default Length</option>
                      <option value="short">Short</option>
                      <option value="medium">Medium</option>
                      <option value="detailed">Detailed</option>
                    </select>
                    <button
                      onClick={() => removeRow(row.id)}
                      disabled={rows.length === 1}
                      className="rounded-xl p-2.5 text-slate-500 hover:bg-rose-500/10 hover:text-rose-400 disabled:opacity-30 transition-all"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Live Anxiety-Free Progress Banner during Generation */}
              {isGenerating && (
                <div className="rounded-2xl border border-indigo-500/30 bg-indigo-500/10 p-6 space-y-3 backdrop-blur animate-pulse">
                  <div className="flex items-center justify-between text-xs font-semibold text-indigo-300">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-indigo-400 animate-spin" />
                      <span>{genProgressStage || 'Processing Outreach Generation...'}</span>
                    </div>
                    <span className="font-mono bg-indigo-950/80 px-2.5 py-1 rounded-lg border border-indigo-500/30 text-indigo-200">
                      ⏱️ {elapsedSeconds}s elapsed
                    </span>
                  </div>
                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                    <div className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-full w-2/3 animate-pulse transition-all duration-500" />
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  onClick={handleGenerateBatch}
                  disabled={isGenerating}
                  className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-xs font-semibold text-white shadow-lg hover:bg-indigo-500 disabled:opacity-50 transition-all"
                >
                  {isGenerating ? <><RefreshCw className="h-4 w-4 animate-spin" /> Generating Outreach...</> : <><Sparkles className="h-4 w-4" /> Generate All Outreach ({rows.length})</>}
                </button>
              </div>
            </div>

            {/* Expandable Cards with Card Info — click header to expand */}
            {generatedCards.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-200">Enriched Results ({generatedCards.length})</h3>
                  <span className="text-xs text-slate-400">Click card to expand — shows card info, activity, posts, message, history</span>
                </div>
                {generatedCards.map((card, idx) => {
                  const enrich = enrichCache[card.linkedin_url] || {};
                  const cardInfo: any = enrich.card || null;
                  const activity: any = enrich.activity || null;
                  const discovery: any = enrich.discovery || null;
                  const isExpanded = !!expandedCards[card.linkedin_url];
                  const cardLetter = String.fromCharCode(65 + idx);
                  const urlHistory = (historyData[card.linkedin_url] as any)?.generations || [];
                  const originalRow = rows.find(r => r.linkedin_url === card.linkedin_url);
                  const isHistoryOpen = openHistoryDrawers[card.linkedin_url] || false;
                  return (
                    <div key={idx} className="rounded-2xl border border-slate-800 bg-slate-900/80 overflow-hidden shadow-xl">
                      {/* Collapsed header — card info summary */}
                      <button
                        onClick={() => toggleCardExpand(card.linkedin_url)}
                        className="w-full flex items-center justify-between p-4 hover:bg-slate-800/50 transition-all text-left"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-xs font-bold bg-indigo-600 text-white px-2.5 py-1 rounded-lg shrink-0">Card {cardLetter}</span>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-slate-100 truncate">{cardInfo?.name || card.linkedin_url.split('/in/')[1]?.replace(/\/$/, '') || 'LinkedIn Profile'}</span>
                              <span className={`h-2 w-2 rounded-full shrink-0 ${card.status === 'success' ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-400 truncate">
                              {cardInfo ? (
                                <>
                                  <span className="flex items-center gap-1"><UserCheck className="h-3 w-3" /> {cardInfo.current_company_name || '—'}</span>
                                  <span>•</span>
                                  <span className="flex items-center gap-1"><Layers className="h-3 w-3" /> {cardInfo.location || '—'}</span>
                                  <span>•</span>
                                  <span>{cardInfo.followers ?? '—'} followers • {cardInfo.connections ?? '—'} conn.</span>
                                </>
                              ) : (
                                <span className="font-mono text-indigo-300 truncate">{card.linkedin_url}</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`hidden sm:inline rounded-full px-3 py-1 text-xs font-medium ${card.status === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>{card.status === 'success' ? 'Ready' : 'Failed'}</span>
                          {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                        </div>
                      </button>
                      {isExpanded && (
                        <div className="border-t border-slate-800 p-6 space-y-6 bg-slate-900/40">
                          {/* Detailed card info */}
                          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                            <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-indigo-400" /> Card Details</h4>
                            {cardInfo ? (
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div><span className="text-slate-500">Name</span><p className="text-slate-200 font-medium">{cardInfo.name || '—'}</p></div>
                                <div><span className="text-slate-500">Position</span><p className="text-slate-200">{cardInfo.position || '—'}</p></div>
                                <div><span className="text-slate-500">Company</span><p className="text-slate-200">{cardInfo.current_company_name || '—'}</p></div>
                                <div><span className="text-slate-500">Location</span><p className="text-slate-200">{cardInfo.location || '—'}</p></div>
                                <div><span className="text-slate-500">Followers</span><p className="text-slate-200">{cardInfo.followers ?? '—'}</p></div>
                                <div><span className="text-slate-500">Connections</span><p className="text-slate-200">{cardInfo.connections ?? '—'}</p></div>
                                <div className="col-span-2"><span className="text-slate-500">URL</span><p className="text-indigo-400 font-mono truncate">{cardInfo.url || card.linkedin_url}</p></div>
                              </div>
                            ) : (
                              <p className="text-xs text-slate-500">Enrich data not yet available — <span className="text-slate-400">old string format, re-enrich will populate</span> • <span className="font-mono">{card.linkedin_url}</span></p>
                            )}
                            <a href={card.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 mt-3 text-xs font-mono text-indigo-400 hover:underline">Open LinkedIn <ArrowRight className="h-3 w-3" /></a>
                          </div>

                          {/* Activity - hiring / dropped */}
                          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3">
                            <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-2"><MessageSquare className="h-4 w-4 text-emerald-400" /> Activity — Hiring Posts {activity ? `(${activity.hiring?.length || 0} hiring, ${activity.dropped?.length || 0} other)` : ''}</h4>
                            {activity ? (
                              <>
                                {activity.hiring?.length > 0 ? (
                                  <div className="space-y-2">
                                    <p className="text-xs font-medium text-emerald-300">Hiring ({activity.hiring.length})</p>
                                    {activity.hiring.map((post: any, i: number) => (
                                      <div key={i} className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                                        <p className="text-xs text-slate-200 whitespace-pre-wrap">{post.title || JSON.stringify(post)}</p>
                                        {post.link && <a href={post.link} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline mt-1 inline-block">View post →</a>}
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-xs text-slate-500">No hiring posts detected</p>
                                )}
                                {activity.dropped?.length > 0 && (
                                  <details className="group">
                                    <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-300">Show other posts ({activity.dropped.length})</summary>
                                    <div className="mt-2 space-y-2 max-h-40 overflow-y-auto">
                                      {activity.dropped.slice(0,5).map((post: any, i: number) => (
                                        <div key={i} className="rounded-lg border border-slate-800 bg-slate-900 p-2">
                                          <p className="text-xs text-slate-400 whitespace-pre-wrap line-clamp-3">{post.title || '—'}</p>
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

                          {/* Discovery */}
                          {discovery && discovery.people_also_viewed?.length > 0 && (
                            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                              <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2"><UserCheck className="h-4 w-4 text-indigo-400" /> People Also Viewed ({discovery.people_also_viewed.length})</h4>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                                {discovery.people_also_viewed.map((p: any, i: number) => (
                                  <div key={i} className="rounded-lg border border-slate-800 bg-slate-900 p-2">
                                    <p className="text-xs font-medium text-slate-200">{p.name}</p>
                                    <p className="text-xs text-slate-400 truncate">{p.about || '—'}</p>
                                    <p className="text-xs text-slate-500">{p.location || ''}</p>
                                    {p.profile_link && <a href={p.profile_link} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline">Profile →</a>}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Generated message */}
                          {card.status === 'success' && card.generated_message ? (
                            <div className="space-y-3">
                              <div className="flex justify-between items-center text-xs text-slate-400">
                                <span className="font-semibold text-slate-300">Generated Outreach Message</span>
                                <span>{card.generated_at || 'Just now'}</span>
                              </div>
                              <div className="relative group">
                                <div className="rounded-xl bg-slate-950 p-5 text-sm text-slate-100 leading-relaxed font-sans whitespace-pre-wrap border border-slate-800/80 shadow-inner">
                                  {card.generated_message}
                                </div>
                                <button
                                  onClick={() => copyToClipboard(card.generated_message!, card.linkedin_url)}
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
                                onClick={() => handleRetryCard(card, idx)}
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

                          {card.status === 'success' && (
                            <div className="space-y-4 pt-2 border-t border-slate-800">
                              <div className="space-y-2">
                                <label className="text-xs font-semibold text-slate-300">Tweak / Refine Message</label>
                                <div className="flex gap-2">
                                  <input
                                    type="text"
                                    value={tweakInputs[card.linkedin_url] || ''}
                                    onChange={(e) => setTweakInputs({ ...tweakInputs, [card.linkedin_url]: e.target.value })}
                                    placeholder="E.g., make it more punchy, mention our mutual connection..."
                                    className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                                  />
                                  <button
                                    onClick={() => handleRegenerateCard(card, idx)}
                                    disabled={card.isRegenerating}
                                    className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-all shadow"
                                  >
                                    {card.isRegenerating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                                    Regenerate
                                  </button>
                                </div>
                              </div>
                              {urlHistory.length > 0 && (
                                <div className="pt-2">
                                  <button
                                    onClick={() => setOpenHistoryDrawers({ ...openHistoryDrawers, [card.linkedin_url]: !isHistoryOpen })}
                                    className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                                  >
                                    <History className="h-4 w-4" />
                                    <span>Version History Timeline ({urlHistory.length} Iteration{urlHistory.length > 1 ? 's' : ''})</span>
                                    {isHistoryOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                  </button>
                                  {isHistoryOpen && (
                                    <div className="mt-3 space-y-3 max-h-64 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-4">
                                      {urlHistory.map((hist: any, hIdx: number) => (
                                        <div key={hIdx} className="rounded-lg border border-slate-800 bg-slate-900/60 p-3.5 space-y-2">
                                          <div className="flex justify-between items-center text-[11px] text-slate-400">
                                            <span className="font-bold text-indigo-400">Version {hIdx + 1}</span>
                                            <span>{hist.generated_at}</span>
                                          </div>
                                          <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">{hist.generated_message}</p>
                                          <div className="flex justify-end pt-1">
                                            <button
                                              onClick={() => copyToClipboard(hist.generated_message, card.linkedin_url + hIdx)}
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
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-100">Generation History Log</h2>
              <p className="text-xs text-slate-400">Append-only history of all outreach messages generated across profiles.</p>
            </div>

            <div className="space-y-4">
              {Object.keys(historyData).length === 0 ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-12 text-center text-slate-500">
                  No generation history found yet.
                </div>
              ) : (
                Object.entries(historyData).map(([url, data]: [string, any], idx) => {
                  const generations = data.generations || [];
                  const isRegenerating = isGenerating && selectedCardIndex === idx;
                  const enrich: any = enrichCache[url] || {};
                  const cardInfo: any = enrich.card || null;
                  const activity: any = enrich.activity || null;
                  const discovery: any = enrich.discovery || null;
                  const isExpanded = !!expandedCards[url];

                  return (
                    <div key={idx} className="rounded-2xl border border-slate-800 bg-slate-900/80 overflow-hidden shadow-xl">
                      {/* History Card Header — card info */}
                      <button
                        onClick={() => toggleCardExpand(url)}
                        className="w-full flex items-center justify-between p-5 hover:bg-slate-800/40 transition-all text-left"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-semibold text-slate-100 truncate">{cardInfo?.name || url.split('/in/')[1]?.replace(/\/$/, '') || 'LinkedIn Profile'}</span>
                            <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-[10px] text-slate-300 shrink-0">{generations.length} Version{generations.length > 1 ? 's' : ''}</span>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-slate-400 truncate">
                            {cardInfo ? (
                              <>
                                <span className="flex items-center gap-1"><ShieldCheck className="h-3 w-3 text-indigo-400" /> {cardInfo.current_company_name || '—'}</span>
                                <span>•</span>
                                <span className="flex items-center gap-1"><Layers className="h-3 w-3" /> {cardInfo.location || '—'}</span>
                                <span>•</span>
                                <span>{cardInfo.followers ?? '—'} followers</span>
                              </>
                            ) : (
                              <span className="font-mono text-indigo-300 truncate">{url}</span>
                            )}
                          </div>
                          {!cardInfo && <span className="text-xs font-mono text-slate-500 truncate block mt-1">{url}</span>}
                        </div>
                        <div className="flex items-center gap-2 shrink-0 ml-3">
                          {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                        </div>
                      </button>
                      {isExpanded && (
                        <div className="border-t border-slate-800 p-5 space-y-5 bg-slate-900/30">
                          {/* Card Details */}
                          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                            <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-indigo-400" /> Card Details</h4>
                            {cardInfo ? (
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div><span className="text-slate-500">Name</span><p className="text-slate-200 font-medium">{cardInfo.name || '—'}</p></div>
                                <div><span className="text-slate-500">Position</span><p className="text-slate-200">{cardInfo.position || '—'}</p></div>
                                <div><span className="text-slate-500">Company</span><p className="text-slate-200">{cardInfo.current_company_name || '—'}</p></div>
                                <div><span className="text-slate-500">Location</span><p className="text-slate-200">{cardInfo.location || '—'}</p></div>
                                <div><span className="text-slate-500">Followers</span><p className="text-slate-200">{cardInfo.followers ?? '—'}</p></div>
                                <div><span className="text-slate-500">Connections</span><p className="text-slate-200">{cardInfo.connections ?? '—'}</p></div>
                                <div className="col-span-2"><span className="text-slate-500">URL</span><p className="text-indigo-400 font-mono truncate">{cardInfo.url || url}</p></div>
                              </div>
                            ) : (
                              <p className="text-xs text-slate-500">Enrich data not yet available — re-enrich will populate card • <span className="font-mono">{url}</span></p>
                            )}
                          </div>
                          {/* Activity */}
                          {activity && (
                            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                              <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-2"><MessageSquare className="h-4 w-4 text-emerald-400" /> Activity — Hiring ({activity.hiring?.length || 0}) • Other ({activity.dropped?.length || 0})</h4>
                              {activity.hiring?.length > 0 ? (
                                <div className="space-y-2">
                                  {activity.hiring.slice(0,3).map((post: any, i: number) => (
                                    <div key={i} className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                                      <p className="text-xs text-slate-200 whitespace-pre-wrap">{post.title || '—'}</p>
                                      {post.link && <a href={post.link} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline mt-1 inline-block">View post →</a>}
                                    </div>
                                  ))}
                                </div>
                              ) : <p className="text-xs text-slate-500">No hiring posts</p>}
                            </div>
                          )}
                          {/* People Also Viewed */}
                          {discovery && discovery.people_also_viewed?.length > 0 && (
                            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                              <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2"><UserCheck className="h-4 w-4 text-indigo-400" /> People Also Viewed ({discovery.people_also_viewed.length})</h4>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                                {discovery.people_also_viewed.slice(0,6).map((p: any, i: number) => (
                                  <div key={i} className="rounded-lg border border-slate-800 bg-slate-900 p-2">
                                    <p className="text-xs font-medium text-slate-200">{p.name}</p>
                                    <p className="text-xs text-slate-400 truncate">{p.about || '—'}</p>
                                    <p className="text-xs text-slate-500">{p.location || ''}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          <div className="space-y-3">
                            {generations.map((gen: any, gIdx: number) => {
                          const isLatest = gIdx === generations.length - 1;
                          const isRegenActive = isRegenerating && selectedHistoryRegenIdx === `${idx}-${gIdx}`;

                          return (
                            <div key={gIdx} className={`rounded-xl border bg-slate-950 p-4 space-y-3 ${
                              isLatest ? 'border-indigo-500/30' : 'border-slate-800'
                            }`}>
                              <div className="flex justify-between items-center text-[10px] text-slate-500">
                                <span className={`font-semibold ${isLatest ? 'text-indigo-400' : 'text-slate-400'}`}>
                                  Iteration #{gIdx + 1} {isLatest && <span className="inline-block bg-indigo-600 text-white px-1.5 py-0.5 rounded text-[9px] align-middle">Latest</span>}
                                </span>
                                <span>{gen.generated_at}</span>
                              </div>
                              <p className="text-xs text-slate-200 whitespace-pre-wrap">{gen.generated_message}</p>

                              <div className="flex items-center gap-2">
                                <input
                                  type="text"
                                  value={historyTweaks[`${idx}-${gIdx}`] || ''}
                                  onChange={(e) => setHistoryTweaks({ ...historyTweaks, [`${idx}-${gIdx}`]: e.target.value })}
                                  placeholder="Tweak this message..."
                                  className="flex-1 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                                />
                                <button
                                  onClick={() => handleRegenerateFromHistory(url, gIdx)}
                                  disabled={isRegenActive || !historyTweaks[`${idx}-${gIdx}`]?.trim()}
                                  className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-all"
                                >
                                  {isRegenActive ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                                  Regenerate
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {activeTab === 'resume' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-100">Resume & Profile</h2>
              <p className="text-xs text-slate-400">Current parsed resume Markdown used for context enrichment.</p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-6">
              <div className="flex justify-between items-center border-b border-slate-800 pb-4">
                <span className="text-xs font-semibold text-slate-300">Active Resume Markdown</span>
                <label className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white cursor-pointer hover:bg-indigo-500 transition-all">
                  <Upload className="h-3.5 w-3.5" /> Upload New PDF Resume
                  <input
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={async (e) => {
                      if (e.target.files && e.target.files[0]) {
                        const fd = new FormData();
                        fd.append('file', e.target.files[0]);
                        await api.post('/resume/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
                        const res = await api.get('/resume/');
                        setResumeMarkdown(res.data);
                        alert('Resume updated successfully!');
                      }
                    }}
                  />
                </label>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 text-xs font-mono text-slate-300 whitespace-pre-wrap max-h-[500px] overflow-y-auto">
                {resumeMarkdown || 'No resume loaded.'}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'style' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-100">Communication Style</h2>
              <p className="text-xs text-slate-400">Configure your active writing tone and preferences.</p>
            </div>

            <form onSubmit={handleSaveStyle} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-6">
              {fullPrompt && (
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300">Full Analyst Prompt (from backend)</span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(fullPrompt, 'full-prompt')}
                      className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 text-xs font-semibold shadow transition-all"
                    >
                      {copiedUrl === 'full-prompt' ? <><Check className="h-3.5 w-3.5 text-emerald-300" /> Copied!</> : <><Copy className="h-3.5 w-3.5" /> Copy Prompt</>}
                    </button>
                  </div>
                  <p className="text-xs text-slate-400">This is the exact prompt used to infer your communication style. Copy to share or edit externally.</p>
                  <div className="max-h-32 overflow-y-auto rounded-lg bg-slate-900 border border-slate-800 p-3 text-xs font-mono text-slate-300 whitespace-pre-wrap">
                    {fullPrompt.slice(0, 800)}{fullPrompt.length > 800 ? '...' : ''}
                  </div>
                </div>
              )}

              <div className="relative group">
                <textarea
                  rows={8}
                  value={styleText}
                  onChange={(e) => setStyleText(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-4 pr-12 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
                  required
                />
                <button
                  type="button"
                  onClick={() => copyToClipboard(styleText, 'style-text')}
                  className="absolute top-3 right-3 flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-3 py-1.5 text-xs font-semibold shadow transition-all"
                  title="Copy style to clipboard"
                >
                  {copiedUrl === 'style-text' ? <><Check className="h-3.5 w-3.5 text-emerald-400" /> Copied!</> : <><Copy className="h-3.5 w-3.5" /> Copy Style</>}
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => copyToClipboard(styleText, 'style-text-footer')}
                    className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 px-4 py-2.5 text-xs font-semibold text-slate-200 transition-all"
                  >
                    {copiedUrl === 'style-text-footer' ? <><Check className="h-4 w-4 text-emerald-400" /> Copied!</> : <><Copy className="h-4 w-4" /> Copy Style</>}
                  </button>
                  {fullPrompt && (
                    <button
                      type="button"
                      onClick={() => copyToClipboard(fullPrompt, 'full-prompt-footer')}
                      className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 px-4 py-2.5 text-xs font-semibold text-slate-200 transition-all"
                    >
                      {copiedUrl === 'full-prompt-footer' ? <><Check className="h-4 w-4 text-emerald-400" /> Copied!</> : <><Copy className="h-4 w-4" /> Copy Prompt</>}
                    </button>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={isSavingStyle}
                  className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-xs font-semibold text-white shadow-lg hover:bg-indigo-500 disabled:opacity-50 transition-all"
                >
                  {isSavingStyle ? <RefreshCw className="h-4 w-4 animate-spin" /> : <>Save Changes <Sparkles className="h-4 w-4" /></>}
                </button>
              </div>
            </form>
          </div>
        )}

        {activeTab === 'config' && (
          <div className="max-w-2xl mx-auto space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-100">API Keys</h2>
              <p className="text-xs text-slate-400">Store and test your API credentials. Keys are saved securely in your system keyring.</p>
            </div>

            {/* BrightData Key */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-indigo-400" />
                BrightData API Key
              </h3>
              <p className="text-xs text-slate-400">Used for LinkedIn profile enrichment.</p>

              {savedBrightdataKey && (
                <div className="space-y-3 mb-4">
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 flex items-center justify-between">
                    <span className="text-xs font-mono text-emerald-300">
                      {maskKey(savedBrightdataKey)}
                    </span>
                    <span className="rounded-full bg-emerald-500/20 text-emerald-400 px-2 py-0.5 text-[10px] font-medium">
                      Saved
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={handleTestStoredBrightdata}
                    disabled={brightdataTestStatus === 'testing'}
                    className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 disabled:opacity-50 transition-all"
                  >
                    {brightdataTestStatus === 'testing' ? (
                      <><RefreshCw className="h-4 w-4 animate-spin text-indigo-400" /> Checking Stored Key...</>
                    ) : (
                      <><Key className="h-4 w-4 text-indigo-400" /> Check / Test Stored Key</>
                    )}
                  </button>

                  {brightdataTestStatus === 'success' && (
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 shrink-0" />
                      <span>Stored BrightData key is valid and working!</span>
                    </div>
                  )}

                  {brightdataTestStatus === 'error' && brightdataTestError && (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>{brightdataTestError}</span>
                    </div>
                  )}
                </div>
              )}

              <form onSubmit={handleSaveBrightdataKey} className="space-y-3">
                <div className="relative">
                  <input
                    type="password"
                    value={brightdataKey}
                    onChange={(e) => setBrightdataKey(e.target.value)}
                    placeholder="Enter BrightData API key"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    disabled={brightdataStatus === 'testing'}
                  />
                  {brightdataStatus === 'testing' && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-indigo-400">
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    </span>
                  )}
                </div>

                {brightdataStatus === 'error' && brightdataError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{brightdataError}</span>
                  </div>
                )}

                {brightdataStatus === 'success' && (
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 shrink-0" />
                    <span>Key saved and validated successfully!</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!brightdataKey.trim() || brightdataStatus === 'testing'}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-all"
                >
                  {brightdataStatus === 'testing' ? (
                    <> <RefreshCw className="h-4 w-4 animate-spin" /> Testing & Saving... </>
                  ) : (
                    <> <ShieldCheck className="h-4 w-4" /> Save & Test BrightData Key </>
                  )}
                </button>
              </form>
            </div>

            {/* Gemini Key */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-indigo-400" />
                Gemini API Key
              </h3>
              <p className="text-xs text-slate-400">Used for generating outreach messages.</p>

              {savedGeminiKey && (
                <div className="space-y-3 mb-4">
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 flex items-center justify-between">
                    <span className="text-xs font-mono text-emerald-300">
                      {maskKey(savedGeminiKey)}
                    </span>
                    <span className="rounded-full bg-emerald-500/20 text-emerald-400 px-2 py-0.5 text-[10px] font-medium">
                      Saved
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={handleTestStoredGemini}
                    disabled={geminiTestStatus === 'testing'}
                    className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 disabled:opacity-50 transition-all"
                  >
                    {geminiTestStatus === 'testing' ? (
                      <><RefreshCw className="h-4 w-4 animate-spin text-indigo-400" /> Checking Stored Key...</>
                    ) : (
                      <><Key className="h-4 w-4 text-indigo-400" /> Check / Test Stored Key</>
                    )}
                  </button>

                  {geminiTestStatus === 'success' && (
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 shrink-0" />
                      <span>Stored Gemini key is valid and working!</span>
                    </div>
                  )}

                  {geminiTestStatus === 'error' && geminiTestError && (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>{geminiTestError}</span>
                    </div>
                  )}
                </div>
              )}

              <form onSubmit={handleSaveGeminiKey} className="space-y-3">
                <div className="relative">
                  <input
                    type="password"
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    placeholder="Enter Gemini API key"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    disabled={geminiStatus === 'testing'}
                  />
                  {geminiStatus === 'testing' && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-indigo-400">
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    </span>
                  )}
                </div>

                {geminiStatus === 'error' && geminiError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{geminiError}</span>
                  </div>
                )}

                {geminiStatus === 'success' && (
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 shrink-0" />
                    <span>Key saved and validated successfully!</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!geminiKey.trim() || geminiStatus === 'testing'}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-all"
                >
                  {geminiStatus === 'testing' ? (
                    <> <RefreshCw className="h-4 w-4 animate-spin" /> Testing & Saving... </>
                  ) : (
                    <> <Sparkles className="h-4 w-4" /> Save & Test Gemini Key </>
                  )}
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
