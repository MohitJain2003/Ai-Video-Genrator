/**
 * Shared TypeScript types for the frontend.
 */

// ── Job Types ──────────────────────────────────────────────────

export type JobStatus =
  | "pending"
  | "ingesting"
  | "transcribing"
  | "extracting"
  | "generating_hooks"
  | "generating_script"
  | "generating_voice"
  | "planning_scenes"
  | "generating_captions"
  | "generating_visuals"
  | "generating_video"
  | "awaiting_assembly"
  | "assembling"
  | "quality_check"
  | "completed"
  | "completed_low_quality"
  | "failed";

export type InputType =
  | "instagram_url"
  | "youtube_url"
  | "upload"
  | "article_url"
  | "pdf"
  | "manual"
  | "announcement";

export interface JobData {
  company_name: string | null;
  job_role: string | null;
  salary: string | null;
  eligibility: string | null;
  degree_requirements: string[];
  batch: string | null;
  experience: string | null;
  location: string | null;
  last_date: string | null;
  selection_process: string[];
  apply_link: string | null;
  important_notes: string[];
  work_mode?: string | null;
  cta_text?: string | null;
  bgm_name?: string | null;
}

export interface HookVariant {
  index: number;
  text: string;
  score: number;
  reasoning: string;
  is_selected: boolean;
}

export interface ScenePlan {
  scene_number: number;
  start_time: number;
  end_time: number;
  duration: number;
  visual_description: string;
  search_query: string;
  ai_prompt: string;
  transition: string;
  text_overlay: string;
}

export interface QualityScores {
  hook_quality: { score: number; reasoning: string };
  retention_score: { score: number; reasoning: string };
  readability: { score: number; reasoning: string };
  cta_effectiveness: { score: number; reasoning: string };
  overall_score: number;
  improvement_suggestions: string[];
}

export interface Job {
  id: string;
  status: JobStatus;
  input_type: InputType;
  input_value: string;
  job_data: JobData | null;
  hook_variants: HookVariant[] | null;
  selected_hook: string | null;
  script: string | null;
  scene_plan: ScenePlan[] | null;
  quality_scores: QualityScores | null;
  overall_score: number | null;
  llm_provider: string | null;
  voice_provider: string | null;
  voice_id: string | null;
  video_provider: string | null;
  voice_language: string | null;
  output_path: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProviderStatus {
  name: string;
  type: "llm" | "voice" | "video" | "stock";
  available: boolean;
}

// ── WebSocket Types ────────────────────────────────────────────

export interface WSStatusUpdate {
  type: "status_update" | "pipeline_complete" | "error";
  job_id: string;
  status: JobStatus;
  overall_score?: number;
  retry_count?: number;
  error_message?: string;
  output_path?: string;
  message?: string;
  timestamp: string;
}

// ── Status Display Info ────────────────────────────────────────

export const STATUS_INFO: Record<
  JobStatus,
  { label: string; color: string; icon: string; progress: number }
> = {
  pending: { label: "Pending", color: "#6b7280", icon: "⏳", progress: 0 },
  ingesting: { label: "Downloading & Extracting", color: "#3b82f6", icon: "📥", progress: 8 },
  transcribing: { label: "Transcribing Audio", color: "#6366f1", icon: "🎤", progress: 16 },
  extracting: { label: "Extracting Job Info", color: "#8b5cf6", icon: "🔍", progress: 24 },
  generating_hooks: { label: "Creating Hooks", color: "#a855f7", icon: "🪝", progress: 32 },
  generating_script: { label: "Writing Script", color: "#d946ef", icon: "📝", progress: 40 },
  generating_voice: { label: "Generating Voice", color: "#ec4899", icon: "🗣️", progress: 50 },
  planning_scenes: { label: "Planning Scenes", color: "#f43f5e", icon: "🎬", progress: 58 },
  generating_captions: { label: "Creating Captions", color: "#f97316", icon: "💬", progress: 66 },
  generating_visuals: { label: "Acquiring Visuals", color: "#eab308", icon: "🖼️", progress: 74 },
  generating_video: { label: "AI Video Generation", color: "#84cc16", icon: "🎥", progress: 80 },
  awaiting_assembly: { label: "Preparing Assembly", color: "#22c55e", icon: "⚙️", progress: 85 },
  assembling: { label: "Assembling Reel", color: "#14b8a6", icon: "🎞️", progress: 90 },
  quality_check: { label: "Quality Check", color: "#06b6d4", icon: "✅", progress: 95 },
  completed: { label: "Completed!", color: "#10b981", icon: "🎉", progress: 100 },
  completed_low_quality: { label: "Completed (Low Quality)", color: "#f59e0b", icon: "⚠️", progress: 100 },
  failed: { label: "Failed", color: "#ef4444", icon: "❌", progress: 0 },
};
