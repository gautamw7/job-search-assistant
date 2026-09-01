export const appState = {
    currentView: "intake",
    resumeLoaded: false,
    styleLoaded: false,
    activeResumeText: "",
    activeStyleText: "",
    targets: [],
    history: {},
    latestBatch: {},
    targetKeys: [],
    selectedTargetUrl: null,
    personalizationConfigQuestions: [],
    availableQuestions: []
};

export function updateState(newState) {
    Object.assign(appState, newState);
}
