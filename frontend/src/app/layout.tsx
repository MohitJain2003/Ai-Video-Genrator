import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReelGen AI — Job Reel Generator",
  description:
    "Generate stunning faceless job opportunity reels with AI voiceover, captions, and B-roll visuals. Powered by Whisper, GPT-4o, and ElevenLabs.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside className="hidden lg:flex w-64 flex-col glass border-r border-[var(--border)] fixed h-full z-30">
            <div className="p-6 border-b border-[var(--border)]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
                  style={{ background: "var(--gradient-1)" }}>
                  🎬
                </div>
                <div>
                  <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                    ReelGen AI
                  </h1>
                  <p className="text-xs text-[var(--text-muted)]">Job Reel Generator</p>
                </div>
              </div>
            </div>

            <nav className="flex-1 p-4 space-y-1">
              <a
                href="/"
                className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all duration-200"
              >
                <span className="text-lg">🏠</span>
                Dashboard
              </a>
              <a
                href="/create"
                className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-[var(--text-primary)] bg-[var(--bg-hover)] border border-[var(--accent)] transition-all duration-200"
                style={{ boxShadow: "0 0 15px var(--accent-glow)" }}
              >
                <span className="text-lg">✨</span>
                Create Reel
              </a>
              <a
                href="/create-announcement"
                className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all duration-200"
              >
                <span className="text-lg">📣</span>
                Announcement Reel
              </a>
              <a
                href="/jobs"
                className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all duration-200"
              >
                <span className="text-lg">📋</span>
                Job History
              </a>
            </nav>

            <div className="p-4 border-t border-[var(--border)]">
              <div className="glass rounded-xl p-4 text-center">
                <p className="text-xs text-[var(--text-muted)] mb-2">Powered by</p>
                <div className="flex flex-wrap justify-center gap-1 text-[10px] text-[var(--text-secondary)]">
                  <span className="px-2 py-0.5 bg-[var(--bg-tertiary)] rounded-full">Whisper</span>
                  <span className="px-2 py-0.5 bg-[var(--bg-tertiary)] rounded-full">GPT-4o</span>
                  <span className="px-2 py-0.5 bg-[var(--bg-tertiary)] rounded-full">ElevenLabs</span>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1 lg:ml-64">
            {/* Mobile Header */}
            <header className="lg:hidden glass border-b border-[var(--border)] px-4 py-3 flex items-center justify-between sticky top-0 z-20">
              <div className="flex items-center gap-2">
                <span className="text-xl">🎬</span>
                <span className="font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                  ReelGen AI
                </span>
              </div>
              <nav className="flex gap-2 items-center">
                <a href="/" className="px-2.5 py-1 text-xs rounded bg-[var(--bg-tertiary)] text-[var(--text-secondary)]">
                  Home
                </a>
                <a href="/create" className="px-2.5 py-1 text-xs rounded text-white"
                  style={{ background: "var(--gradient-1)" }}>
                  + Reel
                </a>
                <a href="/create-announcement" className="px-2.5 py-1 text-xs rounded text-white"
                  style={{ background: "var(--gradient-1)" }}>
                  + Promo
                </a>
                <a href="/jobs" className="px-2.5 py-1 text-xs rounded bg-[var(--bg-tertiary)] text-[var(--text-secondary)]">
                  History
                </a>
              </nav>
            </header>

            <div className="p-4 md:p-8">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
