"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { getJob, retryJob, getDownloadURL } from "@/lib/api";
import { useJobWebSocket } from "@/hooks/useWebSocket";
import type { Job } from "@/types";
import { STATUS_INFO } from "@/types";

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "hooks" | "script" | "scenes" | "quality">("overview");

  // WebSocket for real-time updates
  const ws = useJobWebSocket(jobId);

  useEffect(() => {
    loadJob();
  }, [jobId]);

  // Refresh job data when WS status changes
  useEffect(() => {
    if (ws.status) {
      loadJob();
    }
  }, [ws.status]);

  async function loadJob() {
    try {
      const data = await getJob(jobId);
      setJob(data);
    } catch {
      // API error
    } finally {
      setLoading(false);
    }
  }

  async function handleRetry() {
    try {
      await retryJob(jobId);
      loadJob();
    } catch (err) {
      console.error("Retry failed:", err);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[var(--accent)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-[var(--text-muted)]">Loading job details...</p>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl block mb-4">🔍</span>
        <h2 className="text-xl font-bold mb-2">Job not found</h2>
        <a href="/" className="text-[var(--accent)]">Go back home</a>
      </div>
    );
  }

  const statusInfo = STATUS_INFO[ws.status || job.status];
  const isProcessing = !["completed", "completed_low_quality", "failed", "pending"].includes(ws.status || job.status);
  const isCompleted = (ws.status || job.status) === "completed" || (ws.status || job.status) === "completed_low_quality";

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-3xl">{statusInfo.icon}</span>
            <h1 className="text-2xl font-black text-[var(--text-primary)]">
              {job.job_data?.company_name || "Processing..."}
            </h1>
          </div>
          <p className="text-[var(--text-muted)]">
            {job.job_data?.job_role || job.input_type.replace("_", " ")} • Created{" "}
            {new Date(job.created_at).toLocaleString()}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Status Badge */}
          <span
            className="px-4 py-2 rounded-xl text-sm font-semibold"
            style={{
              color: statusInfo.color,
              background: `${statusInfo.color}15`,
              border: `1px solid ${statusInfo.color}40`,
              boxShadow: isProcessing ? `0 0 15px ${statusInfo.color}30` : "none",
            }}
          >
            {isProcessing && (
              <span className="inline-block w-2 h-2 rounded-full mr-2 animate-pulse" style={{ background: statusInfo.color }} />
            )}
            {statusInfo.label}
          </span>

          {/* Actions */}
          {isCompleted && (
            <a
              href={getDownloadURL(jobId)}
              className="px-5 py-2 rounded-xl text-white font-semibold text-sm transition-all duration-300 hover:scale-105"
              style={{ background: "var(--gradient-1)" }}
            >
              ⬇️ Download Reel
            </a>
          )}
          {job.status === "failed" && (
            <button
              onClick={handleRetry}
              className="px-5 py-2 rounded-xl text-white font-semibold text-sm bg-[var(--danger)] hover:opacity-90 transition-opacity"
            >
              🔄 Retry
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar (during processing) */}
      {isProcessing && (
        <div className="glass rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-[var(--text-secondary)]">{statusInfo.label}</p>
            <p className="text-sm text-[var(--accent)]">{statusInfo.progress}%</p>
          </div>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${statusInfo.progress}%` }} />
          </div>
          {ws.isConnected && (
            <p className="text-xs text-[var(--text-muted)] mt-2 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Live updates connected
            </p>
          )}
        </div>
      )}

      {/* Error Message */}
      {job.error_message && (
        <div className="rounded-xl p-4 border border-red-500/30 bg-red-500/10 text-sm text-red-400">
          <strong>Error:</strong> {job.error_message}
        </div>
      )}

      {/* Content Tabs */}
      <div className="flex gap-1 bg-[var(--bg-secondary)] p-1 rounded-xl overflow-x-auto">
        {(["overview", "hooks", "script", "scenes", "quality"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              activeTab === tab
                ? "bg-[var(--bg-hover)] text-[var(--text-primary)] shadow-lg"
                : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
            }`}
            style={activeTab === tab ? { boxShadow: "0 0 10px var(--accent-glow)" } : {}}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="glass rounded-2xl p-6 md:p-8 min-h-[300px]">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Left: Job Data */}
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-[var(--text-primary)] mb-4">📋 Extracted Job Data</h3>
              {job.job_data ? (
                <div className="space-y-3">
                  {[
                    { label: "Company", value: job.job_data.company_name, icon: "🏢" },
                    { label: "Role", value: job.job_data.job_role, icon: "💼" },
                    { label: "Salary", value: job.job_data.salary, icon: "💰" },
                    { label: "Eligibility", value: job.job_data.eligibility, icon: "🎓" },
                    { label: "Batch", value: job.job_data.batch, icon: "📅" },
                    { label: "Experience", value: job.job_data.experience, icon: "⭐" },
                    { label: "Location", value: job.job_data.location, icon: "📍" },
                    { label: "Last Date", value: job.job_data.last_date, icon: "⏰" },
                    { label: "Apply Link", value: job.job_data.apply_link, icon: "🔗" },
                  ].map((field) => (
                    field.value && (
                      <div key={field.label} className="flex items-start gap-3 p-3 bg-[var(--bg-tertiary)] rounded-lg">
                        <span>{field.icon}</span>
                        <div>
                          <p className="text-xs text-[var(--text-muted)]">{field.label}</p>
                          <p className="text-sm font-medium text-[var(--text-primary)]">
                            {field.label === "Apply Link" ? (
                              <a href={field.value} target="_blank" rel="noopener noreferrer" className="text-[var(--accent)] hover:underline">
                                {field.value}
                              </a>
                            ) : field.value}
                          </p>
                        </div>
                      </div>
                    )
                  ))}
                </div>
              ) : (
                <p className="text-[var(--text-muted)]">Job data not yet extracted...</p>
              )}
            </div>

            {/* Right: Preview or Metadata */}
            <div className="space-y-4">
              {isCompleted && job.output_path ? (
                <div>
                  <h3 className="text-lg font-bold text-[var(--text-primary)] mb-4">🎬 Reel Preview</h3>
                  <div className="reel-preview mx-auto" style={{ maxWidth: "280px" }}>
                    <video
                      src={getDownloadURL(jobId)}
                      controls
                      playsInline
                      className="w-full h-full"
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <h3 className="text-lg font-bold text-[var(--text-primary)] mb-4">ℹ️ Job Info</h3>
                  <div className="space-y-3">
                    <div className="p-3 bg-[var(--bg-tertiary)] rounded-lg">
                      <p className="text-xs text-[var(--text-muted)]">Input Type</p>
                      <p className="text-sm font-medium">{job.input_type.replace("_", " ")}</p>
                    </div>
                    <div className="p-3 bg-[var(--bg-tertiary)] rounded-lg">
                      <p className="text-xs text-[var(--text-muted)]">Voice Provider</p>
                      <p className="text-sm font-medium">{job.voice_provider || "Default"}</p>
                    </div>
                    <div className="p-3 bg-[var(--bg-tertiary)] rounded-lg">
                      <p className="text-xs text-[var(--text-muted)]">Language</p>
                      <p className="text-sm font-medium">{job.voice_language || "Hinglish"}</p>
                    </div>
                    {job.overall_score != null && (
                      <div className="p-3 bg-[var(--bg-tertiary)] rounded-lg">
                        <p className="text-xs text-[var(--text-muted)]">Quality Score</p>
                        <p className="text-2xl font-bold" style={{
                          color: job.overall_score >= 90 ? "var(--success)" : job.overall_score >= 70 ? "var(--warning)" : "var(--danger)"
                        }}>
                          {job.overall_score.toFixed(0)}/100
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Hooks Tab */}
        {activeTab === "hooks" && (
          <div>
            <h3 className="text-lg font-bold text-[var(--text-primary)] mb-4">🪝 Hook Variants</h3>
            {job.hook_variants && job.hook_variants.length > 0 ? (
              <div className="space-y-3">
                {job.hook_variants.map((hook, i) => (
                  <div
                    key={i}
                    className={`p-4 rounded-xl border transition-all duration-200 ${
                      hook.is_selected
                        ? "border-[var(--accent)] bg-[var(--accent)]10"
                        : "border-[var(--border)] bg-[var(--bg-tertiary)] hover:border-[var(--text-muted)]"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <p className="font-medium text-[var(--text-primary)]">&ldquo;{hook.text}&rdquo;</p>
                        {hook.reasoning && (
                          <p className="text-xs text-[var(--text-muted)] mt-1">{hook.reasoning}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className="text-sm font-bold px-3 py-1 rounded-full"
                          style={{
                            color: hook.score >= 85 ? "var(--success)" : hook.score >= 70 ? "var(--warning)" : "var(--danger)",
                            background: `${hook.score >= 85 ? "var(--success)" : hook.score >= 70 ? "var(--warning)" : "var(--danger)"}15`,
                          }}
                        >
                          {hook.score}
                        </span>
                        {hook.is_selected && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--accent)] text-white">
                            Selected
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[var(--text-muted)]">Hooks not yet generated...</p>
            )}
          </div>
        )}

        {/* Script Tab */}
        {activeTab === "script" && (
          <div>
            <h3 className="text-lg font-bold text-[var(--text-primary)] mb-4">📝 Generated Script</h3>
            {job.script ? (
              <div className="bg-[var(--bg-tertiary)] rounded-xl p-6 font-mono text-sm leading-relaxed whitespace-pre-wrap text-[var(--text-secondary)]">
                {job.script}
              </div>
            ) : (
              <p className="text-[var(--text-muted)]">Script not yet generated...</p>
            )}
          </div>
        )}

        {/* Scenes Tab */}
        {activeTab === "scenes" && (
          <div>
            <h3 className="text-lg font-bold text-[var(--text-primary)] mb-4">🎬 Scene Plan</h3>
            {job.scene_plan && job.scene_plan.length > 0 ? (
              <div className="space-y-3">
                {job.scene_plan.map((scene, i) => (
                  <div key={i} className="flex gap-4 p-4 bg-[var(--bg-tertiary)] rounded-xl">
                    <div className="flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center text-sm font-bold"
                      style={{ background: "var(--gradient-2)" }}>
                      S{scene.scene_number}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-[var(--accent)]">
                          {scene.start_time}s — {scene.end_time}s
                        </span>
                        <span className="text-xs px-2 py-0.5 bg-[var(--bg-hover)] rounded text-[var(--text-muted)]">
                          {scene.transition}
                        </span>
                      </div>
                      <p className="text-sm text-[var(--text-primary)]">{scene.visual_description}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[var(--text-muted)]">Scene plan not yet created...</p>
            )}
          </div>
        )}

        {/* Quality Tab */}
        {activeTab === "quality" && (
          <div>
            <h3 className="text-lg font-bold text-[var(--text-primary)] mb-4">✅ Quality Report</h3>
            {job.quality_scores ? (
              <div className="space-y-6">
                {/* Overall Score */}
                <div className="text-center p-6 bg-[var(--bg-tertiary)] rounded-xl">
                  <p className="text-sm text-[var(--text-muted)] mb-2">Overall Quality Score</p>
                  <p className="text-5xl font-black" style={{
                    color: (job.overall_score || 0) >= 90 ? "var(--success)" : (job.overall_score || 0) >= 70 ? "var(--warning)" : "var(--danger)"
                  }}>
                    {job.overall_score?.toFixed(0) || "—"}
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">out of 100</p>
                </div>

                {/* Dimension Scores */}
                <div className="grid md:grid-cols-2 gap-4">
                  {[
                    { key: "hook_quality", label: "Hook Quality", icon: "🪝", weight: "30%" },
                    { key: "retention_score", label: "Retention", icon: "📈", weight: "30%" },
                    { key: "readability", label: "Readability", icon: "👁️", weight: "20%" },
                    { key: "cta_effectiveness", label: "CTA Effectiveness", icon: "🎯", weight: "20%" },
                  ].map((dim) => {
                    const score = (job.quality_scores as Record<string, any>)?.[dim.key];
                    const scoreVal = typeof score === "object" ? score?.score : score;
                    const reasoning = typeof score === "object" ? score?.reasoning : "";
                    return (
                      <div key={dim.key} className="p-4 bg-[var(--bg-tertiary)] rounded-xl">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-[var(--text-secondary)]">
                            {dim.icon} {dim.label}
                          </span>
                          <span className="text-xs text-[var(--text-muted)]">Weight: {dim.weight}</span>
                        </div>
                        <p className="text-2xl font-bold" style={{
                          color: scoreVal >= 90 ? "var(--success)" : scoreVal >= 70 ? "var(--warning)" : "var(--danger)"
                        }}>
                          {scoreVal || "—"}
                        </p>
                        {reasoning && (
                          <p className="text-xs text-[var(--text-muted)] mt-1">{reasoning}</p>
                        )}
                        <div className="progress-bar mt-2">
                          <div className="progress-bar-fill" style={{ width: `${scoreVal || 0}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Suggestions */}
                {job.quality_scores.improvement_suggestions && job.quality_scores.improvement_suggestions.length > 0 && (
                  <div className="p-4 bg-[var(--bg-tertiary)] rounded-xl">
                    <h4 className="text-sm font-semibold text-[var(--text-secondary)] mb-3">💡 Improvement Suggestions</h4>
                    <ul className="space-y-2">
                      {job.quality_scores.improvement_suggestions.map((s: string, i: number) => (
                        <li key={i} className="text-sm text-[var(--text-muted)] flex items-start gap-2">
                          <span className="text-[var(--accent)] mt-0.5">•</span>
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {job.retry_count > 0 && (
                  <p className="text-xs text-[var(--text-muted)]">
                    Quality retries: {job.retry_count}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-[var(--text-muted)]">Quality report not yet available...</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
