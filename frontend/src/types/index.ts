export interface TargetRow {
  id: string;
  linkedin_url: string;
  additional_note: string;
  length?: "short" | "medium" | "detailed";
  tone?: "professional" | "friendly" | "casual" | "confident" | "neutral";
}

export interface MessageCardData {
  linkedin_url: string;
  generated_message: string | null;
  generated_at: string | null;
  status: "success" | "failed";
  error: string | null;
  isRegenerating?: boolean;
}

export type ActiveTab = "generator" | "history" | "resume" | "style" | "config";
