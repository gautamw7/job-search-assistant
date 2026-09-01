import { appState, updateState } from '/js/state.js';
import { fetchCommunicationPrompt, updateCommunicationStyle } from '/js/api.js';

export async function renderStyleView(container, showToast, onNavigateOnboarding, onNavigateIntake) {
    let promptData = { prompt: "Loading prompt...", questions: [] };
    try {
        promptData = await fetchCommunicationPrompt();
    } catch (err) {
        console.warn("Could not load prompt config:", err);
    }

    container.innerHTML = `
        <div id="style-view" class="max-w-5xl mx-auto app-view bg-slate-800 rounded-xl shadow-2xl border border-slate-700 p-8 space-y-8 overflow-y-auto">
            <div class="view-inner space-y-6">
                <div class="progress-rail flex items-center justify-center gap-2 border-b border-slate-700 pb-4">
                    <button class="progress-step done px-3 py-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 text-xs font-bold">✓ Resume</button>
                    <div class="w-12 h-0.5 bg-emerald-500"></div>
                    <button class="progress-step active px-3 py-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 text-cyan-300 text-xs font-bold">2. Style</button>
                    <div class="w-12 h-0.5 bg-slate-700"></div>
                    <button class="progress-step px-3 py-1.5 rounded-lg border border-slate-700 text-slate-500 text-xs font-bold">3. Targets</button>
                </div>

                <div class="flex justify-between items-center pb-2">
                    <button id="back-to-resume-btn" class="text-xs text-slate-400 hover:text-slate-200 flex items-center space-x-1 cursor-pointer">
                        <span>← Back to Resume</span>
                    </button>
                    <span class="text-xs font-bold text-cyan-400 uppercase tracking-widest">Step 2 of 3</span>
                </div>

                <div class="text-center space-y-2">
                    <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
                        Step 2: Communication Style Setup
                    </h1>
                    <p class="text-slate-400 text-sm">
                        Choose how your outreach should sound. Paste a generated style guide, answer questions, or skip.
                    </p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
                    <div class="md:col-span-6 bg-slate-900/80 border border-slate-700 rounded-xl p-6 space-y-4">
                        <h3 class="text-sm font-bold text-cyan-400 uppercase tracking-wider">Why We Need This Prompt</h3>
                        <p class="text-xs text-slate-300 leading-relaxed">
                            To ensure your outreach messages never sound like a generic sales bot, we analyze your authentic writing style. Copy the analysis prompt below, paste it into ChatGPT or Claude with your writing samples, and copy the resulting style guide back.
                        </p>
                        <div class="space-y-2">
                            <div class="flex items-center justify-between">
                                <label class="block text-xs font-semibold text-slate-300">Style Analysis Prompt</label>
                                <button id="copy-prompt-btn" class="text-[11px] bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 px-2.5 py-1 rounded border border-cyan-500/30 transition cursor-pointer">
                                    Copy Prompt 📋
                                </button>
                            </div>
                            <div id="backend-prompt-box" class="p-3 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 font-mono h-[160px] overflow-y-auto whitespace-pre-wrap">
                                ${escapeHtml(promptData.prompt || "No prompt available.")}
                            </div>
                        </div>
                    </div>

                    <div class="md:col-span-6 bg-slate-900/80 border border-slate-700 rounded-xl p-6 space-y-5">
                        <div class="flex items-center justify-between border-b border-slate-700 pb-3">
                            <h3 class="text-sm font-bold text-emerald-400 uppercase tracking-wider">Configure Style</h3>
                            <button id="style-mode-toggle" class="text-xs text-cyan-400 hover:underline font-medium cursor-pointer">
                                Switch to Interactive Questions ➔
                            </button>
                        </div>

                        <div id="style-paste-section" class="space-y-4">
                            <div class="space-y-1">
                                <label for="style-input" class="block text-xs font-semibold text-slate-300">Paste your generated Style Guide</label>
                                <textarea
                                    id="style-input"
                                    rows="6"
                                    placeholder="=== USER WRITING STYLE ===&#10;- Greeting: Casual&#10;- Directness: High..."
                                    class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition font-mono"
                                >${escapeHtml(appState.activeStyleText)}</textarea>
                            </div>
                            <button id="submit-style-paste-btn" class="w-full py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg transition duration-150 text-sm shadow-lg cursor-pointer">
                                Save & Continue to Target 🚀
                            </button>
                        </div>

                        <div id="style-questions-section" class="space-y-4 hidden">
                            <p class="text-xs text-slate-400">Answer these quick questions to automatically build your style profile:</p>
                            <div id="interactive-questions-container" class="space-y-3 max-h-[220px] overflow-y-auto pr-1"></div>
                            <button id="submit-questions-btn" class="w-full py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg transition duration-150 text-sm shadow-lg cursor-pointer">
                                Save Answers & Continue 🚀
                            </button>
                        </div>
                    </div>
                </div>

                <div class="flex justify-center pt-2">
                    <button id="skip-style-btn" class="text-xs text-slate-400 hover:text-slate-200 underline transition cursor-pointer">
                        Skip this step (Use Default Writing Style)
                    </button>
                </div>
            </div>
        </div>
    `;

    document.getElementById("back-to-resume-btn")?.addEventListener("click", onNavigateOnboarding);

    document.getElementById("copy-prompt-btn")?.addEventListener("click", async () => {
        const text = promptData.prompt || "";
        try {
            await navigator.clipboard.writeText(text);
            showToast("Style analysis prompt copied to clipboard.");
        } catch {
            showToast("Clipboard access failed.", "error");
        }
    });

    let isInteractive = false;
    const modeToggle = document.getElementById("style-mode-toggle");
    const pasteSec = document.getElementById("style-paste-section");
    const questionsSec = document.getElementById("style-questions-section");
    const qContainer = document.getElementById("interactive-questions-container");

    const questions = promptData.questions || [];
    if (qContainer && questions.length > 0) {
        qContainer.innerHTML = questions.map((q, idx) => `
            <div class="space-y-1 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <label class="block text-xs font-semibold text-slate-200">${idx + 1}. ${escapeHtml(q.question)}</label>
                <select id="q-ans-${escapeHtml(q.id)}" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500">
                    ${(q.options || []).map(opt => `<option value="${escapeHtml(opt)}">${escapeHtml(opt)}</option>`).join("")}
                </select>
            </div>
        `).join("");
    }

    modeToggle?.addEventListener("click", () => {
        isInteractive = !isInteractive;
        pasteSec?.classList.toggle("hidden", isInteractive);
        questionsSec?.classList.toggle("hidden", !isInteractive);
        modeToggle.textContent = isInteractive ? "Switch to Paste Style Guide →" : "Switch to Interactive Questions →";
    });

    document.getElementById("submit-style-paste-btn")?.addEventListener("click", async () => {
        const val = document.getElementById("style-input")?.value.trim();
        if (!val) {
            showToast("Style guide cannot be empty.", "error");
            return;
        }
        try {
            await updateCommunicationStyle(val);
            updateState({ activeStyleText: val, styleLoaded: true });
            showToast("Communication style saved.");
            onNavigateIntake();
        } catch (err) {
            showToast(err.message, "error");
        }
    });

    document.getElementById("submit-questions-btn")?.addEventListener("click", async () => {
        let summary = "=== USER WRITING STYLE (Generated from Q&A) ===\n";
        questions.forEach(q => {
            const el = document.getElementById(`q-ans-${q.id}`);
            if (el) summary += `- **${q.id}**: ${el.value}\n`;
        });
        try {
            await updateCommunicationStyle(summary);
            updateState({ activeStyleText: summary, styleLoaded: true });
            showToast("Communication style saved.");
            onNavigateIntake();
        } catch (err) {
            showToast(err.message, "error");
        }
    });

    document.getElementById("skip-style-btn")?.addEventListener("click", () => {
        updateState({ styleLoaded: true });
        showToast("Style setup skipped.");
        onNavigateIntake();
    });
}

function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
