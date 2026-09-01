import { appState } from '/js/state.js';

export function renderWorkspaceView(container, showToast, onNavigateIntake, onNavigateProfile) {
    const results = appState.latestBatch || {};
    const urls = Object.keys(results);

    container.innerHTML = `
        <div id="workspace-view" class="max-w-4xl mx-auto app-view bg-slate-800 rounded-xl shadow-2xl border border-slate-700 p-6 overflow-y-auto">
            <div class="view-inner space-y-4">
                <div class="flex items-center justify-between gap-4">
                    <div>
                        <span class="text-xs text-slate-500 font-bold tracking-widest uppercase">Outreach Workspace</span>
                        <h2 class="text-2xl font-extrabold text-slate-100 mt-1">Generated Messages</h2>
                        <p class="text-slate-400 text-sm mt-1">Review, copy, or regenerate personalized outreach messages tailored to your profile and target profiles.</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <button id="nav-intake-btn" class="px-3 py-1.5 text-xs font-semibold text-slate-200 rounded-lg border border-slate-700 bg-slate-900 hover:border-cyan-500 transition cursor-pointer">+ New Batch</button>
                        <button id="nav-profile-btn" class="text-xs text-emerald-400 font-semibold hover:underline whitespace-nowrap cursor-pointer">Edit Profile</button>
                    </div>
                </div>

                <div id="workspace-content" class="space-y-4">
                    ${urls.length === 0 ? `
                        <div class="text-center py-12 border-2 border-dashed border-slate-700 rounded-xl bg-slate-900/50 p-6">
                            <svg class="w-12 h-12 text-slate-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                            </svg>
                            <h3 class="text-lg font-bold text-slate-200">No Messages Generated Yet</h3>
                            <p class="text-slate-400 text-sm max-w-md mx-auto mt-1">Start by adding your target LinkedIn profiles to generate custom networking messages.</p>
                            <button id="empty-add-btn" class="mt-4 px-4 py-2 bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-sm rounded-lg hover:from-emerald-400 hover:to-cyan-400 transition cursor-pointer">Add Target Profiles</button>
                        </div>
                    ` : `
                        <div class="grid grid-cols-1 gap-4">
                            ${urls.map((url, index) => {
                                const msg = results[url];
                                const safeId = `msg-${index}`;
                                return `
                                    <div class="p-4 rounded-xl bg-slate-900 border border-slate-700/80 space-y-3">
                                        <div class="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
                                            <a href="${escapeHtml(url)}" target="_blank" rel="noreferrer" class="text-xs font-semibold text-cyan-400 hover:underline truncate max-w-md" title="${escapeHtml(url)}">${escapeHtml(url)}</a>
                                            <div class="flex items-center gap-2">
                                                <button class="copy-btn px-2.5 py-1 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 transition cursor-pointer" data-target="${safeId}">Copy</button>
                                            </div>
                                        </div>
                                        <div class="relative">
                                            <textarea id="${safeId}" rows="4" class="w-full p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-y">${escapeHtml(msg)}</textarea>
                                        </div>
                                    </div>
                                `;
                            }).join("")}
                        </div>
                    `}
                </div>
            </div>
        </div>
    `;

    document.getElementById("nav-profile-btn")?.addEventListener("click", onNavigateProfile);
    document.getElementById("nav-intake-btn")?.addEventListener("click", onNavigateIntake);
    document.getElementById("empty-add-btn")?.addEventListener("click", onNavigateIntake);

    container.querySelectorAll(".copy-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const targetId = btn.getAttribute("data-target");
            const textarea = document.getElementById(targetId);
            if (!textarea) return;
            try {
                await navigator.clipboard.writeText(textarea.value);
                showToast("Copied message to clipboard!");
            } catch {
                textarea.select();
                document.execCommand("copy");
                showToast("Copied message to clipboard!");
            }
        });
    });
}

function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
