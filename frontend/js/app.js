import { appState } from '/js/state.js';
import { getProfile, saveProfile, getCommunicationStyle, saveCommunicationStyle, checkBackendHealth } from '/js/api.js';
import { renderOnboardingView } from '/js/views/onboardingView.js';
import { renderStyleView } from '/js/views/styleView.js';
import { renderProfileView } from '/js/views/profileView.js';
import { renderIntakeView } from '/js/views/intakeView.js';
import { renderWorkspaceView } from '/js/views/workspaceView.js';

document.addEventListener("DOMContentLoaded", async () => {
    const rootContainer = document.getElementById("spa-container");
    if (!rootContainer) return;

    // Wire up topbar navigation buttons
    document.getElementById("nav-btn-targets")?.addEventListener("click", () => navigateTo("intake"));
    document.getElementById("nav-btn-workspace")?.addEventListener("click", () => navigateTo("workspace"));
    document.getElementById("nav-btn-profile")?.addEventListener("click", () => navigateTo("profile"));

    function showToast(message, type = "success") {
        const toast = document.createElement("div");
        toast.className = `fixed bottom-4 right-4 z-50 px-4 py-3 rounded-xl shadow-2xl border text-xs font-semibold flex items-center gap-2 transition transform translate-y-2 opacity-0 ${
            type === "error"
                ? "bg-red-900/90 border-red-700 text-red-100"
                : "bg-slate-900/95 border-emerald-500/40 text-emerald-300"
        }`;
        toast.innerHTML = `<span>${type === "error" ? "⚠️" : "✨"}</span><span>${escapeHtml(message)}</span>`;
        document.body.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.remove("translate-y-2", "opacity-0");
        });

        setTimeout(() => {
            toast.classList.add("translate-y-2", "opacity-0");
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    async function navigateTo(viewName) {
        appState.currentView = viewName;
        rootContainer.innerHTML = "";

        switch (viewName) {
            case "onboarding_resume":
                renderOnboardingView(
                    rootContainer,
                    showToast,
                    () => navigateTo("onboarding_style"),
                    () => navigateTo("profile")
                );
                break;

            case "onboarding_style":
                renderStyleView(
                    rootContainer,
                    showToast,
                    () => navigateTo("onboarding_resume"),
                    () => navigateTo("intake")
                );
                break;

            case "profile":
                renderProfileView(rootContainer, showToast, async () => {
                    if (appState.hasInitialized) {
                        await navigateTo("intake");
                    } else {
                        await initApp();
                    }
                });
                break;

            case "intake":
                renderIntakeView(rootContainer, showToast, () => navigateTo("workspace"), () => navigateTo("profile"));
                break;

            case "workspace":
                renderWorkspaceView(rootContainer, showToast, () => navigateTo("intake"), () => navigateTo("profile"));
                break;

            default:
                renderIntakeView(rootContainer, showToast, () => navigateTo("workspace"), () => navigateTo("profile"));
                break;
        }
    }

    async function initApp() {
        rootContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <svg class="animate-spin h-10 w-10 text-cyan-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 5.373 0 8 12 8z"></path>
                </svg>
                <p class="text-xs text-slate-400 font-medium">Connecting to backend & checking state...</p>
            </div>
        `;

        try {
            const healthy = await checkBackendHealth();
            if (!healthy) throw new Error("Backend service is unavailable.");

            let profileData = null;
            let styleData = null;

            try {
                profileData = await getProfile();
            } catch {
                profileData = null;
            }

            try {
                styleData = await getCommunicationStyle();
            } catch {
                styleData = null;
            }

            const hasResume = Boolean(profileData);
            const hasStyle = Boolean(styleData && styleData.source && styleData.source !== "default");

            appState.resumeText = profileData?.raw_markdown || profileData?.content || "";
            appState.activeResumeText = profileData?.raw_markdown || profileData?.content || "";
            appState.resumeLoaded = hasResume;

            appState.styleData = styleData || {};
            appState.activeStyleText = styleData?.content || styleData?.style || "";
            appState.styleLoaded = hasStyle;

            if (hasResume && hasStyle) {
                appState.hasInitialized = true;
                await navigateTo("intake");
            } else if (!hasResume) {
                appState.hasInitialized = false;
                await navigateTo("onboarding_resume");
            } else {
                appState.hasInitialized = false;
                await navigateTo("onboarding_style");
            }
        } catch (err) {
            rootContainer.innerHTML = `
                <div class="max-w-md mx-auto mt-20 p-6 bg-red-950/40 border border-red-500/30 rounded-2xl text-center space-y-4">
                    <div class="text-3xl">⚠️</div>
                    <h3 class="text-base font-bold text-red-200">Backend Connection Error</h3>
                    <p class="text-xs text-red-300/80">${escapeHtml(err.message || "Failed to reach the FastAPI backend.")}</p>
                    <button id="retry-btn" class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-bold text-xs rounded-lg transition cursor-pointer">Retry Connection</button>
                </div>
            `;
            document.getElementById("retry-btn")?.addEventListener("click", initApp);
        }
    }

    await initApp();
});

function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
