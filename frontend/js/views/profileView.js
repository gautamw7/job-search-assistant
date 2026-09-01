import { appState, updateState } from '/js/state.js';
import { uploadResumeFile, updateCommunicationStyle, fetchCommunicationPrompt, fetchResume } from '/js/api.js';

export async function renderProfileView(container, showToast, onNavigateIntake) {
    let promptData = { prompt: "Loading prompt...", questions: [] };
    try {
        promptData = await fetchCommunicationPrompt();
    } catch (err) {
        console.warn("Could not load prompt config:", err);
    }

    container.innerHTML = `
        <div class="max-w-6xl mx-auto app-view bg-slate-800 rounded-xl shadow-2xl border border-slate-700 p-8 space-y-6 overflow-y-auto">
            <div class="view-inner space-y-6">
                <div class="flex items-center justify-between border-b border-slate-700 pb-4">
                    <div>
                        <span class="text-[10px] text-emerald-400 font-bold tracking-[0.22em]">SETTINGS</span>
                        <h1 class="text-2xl font-extrabold text-slate-100 mt-1">Profile & Communication Style</h1>
                        <p class="text-xs text-slate-400 mt-1">Manage your master resume, style analysis prompt, and communication style preferences at any time.</p>
                    </div>
                    <button id="profile-back-btn" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold text-xs rounded-lg transition cursor-pointer">
                        ← Back to Targets
                    </button>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-12 gap-6">
                    <!-- Left Column: Resume Management -->
                    <div class="md:col-span-6 space-y-4 bg-slate-900/80 border border-slate-700 rounded-xl p-6 flex flex-col">
                        <h3 class="text-sm font-bold text-emerald-400 uppercase tracking-wider">Master Resume Management</h3>
                        <div class="w-full border-2 border-dashed border-slate-600 rounded-xl p-5 hover:border-emerald-500 transition relative flex flex-col items-center justify-center cursor-pointer bg-slate-950/50 text-center">
                            <input type="file" id="profile-resume-file-input" accept="application/pdf" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer">
                            <div id="profile-upload-status" class="space-y-1 pointer-events-none">
                                <p class="text-xs text-slate-200 font-semibold">Click or drag new PDF resume to replace</p>
                                <p class="text-[10px] text-slate-400">PDF format required</p>
                            </div>
                        </div>
                        <div class="flex-1 flex flex-col space-y-2 min-h-[220px]">
                            <span class="text-xs font-semibold text-slate-300">Current Parsed Resume Markdown</span>
                            <div class="flex-1 bg-slate-950 border border-slate-700 rounded-lg p-3 overflow-y-auto">
                                <div id="profile-resume-preview" class="text-xs text-slate-300 font-mono whitespace-pre-line leading-relaxed">
                                    ${appState.activeResumeText ? escapeHtml(appState.activeResumeText) : "No resume loaded."}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Right Column: Style Guide & Prompt -->
                    <div class="md:col-span-6 space-y-4 bg-slate-900/80 border border-slate-700 rounded-xl p-6 flex flex-col">
                        <div class="flex items-center justify-between">
                            <h3 class="text-sm font-bold text-cyan-400 uppercase tracking-wider">Communication Style & Prompt</h3>
                            <button id="copy-profile-prompt-btn" class="text-[11px] bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 px-2.5 py-1 rounded border border-cyan-500/30 transition cursor-pointer">
                                Copy Analysis Prompt 📋
                            </button>
                        </div>

                        <div class="space-y-1">
                            <label class="block text-[11px] font-semibold text-slate-400">Style Analysis Prompt (Reference)</label>
                            <div class="p-2.5 bg-slate-950 border border-slate-700 rounded-lg text-[11px] text-slate-300 font-mono h-[100px] overflow-y-auto whitespace-pre-wrap">
                                ${escapeHtml(promptData.prompt || "No prompt available.")}
                            </div>
                        </div>

                        <div class="flex-1 flex flex-col space-y-2">
                            <label for="profile-style-input" class="block text-xs font-semibold text-slate-300">Saved Style Guide Content</label>
                            <textarea
                                id="profile-style-input"
                                rows="6"
                                class="w-full flex-1 px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono"
                            >${escapeHtml(appState.activeStyleText)}</textarea>
                        </div>
                        <button id="profile-save-btn" class="w-full py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold rounded-lg transition text-sm shadow-lg cursor-pointer">
                            Save Profile Changes 💾
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById("profile-back-btn")?.addEventListener("click", onNavigateIntake);

    document.getElementById("copy-profile-prompt-btn")?.addEventListener("click", async () => {
        const text = promptData.prompt || "";
        try {
            await navigator.clipboard.writeText(text);
            showToast("Style analysis prompt copied to clipboard.");
        } catch {
            showToast("Clipboard access failed.", "error");
        }
    });

    document.getElementById("profile-save-btn")?.addEventListener("click", async () => {
        const styleVal = document.getElementById("profile-style-input")?.value.trim();
        if (styleVal) {
            try {
                await updateCommunicationStyle(styleVal);
                updateState({ activeStyleText: styleVal, styleLoaded: true });
                showToast("Profile settings updated successfully.");
                onNavigateIntake();
            } catch (err) {
                showToast(err.message, "error");
            }
        }
    });

    const fileInput = document.getElementById("profile-resume-file-input");
    fileInput?.addEventListener("change", async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const statusDiv = document.getElementById("profile-upload-status");
        const previewBox = document.getElementById("profile-resume-preview");
        statusDiv.innerHTML = `<p class="text-xs text-cyan-400 font-semibold animate-pulse">Uploading & Parsing...</p>`;
        try {
            await uploadResumeFile(file);
            const mdText = await fetchResume();
            updateState({ activeResumeText: mdText, resumeLoaded: true });
            previewBox.textContent = mdText;
            statusDiv.innerHTML = `<p class="text-xs text-emerald-400 font-bold">✓ Resume Updated Successfully!</p>`;
            showToast("Resume updated successfully.");
        } catch (err) {
            statusDiv.innerHTML = `<p class="text-xs text-red-400 font-bold">✗ Upload Failed: ${escapeHtml(err.message)}</p>`;
            showToast(err.message, "error");
        }
    });
}

function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
