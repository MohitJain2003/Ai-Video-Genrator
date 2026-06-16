"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createJobFromURL, createJobFromUpload, createJobManual, listVoices } from "@/lib/api";

type InputMode = "url" | "upload" | "manual";

export default function CreateReelPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<InputMode>("url");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // URL state
  const [url, setUrl] = useState("");

  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // Manual state
  const [manualData, setManualData] = useState({
    company_name: "",
    job_role: "",
    salary: "",
    eligibility: "",
    batch: "",
    experience: "",
    location: "",
    last_date: "",
    apply_link: "",
  });

  // Provider settings
  const [llmProvider, setLlmProvider] = useState("openai");
  const [voiceProvider, setVoiceProvider] = useState("openai");
  const [voiceId, setVoiceId] = useState("");
  const [voicesList, setVoicesList] = useState<{ id: string; name: string; gender: string }[]>([]);
  const [loadingVoices, setLoadingVoices] = useState(false);
  const [videoProvider, setVideoProvider] = useState("pexels");
  const [voiceLanguage, setVoiceLanguage] = useState("hinglish");

  // Load voices when provider or language changes
  useEffect(() => {
    let active = true;
    const fetchVoices = async () => {
      setLoadingVoices(true);
      try {
        const list = await listVoices(voiceProvider, voiceLanguage);
        if (!active) return;
        setVoicesList(list);
        if (list.length > 0) {
          setVoiceId(list[0].id);
        } else {
          setVoiceId("");
        }
      } catch (err) {
        console.error("Failed to load voices:", err);
      } finally {
        if (active) setLoadingVoices(false);
      }
    };
    fetchVoices();
    return () => {
      active = false;
    };
  }, [voiceProvider, voiceLanguage]);

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      let job;

      if (mode === "url") {
        if (!url.trim()) throw new Error("Please enter a URL");
        job = await createJobFromURL(url, llmProvider, voiceProvider, voiceId, videoProvider, voiceLanguage);
      } else if (mode === "upload") {
        if (!file) throw new Error("Please select a file");
        job = await createJobFromUpload(file, llmProvider, voiceProvider, voiceId, videoProvider, voiceLanguage);
      } else {
        if (!manualData.company_name || !manualData.job_role) {
          throw new Error("Company name and job role are required");
        }
        job = await createJobManual(manualData, llmProvider, voiceProvider, voiceId, videoProvider, voiceLanguage);
      }

      router.push(`/jobs/${job.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  }, []);

  const modes: { key: InputMode; label: string; icon: string; desc: string }[] = [
    { key: "url", label: "URL Input", icon: "🔗", desc: "Instagram, YouTube, or article URL" },
    { key: "upload", label: "Upload File", icon: "📁", desc: "MP4, MOV, WebM, or PDF file" },
    { key: "manual", label: "Manual Entry", icon: "✏️", desc: "Type job details directly" },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-black mb-2">
          <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Create New Reel
          </span>
        </h1>
        <p className="text-[var(--text-muted)]">
          Provide a job source and we&apos;ll generate a complete AI-powered reel.
        </p>
      </div>

      {/* Input Mode Tabs */}
      <div className="grid grid-cols-3 gap-3">
        {modes.map((m) => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            className={`p-4 rounded-xl text-left transition-all duration-300 border ${
              mode === m.key
                ? "border-[var(--accent)] bg-[var(--bg-hover)]"
                : "border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--text-muted)]"
            }`}
            style={mode === m.key ? { boxShadow: "0 0 20px var(--accent-glow)" } : {}}
          >
            <span className="text-2xl block mb-2">{m.icon}</span>
            <p className="font-semibold text-sm text-[var(--text-primary)]">{m.label}</p>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">{m.desc}</p>
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="glass rounded-2xl p-6 md:p-8 space-y-6">
        {/* URL Mode */}
        {mode === "url" && (
          <div className="space-y-4">
            <label className="block text-sm font-medium text-[var(--text-secondary)]">
              Paste URL
            </label>
            <div className="relative">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.instagram.com/reel/... or https://youtube.com/shorts/..."
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-4 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] transition-all duration-200"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
                🔗
              </span>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-[var(--text-muted)]">
              <span className="px-2 py-1 bg-[var(--bg-tertiary)] rounded-full">Instagram Reels</span>
              <span className="px-2 py-1 bg-[var(--bg-tertiary)] rounded-full">YouTube Shorts</span>
              <span className="px-2 py-1 bg-[var(--bg-tertiary)] rounded-full">Job Article URLs</span>
            </div>
          </div>
        )}

        {/* Upload Mode */}
        {mode === "upload" && (
          <div className="space-y-4">
            <label className="block text-sm font-medium text-[var(--text-secondary)]">
              Upload File
            </label>
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300 ${
                dragActive
                  ? "border-[var(--accent)] bg-[var(--accent-glow)]"
                  : file
                  ? "border-[var(--success)] bg-[var(--success)]10"
                  : "border-[var(--border)] hover:border-[var(--accent)] bg-[var(--bg-tertiary)]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".mp4,.mov,.webm,.pdf"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
              />

              {file ? (
                <div>
                  <span className="text-4xl block mb-3">✅</span>
                  <p className="font-semibold text-[var(--text-primary)]">{file.name}</p>
                  <p className="text-sm text-[var(--text-muted)] mt-1">
                    {(file.size / 1024 / 1024).toFixed(1)} MB
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    className="text-xs text-[var(--danger)] mt-2 hover:underline"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div>
                  <span className="text-4xl block mb-3">📁</span>
                  <p className="font-semibold text-[var(--text-primary)]">
                    Drop file here or click to browse
                  </p>
                  <p className="text-sm text-[var(--text-muted)] mt-1">
                    MP4, MOV, WebM, PDF — Max 500MB
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Manual Mode */}
        {mode === "manual" && (
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              {[
                { key: "company_name", label: "Company Name *", placeholder: "e.g., Infosys" },
                { key: "job_role", label: "Job Role *", placeholder: "e.g., Systems Engineer" },
                { key: "salary", label: "Salary", placeholder: "e.g., 3.6 - 6 LPA" },
                { key: "eligibility", label: "Eligibility", placeholder: "e.g., B.Tech/MCA" },
                { key: "batch", label: "Batch", placeholder: "e.g., 2024, 2025" },
                { key: "experience", label: "Experience", placeholder: "e.g., Fresher" },
                { key: "location", label: "Location", placeholder: "e.g., Pan India" },
                { key: "last_date", label: "Last Date", placeholder: "e.g., 2025-07-15" },
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                    {field.label}
                  </label>
                  <input
                    type="text"
                    value={manualData[field.key as keyof typeof manualData]}
                    onChange={(e) =>
                      setManualData((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                    placeholder={field.placeholder}
                    className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
                  />
                </div>
              ))}
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
                Apply Link
              </label>
              <input
                type="url"
                value={manualData.apply_link}
                onChange={(e) => setManualData((prev) => ({ ...prev, apply_link: e.target.value }))}
                placeholder="https://careers.example.com/apply"
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
            </div>
          </div>
        )}
      </div>

      {/* Settings */}
      <div className="glass rounded-2xl p-6 md:p-8">
        <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">⚙️ Generation Settings</h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">LLM Provider (Script)</label>
            <select
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
            >
              <option value="openai">OpenAI (GPT-4o)</option>
              <option value="claude">Anthropic Claude</option>
              <option value="groq">Groq (Llama 3.3)</option>
              <option value="sambanova">SambaNova (Llama 3.3)</option>
              <option value="cerebras">Cerebras (Llama 3.1)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">Voice Provider</label>
            <select
              value={voiceProvider}
              onChange={(e) => setVoiceProvider(e.target.value)}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
            >
              <option value="openai">OpenAI TTS</option>
              <option value="elevenlabs">ElevenLabs</option>
              <option value="cartesia">Cartesia</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">Voice Select</label>
            <select
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              disabled={loadingVoices}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)] disabled:opacity-50"
            >
              {loadingVoices ? (
                <option value="">Loading voices...</option>
              ) : voicesList.length > 0 ? (
                voicesList.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.gender})
                  </option>
                ))
              ) : (
                <option value="">Default Voice</option>
              )}
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">Video Provider</label>
            <select
              value={videoProvider}
              onChange={(e) => setVideoProvider(e.target.value)}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
            >
              <option value="pexels">Pexels (Stock Video)</option>
              <option value="veo">Google Veo (AI Video)</option>
              <option value="kling">Kling AI (AI Video)</option>
              <option value="runway">Runway ML (AI Video)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">Language</label>
            <select
              value={voiceLanguage}
              onChange={(e) => setVoiceLanguage(e.target.value)}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
            >
              <option value="hinglish">Hinglish</option>
              <option value="hi">Hindi</option>
              <option value="en">English</option>
            </select>
          </div>
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
        onClick={handleSubmit}
        disabled={loading}
        className="w-full py-4 rounded-xl text-white font-bold text-lg transition-all duration-300 hover:scale-[1.01] hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
        style={{
          background: loading ? "var(--bg-tertiary)" : "var(--gradient-1)",
          boxShadow: loading ? "none" : "0 4px 20px var(--accent-glow)",
        }}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Processing...
          </span>
        ) : (
          "🚀 Generate Reel"
        )}
      </button>
    </div>
  );
}
