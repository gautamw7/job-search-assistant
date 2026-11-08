export type Length = "short" | "medium" | "detailed";
export type Tone = "professional" | "friendly" | "casual" | "confident" | "neutral";

export interface TargetRow {
  id: string;
  url: string;
  note: string;
  length?: Length;
  tone?: Tone;
  /** Re-scrape the profile instead of using the cached copy. */
  refresh?: boolean;
}

export type TargetStatus =
  | "queued"
  | "enriching"
  | "drafting"
  | "checking"
  | "success"
  | "failed"
  | "cancelled";

export interface FactCheck {
  status: "pass" | "flagged" | "skipped" | "error";
  issues: { claim: string; reason: string }[];
  error?: string | null;
}

export interface JobTarget {
  linkedin_url: string;
  status: TargetStatus;
  generated_message: string | null;
  generated_at: string | null;
  error: string | null;
  fact_check?: FactCheck | null;
  shared_background?: string[];
}

export interface UsageTotals {
  brightdata_profiles: number;
  gemini_calls: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost: number | null;
}

export interface Job {
  job_id: string;
  status: "running" | "done" | "cancelled";
  targets: JobTarget[];
  usage?: UsageTotals;
}

export interface Generation {
  generated_message: string;
  generated_at: string;
  user_note?: string | null;
  kind?: "outreach" | "followup";
  fact_check?: FactCheck | null;
  shared_background?: string[];
}

export type ContactStatus = "drafted" | "sent" | "replied" | "interviewing" | "closed";

export interface Tracking {
  status: ContactStatus;
  notes: string;
  sent_at: string | null;
  last_contact_at: string | null;
  replied_at: string | null;
  followup_count: number;
  updated_at: string | null;
}

export interface HistoryEntry {
  generations?: Generation[];
  tracking?: Tracking;
}

export interface Contact extends Tracking {
  linkedin_url: string;
  latest_message: string;
  latest_kind: "outreach" | "followup";
  latest_at: string | null;
  original_message: string;
  message_count: number;
  followup_due: boolean;
  followup_due_at: string | null;
  days_since_contact: number | null;
}

export interface HiringContact {
  linkedin_url: string;
  name: string;
  headline: string;
  location: string;
  signals: string[];
  checked: boolean;
  hiring_posts: number | null;
  latest_hiring_post: string | null;
}

export interface UsageSettings {
  pricing: {
    brightdata_per_profile: number | null;
    gemini_input_per_million: number | null;
    gemini_output_per_million: number | null;
  };
  budget: { monthly_usd: number | null; monthly_profiles: number | null };
  fact_check_enabled: boolean;
}

export interface UsageSummary {
  month: UsageTotals & { period: string };
  today: UsageTotals;
  settings: UsageSettings;
  pricing_configured: boolean;
}

export interface ProfileCard {
  name?: string;
  position?: string;
  current_company_name?: string;
  location?: string;
  followers?: number;
  connections?: number;
  url?: string;
}

export interface Post {
  title?: string;
  link?: string;
}

export interface ProfileDetails {
  card: ProfileCard | null;
  activity: { hiring: Post[]; dropped: Post[] } | null;
  discovery: { people_also_viewed: Array<Record<string, string>> } | null;
}

export type ActiveTab = "generator" | "tracker" | "history" | "resume" | "style" | "config";
export type KeyService = "brightdata" | "gemini" | "adzuna" | "apify";

export interface StructuredResume {
  contact: { name: string; email: string; phone: string; location: string; links: string[] };
  summary: string;
  education: {
    institution: string;
    degree: string;
    field: string;
    location: string;
    start: string;
    end: string;
    grade: string;
    highlights: string[];
  }[];
  experience: { title: string; company: string; location: string; start: string; end: string; bullets: string[] }[];
  projects: { name: string; tech: string[]; link: string; bullets: string[] }[];
  skills: { category: string; items: string[] }[];
  certifications: string[];
  languages: { name: string; level: string }[];
}

export interface StructuredResumeState {
  resume: StructuredResume;
  confirmed: boolean;
  updated_at: string;
  stale: boolean;
}
