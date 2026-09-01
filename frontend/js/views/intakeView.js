import { appState } from '/js/state.js';
import { generateBatchMessages } from '/js/api.js';

export function renderIntakeView(container, showToast, onNavigateWorkspace, onNavigateProfile) {
    container.innerHTML = `
        <div id="intake-view" class="max-w-4xl mx-auto app-view bg-slate-800 rounded-xl shadow-2xl border border-slate-700 p-6 overflow-y-auto">
            <div class="view-inner space-y-4">
                <div class="flex items-center justify-between gap-4">
                    <div>
                        <span class="text-xs text-slate-500 font-bold tracking-widest uppercase">Batch Outreach</span>
                        <h2 class="text-2xl font-extrabold text-slate-100 mt-1">Who are we reaching out to?</h2>
                        <p class="text-slate-400 text-sm mt-1">Add one or more LinkedIn profiles. Each target can have its own note and message preference.</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <button id="nav-history-btn" class="text-xs text-cyan-400 font-semibold hover:underline whitespace-nowrap cursor-pointer">View History</button>
                        <button id="nav-profile-btn" class="text-xs text-emerald-400 font-semibold hover:underline whitespace-nowrap cursor-pointer">Edit Profile</button>
                    </div>
                </div>

                <div id="target-rows" class="space-y-3"></div>

                <div class="flex items-center justify-between gap-3 mt-4">
                    <button id="add-target-btn" class="px-3 py-2 text-xs font-bold text-slate-200 rounded-lg border border-slate-700 bg-slate-900 hover:border-cyan-500 hover:text-cyan-300 transition cursor-pointer">
                        + Add Target
                    </button>
                    <span id="target-count" class="text-xs text-slate-500">1 target (Explicit 3-Input Schema)</span>
                </div>

                <div class="p-3 rounded-lg border border-cyan-500/10 bg-cyan-500/5 text-xs text-slate-400">
                    <span class="text-cyan-300 font-semibold">Batch mode:</span> the backend accepts structured target objects containing <code class="text-slate-300">linkedin_url</code>, <code class="text-slate-300">additional_note</code>, and <code class="text-slate-300">additional_preferences</code>.
                </div>

                <button id="generate-all-btn" class="w-full py-3.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-base rounded-lg hover:from-emerald-400 hover:to-cyan-400 transition flex items-center justify-center gap-2 shadow-lg cursor-pointer">
                    <span id="generate-all-text">Generate All Messages 🚀</span>
                    <svg id="generate-all-spinner" class="animate-spin h-5 w-5 text-slate-950 hidden" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 5.373 0 8 12 8z"></path>
                    </svg>
                </button>

                <div id="error-card" class="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg text-sm hidden">
                    <strong>Error:</strong> <span id="error-msg">Failed to connect to the backend.</span>
                </div>
            </div>
        </div>
    `;

    document.getElementById("nav-profile-btn")?.addEventListener("click", onNavigateProfile);
    document.getElementById("nav-history-btn")?.addEventListener("click", onNavigateWorkspace);
    document.getElementById("add-target-btn")?.addEventListener("click", () => addTargetRow());

    ensureTargetRows();

    document.getElementById("generate-all-btn")?.addEventListener("click", async () => {
        const btn = document.getElementById("generate-all-btn");
        const text = document.getElementById("generate-all-text");
        const spinner = document.getElementById("generate-all-spinner");
        const errorCard = document.getElementById("error-card");
        errorCard?.classList.add("hidden");

        try {
            const targets = collectTargets();
            appState.targets = targets;
            btn.disabled = true;
            spinner?.classList.remove("hidden");
            text.textContent = `Generating ${targets.length} message${targets.length === 1 ? "" : "s"}...`;

            const payload = targets.map(target => ({
                linkedin_url: target.url,
                additional_note: target.note || null,
                additional_preferences: {
                    length: target.preference === "concise" ? "short" : (target.preference === "standard" ? "medium" : "detailed"),
                    style: target.preference === "concise" ? "concise" : "conversational"
                }
            }));

            const batchList = await generateBatchMessages(payload);
            const data = {};
            batchList.forEach(item => {
                if (item.status === "success" && item.generated_message) {
                    data[item.linkedin_url] = item.generated_message;
                }
            });

            appState.latestBatch = data;
            onNavigateWorkspace();
            showToast(`Generated ${Object.keys(data).length} outreach message${Object.keys(data).length === 1 ? "" : "s"}.`);
        } catch (err) {
            document.getElementById("error-msg").textContent = err.message;
            errorCard?.classList.remove("hidden");
            showToast(err.message, "error");
        } finally {
            btn.disabled = false;
            spinner?.classList.add("hidden");
            text.textContent = "Generate All Messages 🚀";
        }
    });
}

