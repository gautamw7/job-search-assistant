import { http } from "../lib/http";
import type {
  Contact,
  ContactStatus,
  FactCheck,
  HiringContact,
  HistoryEntry,
  Job,
  JobListing,
  JobsMeta,
  JobStatus,
  ProfileQuestion,
  SearchProfile,
  SearchRun,
  KeyService,
  Length,
  ProfileCard,
  ProfileDetails,
  Tone,
  StructuredResume,
  StructuredResumeState,
  Tracking,
  UsageSettings,
  UsageSummary,
} from "../types";

export interface GeneratedResult {
  generated_message: string;
  generated_at: string;
  fact_check?: FactCheck | null;
  shared_background?: string[];
}

export interface BatchResult {
  ok: boolean;
  cached: boolean;
  hiring_posts: number | null;
  latest_hiring_post: string | null;
  error: string | null;
}

export interface TargetPayload {
  linkedin_url: string;
  additional_note?: string;
  additional_preferences?: { length?: Length; tone?: Tone };
  refresh_profile?: boolean;
}

export const api = {
  health: () => http.get("/health", { timeout: 2000 }).then((r) => r.status === 200),

  // resume
  async getResume(): Promise<string | null> {
    try {
      const r = await http.get<string>("/resume/", { transformResponse: (d) => d });
      return r.data || null;
    } catch (e) {
      if ((e as { response?: { status?: number } }).response?.status === 404) return null;
      throw e;
    }
  },
  uploadResume(file: File) {
    const body = new FormData();
    body.append("file", file);
    return http.post("/resume/", body, { headers: { "Content-Type": "multipart/form-data" } });
  },
  saveResumeMarkdown: (raw_markdown: string) => http.post("/resume/markdown", { raw_markdown }),
  async getStructuredResume(): Promise<StructuredResumeState | null> {
    try {
      return (await http.get<StructuredResumeState>("/resume/structured")).data;
    } catch (e) {
      if ((e as { response?: { status?: number } }).response?.status === 404) return null;
      throw e;
    }
  },
  convertStructuredResume: () =>
    http
      .post<StructuredResumeState>("/resume/structured/convert", undefined, { timeout: 3 * 60 * 1000 })
      .then((r) => r.data),
  saveStructuredResume: (resume: StructuredResume) =>
    http.put<StructuredResumeState>("/resume/structured", resume).then((r) => r.data),

  // communication style
  getStyle: () =>
    http
      .get<{ content: string; source: "response" | "questions" | "default" }>("/user-communication/")
      .then((r) => r.data),
  getStylePrompt: () =>
    http
      .get<{ prompt: string; default: string }>("/user-communication/prompt")
      .then((r) => r.data),
  saveStyle: (content: string, source: "response" | "questions" | "default" = "response") =>
    http.post("/user-communication/update", { content, source }),

  // generation
  startJob: (targets: TargetPayload[]) =>
    http.post<{ job_id: string }>("/messages/jobs", targets).then((r) => r.data.job_id),
  getJob: (id: string) => http.get<Job>(`/messages/jobs/${id}`).then((r) => r.data),
  cancelJob: (id: string) => http.delete<Job>(`/messages/jobs/${id}`).then((r) => r.data),
  generateOne: (target: TargetPayload) =>
    http.post<GeneratedResult>("/messages/", target).then((r) => r.data),
  regenerate: (linkedin_url: string, additional_note?: string) =>
    http
      .post<GeneratedResult>("/messages/regenerate", {
        linkedin_url,
        additional_note: additional_note || undefined,
      })
      .then((r) => r.data),
  followup: (linkedin_url: string, additional_note?: string) =>
    http
      .post<GeneratedResult>("/messages/followup", {
        linkedin_url,
        additional_note: additional_note || undefined,
      })
      .then((r) => r.data),

  // tracker
  contacts: () =>
    http
      .get<{ contacts: Contact[]; statuses: ContactStatus[]; followup_after_days: number }>("/tracker/")
      .then((r) => r.data),
  updateContact: (
    linkedin_url: string,
    patch: { status?: ContactStatus; notes?: string; followup_sent?: boolean },
  ) => http.post<Tracking>("/tracker/update", { linkedin_url, ...patch }).then((r) => r.data),

  // usage & budget
  usage: () => http.get<UsageSummary>("/usage/").then((r) => r.data),
  saveUsageSettings: (patch: Partial<UsageSettings>) =>
    http.put<UsageSummary>("/usage/settings", patch).then((r) => r.data),
  history: () => http.get<Record<string, HistoryEntry>>("/messages/").then((r) => r.data),

  // profiles
  allCards: () => http.get<Record<string, ProfileCard>>("/enrich/cards").then((r) => r.data),
  async profile(url: string): Promise<ProfileDetails> {
    const base = `/enrich/${encodeURIComponent(url)}`;
    const pick = <T,>(p: Promise<{ data: T }>) => p.then((r) => r.data).catch(() => null);
    const [card, activity, discovery] = await Promise.all([
      pick(http.get<ProfileCard>(`${base}/card`)),
      pick(http.get<ProfileDetails["activity"]>(`${base}/activity`)),
      pick(http.get<ProfileDetails["discovery"]>(`${base}/discovery`)),
    ]);
    return { card, activity, discovery };
  },
  refreshProfile: (linkedin_url: string) => http.post("/enrich/refresh", { linkedin_url }),
  hiringContacts: (url: string) =>
    http
      .get<HiringContact[]>(`/enrich/${encodeURIComponent(url)}/hiring-contacts`)
      .then((r) => r.data),
  batchEnrich: (linkedin_urls: string[]) =>
    http
      .post<Record<string, BatchResult>>("/enrich/batch", { linkedin_urls }, { timeout: 15 * 60 * 1000 })
      .then((r) => r.data),

  // job search
  jobsMeta: () => http.get<JobsMeta>("/jobs/meta").then((r) => r.data),
  async getSearchProfile(): Promise<{ profile: SearchProfile; confirmed: boolean; stale: boolean } | null> {
    try {
      return (await http.get("/jobs/profile")).data;
    } catch (e) {
      if ((e as { response?: { status?: number } }).response?.status === 404) return null;
      throw e;
    }
  },
  suggestSearchProfile: (ambitions: string) =>
    http
      .post<{ profile: SearchProfile; questions: ProfileQuestion[] }>("/jobs/profile/suggest", { ambitions }, { timeout: 3 * 60 * 1000 })
      .then((r) => r.data),
  saveSearchProfile: (profile: SearchProfile) =>
    http.put<{ profile: SearchProfile; confirmed: boolean; stale: boolean }>("/jobs/profile", profile).then((r) => r.data),
  startJobSearch: (force = false) =>
    http.post<{ search_id: string; cached: boolean }>("/jobs/search", { force }).then((r) => r.data),
  getJobSearch: (id: string) => http.get<SearchRun>(`/jobs/search/${id}`).then((r) => r.data),
  async latestJobSearch(): Promise<SearchRun | null> {
    try {
      return (await http.get<SearchRun>("/jobs/search/latest")).data;
    } catch {
      return null;
    }
  },
  listJobs: (params: { status: string; country?: string; startup_only?: boolean; hide_german_required?: boolean }) =>
    http.get<{ jobs: JobListing[]; total: number }>("/jobs", { params }).then((r) => r.data),
  setJobStatus: (id: string, status: JobStatus) =>
    http.post<JobListing>(`/jobs/${id}/status`, { status }).then((r) => r.data),
  peopleAtCompany: (id: string) =>
    http
      .get<{ linkedin_url: string; name: string; position: string; status: string }[]>(`/jobs/${id}/people`)
      .then((r) => r.data),

  // api keys
  async getKey(service: KeyService): Promise<string | null> {
    try {
      const r = await http.get<{ masked: string }>(`/config/${service}`);
      return r.data.masked;
    } catch {
      return null;
    }
  },
  /** Most services take {api_key}; Adzuna takes {app_id, app_key}. */
  saveKey: (service: KeyService, payload: Record<string, string>) =>
    http
      .post<{ message: string; verified?: boolean }>(`/config/${service}`, payload)
      .then((r) => r.data),
  testKey: (service: KeyService) =>
    http.post<{ message: string }>(`/config/${service}/test`).then((r) => r.data),
};
