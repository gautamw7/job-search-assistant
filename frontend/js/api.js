const API_BASE = "";

export async function checkBackendHealth() {
    try {
        const res = await fetch(`${API_BASE}/`);
        return res.ok;
    } catch {
        return false;
    }
}

export async function getProfile() {
    const res = await fetch(`${API_BASE}/resume/`);
    if (!res.ok) {
        if (res.status === 404) return null;
        throw new Error("Failed to fetch resume.");
    }
    const text = await res.text();
    return { raw_markdown: text, content: text };
}

export async function saveProfile(payload) {
    // If payload has raw_markdown, convert it to a text file blob and upload it via POST /resume/
    const markdown = payload.raw_markdown || payload.content || "";
    const blob = new Blob([markdown], { type: "text/plain" });
    const file = new File([blob], "resume.md", { type: "text/plain" });

    const formData = new FormData();
    // Since backend expects PDF or text, let's see if we can post it or if we need a dedicated endpoint.
    // Actually, backend api/routers/resume.py checks: if file.content_type != "application/pdf".
    // Let's check if we should update api/routers/resume.py to accept raw markdown or if uploadResumeFile expects PDF.
    const res = await fetch(`${API_BASE}/resume/`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "Failed to save profile.");
    return data;
}

export async function fetchResume() {
    const res = await fetch(`${API_BASE}/resume/`);
    if (!res.ok) throw new Error("Failed to fetch resume.");
    return await res.text();
}

export async function uploadResumeFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/resume/`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "Resume upload failed.");
    return data;
}

export async function getCommunicationStyle() {
    const res = await fetch(`${API_BASE}/user-communication/`);
    if (!res.ok) {
        if (res.status === 404) return null;
        throw new Error("Failed to fetch communication style.");
    }
    return await res.json();
}

export async function saveCommunicationStyle(content) {
    const bodyContent = typeof content === "object" && content !== null ? (content.content || content.style || JSON.stringify(content)) : content;
    const res = await fetch(`${API_BASE}/user-communication/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: bodyContent, style: bodyContent, source: "response" })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Failed to update communication style.");
    return data;
}

export async function updateCommunicationStyle(content) {
    return await saveCommunicationStyle(content);
}

export async function fetchUserCommunication() {
    return await getCommunicationStyle();
}

export async function fetchCommunicationPrompt() {
    const res = await fetch(`${API_BASE}/user-communication/prompt`);
    if (!res.ok) throw new Error("Failed to fetch prompt config.");
    return await res.json();
}

export async function fetchPersonalizationConfig() {
    const res = await fetch(`${API_BASE}/personalization/config`);
    if (!res.ok) throw new Error("Failed to fetch personalization config.");
    return await res.json();
}

export async function generateBatchMessages(payload) {
    const res = await fetch(`${API_BASE}/messages/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Batch generation failed.");
    return data;
}

export async function regenerateMessage(payload) {
    const res = await fetch(`${API_BASE}/messages/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Regeneration failed.");
    return data;
}

export async function fetchMessageHistory() {
    const res = await fetch(`${API_BASE}/messages/`);
    if (!res.ok) throw new Error("Failed to fetch history.");
    return await res.json();
}

export async function fetchTargetKeys() {
    const res = await fetch(`${API_BASE}/messages/targets`);
    if (!res.ok) throw new Error("Failed to fetch targets.");
    return await res.json();
}
