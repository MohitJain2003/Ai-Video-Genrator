/**
 * API client for communicating with the FastAPI backend.
 */

import type { Job, JobListResponse, ProviderStatus } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Helper ─────────────────────────────────────────────────────

async function fetchJSON<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || errBody.error || `API error: ${res.status}`);
  }

  return res.json();
}

// ── Jobs API ───────────────────────────────────────────────────

export async function createJobFromURL(
  url: string,
  llm_provider?: string,
  voice_provider?: string,
  voice_id?: string,
  video_provider?: string,
  voice_language?: string
): Promise<Job> {
  return fetchJSON<Job>("/api/v1/jobs", {
    method: "POST",
    body: JSON.stringify({ url, llm_provider, voice_provider, voice_id, video_provider, voice_language }),
  });
}

export async function createJobFromUpload(
  file: File,
  llm_provider?: string,
  voice_provider?: string,
  voice_id?: string,
  video_provider?: string,
  voice_language?: string
): Promise<Job> {
  const formData = new FormData();
  formData.append("file", file);
  if (llm_provider) formData.append("llm_provider", llm_provider);
  if (voice_provider) formData.append("voice_provider", voice_provider);
  if (voice_id) formData.append("voice_id", voice_id);
  if (video_provider) formData.append("video_provider", video_provider);
  if (voice_language) formData.append("voice_language", voice_language);

  const res = await fetch(`${API_BASE}/api/v1/jobs/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Upload failed: ${res.status}`);
  }

  return res.json();
}

export async function createJobManual(
  jobData: Record<string, unknown>,
  llm_provider?: string,
  voice_provider?: string,
  voice_id?: string,
  video_provider?: string,
  voice_language?: string
): Promise<Job> {
  return fetchJSON<Job>("/api/v1/jobs/manual", {
    method: "POST",
    body: JSON.stringify({
      job_data: jobData,
      llm_provider,
      voice_provider,
      voice_id,
      video_provider,
      voice_language,
    }),
  });
}

export async function createJobAnnouncement(
  jobData: Record<string, unknown>
): Promise<Job> {
  return fetchJSON<Job>("/api/v1/jobs/announcement", {
    method: "POST",
    body: JSON.stringify({
      job_data: jobData,
    }),
  });
}

export interface VoiceInfo {
  id: string;
  name: string;
  language: string;
  gender: string;
}

export async function listVoices(provider: string, language: string): Promise<VoiceInfo[]> {
  const params = new URLSearchParams({ provider, language });
  const data = await fetchJSON<{ voices: VoiceInfo[] }>(`/api/v1/voices?${params.toString()}`);
  return data.voices;
}

export async function listJobs(
  page = 1,
  pageSize = 20,
  status?: string
): Promise<JobListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) params.set("status", status);
  return fetchJSON<JobListResponse>(`/api/v1/jobs?${params}`);
}

export async function getJob(jobId: string): Promise<Job> {
  return fetchJSON<Job>(`/api/v1/jobs/${jobId}`);
}

export async function deleteJob(jobId: string): Promise<void> {
  await fetchJSON(`/api/v1/jobs/${jobId}`, { method: "DELETE" });
}

export async function retryJob(jobId: string): Promise<Job> {
  return fetchJSON<Job>(`/api/v1/jobs/${jobId}/retry`, { method: "POST" });
}

export async function getJobStatus(
  jobId: string
): Promise<{ status: string; overall_score?: number }> {
  return fetchJSON(`/api/v1/jobs/${jobId}/status`);
}

export async function getHooks(
  jobId: string
): Promise<{ hooks: Job["hook_variants"]; selected_hook: string }> {
  return fetchJSON(`/api/v1/jobs/${jobId}/hooks`);
}

export async function selectHook(
  jobId: string,
  hookIndex: number
): Promise<Job> {
  return fetchJSON<Job>(`/api/v1/jobs/${jobId}/hooks/select`, {
    method: "PUT",
    body: JSON.stringify({ hook_index: hookIndex }),
  });
}

export async function updateScript(
  jobId: string,
  script: string
): Promise<Job> {
  return fetchJSON<Job>(`/api/v1/jobs/${jobId}/script`, {
    method: "PUT",
    body: JSON.stringify({ script }),
  });
}

export async function getProviders(): Promise<{ providers: ProviderStatus[] }> {
  return fetchJSON(`/api/v1/providers`);
}

export function getDownloadURL(jobId: string): string {
  return `${API_BASE}/api/v1/jobs/${jobId}/download`;
}

export function getPreviewURL(jobId: string): string {
  return `${API_BASE}/api/v1/jobs/${jobId}/preview`;
}

// ── WebSocket ──────────────────────────────────────────────────

export function getWSURL(jobId: string): string {
  const wsBase = API_BASE.replace("http://", "ws://").replace("https://", "wss://");
  return `${wsBase}/api/v1/ws/${jobId}`;
}
