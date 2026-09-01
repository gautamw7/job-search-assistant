import { appState, updateState } from '/js/state.js';
import { uploadResumeFile, fetchResume } from '/js/api.js';

export function renderOnboardingView(container, showToast, onNavigateStyle, onNavigateIntake) {
    container.innerHTML = `
        <div id="onboarding-view" class="max-w-5xl mx-auto app-view bg-slate-800 rounded-xl shadow-2xl border border-slate-700 p-8 space-y-8 overflow-y-auto">
            <div class="view-inner space-y-6">
                <div class="progress-rail flex items-center justify-center gap-2 border-b border-slate-700 pb-4">
                    <button class="progress-step active px-3 py-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 text-xs font-bold">1. Resume</button>
                    <div class="w-12 h-0.5 bg-slate-700"></div>
                    <button class="progress-step px-3 py-1.5 rounded-lg border border-slate-700 text-slate-500 text-xs font-bold">2. Style</button>
                    <div class="w-12 h-0.5 bg-slate-700"></div>
                    <button class="progress-step px-3 py-1.5 rounded-lg border border-slate-700 text-slate-500 text-xs font-bold">3. Targets</button>
                </div>

                <div class="text-center space-y-2">
                    <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                        Step 1: Build Your Profile
                    </h1>
                    <p class="text-slate-400 text-sm">
                        Start with your resume, then set your communication style. Both can be skipped or updated anytime.
                    </p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
                    <div class="md:col-span-6 bg-slate-900/80 border border-slate-700 rounded-xl p-6 flex flex-col items-center justify-center space-y-4 text-center">
                        <h3 class="text-sm font-bold text-emerald-400 uppercase tracking-wider">Upload Resume PDF</h3>
                        <div class="w-full border-2 border-dashed border-slate-600 rounded-xl p-8 hover:border-emerald-500 transition relative flex flex-col items-center justify-center cursor-pointer bg-slate-950/50">
                            <input type="file" id="resume-file-input" accept="application/pdf" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer">
                            <div id="upload-status" class="space-y-2 pointer-events-none">
                                <p class="text-sm text-slate-200 font-semibold">Click or drag PDF resume here</p>
                                <p class="text-xs text-slate-400">PDF format required</p>
                            </div>
                        </div>
                    </div>

                    <div class="md:col-span-6 bg-slate-900/80 border border-slate-700 rounded-xl p-6 space-y-3 flex flex-col h-[380px]">
                        <div class="flex items-center justify-between border-b border-slate-700 pb-2">
                            <h3 class="text-sm font-bold text-cyan-400 uppercase tracking-wider">Parsed Resume Preview</h3>
                            <span id="preview-status-badge" class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700">${appState.resumeLoaded ? "Cached Resume Loaded ✓" : "Waiting for upload..."}</span>
                        </div>
                        <div class="flex-1 bg-slate-950 border border-slate-700 rounded-lg p-4 overflow-y-auto">
                            <div id="onboarding-resume-preview" class="text-xs text-slate-300 font-mono whitespace-pre-line leading-relaxed">
                                ${appState.activeResumeText ? escapeHtml(appState.activeResumeText) : "No resume uploaded yet. Your parsed markdown text will appear here."}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="flex justify-center gap-4 pt-4">
                    <button id="skip-resume-btn" class="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-lg transition text-sm cursor-pointer">
                        Skip Resume ➔
                    </button>
                    <button id="resume-continue-btn" ${appState.resumeLoaded ? "" : "disabled"} class="px-8 py-3 ${appState.resumeLoaded ? "bg-emerald-500 hover:bg-emerald-400 text-slate-950 cursor-pointer shadow-lg" : "bg-slate-700 text-slate-400 cursor-not-allowed"} font-bold rounded-lg transition text-sm">
                        Continue to Style Setup ➔
                    </button>
                </div>
            </div>
        </div>
    `;

    const fileInput = document.getElementById("resume-file-input");
    fileInput?.addEventListener("change", async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const statusDiv = document.getElementById("upload-status");
        const previewBox = document.getElementById("onboarding-resume-preview");
        const continueBtn = document.getElementById("resume-continue-btn");
        const badge = document.getElementById("preview-status-badge");

        statusDiv.innerHTML = `<p class="text-xs text-cyan-400 font-semibold animate-pulse">Uploading & Parsing...</p>`;
        try {
            await uploadResumeFile(file);
            const mdText = await fetchResume();
            updateState({ activeResumeText: mdText, resumeLoaded: true });
            previewBox.textContent = mdText;
            badge.textContent = "Parsed Successfully ✓";
            badge.className = "text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/30";
            statusDiv.innerHTML = `<p class="text-xs text-emerald-400 font-bold">✓ Uploaded Successfully!</p>`;
            continueBtn.disabled = false;
            continueBtn.className = "px-8 py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg transition text-sm shadow-lg cursor-pointer";
            showToast("Resume uploaded and parsed successfully.");
        } catch (err) {
            statusDiv.innerHTML = `<p class="text-xs text-red-400 font-bold">✗ Upload Failed: ${escapeHtml(err.message)}</p>`;
            showToast(err.message, "error");
        }
    });

    document.getElementById("skip-resume-btn")?.addEventListener("click", () => {
        updateState({ resumeSkipped: true });
        showToast("Resume skipped.");
        onNavigateStyle();
    });

    document.getElementById("resume-continue-btn")?.addEventListener("click", () => {
        if (!appState.resumeLoaded) {
            showToast("Please upload a resume or skip first.", "error");
            return;
        }
        onNavigateStyle();
    });
}

function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