function ensureTargetRows() {
    const container = document.getElementById("target-rows");
    if (!container) return;
    if (!container.children.length) addTargetRow();
}

function addTargetRow(seed = {}) {
    const container = document.getElementById("target-rows");
    if (!container) return;
    const row = document.createElement("div");
    row.className = "target-row grid grid-cols-1 md:grid-cols-12 gap-3 p-3 rounded-xl bg-slate-900/70 border border-slate-700";
    row.innerHTML = `
        <div class="md:col-span-5">
            <label class="block text-[11px] font-semibold text-slate-400 mb-1">LinkedIn URL</label>
            <input type="url" class="target-url w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-emerald-500" placeholder="https://www.linkedin.com/in/username/" value="${escapeHtml(seed.url || "")}">
        </div>
        <div class="md:col-span-4">
            <label class="block text-[11px] font-semibold text-slate-400 mb-1">User Note <span class="text-slate-600">(optional)</span></label>
            <input type="text" class="target-note w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-emerald-500" placeholder="e.g. Met at an AI meetup" value="${escapeHtml(seed.note || "")}">
        </div>
        <div class="md:col-span-2">
            <label class="block text-[11px] font-semibold text-slate-400 mb-1">Preference</label>
            <select class="target-preference w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500">
                <option value="concise" ${seed.preference === "concise" || !seed.preference ? "selected" : ""}>Concise</option>
                <option value="standard" ${seed.preference === "standard" ? "selected" : ""}>Standard</option>
                <option value="detailed" ${seed.preference === "detailed" ? "selected" : ""}>Detailed</option>
            </select>
        </div>
        <div class="md:col-span-1 flex items-end">
            <button type="button" class="remove-row-btn w-full px-3 py-2 text-xs rounded-lg border border-slate-700 text-slate-500 hover:border-red-500/50 hover:text-red-300 transition cursor-pointer" title="Remove target">−</button>
        </div>`;

    row.querySelector(".remove-row-btn").addEventListener("click", () => {
        const rows = [...container.querySelectorAll(".target-row")];
        if (rows.length === 1) {
            row.querySelector(".target-url").value = "";
            row.querySelector(".target-note").value = "";
            row.querySelector(".target-preference").value = "concise";
        } else {
            row.remove();
        }
        updateTargetCount();
    });

    container.appendChild(row);
    updateTargetCount();
}

function updateTargetCount() {
    const count = document.querySelectorAll("#target-rows .target-row").length;
    const el = document.getElementById("target-count");
    if (el) el.textContent = `${count} target${count === 1 ? "" : "s"} (Explicit 3-Input Schema)`;
}

function collectTargets() {
    const rows = [...document.querySelectorAll("#target-rows .target-row")];
    const targets = [];
    const seen = new Set();

    rows.forEach((row, idx) => {
        const url = row.querySelector(".target-url")?.value.trim();
        const note = row.querySelector(".target-note")?.value.trim() || "";
        const preference = row.querySelector(".target-preference")?.value || "concise";
        if (!url) return;
        if (!isLinkedInUrl(url)) throw new Error(`Target ${idx + 1} must be a valid LinkedIn profile URL.`);
        if (seen.has(url)) throw new Error(`Duplicate LinkedIn URL found: ${url}`);
        seen.add(url);
        targets.push({ url, note, preference });
    });

    if (!targets.length) throw new Error("Add at least one LinkedIn profile URL.");
    return targets;
}

function isLinkedInUrl(value) {
    try {
        const url = new URL(value);
        return (url.protocol === "http:" || url.protocol === "https:") && /(^|\.)linkedin\.com$/i.test(url.hostname);
    } catch {
        return false;
    }
}

function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
