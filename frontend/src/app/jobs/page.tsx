"use client";

import { useState, useEffect } from "react";
import { listJobs, deleteJob } from "@/lib/api";
import type { Job } from "@/types";
import { STATUS_INFO } from "@/types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | undefined>(undefined);

  useEffect(() => {
    loadJobs();
  }, [page, filter]);

  async function loadJobs() {
    setLoading(true);
    try {
      const data = await listJobs(page, 12, filter);
      setJobs(data.jobs);
      setTotal(data.total);
    } catch {
      // API not running
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this job and all associated files?")) return;
    try {
      await deleteJob(id);
      loadJobs();
    } catch {
      // Error
    }
  }

  const totalPages = Math.ceil(total / 12);

  const filters = [
    { label: "All", value: undefined },
    { label: "Completed", value: "completed" },
    { label: "Processing", value: "assembling" },
    { label: "Failed", value: "failed" },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-[var(--text-primary)]">Job History</h1>
          <p className="text-sm text-[var(--text-muted)]">{total} total jobs</p>
        </div>
        <a
          href="/create"
          className="px-5 py-2.5 rounded-xl text-white font-semibold text-sm transition-all duration-300 hover:scale-105"
          style={{ background: "var(--gradient-1)" }}
        >
          + New Reel
        </a>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {filters.map((f) => (
          <button
            key={f.label}
            onClick={() => { setFilter(f.value); setPage(1); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              filter === f.value
                ? "bg-[var(--accent)] text-white"
                : "bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Job Grid */}
      {loading ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="glass rounded-xl p-5 animate-shimmer h-40" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="glass rounded-2xl p-12 text-center">
          <span className="text-5xl block mb-4">📋</span>
          <h2 className="text-xl font-bold mb-2">No jobs found</h2>
          <p className="text-[var(--text-muted)]">
            {filter ? "Try clearing the filter." : "Create your first reel to get started."}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => {
            const info = STATUS_INFO[job.status];
            return (
              <div key={job.id} className="glass rounded-xl overflow-hidden glass-hover transition-all duration-300 group">
                <a href={`/jobs/${job.id}`} className="block p-5">
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-2xl">{info.icon}</span>
                    <span
                      className="text-xs px-2 py-1 rounded-full font-medium"
                      style={{
                        color: info.color,
                        background: `${info.color}15`,
                        border: `1px solid ${info.color}30`,
                      }}
                    >
                      {info.label}
                    </span>
                  </div>

                  <h3 className="font-semibold text-[var(--text-primary)] group-hover:text-[var(--accent)] transition-colors mb-1 truncate">
                    {job.job_data?.company_name || "Processing..."}
                  </h3>
                  <p className="text-sm text-[var(--text-muted)] truncate mb-3">
                    {job.job_data?.job_role || job.input_type.replace("_", " ")}
                  </p>

                  {job.overall_score != null && (
                    <div className="mb-3">
                      <div className="progress-bar">
                        <div className="progress-bar-fill" style={{ width: `${job.overall_score}%` }} />
                      </div>
                      <p className="text-xs text-[var(--text-muted)] mt-1">
                        Score: {job.overall_score.toFixed(0)}/100
                      </p>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
                    <span>{new Date(job.created_at).toLocaleDateString()}</span>
                    <span className="font-mono">{job.id.slice(0, 8)}</span>
                  </div>
                </a>

                {/* Delete button */}
                <div className="border-t border-[var(--border)] px-5 py-2 flex justify-end">
                  <button
                    onClick={(e) => { e.preventDefault(); handleDelete(job.id); }}
                    className="text-xs text-[var(--text-muted)] hover:text-[var(--danger)] transition-colors"
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg text-sm bg-[var(--bg-tertiary)] text-[var(--text-muted)] disabled:opacity-30"
          >
            ← Prev
          </button>
          <span className="px-4 py-2 text-sm text-[var(--text-secondary)]">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 rounded-lg text-sm bg-[var(--bg-tertiary)] text-[var(--text-muted)] disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
