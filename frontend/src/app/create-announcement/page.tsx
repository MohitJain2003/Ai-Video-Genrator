"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createJobAnnouncement, listJobs } from "@/lib/api";
import type { Job } from "@/types";

export default function CreateAnnouncementPage() {
  const router = useRouter();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Previous jobs for auto-fill dropdown
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");

  // Form state
  const [formData, setFormData] = useState({
    company_name: "",
    job_role: "",
    salary: "",
    eligibility: "",
    batch: "",
    experience: "",
    location: "",
    work_mode: "Hybrid",
    last_date: "",
    cta_text: "Comment 'LINK' to Apply",
    bgm_name: "chill_lofi",
  });

  // Fetch recent completed/successful jobs to auto-fill
  useEffect(() => {
    async function loadRecentJobs() {
      try {
        const data = await listJobs(1, 50);
        // Keep jobs that have valid extracted job data
        const validJobs = data.jobs.filter(j => j.job_data && j.job_data.company_name);
        setRecentJobs(validJobs);
      } catch (err) {
        console.error("Failed to load recent jobs for auto-fill:", err);
      }
    }
    loadRecentJobs();
  }, []);

  // Handle auto-fill selection
  const handleAutoFillChange = (jobId: string) => {
    setSelectedJobId(jobId);
    if (!jobId) return;

    const selectedJob = recentJobs.find(j => j.id === jobId);
    if (selectedJob && selectedJob.job_data) {
      const jd = selectedJob.job_data;
      setFormData({
        company_name: jd.company_name || "",
        job_role: jd.job_role || "",
        salary: jd.salary || "",
        eligibility: jd.eligibility || "",
        batch: jd.batch || "",
        experience: jd.experience || "",
        location: jd.location || "",
        work_mode: jd.work_mode || "Hybrid",
        last_date: jd.last_date || "",
        cta_text: "Comment 'LINK' to Apply",
        bgm_name: "chill_lofi",
      });
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.company_name || !formData.job_role) {
      setError("Company Name and Job Role are required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const job = await createJobAnnouncement(formData);
      router.push(`/jobs/${job.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to generate announcement reel");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-black mb-2">
          <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Job Announcement Reel
          </span>
        </h1>
        <p className="text-[var(--text-muted)]">
          Create a premium 9:16 vertical short video with animated cards and random office background B-roll.
        </p>
      </div>

      {/* Auto-fill Dropdown */}
      {recentJobs.length > 0 && (
        <div className="glass rounded-xl p-5 border border-[var(--border)]">
          <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-2 uppercase tracking-wider">
            💡 Auto-fill from Existing Job
          </label>
          <select
            value={selectedJobId}
            onChange={(e) => handleAutoFillChange(e.target.value)}
            className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
          >
            <option value="">-- Choose an existing job posting to auto-populate --</option>
            {recentJobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.job_data?.company_name} — {j.job_data?.job_role} ({new Date(j.created_at).toLocaleDateString()})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Form Area */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="glass rounded-2xl p-6 md:p-8 space-y-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider border-b border-[var(--border)] pb-3">
            📋 Announcement Specifications
          </h3>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Company Name *
              </label>
              <input
                type="text"
                required
                value={formData.company_name}
                onChange={(e) => handleInputChange("company_name", e.target.value)}
                placeholder="e.g., HSBC"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Job Role *
              </label>
              <input
                type="text"
                required
                value={formData.job_role}
                onChange={(e) => handleInputChange("job_role", e.target.value)}
                placeholder="e.g., Trainee - Data Analyst"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Salary / CTC Package
              </label>
              <input
                type="text"
                value={formData.salary}
                onChange={(e) => handleInputChange("salary", e.target.value)}
                placeholder="e.g., ₹10.2 Lakhs - ₹13.4 Lakhs"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Eligibility / Degree
              </label>
              <input
                type="text"
                value={formData.eligibility}
                onChange={(e) => handleInputChange("eligibility", e.target.value)}
                placeholder="e.g., Bachelor's / Master's degree"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Target Batch
              </label>
              <input
                type="text"
                value={formData.batch}
                onChange={(e) => handleInputChange("batch", e.target.value)}
                placeholder="e.g., 2024 / 2025 grads"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Experience Needed
              </label>
              <input
                type="text"
                value={formData.experience}
                onChange={(e) => handleInputChange("experience", e.target.value)}
                placeholder="e.g., Fresh Graduates"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Location
              </label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => handleInputChange("location", e.target.value)}
                placeholder="e.g., Bangalore / Pune"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Work Mode
              </label>
              <select
                value={formData.work_mode}
                onChange={(e) => handleInputChange("work_mode", e.target.value)}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="Hybrid">Hybrid</option>
                <option value="Remote">Remote</option>
                <option value="On-site">On-site</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Deadline / Last Date to Apply
              </label>
              <input
                type="text"
                value={formData.last_date}
                onChange={(e) => handleInputChange("last_date", e.target.value)}
                placeholder="e.g., Apply Soon"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Bottom CTA Text
              </label>
              <input
                type="text"
                value={formData.cta_text}
                onChange={(e) => handleInputChange("cta_text", e.target.value)}
                placeholder="e.g., Comment 'LINK' to Apply"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>
          </div>
        </div>

        {/* Audio settings */}
        <div className="glass rounded-2xl p-6 md:p-8 space-y-4">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            🎵 Audio Overlay
          </h3>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">
              Select Background Music (Instrumental Only)
            </label>
            <select
              value={formData.bgm_name}
              onChange={(e) => handleInputChange("bgm_name", e.target.value)}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
            >
              <option value="chill_lofi">Chill Lofi (Relaxed Beat)</option>
              <option value="tech_vibes">Tech Vibes (Electronic House)</option>
              <option value="lively_lofi">Lively Lofi (Upbeat corporate)</option>
              <option value="none">Silent (No Audio track)</option>
            </select>
            <p className="text-[11px] text-[var(--text-muted)] mt-1.5">
              Note: Spoken AI voiceover will not be generated for announcement reels.
            </p>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl p-4 border border-[var(--danger)]30 bg-[var(--danger)]10 text-sm text-[var(--danger)]">
            ❌ {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 rounded-xl text-white font-bold text-lg transition-all duration-300 hover:scale-[1.01] hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            background: loading ? "var(--bg-tertiary)" : "var(--gradient-1)",
            boxShadow: loading ? "none" : "0 4px 20px var(--accent-glow)",
          }}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Compiling Announcement Video...
            </span>
          ) : (
            "🚀 Generate Announcement Reel"
          )}
        </button>
      </form>
    </div>
  );
}
