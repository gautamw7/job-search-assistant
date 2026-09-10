import { api } from "./client";

export async function fetchHistory() {
  const res = await api.get("/messages/");
  return res.data as Record<string, unknown>;
}

export async function fetchEnrichForUrl(linkedinUrl: string) {
  const [cardRes, activityRes, discoveryRes] = await Promise.all([
    api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/card`).catch(() => ({ data: null })),
    api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/activity`).catch(() => ({ data: null })),
    api.get(`/enrich/${encodeURIComponent(linkedinUrl)}/discovery`).catch(() => ({ data: null })),
  ]);
  return {
    card: cardRes.data,
    activity: activityRes.data,
    discovery: discoveryRes.data,
  };
}

export async function generateBatch(payload: unknown[], signal?: AbortSignal) {
  const res = await api.post("/messages/batch", payload, { signal });
  return res.data;
}

export async function regenerateMessage(linkedinUrl: string, additionalNote?: string) {
  const res = await api.post("/messages/regenerate", {
    linkedin_url: linkedinUrl,
    additional_note: additionalNote,
  });
  return res.data;
}
