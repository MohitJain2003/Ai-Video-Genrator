"use client";

import { useState, useEffect } from "react";
import { listJobs } from "@/lib/api";
import type { Job } from "@/types";
import { STATUS_INFO } from "@/types";

export default function DashboardPage() {
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, completed: 0, processing: 0, failed: 0 });

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    try {
      const data = await listJobs(1, 6);
      setRecentJobs(data.jobs);

      const completed = data.jobs.filter(j => j.status === "completed" || j.status === "completed_low_quality").length;
      const failed = data.jobs.filter(j => j.status === "failed").length;
      const processing = data.jobs.filter(j => !["completed", "completed_low_quality", "failed", "pending"].includes(j.status)).length;

      setStats({ total: data.total, completed, processing, failed });
    } catch {
      // API not yet running
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-2xl p-8 md:p-12"
        style={{ background: "var(--gradient-3)" }}>
        <div className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: "radial-gradient(circle at 20% 50%, var(--accent) 0%, transparent 50%), radial-gradient(circle at 80% 50%, #a855f7 0%, transparent 50%)",
          }}
        />
        <div className="relative">
          <h1 className="text-3xl md:text-5xl font-black mb-4">
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              AI Job Reel Generator
            </span>
          </h1>
          <p className="text-[var(--text-secondary)] text-lg max-w-2xl mb-8">
            Transform job postings into scroll-stopping vertical reels. AI-powered voiceover,
            captions, and B-roll visuals — generated in minutes, not hours.
          </p>
          <a
            href="/create"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl text-white font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg"
            style={{
              background: "var(--gradient-1)",
              boxShadow: "0 4px 20px var(--accent-glow)",
            }}
          >
            ✨ Create New Reel
          </a>
        </div>
      </section>

      {/* Stats Cards */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Jobs", value: stats.total, icon: "📊", color: "#6366f1" },
          { label: "Completed", value: stats.completed, icon: "✅", color: "#10b981" },
          { label: "Processing", value: stats.processing, icon: "⚡", color: "#f59e0b" },
          { label: "Failed", value: stats.failed, icon: "❌", color: "#ef4444" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="glass rounded-xl p-5 glass-hover transition-all duration-300 cursor-default"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-2xl">{stat.icon}</span>
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: stat.color, boxShadow: `0 0 8px ${stat.color}` }}
              />
            </div>
            <p className="text-3xl font-bold" style={{ color: stat.color }}>
              {loading ? "—" : stat.value}
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-1">{stat.label}</p>
          </div>
        ))}
      </section>

      {/* How It Works */}
      <section>
        <h2 className="text-xl font-bold mb-6 text-[var(--text-primary)]">How It Works</h2>
        <div className="grid md:grid-cols-4 gap-4">
          {[
            { step: "1", title: "Input", desc: "Upload reel, paste URL, or enter job details manually", icon: "📥" },
            { step: "2", title: "Extract", desc: "AI extracts company, role, salary, eligibility & more", icon: "🔍" },
            { step: "3", title: "Generate", desc: "Creates hook, script, voiceover, captions & scene plan", icon: "⚡" },
            { step: "4", title: "Output", desc: "Assembles a premium 9:16 vertical reel ready to post", icon: "🎬" },
          ].map((item, i) => (
            <div
              key={item.step}
              className="glass rounded-xl p-6 glass-hover transition-all duration-300 animate-slide-up"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold mb-4"
                style={{ background: "var(--gradient-1)" }}
              >
                {item.icon}
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-mono text-[var(--accent)] bg-[var(--bg-tertiary)] px-2 py-0.5 rounded">
                  Step {item.step}
                </span>
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-1">{item.title}</h3>
              <p className="text-sm text-[var(--text-muted)]">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Recent Jobs */}
      {recentJobs.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-[var(--text-primary)]">Recent Jobs</h2>
            <a href="/jobs" className="text-sm text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors">
              View All →
            </a>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentJobs.map((job) => {
              const info = STATUS_INFO[job.status];
              return (
                <a
                  key={job.id}
                  href={`/jobs/${job.id}`}
                  className="glass rounded-xl p-5 glass-hover transition-all duration-300 group"
                >
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
                  <h3 className="font-semibold text-[var(--text-primary)] mb-1 group-hover:text-[var(--accent)] transition-colors truncate">
                    {job.job_data?.company_name || job.input_value || "Processing..."}
                  </h3>
                  <p className="text-sm text-[var(--text-muted)] truncate">
                    {job.job_data?.job_role || job.input_type.replace("_", " ")}
                  </p>
                  {job.overall_score != null && (
                    <div className="mt-3">
                      <div className="progress-bar">
                        <div
                          className="progress-bar-fill"
                          style={{ width: `${job.overall_score}%` }}
                        />
                      </div>
                      <p className="text-xs text-[var(--text-muted)] mt-1">
                        Quality: {job.overall_score.toFixed(0)}/100
                      </p>
                    </div>
                  )}
                  <p className="text-xs text-[var(--text-muted)] mt-2">
                    {new Date(job.created_at).toLocaleDateString()}
                  </p>
                </a>
              );
            })}
          </div>
        </section>
      )}

      {/* Empty State */}
      {!loading && recentJobs.length === 0 && (
        <section className="glass rounded-2xl p-12 text-center">
          <div className="text-6xl mb-4">🎬</div>
          <h2 className="text-2xl font-bold mb-2 text-[var(--text-primary)]">No reels yet</h2>
          <p className="text-[var(--text-muted)] mb-6">
            Create your first AI-generated job reel in minutes.
          </p>
          <a
            href="/create"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-white font-semibold transition-all duration-300 hover:scale-105"
            style={{ background: "var(--gradient-1)" }}
          >
            ✨ Get Started
          </a>
        </section>
      )}
    </div>
  );
}
