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
  embedding_calls?: number;
  adzuna_calls?: number;
  apify_results?: number;
  estimated_cost: number | null;
  /** Some used service has no price set, so it was counted as free. */
  free_tier_assumed?: boolean;
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
    apify_per_result: number | null;
  };
  budget: { monthly_usd: number | null; monthly_profiles: number | null; monthly_apify_results: number | null };
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

export type ActiveTab = "generator" | "jobs" | "tracker" | "history" | "resume" | "style" | "config";

export type Seniority = "intern" | "entry" | "junior" | "mid" | "senior";
export type CompanyType = "startup" | "scaleup" | "enterprise" | "any";

export interface SearchProfile {
  titles: string[];
  seniority: Seniority;
  skills: string[];
  countries: string[];
  company_types: CompanyType[];
  needs_sponsorship: boolean;
  languages: { name: string; level: string }[];
  willing_to_relocate: boolean;
  remote: "remote" | "hybrid" | "onsite" | "any";
  min_salary: { amount: number; currency: string } | null;
  career_direction: string;
  clarifications: { question: string; answer: string }[];
  hide_german_required: boolean;
  employment_types: ("full_time" | "part_time" | "contract")[];
  experience_levels: ("internship" | "entry" | "associate" | "mid_senior" | "director")[];
  posted_within_days: 7 | 14 | 30;
  years_experience: number | null;
  hide_above_level: boolean;
}

export interface QuestionnaireOption {
  value: string | number;
  label: string;
}

export interface QuestionnaireQuestion {
  id: "employment_types" | "experience_levels" | "remote" | "posted_within_days";
  label: string;
  multi: boolean;
  options: QuestionnaireOption[];
}

/** One search the profile would run, shown before anything is called. */
export interface JobSearchPreview {
  source: "linkedin" | "adzuna";
  country: string;
  title: string;
  url?: string;
  params?: Record<string, string | number>;
}

export interface ProfileQuestion {
  id: string;
  question: string;
  options: string[];
}

export interface JobsMeta {
  countries: { code: string; name: string; adzuna: boolean }[];
  language_levels: string[];
  sources: Record<string, boolean>;
  resume_confirmed: boolean;
  questionnaire: QuestionnaireQuestion[];
}

export type JobStatus = "new" | "saved" | "applied" | "dismissed";

export interface JobReview {
  fit: number | null;
  reasons: string[];
  missing_skills: string[];
  german_required: "yes" | "no" | "unclear";
  german_level: string;
  sponsorship: "yes" | "no" | "unclear";
  company_kind: string;
}

export interface JobListing {
  id: string;
  title: string;
  company: string;
  location: string;
  country: string;
  description: string;
  description_is_snippet: boolean;
  url: string;
  sources: { source: string; url: string }[];
  posted_at: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  remote: string | null;
  seniority: string | null;
  company_size: number | null;
  applicants: number | null;
  status: JobStatus;
  score: number | null;
  score_breakdown: Record<string, number | null | Record<string, number>> | null;
  review: JobReview | null;
  company_kind: string;
  company_kind_verified: boolean;
  german_required: "yes" | "no" | "unclear";
  german_gap: boolean;
  sponsorship: "yes" | "no" | "unclear";
  via_adzuna: boolean;
  above_level: boolean;
  above_level_reason: string | null;
}

export interface TailoredResume {
  id: string;
  job_id: string | null;
  job_title: string;
  company: string;
  resume: StructuredResume;
  changes: string[];
  keywords: string[];
  guard_notes: string[];
  fact_check: FactCheck | null;
  has_pdf: boolean;
  pdf_compiled_at: string | null;
  created_at: string;
  updated_at: string;
  compiler?: string;
}

export interface SearchRun {
  search_id: string;
  status: "running" | "done" | "failed";
  stage: string;
  message: string;
  started_at: string;
  finished_at: string | null;
  stats: Record<string, number>;
  notices: string[];
  error: string | null;
  usage?: UsageTotals;
}
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
